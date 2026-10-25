"""Recheck frozen evidence offline; never open a Runtime or invoke a provider."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from continuum.research.campaign import report
from continuum.research.scoring import score
from continuum.research.worlds import generate
from continuum.runtime.common import digest


def readonly(path):
    # Immutable mode cannot read an uncheckpointed WAL. Fail instead of omitting it.
    wal = Path(str(path) + '-wal')
    if wal.exists() and wal.stat().st_size:
        raise ValueError(f'Checkpointed, stopped database required: {path}')
    if not path.is_file():
        raise FileNotFoundError(path)
    db = sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    return db


def verify(directory):
    protocol_bytes = (directory / 'protocol.json').read_bytes()
    checksum = hashlib.sha256(protocol_bytes).hexdigest()
    assert checksum == (directory / 'protocol.sha256').read_text().strip()
    protocol = json.loads(protocol_bytes)
    with tarfile.open(directory / 'frozen-source.tar.gz') as archive:
        for name, expected in protocol['source_manifest'].items():
            assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected, name
    for unit in protocol['units']:
        world = generate(unit['family'], unit['seed'])
        assert digest(world.to_dict()) == protocol['world_hashes'][world.id]

    rows = [json.loads(line) for line in (directory / 'results.jsonl').read_text().splitlines()]
    indexed = {r['id']: r for r in rows}
    assert len(indexed) == len(rows) == len(protocol['units'])
    assert set(indexed) == {u['id'] for u in protocol['units']}
    coverage, failures, rescored = {}, {}, 0
    with closing(readonly(directory / 'campaign.sqlite')) as campaign:
        assert campaign.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        saved = {r['id']: json.loads(r['result']) for r in campaign.execute('SELECT * FROM units')}
        assert indexed == saved
        # report() writes its output; use a disposable copy, never the frozen directory.
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache/tmp', prefix='audit-report-') as tmp:
            with closing(sqlite3.connect(Path(tmp) / 'campaign.sqlite')) as copy:
                campaign.backup(copy)
            regenerated = report(Path(tmp))
        assert regenerated == json.loads((directory / 'report.json').read_text())

    for unit in protocol['units']:
        row = indexed[unit['id']]
        assert all(row[k] == value for k, value in unit.items())
        path = directory / 'units' / unit['id'] / 'agent/agent.sqlite'
        with closing(readonly(path)) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', unit['id']
            operations = [dict(r) for r in db.execute('SELECT * FROM operations ORDER BY created,id')]
            calls = [dict(r) for r in db.execute('SELECT * FROM calls ORDER BY created,id')]
            for op in operations:
                op['args'] = json.loads(op['args'])
            for call in calls:
                call['usage'] = json.loads(call['usage']) if call['usage'] else None
                if call['status'] != 'succeeded':
                    key = call['error'] or call['status']
                    failures[key] = failures.get(key, 0) + 1
            result = score(generate(unit['family'], unit['seed']), operations, calls,
                           [dict(r) for r in db.execute('SELECT * FROM memories')],
                           [dict(r) for r in db.execute('SELECT * FROM outbox')])
            assert all(row[k] == value for k, value in result.items()), unit['id']
            assert row['call_times'] == [c['created'] for c in calls]
            rescored += 1
        coverage.setdefault(unit['condition'], []).extend(calls)

    usage = {}
    for condition, calls in sorted(coverage.items()):
        known = [c['usage'] for c in calls if c['usage']]
        usage[condition] = {'attempted_calls': len(calls), 'calls_with_usage': len(known),
                            'calls_without_usage': len(calls) - len(known)}
        stored_path = directory / 'usage-coverage.json'
        if stored_path.exists():
            stored = json.loads(stored_path.read_text())[condition]
            assert all(stored[k] == v for k, v in usage[condition].items())
            for key, category in stored['categories'].items():
                values = [u[key] for u in known if type(u.get(key)) in (int, float)]
                assert len(values) == category['calls_with_category']
                subtotal = sum(values) if values else None
                assert (subtotal == category['known_subtotal'] or
                        abs(subtotal - category['known_subtotal']) < 1e-10)

    return {'campaign': str(directory.relative_to(ROOT)), 'protocol_sha256': checksum,
            'frozen_source_files_verified': len(protocol['source_manifest']),
            'declared_episodes': len(protocol['units']), 'independently_rescored': rescored,
            'report_reconstructed_exactly': True, 'database_integrity_checks': rescored + 1,
            'call_coverage': usage, 'historical_failure_messages': failures,
            'means': {key: {k: value[k] for k in ('episodes', 'goal_completion', 'provider_calls',
                       'total_api_equivalent_usd')} for key, value in regenerated['means'].items()},
            'paired_scenario_bootstrap_95': regenerated['paired_scenario_bootstrap_95'],
            'limits': 'Stored artifacts only; no new inference, browser or soak; no missing usage inferred.'}


if __name__ == '__main__':
    targets = sys.argv[1:] or ['experiments/v02/offline-final-v2', 'experiments/v02/live-heldout-v1']
    directories = [(ROOT / target).resolve() for target in targets]
    if any(not p.is_relative_to(ROOT / 'experiments/v02') for p in directories):
        raise SystemExit('Only repository-local frozen campaigns are supported')
    print(json.dumps({'campaigns': [verify(p) for p in directories], 'new_model_calls': 0}, indent=2))
