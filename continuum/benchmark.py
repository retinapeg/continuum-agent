"""Paired, seed-level bootstrap estimates; deterministic, descriptive inference."""
import csv
import hashlib
import json
from pathlib import Path
import random
import statistics
from .agents import POLICIES
from .scenarios import REGIMES, generate
from .simulation import run

METRICS = ('completion_rate', 'memory_accuracy', 'intervention_precision',
           'intervention_recall', 'latency_mean', 'decisions', 'attempts',
           'interruptions', 'cost_units')


def paired_interval(differences: list[float], draws: int = 2000) -> dict:
    if not differences or draws < 1:
        raise ValueError('nonempty differences and positive draws required')
    rng = random.Random(1729)
    samples = sorted(statistics.mean(rng.choices(differences, k=len(differences)))
                     for _ in range(draws))
    return {'mean': statistics.mean(differences),
            'low': samples[int(0.025 * (draws - 1))],
            'high': samples[int(0.975 * (draws - 1))]}


def summarize(rows: list[dict]) -> dict:
    groups = {}
    for regime in (*REGIMES, 'all'):
        groups[regime] = {}
        for policy in POLICIES:
            selected = [r for r in rows if r['policy'] == policy and
                        (regime == 'all' or r['scenario'] == regime)]
            groups[regime][policy] = {}
            for metric in METRICS:
                values = [r[metric] for r in selected if r[metric] is not None]
                groups[regime][policy][metric] = statistics.mean(values) if values else None
    paired = {}
    seeds = sorted({r['seed'] for r in rows})
    indexed = {(r['seed'], r['scenario'], r['policy']): r for r in rows}
    for baseline in ('reactive', 'periodic'):
        paired[baseline] = {}
        for metric in ('completion_rate', 'cost_units', 'interruptions'):
            differences = [statistics.mean(
                indexed[seed, regime, 'adaptive'][metric] - indexed[seed, regime, baseline][metric]
                for regime in REGIMES) for seed in seeds]
            paired[baseline][metric] = paired_interval(differences)
    return {'means': groups, 'adaptive_minus_baseline_95pct_seed_bootstrap': paired}


def benchmark(output: Path, seeds: int = 30) -> dict:
    if seeds < 2:
        raise ValueError('at least two seeds required')
    output.mkdir(parents=True, exist_ok=True)
    rows = [run(generate(regime, seed), policy).to_dict()
            for seed in range(seeds) for regime in REGIMES for policy in POLICIES]
    with (output / 'runs.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    root = Path(__file__).resolve().parent.parent
    sources = sorted((root / 'continuum').glob('*.py')) + sorted((root / 'tests').glob('*.py'))
    manifest = {
        'version': '0.1.0', 'seeds': list(range(seeds)), 'regimes': list(REGIMES),
        'horizon': 120, 'runs': len(rows), 'period': 6, 'retry_interval': 4,
        'bootstrap_seed': 1729, 'bootstrap_draws': 2000,
        'cost_model': {'ingested_event': 0.01, 'decision': 0.1, 'attempt': 1.0},
        'source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sources},
        'artifact_sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                            for name in ('runs.csv', 'summary.json')},
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return summary
