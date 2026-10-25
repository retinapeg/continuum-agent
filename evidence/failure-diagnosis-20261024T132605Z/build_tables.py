"""Produce diagnosis tables from extracted immutable evidence, without changing verdicts."""
from collections import Counter
import hashlib
import json
import random
import statistics
from inspect_evidence import AUDIT, ROOT, CAMPAIGN, read_db

details = json.loads((AUDIT / 'episode-evidence.json').read_text())
pairs = json.loads((AUDIT / 'paired-outcomes.json').read_text())
errors = json.loads((AUDIT / 'call-errors.json').read_text())
rows = [json.loads(line) for line in (CAMPAIGN / 'results.jsonl').read_text().splitlines()]


def clean(text):
    return str(text).replace('|', '\\|').replace('\n', '<br>')


def fmt(at):
    return str(int(at))


def questions(x):
    return [n for n in x['outbox'] if n['status'] == 'available-locally' and '?' in n['content']
            and any(word in n['content'].lower() for word in ('format', 'preference', 'prefer', 'table', 'narrative'))]


failures = []
(AUDIT / 'episodes').mkdir(exist_ok=True)
table = ['# Every unsuccessful C/D episode', '',
         'All 32 rows retain the original unsuccessful verdict. Confidence describes the **proximate scoring/delivery mechanism**, not why a stochastic model chose particular wording. JSON contains explicit policy/scenario/repetition and all exact requirements. Times are simulated seconds, horizon 120, budget 6.', '',
         'Artifact rule: one successful `create_artifact` in the inclusive opportunity window, all required source IDs and literal fact phrases, no forbidden stale literals, and exact parsed `Status`/`Risk` values. Parser accepts colon lines or table cells (after removing `**`), not heading/value pairs; trailing citations become part of the value. Clarification rule: one `request_clarification` operation, succeeded, in window, evidence IDs, question mark/topic anchor, and its notification ID available locally. Direct messages are not considered clarification attempts.', '',
         '| Episode (policy / scenario / repetition in ID) | Intended outcome / scoring window | Inputs and availability | Recorded work | Observable failure | Calls / errors / opportunity | Confidence | Evidence |',
         '|---|---|---|---|---|---|---|---|']
