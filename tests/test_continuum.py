import math
from pathlib import Path
import sqlite3
import tempfile
import unittest

from continuum.agents import Agent
from continuum.benchmark import benchmark, paired_interval
from continuum.model import ContinuousState, Event, Goal, Scenario
from continuum.scenarios import REGIMES, generate
from continuum.simulation import run
from continuum.storage import Store


class StateTests(unittest.TestCase):
    def test_exact_decay_and_fractional_time(self):
        state = ContinuousState(activation=2)
        state.advance(0.5)
        self.assertAlmostEqual(state.activation, 2 * math.exp(-0.075))

    def test_partition_invariance(self):
        a, b = ContinuousState(activation=3), ContinuousState(activation=3)
        a.advance(12)
        for t in (0.5, 2, 7, 12):
            b.advance(t)
        self.assertAlmostEqual(a.activation, b.activation)

    def test_reject_time_reversal(self):
        with self.assertRaises(ValueError):
            ContinuousState(at=2).advance(1)

    def test_activation_changes_idle_schedule(self):
        calm, active = ContinuousState(), ContinuousState(activation=5)
        self.assertLess(active.idle_interval(), calm.idle_interval())


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.addCleanup(self.store.close)

    def test_duplicate_is_noop(self):
        event = Event('a', 1, 'fact', 'x', 'one')
        self.assertTrue(self.store.ingest(event))
        before = self.store.state()
        self.assertFalse(self.store.ingest(event))
        self.assertEqual(self.store.state(), before)

    def test_conflicting_id_rejected(self):
        self.store.ingest(Event('a', 1, 'fact', 'x', 'one'))
        with self.assertRaisesRegex(ValueError, 'conflicting'):
            self.store.ingest(Event('a', 1, 'fact', 'x', 'two'))
        self.assertEqual(self.store.recall('x', 1)[0], 'one')

    def test_revision_expiry_and_confidence(self):
        self.store.ingest(Event('a', 1, 'fact', 'x', 'one'))
        self.store.ingest(Event('b', 2, 'fact', 'x', 'two', expires=4))
        self.assertEqual(self.store.recall('x', 3)[0], 'two')
        self.assertLess(self.store.recall('x', 3)[1], 1)
        self.assertEqual(self.store.recall('x', 4), (None, 0))
        self.assertEqual(self.store.recall('absent', 4), (None, 0))

    def test_failed_ingestion_rolls_back(self):
        self.store.ingest(Event('a', 1, 'goal', 'g', ready=2, deadline=4))
        before = self.store.state()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.ingest(Event('b', 2, 'goal', 'g', ready=3, deadline=5))
        self.assertEqual(self.store.state(), before)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 1)

    def test_unknown_event_rejected(self):
        with self.assertRaises(ValueError):
            self.store.ingest(Event('a', 1, 'unknown', 'x'))
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)

    def test_out_of_order_event_rejected(self):
        self.store.ingest(Event('a', 3, 'fact', 'x', 'new'))
        with self.assertRaises(ValueError):
            self.store.ingest(Event('b', 2, 'fact', 'x', 'old'))
        self.assertEqual(self.store.recall('x', 3)[0], 'new')

    def test_cancel_blocks_actions(self):
        self.store.ingest(Event('a', 1, 'goal', 'g', ready=2, deadline=4))
        self.store.ingest(Event('b', 2, 'cancel', 'g'))
        self.assertEqual(Agent('adaptive', self.store).candidates(2), [])
        with self.assertRaises(ValueError):
            self.store.attempt('g', 2, True)

    def test_retry_cooldown_and_no_duplicate_success(self):
        self.store.ingest(Event('a', 1, 'goal', 'g', ready=2, deadline=10))
        agent = Agent('adaptive', self.store)
        self.store.attempt('g', 2, False)
        self.assertEqual(agent.candidates(5), [])
        self.assertEqual(agent.candidates(6), ['g'])
        self.store.attempt('g', 6, True)
        self.assertEqual(agent.candidates(7), [])

    def test_action_time_prevents_late_ingestion(self):
        self.store.ingest(Event('a', 1, 'goal', 'g', ready=2, deadline=10))
        self.store.attempt('g', 5, False)
        with self.assertRaises(ValueError):
            self.store.ingest(Event('b', 4, 'fact', 'x', 'late'))
        self.assertEqual(self.store.state().at, 5)

    def test_failed_action_preserves_state(self):
        before = self.store.state()
        with self.assertRaises(ValueError):
            self.store.attempt('missing', 5, True)
        self.assertEqual(self.store.state(), before)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0], 0)

    def test_reopen_preserves_memory_state_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.sqlite'
            first = Store(path)
            first.ingest(Event('a', 1, 'fact', 'x', 'durable'))
            first.ingest(Event('b', 2, 'goal', 'g', ready=3, deadline=10))
            first.attempt('g', 3, False)
            expected = first.checkpoint(4)
            first.close()
            second = Store(path)
            try:
                self.assertEqual(second.state(), expected)
                self.assertEqual(second.recall('x', 4)[0], 'durable')
                self.assertEqual(Agent('adaptive', second).next_wake(4), 7)
                self.assertEqual(second.db.execute('SELECT COUNT(*) FROM audit').fetchone()[0], 1)
            finally:
                second.close()


