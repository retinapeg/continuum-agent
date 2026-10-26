import dataclasses
import math
import unittest
from continuum.lab.world import Change, World, WorldConfig, advance, scenario
from continuum.lab.policies import PolicyInput, Scheduler
from continuum.lab.estimator import Kalman

class PhysicalWorldTests(unittest.TestCase):
    def test_exact_solution_and_partition(self):
        x,v=advance(1,0,1,0,math.pi/2)
        self.assertAlmostEqual(x,0,places=12)
        self.assertAlmostEqual(v,-1,places=12)
        direct=advance(1,.2,.8,.03,3)
        first=advance(1,.2,.8,.03,1)
        split=advance(*first,.8,.03,2)
        for a,b in zip(direct,split): self.assertAlmostEqual(a,b,places=12)

    def test_hidden_change_without_observation(self):
        a=World(WorldConfig(changes=(Change(20,1.5,.02),)))
        b=World(WorldConfig())
        self.assertEqual(a.truth()[:40],b.truth()[:40])
        self.assertNotEqual(a.truth()[50]['x'],b.truth()[50]['x'])
        self.assertEqual(a.truth()[-1]['time'],120)

    def test_replay_and_counterfactual_noise(self):
        a=World(scenario('change',3));b=World(WorldConfig.from_dict(a.config.to_dict()))
        a.measure(17);a.measure(3)
        self.assertEqual(a.measure(22),b.measure(22))
        self.assertEqual(a.truth(),b.truth())
        self.assertEqual(a.fingerprint,b.fingerprint)
        self.assertNotEqual(a.measure(22),World(scenario('change',4)).measure(22))

    def test_stale_and_contradictory_evidence(self):
        w=World(scenario('stale',7));k=Kalman();k.propagate(50)
        old=k.public()
        obs=w.measure(100)
        self.assertEqual(obs['measured_at'],38)
        self.assertEqual(k.update(obs),'stale-rejected')
        self.assertEqual(old,k.public())
        k=Kalman();obs={'measured_at':0,'value':50,'noise_std':.08}
        self.assertEqual(k.update(obs),'contradiction-rejected')
        self.assertEqual(k.x,1)

    def test_information_boundary(self):
        fields={f.name for f in dataclasses.fields(PolicyInput)}
        self.assertFalse(fields & {'seed','truth','changes','omega','damping','world','config'})
        e=PolicyInput(0,120,.5,1,0,.04,.1,None,None,24,24,24,(),(30,60,90))
        with self.assertRaises(dataclasses.FrozenInstanceError): e.x=9
        for policy in ('periodic','event_deadline','original_hybrid','uncertainty'):
            self.assertIn('observe',[a.kind for a in Scheduler(policy).decide(e)])

    def test_no_change_and_invalid_config(self):
        self.assertEqual(scenario('no_change').changes,())
        for kwargs in ({'noise':0},{'dt':0},{'damping':-1},{'horizon':float('nan')},
                       {'changes':(Change(1.2,1,.02),)}):
            with self.assertRaises(ValueError):WorldConfig(**kwargs)
