"""Six in-memory rubric falsification probes, not new agent episodes or repaired scores."""
from copy import deepcopy
import json
import re
from inspect_evidence import AUDIT, generate, score

data = json.loads((AUDIT / 'episode-evidence.json').read_text())
results = []


def verdict(x, operations=None, outbox=None):
    u = x['unit']
    return score(generate(u['family'], u['seed']), operations if operations is not None else x['operations'],
                 x['calls'], x['memories'], outbox if outbox is not None else x['outbox'])['goal_completion']


def record(label, name, change, operations=None, outbox=None, expected=None):
    original = verdict(data[name]); altered = verdict(data[name], operations, outbox)
    assert (original, altered) == expected, label
    results.append({'probe': label, 'episode': name, 'change': change,
                    'original_frozen_verdict': original, 'probe_only_verdict': altered,
                    'does_not_establish': 'Semantic correctness or a new campaign result; originals unchanged.'})


name = 'delayed_dependencies-1001-r0-C-b6'; ops = deepcopy(data[name]['operations'])
artifact = next(o for o in ops if o['kind'] == 'create_artifact')
text = artifact['args']['content']
text = text.replace('## Status\n**Calibration ready**', '**Status:** Calibration ready')
text = text.replace('## Risk\n**Field evidence missing**', '**Risk:** Field evidence missing')
assert text != artifact['args']['content']; artifact['args']['content'] = text
record('headings_to_fields', name, 'Move identical field labels and values onto colon lines; preserve all facts, prose, sources and time.', ops, expected=(0, 1))

name = 'interrupted_work-1003-r1-D-b6'; ops = deepcopy(data[name]['operations'])
artifact = next(o for o in ops if o['kind'] == 'create_artifact')
artifact['args']['content'] = re.sub(r'(\*\*(?:Status|Risk):[^\n]+?\*\*) (\[[^\n]+\])', r'\1\n\2', artifact['args']['content'])
record('citation_to_next_line', name, 'Move source citations onto the next line; all words and evidence remain identical.', ops, expected=(0, 1))

name = 'delayed_dependencies-1003-r0-C-b6'; ops = deepcopy(data[name]['operations'])
artifact = next(o for o in ops if o['kind'] == 'create_artifact')
artifact['args']['content'] = re.sub(r'\*\*(Status|Risk):\*\* ([^\n]+)', r'## \1\n\2', artifact['args']['content'])
record('passing_fields_to_headings', name, 'Equivalent label/value layout changed to headings; no factual change.', ops, expected=(1, 0))

ops = deepcopy(data[name]['operations']); artifact = next(o for o in ops if o['kind'] == 'create_artifact')
artifact['args']['content'] += '\n\nAll field tests passed and production deployment was approved.\n'
record('unsupported_prose_ignored', name, 'Inject a plainly unsupported factual assertion, leaving parsed fields intact.', ops, expected=(1, 1))

name = 'memory_revision-1001-r1-D-b6'; x = data[name]
notification = next(n for n in x['outbox'] if n['created'] == 24 and n['status'] == 'available-locally')
ops = deepcopy(x['operations']) + [{'id': 'audit-only-link', 'kind': 'request_clarification', 'created': 24,
    'status': 'succeeded', 'args': {'question': notification['content'], 'evidence_ids': notification['evidence']},
    'result': {'notification_id': notification['id']}}]
record('link_existing_question_to_operation', name, 'Synthetic operation link to the question already delivered at 24; no new text, time or delivery. Such a link is absent historically.', ops, expected=(0, 1))

name = 'deadline_followup-1001-r0-C-b6'; x = data[name]; notes = deepcopy(x['outbox'])
op = next(o for o in x['operations'] if o['kind'] == 'request_clarification')
notification = next(n for n in notes if n['id'] == op['result']['notification_id'])
assert notification['suppressed_reason'] == 'cooldown'
notification['status'] = 'available-locally'; notification['suppressed_reason'] = None
record('hypothetical_delivery_only', name, 'Hypothetically deliver the suppressed question; not evidence it was delivered. Isolates the failed delivery predicate.', outbox=notes, expected=(0, 1))

(AUDIT / 'scorer-probes.json').write_text(json.dumps(results, indent=2)+'\n')
print('PASS: 6 in-memory scorer probes; no original record or scoring implementation changed')