class SimulationTests(unittest.TestCase):
    def scenario(self, events, goals, horizon=12):
        return Scenario('hand_checked', 0, horizon, tuple(events), tuple(goals))

    def test_quiet_goal_hand_calculated(self):
        scenario = self.scenario([Event('a', 1, 'goal', 'g', ready=3, deadline=4)], [Goal('g', 3, 4)])
        self.assertEqual(run(scenario, 'reactive').completed, 0)
        self.assertEqual(run(scenario, 'periodic').completed, 0)
        adaptive = run(scenario, 'adaptive')
        self.assertEqual(adaptive.completed, 1)
        self.assertEqual(adaptive.latency_mean, 0)
        self.assertEqual(adaptive.intervention_precision, 1)

    def test_false_positive_and_retry(self):
        scenario = self.scenario([Event('a', 1, 'goal', 'g', ready=3, deadline=9)], [Goal('g', 5, 9)])
        result = run(scenario, 'adaptive')
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.intervention_precision, 0.5)
        self.assertEqual(result.latency_mean, 2)

    def test_periodic_can_beat_adaptive_precision(self):
        scenario = self.scenario([Event('a', 1, 'goal', 'g', ready=3, deadline=9)], [Goal('g', 5, 9)])
        self.assertGreater(run(scenario, 'periodic').intervention_precision,
                           run(scenario, 'adaptive').intervention_precision)

    def test_deadline_is_inclusive(self):
        scenario = self.scenario([Event('a', 1, 'goal', 'g', ready=6, deadline=6)], [Goal('g', 6, 6)])
        self.assertEqual(run(scenario, 'periodic').completed, 1)

    def test_cancellation_precedes_same_time_decision(self):
        scenario = self.scenario([Event('a', 1, 'goal', 'g', ready=6, deadline=8),
                                  Event('b', 6, 'cancel', 'g')], [Goal('g', 6, 8, 6)])
        result = run(scenario, 'periodic')
        self.assertEqual(result.attempts, 0)
        self.assertIsNone(result.intervention_precision)
        self.assertIsNone(result.latency_mean)
        self.assertEqual(result.feasible_goals, 0)

    def test_all_policies_same_event_aligned_completion(self):
        scenario = self.scenario([Event('a', 6, 'goal', 'g', ready=6, deadline=10)], [Goal('g', 6, 10)])
        for policy in ('reactive', 'periodic', 'adaptive'):
            self.assertEqual(run(scenario, policy).completed, 1)

    def test_deterministic_scenarios_and_runs(self):
        for regime in REGIMES:
            scenario = generate(regime, 8)
            self.assertEqual(scenario, generate(regime, 8))
            self.assertEqual(run(scenario, 'adaptive'), run(scenario, 'adaptive'))

    def test_memory_control_all_policies(self):
        for policy in ('reactive', 'periodic', 'adaptive'):
            self.assertEqual(run(generate('noisy_stream', 2), policy).memory_accuracy, 1)

    def test_database_contains_complete_trace_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'demo.sqlite')
            result = run(generate('quiet_deadlines', 0), 'adaptive', path)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE kind='decision'").fetchone()[0], result.decisions)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE kind='action'").fetchone()[0], result.attempts)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE kind='result'").fetchone()[0], 1)
            with self.assertRaisesRegex(ValueError, 'empty database'):
                run(generate('quiet_deadlines', 0), 'adaptive', path)

    def test_cost_identity(self):
        scenario = generate('wide_windows', 1)
        result = run(scenario, 'periodic')
        self.assertAlmostEqual(result.cost_units, len(scenario.events) * .01 + result.decisions * .1 + result.attempts)


class BenchmarkTests(unittest.TestCase):
    def test_constant_paired_interval(self):
        self.assertEqual(paired_interval([2, 2, 2]), {'mean': 2, 'low': 2, 'high': 2})

    def test_reproducible_artifacts(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            benchmark(Path(a), 2)
            benchmark(Path(b), 2)
            for name in ('runs.csv', 'summary.json', 'manifest.json'):
                self.assertEqual((Path(a) / name).read_bytes(), (Path(b) / name).read_bytes())

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError):
            generate('invalid', 0)
        with self.assertRaises(ValueError):
            paired_interval([])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                benchmark(Path(tmp), 1)


if __name__ == '__main__':
    unittest.main()