for name, x in sorted(details.items()):
    if x['result']['goal_completion']:
        continue
    unit, world = x['unit'], x['world']; opchecks = x['attempt_predicates']
    interventions = [o for o in x['operations'] if o['kind'] in ('create_artifact', 'request_clarification')]
    es = [c for c in x['calls'] if c['error']]
    qs = questions(x) if unit['family'] == 'memory_revision' else []
    if interventions and interventions[0]['kind'] == 'create_artifact':
        assert len(interventions) == 1
        assert opchecks[0]['gates'][0]['failed_checks'] == ['exact_Status_Risk_fields']
        inline = bool(opchecks[0]['gates'][0]['extracted_fields'])
        category = 'field_layout'
        reason = ('Inline citations are captured as part of both field values, which fail exact equality.' if inline else
                  'Status/Risk values are present under Markdown headings, but the parser extracts neither field.')
        actual = f"Artifact {interventions[0]['args']['path']} created at {fmt(interventions[0]['created'])}; correct required source IDs and phrases; within window."
        confidence = 'demonstrated scoring gate; full prose correctness unresolved'
        secondary = ['recorded_call_error'] if es else []
    elif interventions:
        assert len(interventions) == 1
        assert opchecks[0]['gates'][0]['failed_checks'] == ['notification_delivered']
        category = 'clarification_suppressed'
        op = interventions[0]; n = next(n for n in x['outbox'] if n['id'] == op['result']['notification_id'])
        assert n['suppressed_reason'] == 'cooldown'
        recent = max(n0['created'] for n0 in x['outbox'] if n0['status'] == 'available-locally' and n0['created'] < n['created'])
        assert n['created'] - recent < 30
        reason = f"Clarification at {fmt(n['created'])} suppressed by 30s cooldown after message at {fmt(recent)}; operation nevertheless says succeeded."
        actual = f"request_clarification at {fmt(op['created'])}; suppressed notification."
        if qs:
            actual += ' Direct question notifications also available at ' + ', '.join(fmt(q['created']) for q in qs) + ', but unscored.'
        confidence = 'demonstrated suppression and misleading operation receipt; effect on model belief plausible'
        secondary = ['direct_message_ignored'] if qs else []
    else:
        assert unit['family'] == 'memory_revision' and qs
        category = 'clarification_message_only'
        reason = 'No request_clarification operation; locally available direct question(s) are outside the scorer candidate set.'
        actual = 'Direct format question(s) available at ' + ', '.join(fmt(q['created']) for q in qs) + '; no artifact or operation.'
        confidence = 'demonstrated channel mismatch; why tool path was not chosen unresolved'
        secondary = []
    if len(qs) > 1:
        secondary.append('repeated_delivered_questions')
    input_text = []
    for event in world['events']:
        if event['kind'] == 'document.available':
            input_text.append(f"{event['id']} {event['data']['path']} at {event['at']}")
        elif event['kind'] in ('fact', 'status', 'pause', 'resume'):
            input_text.append(f"{event['kind']} at {event['at']}: {event['data'].get('content', event['data'].get('text', ''))}")
    if unit['family'] == 'memory_revision':
        input_text.append('Distractors at 6/12/18/24; both conflicting preference memories retrieved after 24; no context exclusions.')
        assert all(len(r['receipt']['selected']) >= 2 for r in x['retrievals'] if r['at'] >= 24)
    window = world['opportunities'][0]
    requirement = (f"One {window['kind']}, inclusive {window['start']}–{window['end']}; " +
                   ('Status=calibration ready; Risk=' + world['allowed_claims']['Risk'][0] if window['kind']=='artifact' else
                    'delivered linked clarification with question/topic/evidence; wait, do not choose or create a brief.'))
    if unit['family'] == 'deadline_followup':
        requirement = 'One delivery question, scorer inclusive 42–72; public goal says before 72. No document.'
    call_text = ', '.join(fmt(c['created']) for c in x['calls'])
    error_text = '; '.join(f"{fmt(c['created'])}: {c['error']}" for c in es) or 'none recorded'
    refs = {'database': x['database'], 'calls': [c['id'] for c in x['calls']],
            'operations': [o['id'] for o in x['operations']], 'outbox': [n['id'] for n in x['outbox']],
            'artifacts': [a['evidence_path'] for a in x['artifacts']],
            'context_event_sequences': [e['seq'] for e in x['events'] if e['kind']=='context.selected']}
    row = {'episode_id': name, 'policy': unit['condition'], 'scenario': x['result']['scenario'], 'repetition': unit['repetition'],
           'intended_outcome': world['goal'], 'exact_scoring_requirement': {'description':requirement, 'window':window,
                'allowed_claims':world['allowed_claims'], 'forbidden':world['forbidden'], 'operation_predicates':opchecks},
           'relevant_inputs_and_times': world['events'], 'actual_actions': x['operations'], 'notifications': x['outbox'],
           'observable_failure': reason, 'primary_mechanism': category, 'secondary_overlaps': secondary,
           'recorded_call_errors': es, 'calls_used':len(x['calls']), 'call_times':x['result']['call_times'],
           'budget':6, 'deadline':world['deadline'], 'horizon':world['horizon'],
           'missed_opportunity': {'id':window['id'], 'scored_false_negative':1,
                'interpretation':'No temporal miss for artifact cases; the failed scorer predicate is shown separately.'},
           'root_cause_confidence':confidence, 'evidence_references':refs}
    failures.append(row)
    evidence_link = f'[detail](episodes/{name}.md)'
    table.append('| ' + ' | '.join(clean(v) for v in (name, requirement, '; '.join(input_text), actual, reason,
        f"{len(x['calls'])}/6 at {call_text}; errors: {error_text}; deadline {world['deadline']}; one unmatched opportunity", confidence, evidence_link)) + ' |')
    page = [f'# {name}', '', f"Policy **{unit['condition']}**; scenario **{x['result']['scenario']}**; repetition **{unit['repetition']}**. Original goal_completion=0; episode persistence succeeded.",
            '', '## Requirement and diagnosis', '', world['goal'], '', requirement,
            '', '**Observed mechanism:** ' + reason, '', '**Confidence:** ' + confidence,
            '', '**Limits:** The first recorded mismatch is not proof of the model’s internal cause. Exact field matches do not establish unrestricted prose factuality. Secondary overlaps: ' + (', '.join(secondary) or 'none identified') + '.',
            '', '## Inputs and execution', '', *['- '+line for line in input_text], '',
            f"Calls: {call_text} ({len(x['calls'])}/6); deadline {world['deadline']}; horizon 120. Errors: {error_text}.", '',
            '| At | Operation / status | Arguments and result |', '|---|---|---|']
    for op in x['operations']:
        args = {k:v for k,v in op['args'].items() if k!='content'}
        result = {k:v for k,v in (op['result'] or {}).items() if k!='content'}
        page.append(f"| {fmt(op['created'])} | {op['kind']} / {op['status']} | `{op['id']}`; {clean(json.dumps(args))}; {clean(json.dumps(result))} |")
    page += ['', '## Notifications (available locally is not proof a human read them)', '', '| At | Status / suppression | Text / ID |','|---|---|---|']
    for n in x['outbox']:
        page.append(f"| {fmt(n['created'])} | {n['status']} / {n['suppressed_reason']} | {clean(n['content'])}<br>`{n['id']}` |")
    page += ['', '## Artifact and scoring evidence', '']
    for a in x['artifacts']:
        page += [f"[Original artifact](../../../{a['evidence_path']}) · SHA-256 `{a['checksum']}`", '', '```markdown', a['text'].rstrip(), '```', '']
    page += ['Frozen predicate evaluation:', '', '```json', json.dumps(opchecks,indent=2), '```', '',
             f"[Original database](../../../{x['database']}) (open read-only; operation/call/outbox IDs above).",
             '[Extracted evidence](../episode-evidence.json) keyed by this episode ID includes retrieval receipts and event sequence IDs.', '']
    (AUDIT / 'episodes' / (name+'.md')).write_text('\n'.join(page))
