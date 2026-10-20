import argparse
import json
from pathlib import Path
from .agents import POLICIES
from .benchmark import benchmark
from .scenarios import REGIMES, generate
from .simulation import run


def main() -> None:
    parser = argparse.ArgumentParser(description='CONTINUUM deterministic autonomy experiments')
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo', help='run one scenario; optional durable SQLite audit')
    demo.add_argument('--policy', choices=POLICIES, default='adaptive')
    demo.add_argument('--scenario', choices=REGIMES, default='quiet_deadlines')
    demo.add_argument('--seed', type=int, default=0)
    demo.add_argument('--db', default=':memory:', help='new/empty SQLite database path')
    bench = commands.add_parser('benchmark', help='write CSV, summary, and provenance manifest')
    bench.add_argument('--seeds', type=int, default=30)
    bench.add_argument('--output', type=Path, default=Path('results'))
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            result = run(generate(args.scenario, args.seed), args.policy, args.db).to_dict()
        else:
            result = benchmark(args.output, args.seeds)['means']['all']
    except (ValueError, OSError) as exc:
        parser.exit(2, f'error: {exc}\n')
    print(json.dumps(result, indent=2, sort_keys=True))
