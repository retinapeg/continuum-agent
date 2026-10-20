import argparse
import json
from pathlib import Path
import signal
import threading
import urllib.request
from .common import ROOT, canonical
from .engine import Runtime
from .providers import CLIProvider, FixtureProvider
from .web import Dashboard


def main():
    p=argparse.ArgumentParser(description='CONTINUUM persistent local runtime')
    sub=p.add_subparsers(dest='command',required=True)
    start=sub.add_parser('start')
    start.add_argument('--directory',type=Path,default=ROOT/'.runtime/owner')
    start.add_argument('--provider',choices=['fixture','claude','codex'],default='fixture')
    start.add_argument('--model',default=None)
    start.add_argument('--routing-config',type=Path)
    start.add_argument('--policy',choices=list('ABCDE'),default='D')
    start.add_argument('--port',type=int,default=8787)
    start.add_argument('--reflection',type=float,default=60)
    start.add_argument('--quiet-hours',default=None,help='Comma-separated UTC hours, persisted per run')
    start.add_argument('--interruption-budget',type=int,default=None)
    start.add_argument('--seconds',type=float)
    start.add_argument('--resume',action='store_true',help='explicitly clear persisted pause/stop')
    start.add_argument('--fixtures',type=Path,default=ROOT/'fixtures/documents')
    for name in ('status','pause','resume','stop','message','goal','fact','events'):
        c=sub.add_parser(name);c.add_argument('--directory',type=Path,default=ROOT/'.runtime/owner');c.add_argument('--port',type=int,default=8787)
        if name in ('message','goal'): c.add_argument('text')
        if name=='fact': c.add_argument('subject');c.add_argument('content');c.add_argument('--supersedes')
    args=p.parse_args()
    if args.command=='start':
        if not args.directory.resolve().is_relative_to(ROOT):p.error('runtime must stay inside repository')
        provider=FixtureProvider() if args.provider=='fixture' else CLIProvider(args.provider,args.model or ('claude-sonnet-4-6' if args.provider=='claude' else 'gpt-6-luna'),args.directory/'provider-work')
        if args.routing_config:
            if not args.routing_config.resolve().is_relative_to(ROOT):p.error('routing config must be inside repository')
            from .routing import RoutedProvider
            provider=RoutedProvider(json.loads(args.routing_config.read_text()),args.directory/'router-work')
        elif args.provider!='fixture':provider.auth()
        runtime=Runtime(args.directory,provider,policy=args.policy,reflection=args.reflection,fixtures=args.fixtures)
        settings=runtime.db.get('notification_settings',{'quiet_hours':[],'hourly_budget':8})
        if args.quiet_hours is not None:
            hours=[int(x) for x in args.quiet_hours.split(',') if x]
            if any(h<0 or h>23 for h in hours):p.error('quiet hours must be 0..23 UTC')
            settings['quiet_hours']=hours
        if args.interruption_budget is not None:
            if args.interruption_budget<0:p.error('nonnegative interruption budget required')
            settings['hourly_budget']=args.interruption_budget
        runtime.db.set('notification_settings',settings)
        runtime.notifications.quiet=settings['quiet_hours'];runtime.notifications.budget=settings['hourly_budget']
        if args.resume:runtime.control('running')
        dashboard=Dashboard(runtime,port=args.port)
        thread=threading.Thread(target=dashboard.serve,name='continuum-http',daemon=True);thread.start()
        def stop(*_):runtime.control('stopped')
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        print(f'CONTINUUM http://127.0.0.1:{dashboard.server.server_port} | token file: {args.directory}/control-token',flush=True)
        print('Runtime starts with its persisted control state. Use --resume only to explicitly resume.',flush=True)
        try:runtime.serve(args.seconds)
        finally:dashboard.close();thread.join(3);runtime.close()
    else:
        token=(args.directory/'control-token').read_text()
        url=f'http://127.0.0.1:{args.port}'
        body=None;route=args.command
        if args.command in ('pause','resume','stop'):route='control';body={'action':{'pause':'paused','resume':'running','stop':'stopped'}[args.command]}
        elif args.command=='message':body={'text':args.text}
        elif args.command=='goal':body={'title':args.text}
        elif args.command=='fact':body={'subject':args.subject,'content':args.content,'supersedes':args.supersedes}
        req=urllib.request.Request(url+'/api/'+route,None if body is None else canonical(body).encode(),headers={'Authorization':'Bearer '+token,'Origin':url,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as response:print(json.dumps(json.load(response),indent=2))
