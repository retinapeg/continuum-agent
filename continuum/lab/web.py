"""Loopback experiment UI. All controls operate the same durable simulation."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import threading
import uuid
from urllib.parse import urlparse
from continuum.runtime.common import ROOT, canonical, confined
from .engine import Experiment
from .world import scenario


class Laboratory:
    def __init__(self, directory):
        self.directory=Path(directory).resolve()
        if not self.directory.is_relative_to(ROOT):raise ValueError('laboratory data must stay inside repository')
        self.directory.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.active=self.directory/'active.json'
        self.experiment=None
        if self.active.exists():
            path=confined(self.directory,json.loads(self.active.read_text())['database'],exists=True)
            self.experiment=Experiment(database=path)
        else:self.start({})
        self.stop=threading.Event()
        self.worker=threading.Thread(target=self._loop,daemon=True)
        self.worker.start()

    def _new(self, config, *, name, observations, inferences, replay=None):
        path=self.directory/'runs'/uuid.uuid4().hex/'lab.sqlite'
        experiment=Experiment(config,name=name,observation_budget=observations,inference_budget=inferences,database=path)
        if replay:
            experiment.public_events=list(replay.public_events)
            experiment.injections=list(replay.injections)
            experiment.parameters=replay.parameters
            # Reuse exactly the selected policy parameters as well as the world.
            for new,old in zip(experiment.policies,replay.policies):
                new.scheduler.period_scale=old.scheduler.period_scale
                new.scheduler.threshold=old.scheduler.threshold
            experiment.mode='replay'
            experiment._persist([])
        previous=self.experiment
        self.experiment=experiment
        temp=self.active.with_suffix('.tmp')
        temp.write_text(canonical({'database':str(path.relative_to(self.directory))}))
        temp.replace(self.active)
        if previous:previous.close()
        return self.state()

    def start(self, body):
        with self.lock:
            seed=body.get('seed',7)
            if type(seed) is not int or not 0<=seed<=999999:raise ValueError('seed must be an integer 0..999999')
            values={key:float(body.get(key,default)) for key,default in [('horizon',120),('noise',.08),('damping',.015)]}
            if not all(math.isfinite(v) for v in values.values()) or not 20<=values['horizon']<=300 or not .01<=values['noise']<=1 or not 0<=values['damping']<=.2:
                raise ValueError('invalid horizon, noise or damping')
            return self._new(scenario(body.get('scenario','change'),seed,**values),name=body.get('scenario','change'),
                             observations=body.get('observation_budget',24),inferences=body.get('inference_budget',24))

    def replay(self):
        with self.lock:
            old=self.experiment
            return self._new(old.world.config,name=old.config['scenario'],observations=old.config['observation_budget'],
                             inferences=old.config['inference_budget'],replay=old)

    def state(self):
        state=self.experiment.state()
        reports=sorted((ROOT/'experiments/v1').glob('live-pilot-*/report.json'))
        if reports:
            report=json.loads(reports[-1].read_text())
            state['live']={'status':'recorded','message':f"Recorded live pilot: {report['successful_calls']}/{report['attempted_calls']} successful calls; {report['failed_calls']} failed. This interactive run remains deterministic.",
                           'report':str(reports[-1].relative_to(ROOT))}
        return state

    def _loop(self):
        while not self.stop.wait(.1):
            with self.lock:
                if self.experiment.status=='running':
                    try:
                        for _ in range(self.experiment.speed):
                            self.experiment.step(return_state=False)
                            if self.experiment.status=='completed':break
                    except Exception as exc:
                        self.experiment.status='paused'
                        self.experiment.db.event('lab.worker.failed',{'error':str(exc)},status='failed')
                        self.experiment._persist([])

    def close(self):
        self.stop.set();self.worker.join(5)
        self.experiment.close()


class Dashboard:
    def __init__(self,directory,port=8787):
        laboratory=Laboratory(directory)
        self.laboratory=laboratory
        dashboard=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def send(self,code,value,mime='application/json'):
                data=(canonical(value) if mime=='application/json' else value).encode()
                self.send_response(code)
                self.send_header('Content-Type',mime+'; charset=utf-8')
                self.send_header('Content-Length',str(len(data)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers();self.wfile.write(data)
            def allowed(self,write=False):
                host=f'127.0.0.1:{dashboard.server.server_port}'
                return self.headers.get('Host')==host and (not write or self.headers.get('Origin')=='http://'+host)
            def do_GET(self):
                if not self.allowed():return self.send(403,{'error':'loopback host required'})
                path=urlparse(self.path).path
                if path in ('/','/app.js','/style.css'):
                    name,mime={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}[path]
                    return self.send(200,(Path(__file__).parent/'ui'/name).read_text(),mime)
                if path=='/api/state':
                    with laboratory.lock:return self.send(200,laboratory.state())
                return self.send(404,{'error':'not found'})
            def do_POST(self):
                if not self.allowed(True):return self.send(403,{'error':'same-origin loopback control required'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=4096 or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                        raise ValueError('bounded JSON object required')
                    body=json.loads(self.rfile.read(size),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('finite JSON required')))
                    if not isinstance(body,dict):raise ValueError('JSON object required')
                    with laboratory.lock:
                        path=urlparse(self.path).path
                        if path=='/api/start':laboratory.start(body)
                        elif path=='/api/replay':laboratory.replay()
                        elif path=='/api/control':laboratory.experiment.control(body['action'],body.get('speed',4))
                        elif path=='/api/step':
                            laboratory.experiment.control('pause')
                            laboratory.experiment.step(return_state=False)
                        elif path=='/api/reveal':laboratory.experiment.reveal()
                        elif path=='/api/inject':laboratory.experiment.inject(body['kind'],body.get('omega',1.4),body.get('damping',.03))
                        else:return self.send(404,{'error':'not found'})
                        self.send(200,laboratory.state())
                except (ValueError,KeyError,TypeError) as exc:self.send(400,{'error':str(exc)[:300]})
        try:self.server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        except BaseException:
            laboratory.close();raise
        self.server.daemon_threads=True
    def serve(self):self.server.serve_forever(poll_interval=.1)
    def close(self):
        self.server.shutdown();self.server.server_close();self.laboratory.close()
