"""Offline diagnosis extraction. No Runtime, migrations, providers or report writes."""
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import types

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[1]
CAMPAIGN = ROOT / 'experiments/v02/live-heldout-v1'
# Import only definitions from the archived source; no current runtime is initialized.
package = types.ModuleType('continuum')
package.__path__ = [str(AUDIT / 'frozen/continuum')]
sys.modules['continuum'] = package
from continuum.research.worlds import generate, schedule
from continuum.research.scoring import score


def read_db(path):
    assert path.is_file(), path
    wal = Path(str(path) + '-wal')
    assert not wal.exists() or not wal.stat().st_size, 'Uncheckpointed WAL: ' + str(path)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        db.row_factory = sqlite3.Row
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {name: [dict(r) for r in db.execute('SELECT * FROM ' + name)] for name in tables}


def gates(world, operation, delivered):
    """Expose each predicate of the frozen scorer; not an endorsement of its rubric."""
    args = operation['args']
    text = args.get('content', args.get('question', ''))
    normalized = text.replace('**', '')
    fields = re.findall(r'(?im)^\s*(Status|Risk)\s*:\s*([^\n]+)', normalized)
    fields += re.findall(r'(?im)^\s*\|\s*(Status|Risk)\s*\|\s*([^|]+)\|', normalized)
    fields = [(key.title(), value.strip()) for key, value in fields]
    valid = {k for k, v in fields if v.lower() in [x.lower() for x in world.allowed_claims.get(k, [])]}
    invalid = [(k, v) for k, v in fields if v.lower() not in [x.lower() for x in world.allowed_claims.get(k, [])]]
    result = []
    for window in world.opportunities:
        checks = {'kind': ('artifact' if operation['kind'] == 'create_artifact' else 'clarify') == window['kind'],
                  'effect_succeeded': operation['status'] == 'succeeded',
                  'time_window': window['start'] <= operation['created'] <= window['end'],
                  'required_sources': set(window['sources']) <= set(args.get('sources', [])),
                  'required_words': all(w.lower() in text.lower() for w in window['required']),
                  'no_forbidden_literal': not any(w.lower() in text.lower() for w in world.forbidden)}
        if operation['kind'] == 'create_artifact':
            checks['exact_Status_Risk_fields'] = not invalid and {'Status', 'Risk'} <= valid
        else:
            receipt = operation['result'] or {}
            anchors = ('delivery', 'confirmation', 'confirm') if world.family == 'deadline_followup' else ('format', 'preference', 'prefer', 'table', 'narrative')
            checks['notification_delivered'] = receipt.get('notification_id') in delivered
            checks['question_and_anchor'] = '?' in text and any(x in text.lower() for x in anchors)
            checks['evidence_ids_present'] = bool(args.get('evidence_ids'))
        result.append({'window': window, 'checks': checks, 'failed_checks': [k for k, v in checks.items() if not v],
                       'extracted_fields': fields, 'invalid_fields': invalid})
    return result


