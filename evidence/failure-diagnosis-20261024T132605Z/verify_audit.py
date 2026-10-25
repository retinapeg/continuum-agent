"""Bounded offline verification of this diagnosis; write only this audit directory."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[1]
assert ROOT == Path('/Users/leo/Projects/continuum-agent')
CAMPAIGN = ROOT / 'experiments/v02/live-heldout-v1'
NOTES = {'learning.md', 'decisions.md', 'MORNING_REPORT.md'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, allowed=(0,)):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                            timeout=60, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode in allowed, (args, result.returncode, result.stderr)
    return {'command': args, 'exit_code': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr}


checks = []
for script in ('inspect_evidence.py', 'probe_scoring.py', 'build_tables.py'):
    checks.append(command(['.venv/bin/python', str((AUDIT / script).relative_to(ROOT))]))

before = json.loads((AUDIT / 'before-sha256.json').read_text())
missing = [name for name in before if not (ROOT / name).is_file()]
changed = [name for name, expected in before.items()
           if (ROOT / name).is_file() and sha(ROOT / name) != expected]
assert not missing and set(changed) == NOTES, (missing, changed)
for name in NOTES:
    assert sha(AUDIT / 'prior-notes' / name) == before[name]

protocol = json.loads((CAMPAIGN / 'protocol.json').read_text())
assert sha(CAMPAIGN / 'protocol.json') == (CAMPAIGN / 'protocol.sha256').read_text().strip()
with tarfile.open(CAMPAIGN / 'frozen-source.tar.gz') as archive:
    for name, expected in protocol['source_manifest'].items():
        assert hashlib.sha256(archive.extractfile(name).read()).hexdigest() == expected
        assert sha(AUDIT / 'frozen' / name) == expected
from inspect_evidence import generate
for scenario, expected in protocol['world_hashes'].items():
    family, seed = scenario.rsplit('-', 1)
    world = generate(family, int(seed)).to_dict()
    raw = json.dumps(world, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    assert hashlib.sha256(raw).hexdigest() == expected

details = json.loads((AUDIT / 'episode-evidence.json').read_text())
failures = json.loads((AUDIT / 'failed-episodes.json').read_text())
work = json.loads((AUDIT / 'unmatched-call-work.json').read_text())
errors = json.loads((AUDIT / 'call-errors.json').read_text())
probes = json.loads((AUDIT / 'scorer-probes.json').read_text())
assert len(details) == 72 and len(failures) == 32
assert sum(not f['recorded_call_errors'] for f in failures) == 29
assert len(list((AUDIT / 'episodes').glob('*.md'))) == 32
assert len(probes) == 6
contexts = [e for x in details.values() for e in x['events'] if e['kind'] == 'context.selected']
assert all(not e['data']['payload']['excluded'] for e in contexts)
memory_failures = [x for x in details.values()
                   if x['unit']['family'] == 'memory_revision' and not x['result']['goal_completion']]
assert len(memory_failures) == 7
for x in memory_failures:
    preference_ids = {m['id'] for m in x['memories']
                      if m['kind'] == 'preference' and m['status'] == 'conflicted'}
    assert len(preference_ids) == 2
    assert all(preference_ids <= {s['id'] for s in r['receipt']['selected']}
               for r in x['retrievals'] if r['at'] >= 24)

def explicit_questions(x):
    return [n for n in x['outbox'] if n['status'] == 'available-locally' and '?' in n['content']
            and any(word in n['content'].lower() for word in ('format', 'preference', 'prefer', 'table', 'narrative'))]

repeated = Counter(x['result']['goal_completion'] for x in details.values()
                   if x['unit']['family'] == 'memory_revision' and len(explicit_questions(x)) >= 2)
assert repeated == {0: 4, 1: 4}
unmatched = {}
for policy in ('C', 'D'):
    rows = [w for w in work if w['policy'] == policy]
    unmatched[policy] = {'calls': len(rows), 'new_operations': sum(len(w['new_operations']) for w in rows),
                         'calls_without_new_operations': sum(not w['new_operations'] for w in rows),
                         'available_notifications': sum(n['status'] == 'available-locally' for w in rows for n in w['notifications'])}
assert unmatched['D'] == {'calls': 44, 'new_operations': 4, 'calls_without_new_operations': 40, 'available_notifications': 5}
assert unmatched['C']['calls'] == 12 and unmatched['C']['new_operations'] == 1
error_categories = {}
for label in sorted({e['error'] for e in errors}):
    rows = [e for e in errors if e['error'] == label]
    episodes = {e['episode_id']: e['goal_completion'] for e in rows}
    error_categories[label] = {'calls': len(rows), 'episodes': len(episodes),
                                'unsuccessful_episodes': sum(v == 0 for v in episodes.values()),
                                'successful_episodes': sum(v == 1 for v in episodes.values())}
assert len(errors) == 26 and sum(not e['usage_present'] for e in errors) == 24

# Inspect only the audit's new Markdown and the three authorized current notes.
# Prior-note snapshots retain their original relative links for provenance.
documents = [p for p in AUDIT.rglob('*.md') if 'prior-notes' not in p.parts]
documents += [ROOT / name for name in NOTES]
links_checked = 0
for document in documents:
    rendered_text = re.sub(r'^```.*?^```\s*$', '', document.read_text(), flags=re.M | re.S)
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', rendered_text):
        if target.startswith(('http:', 'https:', '#')):
            continue
        target = target.split('#')[0]
        resolved = (document.parent / target).resolve()
        assert resolved == AUDIT / 'verification.json' or resolved.exists(), (str(document), target)
        links_checked += 1
for script in AUDIT.glob('*.py'):
    ast.parse(script.read_text(), filename=str(script))
    assert all(line == line.rstrip() for line in script.read_text().splitlines()), script
checks.append(command(['git', 'diff', '--check']))
head = command(['git', 'rev-parse', 'HEAD'])['stdout'].strip()
branch = command(['git', 'branch', '--show-current'])['stdout'].strip()
assert head == 'a0ecdd5606ccb8d9629a7c4c85285f071088684f' and branch == 'main'
assert command(['git', 'rev-parse', '--show-toplevel'])['stdout'].strip() == str(ROOT)
assert not command(['git', 'diff', '--cached', '--name-only'])['stdout'].strip()
untracked = command(['git', 'ls-files', '--others', '--exclude-standard', '-z'])['stdout'].split('\0')
new_untracked = [name for name in untracked if name and name not in before]
assert all((ROOT / name).is_relative_to(AUDIT) for name in new_untracked), new_untracked

# Exclude this foreground verifier and its ancestors, not arbitrary project matches.
raw_ps = command(['ps', '-axo', 'pid=,ppid=,command='])['stdout']
processes = {}
for line in raw_ps.splitlines():
    parts = line.strip().split(None, 2)
    if len(parts) == 3:
        processes[int(parts[0])] = (int(parts[1]), parts[2])
ancestors = {os.getpid()}
pid = os.getpid()
while pid in processes and processes[pid][0] not in ancestors:
    pid = processes[pid][0]
    ancestors.add(pid)
matching = [{'pid': pid, 'command': row[1]} for pid, row in processes.items()
            if pid not in ancestors and any(s in row[1] for s in ('continuum-agent', 'continuum.runtime', 'continuum.research'))]
assert not matching, matching
ports = [command(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN'], allowed=(0, 1)) for port in (8787, 8789)]
assert all(not p['stdout'].strip() for p in ports), ports

# The final receipt is itself an authorized new audit file.
receipt = {
    'verified_at_utc': datetime.now(timezone.utc).isoformat(),
    'cwd_and_root': str(ROOT), 'branch': branch, 'HEAD': head,
    'checks': checks, 'python': sys.version,
    'fresh_database_integrity_checks': {'distinct_databases': 181, 'mode': 'read-only immutable', 'migrations': 0},
    'frozen_protocol_sha256': sha(CAMPAIGN / 'protocol.json'),
    'manifest_source_files_verified': len(protocol['source_manifest']),
    'generated_world_hashes_verified': len(protocol['world_hashes']),
    'all_180_stored_scores_reproduced': True,
    'CD_records': 72, 'unsuccessful_records': 32, 'unsuccessful_without_call_error': 29,
    'scorer_probe_count': len(probes), 'unmatched_call_work': unmatched,
    'call_error_categories': error_categories,
    'context_receipts_without_exclusions': len(contexts),
    'all_seven_failed_memory_episodes_retrieve_both_conflicts': True,
    'repeated_explicit_memory_questions': {'unsuccessful_episodes': repeated[0], 'successful_episodes': repeated[1]},
    'software_suite': '124 passing tests in saved receipts; hashes checked, suite NOT rerun in this audit',
    'review_limit': 'Scorer consistency is not semantic validity; independent human review remains pending',
    'new_live_provider_validation': False,
    'preservation': {'protected_files': len(before), 'changed_original_files': sorted(changed),
                     'deleted_original_files': missing, 'other_protected_bytes_unchanged': True,
                     'notes_before_edit_copies_match': True,
                     'scope': 'All initial tracked/nonignored work, all held-out campaign files including ignored DBs, and .runtime files'},
    'diagnosis_markdown_links_checked': links_checked,
    'audit_python_syntax_and_whitespace': 'passed',
    'earlier_audit_verifier_failure': {
        'command': '.venv/bin/python evidence/failure-diagnosis-20261024T132605Z/verify_audit.py',
        'exit_code': 1,
        'reason': 'Link checker initially treated engineering.md inside a fenced literal artifact as a rendered report link.',
        'resolution': 'Exclude fenced code from Markdown link validation; no original artifact or application code changed.'},
    'matching_project_processes': matching, 'listener_checks': ports,
    'new_files_outside_audit': [], 'new_runtime_or_test_changes': False,
    'external_calls': 0, 'live_inference_calls': 0, 'installs': 0,
    'services_started': 0, 'commits_or_pushes': 0,
    'final_git_status': command(['git', 'status', '--short'])['stdout'],
}
(AUDIT / 'verification.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
assert (AUDIT / 'verification.json').is_file()
print(json.dumps({k: receipt[k] for k in ('HEAD', 'unsuccessful_records', 'preservation',
                                        'matching_project_processes', 'diagnosis_markdown_links_checked')}, indent=2))
