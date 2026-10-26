import argparse
import json
from pathlib import Path
from continuum.runtime.common import ROOT
from .engine import Experiment
from .world import scenario


def main():
    parser=argparse.ArgumentParser(description='Continuum 1.0: when is it worth observing?')
    sub=parser.add_subparsers(dest='command')
    serve=sub.add_parser('serve',help='open the local attention laboratory')
    serve.add_argument('--port',type=int,default=8787)
    serve.add_argument('--directory',type=Path,default=ROOT/'.runtime/lab')
    demo=sub.add_parser('compare',help='deterministic four-policy comparison')
    demo.add_argument('--scenario',choices=['change','no_change','stale','adversarial'],default='change')
    demo.add_argument('--seed',type=int,default=7)
    demo.add_argument('--budget',type=int,default=24)
    args=parser.parse_args()
    if args.command in ('serve',None):
        from .web import Dashboard
        dashboard=Dashboard(getattr(args,'directory',ROOT/'.runtime/lab'),getattr(args,'port',8787))
        print(f'Continuum Attention Laboratory: http://127.0.0.1:{dashboard.server.server_port}',flush=True)
        print('Deterministic classical estimator. No live model calls. Ctrl-C to stop.',flush=True)
        try:dashboard.serve()
        except KeyboardInterrupt:pass
        finally:
            # serve_forever has already stopped on KeyboardInterrupt.
            dashboard.server.server_close();dashboard.laboratory.close()
    else:
        experiment=Experiment(scenario(args.scenario,args.seed),name=args.scenario,
                              observation_budget=args.budget,inference_budget=args.budget)
        state=experiment.run_all()
        print(json.dumps({'world_fingerprint':state['world_fingerprint'],
                          'policies':{p['id']:p['metrics'] for p in state['policies']}},indent=2))

if __name__=='__main__':main()
