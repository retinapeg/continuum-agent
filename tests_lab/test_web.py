import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from continuum.lab.web import Dashboard
from continuum.runtime.common import ROOT


class WebAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.cache/tmp',prefix='lab-http-')
        self.dashboard=Dashboard(Path(self.tmp.name),port=0)
        self.thread=threading.Thread(target=self.dashboard.serve,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.dashboard.server.server_port}'
    def tearDown(self):
        self.dashboard.close();self.thread.join(3);self.tmp.cleanup()
    def request(self,path,body=None,origin=None):
        headers={'Content-Type':'application/json','Origin':origin or self.url}
        req=urllib.request.Request(self.url+path,headers=headers,data=None if body is None else json.dumps(body).encode())
        with urllib.request.urlopen(req,timeout=5) as response:return json.load(response)
    def test_no_early_truth_and_same_origin_controls(self):
        self.assertEqual(self.request('/api/state')['truth'],[])
        with self.assertRaises(urllib.error.HTTPError) as exc:self.request('/api/reveal',{})
        self.assertEqual(exc.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as exc:self.request('/api/step',{},origin='https://example.com')
        self.assertEqual(exc.exception.code,403)
        self.request('/api/step',{})
        state=self.request('/api/step',{})
        self.assertEqual(state['time'],.5)
        self.assertEqual(state['status'],'paused')
    def test_replay_preserves_world_and_records_new_database(self):
        self.request('/api/start',{'scenario':'stale','seed':8,'horizon':20,'noise':.2,'damping':.03})
        original=self.dashboard.laboratory.experiment.db.path
        self.request('/api/step',{})
        self.request('/api/inject',{'kind':'change','omega':1.5})
        fingerprint=self.dashboard.laboratory.experiment.world.fingerprint
        replay=self.request('/api/replay',{})
        self.assertEqual(replay['mode'],'replay')
        self.assertEqual(fingerprint,self.dashboard.laboratory.experiment.world.fingerprint)
        self.assertNotEqual(original,self.dashboard.laboratory.experiment.db.path)
        self.assertTrue(original.exists())
    def test_invalid_configuration_does_not_replace_run(self):
        before=self.request('/api/state')['run_id']
        for body in ({'horizon':-1},{'noise':0},{'seed':'bad'},{'observation_budget':501}):
            with self.assertRaises(urllib.error.HTTPError):self.request('/api/start',body)
        self.assertEqual(before,self.request('/api/state')['run_id'])