assert len(failures) == 32 and sum(not f['recorded_call_errors'] for f in failures) == 29
assert Counter(f['primary_mechanism'] for f in failures) == {'field_layout':23,'clarification_message_only':5,'clarification_suppressed':4}
(AUDIT/'FAILED_EPISODES.md').write_text('\n'.join(table)+'\n')
(AUDIT/'failed-episodes.json').write_text(json.dumps(failures,indent=2,sort_keys=True)+'\n')

# Tie every call error to its original stream/application trace without guessing tool names.
guard = []
for name in sorted({e['episode_id'] for e in errors}):
    db = read_db(CAMPAIGN/'units'/name/'agent/agent.sqlite')
    events = [{**e,'data':json.loads(e['data'])} for e in db['events']]
    for error in [e for e in errors if e['episode_id']==name]:
        start = next(e for e in events if e['kind']=='deliberation.started' and e['data']['payload']['call_id']==error['call_id'])
        trace = start['trace_id']; linked=[e for e in events if e['trace_id']==trace]
        effect = [e['seq'] for e in linked if e['kind']=='action.completed']
        init = [e['data']['payload'] for e in linked if e['kind']=='provider.progress' and e['data']['payload'].get('type')=='provider.initialized']
        if error['error'] != 'unsupported goal update':
            assert not effect
        guard.append({**error,'trace_id':trace,'start_sequence':start['seq'],'completed_effect_event_sequences':effect,
                      'initialized_receipts':init,'requested_ambient_tool_name':None})
(AUDIT/'error-traces.json').write_text(json.dumps(guard,indent=2)+'\n')
lines=['# All 26 recorded call errors','','22 affected episodes: 15 unsuccessful and 7 successful under the frozen rubric. Categories overlap at episode level; they are not exclusive task causes. Unknown usage remains unknown.', '',
       '| Episode | Call time | Error | Frozen task result | Usage present | Call / trace reference |','|---|---|---|---|---|---|']
for e in guard:
    lines.append('| '+' | '.join(clean(v) for v in (e['episode_id'],fmt(e['at']),e['error'],e['goal_completion'],e['usage_present'],f"{e['call_id']} / event {e['start_sequence']} / {e['trace_id']}"))+' |')
lines += ['', 'Read the episode database `experiments/v02/live-heldout-v1/units/<episode>/agent/agent.sqlite` in immutable read-only mode; [error-traces.json](error-traces.json) contains exact IDs and observed init inventories. The unexpected tool name/arguments were not retained; no attribution to a particular tool or malicious intent is possible.', '']
(AUDIT/'CALL_ERRORS.md').write_text('\n'.join(lines))

extra = []
for pair in pairs:
    for policy, times in [('D',pair['D_only_times']),('C',pair['C_only_times'])]:
        x=details[pair[policy]]
        for at in times:
            call=next(c for c in x['calls'] if c['created']==at)
            start=next(e for e in x['events'] if e['kind']=='deliberation.started' and e['data']['payload']['call_id']==call['id'])
            trace=start['trace_id']
            proposals=[e['data']['payload']['proposal'] for e in x['events'] if e['kind']=='proposal.validated' and e['trace_id']==trace]
            operations=[o for o in x['operations'] if o['trace_id']==trace]
            extra.append({'episode':pair[policy], 'policy':policy, 'at':at, 'call_id':call['id'], 'trace_id':trace,
                          'error':call['error'], 'new_operations':operations,
                          'notifications':[n for n in x['outbox'] if n['created']==at], 'proposals':proposals})