def main():
    protocol_bytes = (CAMPAIGN / 'protocol.json').read_bytes()
    assert hashlib.sha256(protocol_bytes).hexdigest() == (CAMPAIGN / 'protocol.sha256').read_text().strip()
    protocol = json.loads(protocol_bytes)
    rows = [json.loads(line) for line in (CAMPAIGN / 'results.jsonl').read_text().splitlines()]
    indexed = {r['id']: r for r in rows}
    assert len(indexed) == len(rows) == 180
    assert set(indexed) == {u['id'] for u in protocol['units']}
    campaign = read_db(CAMPAIGN / 'campaign.sqlite')
    assert {r['id']: json.loads(r['result']) for r in campaign['units']} == indexed
    details, errors, coverage, all_calls = {}, [], {}, 0
    for unit in protocol['units']:
        uid = unit['id']; result = indexed[uid]
        base = CAMPAIGN / 'units' / uid
        db = read_db(base / 'agent/agent.sqlite')
        for table, fields in {'operations': ('args', 'result'), 'calls': ('usage',), 'observations': ('content',),
                              'memories': ('provenance',), 'retrievals': ('receipt',), 'events': ('data',),
                              'outbox': ('evidence',)}.items():
            for row in db[table]:
                for field in fields:
                    row[field] = json.loads(row[field]) if row[field] else None
        db['calls'].sort(key=lambda r: (r['created'], r['id']))
        db['operations'].sort(key=lambda r: (r['created'], r['id']))
        world = generate(unit['family'], unit['seed'])
        rescore = score(world, db['operations'], db['calls'], db['memories'], db['outbox'])
        assert all(result[k] == v for k, v in rescore.items()), uid
        assert result['call_times'] == [c['created'] for c in db['calls']]
        all_calls += len(db['calls'])
        cov = coverage.setdefault(unit['condition'], Counter())
        cov['calls'] += len(db['calls'])
        cov['missing_usage'] += sum(not c['usage'] for c in db['calls'])
        for call in db['calls']:
            if call['status'] != 'succeeded':
                errors.append({'episode_id': uid, 'policy': unit['condition'], 'family': unit['family'],
                               'goal_completion': result['goal_completion'], 'call_id': call['id'],
                               'at': call['created'], 'error': call['error'], 'usage_present': bool(call['usage'])})
        if unit['condition'] not in ('C', 'D'):
            continue
        relevant_events = [e for e in db['events'] if e['kind'] != 'provider.progress' or
                           e['data']['payload'].get('type') != 'provider.delta']
        delivered = {n['id'] for n in db['outbox'] if n['status'] == 'available-locally'}
        attempts = [op for op in db['operations'] if op['kind'] in ('create_artifact', 'request_clarification')]
        artifacts = []
        for artifact in db['artifacts']:
            path = (base / 'agent/artifacts' / artifact['path']).resolve()
            assert path.is_relative_to(base / 'agent/artifacts')
            raw = path.read_bytes(); assert hashlib.sha256(raw).hexdigest() == artifact['checksum']
            artifacts.append({**artifact, 'text': raw.decode(), 'evidence_path': str(path.relative_to(ROOT))})
        details[uid] = {'unit': unit, 'result': result, 'world': world.to_dict(),
                        'full_policy_schedule': schedule(world, unit['condition']),
                        'database': str((base / 'agent/agent.sqlite').relative_to(ROOT)),
                        'calls': db['calls'], 'operations': db['operations'], 'outbox': db['outbox'],
                        'observations': db['observations'], 'memories': db['memories'],
                        'retrievals': db['retrievals'], 'events': relevant_events, 'artifacts': artifacts,
                        'attempt_predicates': [{'operation_id': op['id'], 'at': op['created'], 'kind': op['kind'],
                                                'gates': gates(world, op, delivered)} for op in attempts]}
    pairs = []
    for c in sorted((d for d in details.values() if d['unit']['condition'] == 'C'), key=lambda d:d['unit']['id']):
        u = c['unit']; did = u['id'].replace('-C-', '-D-'); d = details[did]
        ct, dt = c['result']['call_times'], d['result']['call_times']
        pairs.append({'scenario': c['result']['scenario'], 'repetition': u['repetition'],
                      'C': u['id'], 'D': did, 'C_success': c['result']['goal_completion'],
                      'D_success': d['result']['goal_completion'], 'C_times': ct, 'D_times': dt,
                      'D_only_times': [t for t in dt if t not in ct], 'C_only_times': [t for t in ct if t not in dt]})
    failures = [d for d in details.values() if not d['result']['goal_completion']]
    summary = {'fresh_checks': 'read-only databases, frozen scorer and independent counts; no software suite rerun',
               'episodes': len(rows), 'persistence_statuses': dict(Counter(u['status'] for u in campaign['units'])),
               'completion_by_policy': {p: sum(r['goal_completion'] for r in rows if r['condition']==p) for p in 'ABCDE'},
               'calls': all_calls, 'usage_coverage': coverage,
               'CD_unsuccessful': dict(Counter(d['unit']['condition'] for d in failures)),
               'CD_unsuccessful_without_call_errors': sum(d['result']['provider_failures']==0 for d in failures),
               'error_calls': len(errors), 'error_taxonomy': dict(Counter(e['error'] for e in errors)),
               'episodes_with_call_error': len({e['episode_id'] for e in errors}),
               'unsuccessful_episodes_with_call_error': len({e['episode_id'] for e in errors if not e['goal_completion']}),
               'paired_outcomes': dict(Counter(f"C={p['C_success']},D={p['D_success']}" for p in pairs))}
    for name, value in [('episode-evidence.json', details), ('call-errors.json', errors), ('paired-outcomes.json', pairs), ('counts.json', summary)]:
        (AUDIT / name).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
