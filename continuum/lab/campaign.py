"""Frozen deterministic scheduling comparisons; never invokes a model provider."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import random
import statistics
import tarfile
import time
import traceback

from .engine import PolicyRun
from .policies import LABELS
from .world import World, WorldConfig, scenario

ROOT = Path(__file__).resolve().parents[2]
DEV_SEEDS = tuple(range(4))
HELDOUT_SEEDS = tuple(range(1000, 1012))
SCENARIOS = ('no_change', 'change', 'stale', 'adversarial')
BUDGETS = (12, 24)
CANDIDATES = {
    'periodic': tuple({'period_scale': value} for value in (.75, 1., 1.5)),
    'event_deadline': tuple({'period_scale': value} for value in (.75, 1., 1.5)),
    'original_hybrid': tuple({'period_scale': value} for value in (.75, 1., 1.5)),
    'uncertainty': tuple({'threshold': value} for value in (.015, .035, .08)),
}
PUBLIC_EVENTS = (19., 49., 89.)
DEADLINE_FRACTIONS = (.25, .5, .75)
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261026


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_hashes():
    paths = list((ROOT / 'continuum').rglob('*.py')) + list((ROOT / 'tests_lab').rglob('*.py'))
    paths += [ROOT / 'pyproject.toml', ROOT / 'docs' / 'PROTOCOL_V1.md']
    return {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in sorted(paths) if path.is_file()}


def _directory(directory, *, fresh=False):
    path = Path(directory).expanduser().resolve()
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError('campaign directory must be a child of this repository')
    if fresh:
        path.mkdir(parents=True, exist_ok=False)
    elif not path.is_dir():
        raise ValueError('campaign directory does not exist')
    return path


def write_json(path, value):
    with path.open('x', encoding='utf-8') as output:
        output.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


@contextmanager
def trace_writer(path):
    with path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding='utf-8') as output:
                yield output


def world_cases(seeds, scenarios, budgets):
    for seed in seeds:
        for name in scenarios:
            config = scenario(name, seed)
            for budget in budgets:
                yield {'scenario': name, 'seed': seed, 'observation_budget': budget,
                       'inference_budget': budget, 'world_config': config.to_dict(),
                       'public_events': list(PUBLIC_EVENTS),
                       'deadlines': [config.horizon * fraction for fraction in DEADLINE_FRACTIONS]}


def evaluate_unit(case, policy, parameters, *, unit_id):
    """Direct PolicyRun execution avoids dashboard copies and persistence overhead."""
    started = time.monotonic()
    run = world = None
    result = {'unit_id': unit_id, 'policy': policy, 'scenario': case['scenario'],
              'seed': case['seed'], 'observation_budget': case['observation_budget'],
              'inference_budget': case['inference_budget'], 'parameters': parameters,
              'world_config_sha256': digest(canonical(case['world_config']).encode())}
    trace = {'unit_id': unit_id, 'world_config': case['world_config'], 'public_events': case['public_events'],
             'deadlines': case['deadlines'], 'policy': policy, 'parameters': parameters}
    try:
        config = WorldConfig.from_dict(case['world_config'])
        world = World(config)
        run = PolicyRun(policy, config, case['observation_budget'], case['inference_budget'], parameters)
        for tick in range(round(config.horizon / config.dt) + 1):
            at = round(tick * config.dt, 9)
            events = ['public inspection event'] if at in case['public_events'] else []
            run.step(world, tick, events, case['deadlines'])
        run.finish(world)
        result.update(status='succeeded', metrics=run.metrics, world_fingerprint=world.fingerprint)
    except Exception as exc:
        # A unit exception invalidates aggregate comparisons, but never removes
        # the unit or its already emitted receipts from the evidence.
        result.update(status='failed', metrics=None,
                      error={'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
    result['elapsed_seconds'] = time.monotonic() - started
    trace.update(status=result['status'], history=run.history if run else [],
                 receipts=run.events if run else [], alerts=run.alerts if run else [],
                 resources=run.budget if run else {}, truth=world.truth() if world else [],
                 error=result.get('error'))
    return result, trace


def develop(directory):
    directory = _directory(directory, fresh=True)
    sources = source_hashes()
    rows, candidates, selected = [], [], {}
    cases = list(world_cases(DEV_SEEDS, SCENARIOS, BUDGETS))
    with (directory / 'results.jsonl').open('x', encoding='utf-8') as output, trace_writer(directory / 'traces.jsonl.gz') as traces:
        for policy in LABELS:
            for index, parameters in enumerate(CANDIDATES[policy]):
                candidate_rows = []
                for case_index, case in enumerate(cases):
                    row, trace = evaluate_unit(case, policy, parameters, unit_id=f'dev:{policy}:{index}:{case_index}')
                    output.write(canonical(row) + '\n')
                    traces.write(canonical(trace) + '\n')
                    rows.append(row)
                    candidate_rows.append(row)
                valid = all(row['status'] == 'succeeded' for row in candidate_rows)
                candidates.append({'policy': policy, 'candidate_index': index, 'parameters': parameters,
                                   'units': len(candidate_rows), 'valid': valid,
                                   'mean_rmse': statistics.fmean(row['metrics']['rmse'] for row in candidate_rows) if valid else None})
            eligible = [candidate for candidate in candidates if candidate['policy'] == policy and candidate['valid']]
            if eligible:
                best = min(eligible, key=lambda item: (item['mean_rmse'], item['candidate_index']))
                selected[policy] = best['parameters']
    valid = all(row['status'] == 'succeeded' for row in rows) and source_hashes() == sources
    manifest = {'stage': 'development', 'valid': valid, 'primary_metric': 'mean fixed-grid one-second-ahead RMSE',
                'seeds': list(DEV_SEEDS), 'scenarios': list(SCENARIOS), 'budgets': list(BUDGETS),
                'source_hashes': sources, 'candidates': candidates, 'selected_parameters': selected,
                'tie_break': 'first declared candidate', 'units': len(rows),
                'runtime_failures': sum(row['status'] != 'succeeded' for row in rows),
                'results_sha256': digest((directory / 'results.jsonl').read_bytes()),
                'traces_sha256': digest((directory / 'traces.jsonl.gz').read_bytes())}
    write_json(directory / 'development.json', manifest)
    return manifest


def freeze(directory, development):
    development = _directory(development)
    dev = json.loads((development / 'development.json').read_text())
    sources = source_hashes()
    if not dev['valid'] or dev['source_hashes'] != sources:
        raise ValueError('development invalid or source changed; rerun development in a new directory')
    if dev['seeds'] != list(DEV_SEEDS) or dev['scenarios'] != list(SCENARIOS) or dev['budgets'] != list(BUDGETS):
        raise ValueError('development split differs from declared protocol')
    for filename, key in (('results.jsonl', 'results_sha256'), ('traces.jsonl.gz', 'traces_sha256')):
        if digest((development / filename).read_bytes()) != dev[key]:
            raise ValueError('development evidence changed')
    if set(dev['selected_parameters']) != set(LABELS):
        raise ValueError('all schedulers require development selections')
    directory = _directory(directory, fresh=True)
    protocol = {
        'version': 'continuum-lab-v1', 'mode': 'deterministic', 'stage': 'heldout',
        'hypothesis': 'uncertainty-aware scheduling lowers prediction RMSE relative to strong periodic and event/deadline baselines under equal caps',
        'primary_metric': 'mean per-episode fixed-grid one-second-ahead RMSE; lower is better',
        'policies': list(LABELS), 'parameters': dev['selected_parameters'],
        'development': dev, 'source_hashes': sources,
        'heldout_seeds': list(HELDOUT_SEEDS), 'scenarios': list(SCENARIOS), 'budgets': list(BUDGETS),
        'world_cases': list(world_cases(HELDOUT_SEEDS, SCENARIOS, BUDGETS)),
        'scoring': {'prediction_horizon_seconds': 1., 'prediction_grid_seconds': .5,
                    'detection_window_seconds': 20., 'matching': 'chronological one-to-one inclusive window',
                    'missed_detection_delay': 20., 'coverage': 'Gaussian mean +/- 1.96 standard deviations',
                    'cost_weights': {'observations': 1., 'inferences': 2., 'actions': .1},
                    'failures': 'all unsuccessful operation receipts retained; unit exceptions invalidate comparisons'},
        'bootstrap': {'cluster': 'seed', 'replicates': BOOTSTRAP_REPLICATES,
                      'seed': BOOTSTRAP_SEED, 'interval': '95% percentile; descriptive, not multiplicity adjusted'},
        'resource_contract': {'observation_and_inference_caps': 'equal to case budget', 'alert_cap': 30,
                              'estimator': 'shared nominal two-state Kalman reference',
                              'fixed_overhead': 'clock, scheduling, prior propagation, fixed-grid forecasts, scoring',
                              'inference': 'paid classical measurement update, not an LLM call',
                              'model_calls': 0, 'initial_state': 'known x=1, v=0'},
        'limitations': ['single physical task family', 'no optimal-VOI or novelty claim',
                        'hybrid is an oscillator adaptation using preserved original analytic dynamics',
                        'nominal Kalman covariance can be miscalibrated after hidden shifts',
                        'same resource caps do not guarantee equal realized consumption'],
    }
    protocol['expected_units'] = len(protocol['world_cases']) * len(protocol['policies'])
    write_json(directory / 'protocol.json', protocol)
    (directory / 'protocol.sha256').write_text(digest((directory / 'protocol.json').read_bytes()) + '\n')
    with (directory / 'frozen-source.tar.gz').open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                for relative in sources:
                    data = (ROOT / relative).read_bytes()
                    info = tarfile.TarInfo(relative)
                    info.size, info.mode, info.mtime = len(data), 0o644, 0
                    archive.addfile(info, io.BytesIO(data))
    (directory / 'source-archive.sha256').write_text(digest((directory / 'frozen-source.tar.gz').read_bytes()) + '\n')
    return protocol


def _verify_frozen(directory):
    raw = (directory / 'protocol.json').read_bytes()
    if digest(raw) != (directory / 'protocol.sha256').read_text().strip():
        raise ValueError('frozen protocol hash mismatch')
    protocol = json.loads(raw)
    if source_hashes() != protocol['source_hashes']:
        raise ValueError('source drift: current source differs from frozen protocol')
    archive_path = directory / 'frozen-source.tar.gz'
    if digest(archive_path.read_bytes()) != (directory / 'source-archive.sha256').read_text().strip():
        raise ValueError('source archive hash mismatch')
    with tarfile.open(archive_path, 'r:gz') as archive:
        archived = {member.name: digest(archive.extractfile(member).read()) for member in archive.getmembers() if member.isfile()}
    if archived != protocol['source_hashes']:
        raise ValueError('source archive contents mismatch')
    return protocol


def _mean_metrics(rows):
    keys = ('rmse', 'zero_rmse', 'nll', 'coverage95', 'detection_delay', 'censored_delay',
            'detected_changes', 'missed_changes', 'false_alarms', 'observations', 'inferences', 'actions', 'cost', 'failures')
    metrics = {'units': len(rows)}
    for key in keys:
        values = [row['metrics'][key] for row in rows if row['metrics'][key] is not None]
        metrics[key] = statistics.fmean(values) if values else None
        if key in ('detection_delay', 'censored_delay'):
            metrics[key + '_defined_units'] = len(values)
    for key in ('detected_changes', 'missed_changes', 'false_alarms', 'failures'):
        metrics[key + '_total'] = sum(row['metrics'][key] for row in rows)
    return metrics


def _percentile(values, fraction):
    rank = (len(values) - 1) * fraction
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return values[lower] + (values[upper] - values[lower]) * (rank - lower)


def summarize(rows, protocol):
    failed = [row['unit_id'] for row in rows if row['status'] != 'succeeded']
    valid = len(rows) == protocol['expected_units'] and not failed
    summary = {'valid_comparison': valid, 'expected_units': protocol['expected_units'], 'recorded_units': len(rows),
               'runtime_failures': failed, 'primary_metric': protocol['primary_metric'],
               'model_calls': 0, 'mode': 'deterministic', 'overall': {}, 'breakdown': [], 'paired_rmse': {}}
    if not valid:
        summary['conclusion'] = 'Comparison invalid: failed or missing units are retained; no performance claim is made.'
        return summary
    for policy in protocol['policies']:
        summary['overall'][policy] = _mean_metrics([row for row in rows if row['policy'] == policy])
        for name in protocol['scenarios']:
            for budget in protocol['budgets']:
                selected = [row for row in rows if row['policy'] == policy and row['scenario'] == name and row['observation_budget'] == budget]
                summary['breakdown'].append({'policy': policy, 'scenario': name, 'observation_budget': budget,
                                             **_mean_metrics(selected)})
    lookup = {(row['seed'], row['scenario'], row['observation_budget'], row['policy']): row['metrics']['rmse'] for row in rows}
    for baseline in ('periodic', 'event_deadline', 'original_hybrid'):
        differences = []
        for seed in protocol['heldout_seeds']:
            paired = [lookup[(seed, name, budget, 'uncertainty')] - lookup[(seed, name, budget, baseline)]
                      for name in protocol['scenarios'] for budget in protocol['budgets']]
            differences.append(statistics.fmean(paired))
        rng = random.Random(protocol['bootstrap']['seed'])
        bootstrapped = sorted(statistics.fmean(rng.choices(differences, k=len(differences)))
                              for _ in range(protocol['bootstrap']['replicates']))
        summary['paired_rmse'][baseline] = {'difference': statistics.fmean(differences),
                                           'ci95': [_percentile(bootstrapped, .025), _percentile(bootstrapped, .975)],
                                           'seed_clusters': len(differences), 'direction': 'uncertainty minus baseline; negative favors uncertainty'}
    supported = [name for name, comparison in summary['paired_rmse'].items() if comparison['ci95'][1] < 0]
    summary['conclusion'] = ('Uncertainty has lower RMSE with a descriptive paired 95% interval below zero versus: ' + ', '.join(supported) + '.'
                             if supported else 'No paired comparison demonstrates lower uncertainty-policy RMSE with a 95% interval wholly below zero.')
    summary['conclusion'] += ' This is a bounded oscillator result, not evidence of general autonomous-agent superiority or novelty.'
    return summary


def _report_markdown(summary):
    lines = ['# Frozen oscillator evaluation', '', summary['conclusion'], '',
             f"Recorded units: {summary['recorded_units']} / {summary['expected_units']}. Model calls: 0. Mode: deterministic.", '']
    if not summary['valid_comparison']:
        lines += ['Failed units: ' + ', '.join(summary['runtime_failures']), '']
        return '\n'.join(lines)
    lines += ['| Policy | RMSE ↓ | Zero RMSE | NLL ↓ | 95% coverage | False alarms | Cost | Failed receipts |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for policy, values in summary['overall'].items():
        lines.append(f"| {policy} | {values['rmse']:.6f} | {values['zero_rmse']:.6f} | {values['nll']:.6f} | {values['coverage95']:.3f} | {values['false_alarms']:.3f} | {values['cost']:.3f} | {values['failures_total']} |")
    lines += ['', 'Means are per episode except failed receipts, which are totals. Full detection/censoring and scenario/budget breakdowns are in report.json.', '',
              '| Paired RMSE difference: uncertainty minus | Difference | Seed-cluster 95% interval |', '| --- | ---: | --- |']
    for baseline, values in summary['paired_rmse'].items():
        low, high = values['ci95']
        lines.append(f"| {baseline} | {values['difference']:.6f} | [{low:.6f}, {high:.6f}] |")
    lines += ['', 'Intervals use the frozen seed-cluster bootstrap and are descriptive, without multiple-comparison adjustment. Operation failures, stale evidence rejections, and contradictions remain in the raw receipts.', '',
              'The preserved v0.2 result remains unchanged: hybrid did not demonstrate a completion advantage over event/deadline scheduling. This evaluation measures a different task.', '']
    return '\n'.join(lines)


def run_campaign(directory):
    directory = _directory(directory)
    protocol = _verify_frozen(directory)
    for name in ('results.jsonl', 'traces.jsonl.gz', 'run-receipt.json', 'report.json', 'REPORT.md'):
        if (directory / name).exists():
            raise FileExistsError('campaign evidence exists; never overwrite or rerun a frozen campaign')
    rows = []
    with (directory / 'results.jsonl').open('x', encoding='utf-8') as output, trace_writer(directory / 'traces.jsonl.gz') as traces:
        for index, case in enumerate(protocol['world_cases']):
            for policy in protocol['policies']:
                row, trace = evaluate_unit(case, policy, protocol['parameters'][policy], unit_id=f'heldout:{index}:{policy}')
                output.write(canonical(row) + '\n')
                output.flush()
                traces.write(canonical(trace) + '\n')
                rows.append(row)
    summary = summarize(rows, protocol)
    if source_hashes() != protocol['source_hashes']:
        summary['valid_comparison'] = False
        summary['conclusion'] = 'Comparison invalid: source changed during execution. All outcomes are retained.'
    write_json(directory / 'report.json', summary)
    with (directory / 'REPORT.md').open('x', encoding='utf-8') as output:
        output.write(_report_markdown(summary))
    receipt = {'completed': True, 'valid_comparison': summary['valid_comparison'], 'units': len(rows),
               'protocol_sha256': digest((directory / 'protocol.json').read_bytes()),
               'results_sha256': digest((directory / 'results.jsonl').read_bytes()),
               'traces_sha256': digest((directory / 'traces.jsonl.gz').read_bytes()),
               'report_sha256': digest((directory / 'report.json').read_bytes())}
    write_json(directory / 'run-receipt.json', receipt)
    return summary


def verify(directory, *, reproduce=False):
    directory = _directory(directory)
    protocol = _verify_frozen(directory)
    receipt_path = directory / 'run-receipt.json'
    if not receipt_path.exists():
        if reproduce:
            raise ValueError('cannot reproduce an unfinished campaign')
        return {'verified': True, 'stage': 'frozen', 'expected_units': protocol['expected_units']}
    receipt = json.loads(receipt_path.read_text())
    for filename, key in (('protocol.json', 'protocol_sha256'), ('results.jsonl', 'results_sha256'),
                          ('traces.jsonl.gz', 'traces_sha256'), ('report.json', 'report_sha256')):
        if digest((directory / filename).read_bytes()) != receipt[key]:
            raise ValueError(f'evidence hash mismatch: {filename}')
    rows = [json.loads(line) for line in (directory / 'results.jsonl').read_text().splitlines()]
    expected_ids = [f'heldout:{index}:{policy}' for index, _ in enumerate(protocol['world_cases']) for policy in protocol['policies']]
    if [row['unit_id'] for row in rows] != expected_ids:
        raise ValueError('missing, duplicate, or reordered experimental units')
    replay_count = 0
    if reproduce:
        with gzip.open(directory / 'traces.jsonl.gz', 'rt', encoding='utf-8') as traces:
            for original in rows:
                case_index = int(original['unit_id'].split(':')[1])
                replay, trace = evaluate_unit(protocol['world_cases'][case_index], original['policy'],
                                              protocol['parameters'][original['policy']], unit_id=original['unit_id'])
                stable = lambda row: {key: value for key, value in row.items() if key != 'elapsed_seconds'}
                if stable(replay) != stable(original) or trace != json.loads(next(traces)):
                    raise ValueError(f'deterministic reproduction mismatch: {original["unit_id"]}')
                replay_count += 1
            if traces.readline():
                raise ValueError('extra trace records')
    return {'verified': True, 'stage': 'completed', 'units': len(rows),
            'valid_comparison': receipt['valid_comparison'], 'reproduced_units': replay_count}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('develop', 'freeze', 'run', 'verify'))
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--development', type=Path)
    parser.add_argument('--reproduce', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.command == 'develop':
            result = develop(args.directory)
        elif args.command == 'freeze':
            if args.development is None:
                parser.error('freeze requires --development')
            result = freeze(args.directory, args.development)
        elif args.command == 'run':
            result = run_campaign(args.directory)
        else:
            result = verify(args.directory, reproduce=args.reproduce)
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        parser.exit(2, str(exc) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('source_hashes', 'world_cases', 'development')}, indent=2))


if __name__ == '__main__':
    main()