(AUDIT/'unmatched-call-work.json').write_text(json.dumps(extra,indent=2)+'\n')
lines=['# Work at unmatched C/D call times', '', '44 D-only timestamps minus 12 C-only timestamps = 32 additional D calls overall. A D-only timestamp is not necessarily an extra call: twelve replace C’s final 84s call with D’s 72s call. These are observed effects, not counterfactual benefits.', '',
       '| Episode | Policy / time | Error | New operations | Available notifications | Proposal summary |','|---|---|---|---|---|---|']
for x in extra:
    lines.append('| '+' | '.join(clean(v) for v in (x['episode'],f"{x['policy']} / {fmt(x['at'])}",x['error'],
         ', '.join(o['kind']+'/'+o['status'] for o in x['new_operations']) or 'none',
         '; '.join(n['content'] for n in x['notifications'] if n['status']=='available-locally') or 'none',
         '; '.join(p['summary'] for p in x['proposals'])) )+' |')
(AUDIT/'CALL_WORK.md').write_text('\n'.join(lines)+'\n')
lines=['# Paired C/D outcomes', '', '| Scenario | Rep | C | D | C calls | D calls | D-only times | C-only times |','|---|---|---|---|---|---|---|---|']
for p in pairs:
    lines.append('| '+' | '.join(str(v) for v in (p['scenario'],p['repetition'],p['C_success'],p['D_success'],len(p['C_times']),len(p['D_times']),p['D_only_times'],p['C_only_times']))+' |')
(AUDIT/'PAIRS.md').write_text('\n'.join(lines)+'\n')

# Recalculate the predeclared interval; this checks arithmetic, not rubric validity.
diffs=[statistics.mean(p['D_success']-p['C_success'] for p in pairs if p['scenario']==scenario) for scenario in sorted({p['scenario'] for p in pairs})]
rng=random.Random(719); draws=sorted(statistics.mean(rng.choices(diffs,k=len(diffs))) for _ in range(2000))
interval={'scenarios':len(diffs),'mean':statistics.mean(diffs),'low':draws[49],'high':draws[1949]}
assert interval==json.loads((CAMPAIGN/'report.json').read_text())['paired_scenario_bootstrap_95']['D-minus-C/budget-6']
packet=json.loads((CAMPAIGN/'human-review-packet.json').read_text())
for sample in packet['samples']:
    x=details[sample['unit']]
    actual=[o for o in x['operations'] if o['kind'] in ('create_artifact','request_clarification')]
    expected=[{**o,'args':json.loads(o['args']),'result':json.loads(o['result']) if o['result'] else None} for o in sample['operations']]
    assert sorted(json.dumps({k:o[k] for k in ('kind','args','status','result')},sort_keys=True) for o in actual)==sorted(json.dumps(o,sort_keys=True) for o in expected)
saved=json.loads((ROOT/'evidence/continuation-20261024/validation.json').read_text())
for name in ('final-runtime.txt','final-legacy.txt'):
    raw=(ROOT/'evidence/continuation-20261024'/name).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==saved['test_logs'][name]['sha256']
    assert raw.decode().rstrip().endswith('OK')
for name,h in saved['tested_source_sha256'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
de_match=0
for d in [r for r in rows if r['condition']=='D']:
    e=next(r for r in rows if r['id']==d['id'].replace('-D-','-E-'))
    de_match+=d['call_times']==e['call_times']
verification={'failed_rows':len(failures),'primary_mechanisms':dict(Counter(f['primary_mechanism'] for f in failures)),
              'call_errors':len(guard),'fresh_interval_recalculation':interval,'D_E_schedule_pairs_equal':de_match,
              'review_packet_samples_checked':len(packet['samples']),'human_review_status':packet['status'],
              'saved_software_test_receipts':{'runtime':96,'legacy':28,'total':124,'freshly_rerun':False,'receipt_and_tested_source_hashes_match':True},
              'new_live_provider_validation':False,'originals_written':False}
(AUDIT/'checks.json').write_text(json.dumps(verification,indent=2)+'\n')
print(json.dumps(verification,indent=2))
