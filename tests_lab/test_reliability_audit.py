"""Independent regressions for evidence charging and checkpoint ownership."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from continuum.lab.engine import Experiment
from continuum.lab.policies import Action
from continuum.lab.world import World, WorldConfig, scenario
from continuum.runtime.common import ROOT


class ReliabilityAuditTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / '.cache/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'lab.sqlite'

    def experiment(self, **kwargs):
        experiment = Experiment(database=self.path, **kwargs)
        self.addCleanup(experiment.close)
        return experiment

    def test_one_owner_per_database_and_release_on_close(self):
        first = self.experiment()
        first.step()
        with self.assertRaises(RuntimeError):
            Experiment(database=self.path)
        before = first.state()
        first.close()
        second = self.experiment()
        self.assertEqual(before, second.state())

    def test_invalid_initialization_releases_database_lock(self):
        with self.assertRaises(ValueError):
            Experiment(database=self.path, observation_budget=-1)
        self.experiment().step()

    def test_running_restart_is_paused_and_persisted(self):
        first = self.experiment()
        first.step()
        first.control('resume')
        first.close()
        second = self.experiment()
        self.assertEqual(second.status, 'paused')
        self.assertEqual(second.db.get('lab_checkpoint')['status'], 'paused')

    def test_duplicate_observe_and_think_do_not_double_charge(self):
        experiment = self.experiment(observation_budget=3, inference_budget=3)
        policy = experiment.policies[0]
        policy.scheduler.decide = lambda _: (Action('observe'), Action('observe'),
                                              Action('think'), Action('think'), Action('predict'))
        with patch.object(experiment.world, 'measure', wraps=experiment.world.measure) as measure:
            experiment.step()
            # Each of the four policy conditions samples once, including this one.
            self.assertEqual(measure.call_count, 4)
        self.assertEqual(policy.budget['observations'], 1)
        self.assertEqual(policy.budget['inferences'], 1)
        self.assertEqual(sum(event['kind'] == 'observe' for event in policy.events), 1)
        self.assertEqual(sum(event['kind'] == 'think' for event in policy.events), 1)
        self.assertEqual(len(experiment.db.rows("SELECT * FROM operations WHERE kind='observe'")), 4)

    def test_explicit_alert_has_one_real_receipt_and_action_charge(self):
        experiment = self.experiment()
        policy = experiment.policies[0]
        policy.scheduler.decide = lambda _: (Action('alert', 'public policy decision'), Action('alert'))
        experiment.step()
        self.assertEqual(policy.budget['actions'], 1)
        self.assertEqual(policy.alerts, [0])
        receipts = [event for event in policy.events if event['kind'] == 'alert']
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]['status'], 'succeeded')
        self.assertEqual(receipts[0]['refs'], [])
        policy.execute_alert(Action('alert'), 0, 0)
        self.assertEqual(policy.budget['actions'], 1)

    def test_failed_control_and_injection_restore_all_state(self):
        experiment = self.experiment()
        experiment.step()
        before = copy.deepcopy(experiment._checkpoint())
        for action in (lambda: experiment.control('resume', speed=9),
                       lambda: experiment.inject('event'),
                       lambda: experiment.inject('change', omega=1.9)):
            with patch.object(experiment.db, 'set', side_effect=OSError('controlled checkpoint failure')):
                with self.assertRaises(OSError):
                    action()
            self.assertEqual(experiment._checkpoint(), before)
            self.assertEqual(experiment.db.get('lab_checkpoint')['status'], 'paused')

    def test_failed_reveal_does_not_reveal_truth(self):
        experiment = self.experiment(config=scenario('no_change', horizon=2))
        experiment.run_all()
        before = experiment.state()
        with patch.object(experiment.db, 'set', side_effect=OSError('controlled checkpoint failure')):
            with self.assertRaises(OSError):
                experiment.reveal()
        self.assertEqual(experiment.state(), before)
        self.assertEqual(experiment.state()['truth'], [])

    def test_simulator_supports_other_grids_but_experiment_rejects_them(self):
        config = WorldConfig(dt=.3, horizon=12)
        self.assertEqual(World(config).truth()[-1]['time'], 12)
        with self.assertRaisesRegex(ValueError, 'forecast horizon'):
            Experiment(config)
        accepted = Experiment(WorldConfig(dt=.25, horizon=12))
        self.assertTrue(accepted.run_all()['policies'][0]['metrics']['prediction_count'])
