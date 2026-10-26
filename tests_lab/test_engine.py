import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from continuum.lab.engine import Experiment
from continuum.lab.world import scenario
from continuum.lab.policies import Action
from continuum.runtime.memory import Memory

class ExperimentTests(unittest.TestCase):
    def test_policy_replay_same_world_and_different_information(self):
        a=Experiment(observation_budget=12,inference_budget=12);b=Experiment(observation_budget=12,inference_budget=12)
        self.assertEqual(a.run_all(),b.run_all())
        schedules=[]
        for p in a.policies:
            schedules.append(tuple(r['time'] for r in p.history if r['observation']))
            self.assertEqual(p.metrics['prediction_count'],239)
            self.assertLessEqual(p.budget['observations'],12)
            self.assertLessEqual(p.budget['inferences'],12)
        self.assertGreater(len(set(schedules)),1)
        self.assertEqual(a.world.fingerprint,b.world.fingerprint)

    def test_hidden_truth_not_in_public_state_before_reveal(self):
        a=Experiment();a.step()
        state=a.state()
        self.assertEqual(state['truth'],[])
        self.assertNotIn('changes',json.dumps(state))
        self.assertTrue(all(p['metrics'] is None for p in state['policies']))
        with self.assertRaises(ValueError):a.reveal()
        a.run_all();self.assertEqual(a.state()['truth'],[])
        self.assertEqual(len(a.reveal()['truth']),241)

    def test_budget_boundary_enforced_even_for_bad_policy(self):
        a=Experiment(observation_budget=0,inference_budget=0)
        a.policies[0].scheduler.decide=lambda e:(Action('observe'),Action('think'))
        with patch.object(a.world,'measure',side_effect=AssertionError('unauthorized observation')):
            a.step()
        self.assertEqual(a.policies[0].budget['observations'],0)
        self.assertEqual(a.policies[0].failures,2)
        self.assertEqual(a.policies[0].events[0]['status'],'failed')

    def test_restart_and_duplicate_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'lab.sqlite'
            a=Experiment(database=path)
            for _ in range(25):a.step(return_state=False)
            before=a.state();receipt=a.policies[0].events[0]
            n=len(a.db.rows('SELECT id FROM operations'))
            a._persist([receipt]);self.assertEqual(n,len(a.db.rows('SELECT id FROM operations')))
            a.close()
            b=Experiment(database=path)
            self.assertEqual(before,b.state())
            resumed=b.run_all();b.close()
            fresh=Experiment().run_all()
            self.assertEqual(resumed,fresh)

    def test_failed_checkpoint_rolls_back_memory_and_database(self):
        with tempfile.TemporaryDirectory() as d:
            a=Experiment(database=Path(d)/'lab.sqlite');before=a.state()
            with patch.object(a.db,'event',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):a.step()
            self.assertEqual(before,a.state())
            self.assertEqual(a.db.rows('SELECT * FROM operations'),[])
            a.close()

    def test_injection_is_hidden_and_replayable(self):
        a=Experiment()
        for _ in range(20):a.step(return_state=False)
        old=a.world.truth()
        a.inject('change',omega=1.7)
        self.assertEqual(old[:20],a.world.truth()[:20])
        self.assertNotEqual(old[25]['x'],a.world.truth()[25]['x'])
        self.assertEqual(a.state()['truth'],[])
        b=Experiment(a.world.config)
        self.assertEqual(a.run_all()['policies'],b.run_all()['policies'])

    def test_stale_failures_remain_in_metrics_and_receipts(self):
        a=Experiment(scenario('stale'),name='stale');a.run_all()
        p=a.policies[0]
        self.assertGreater(p.metrics['failures'],0)
        self.assertTrue(any(e['status']=='stale-rejected' for e in p.events))

    def test_memory_proposals_cannot_override_confirmed_measurements(self):
        with tempfile.TemporaryDirectory() as d:
            a=Experiment(database=Path(d)/'lab.sqlite');memory=Memory(a.db)
            first=memory.add('fact','sensor calibration','value 1',0,['sensor-1'],confirmed=True)
            memory.add('fact','sensor calibration','value 5',1,['model-1'],supersedes=first)
            rows=memory.retrieve('sensor calibration',2,confirmed_only=True)
            self.assertEqual([x['id'] for x in rows],[first])
            memory.add('fact','sensor calibration','value 2',2,['sensor-2'],confirmed=True)
            self.assertEqual(memory.retrieve('sensor calibration',3,confirmed_only=True),[])
            a.close()
