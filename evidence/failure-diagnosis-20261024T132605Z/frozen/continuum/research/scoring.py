"""Predeclared deterministic scorer. Model self-reports never establish success."""
import re


def markdown_table(text):
    lines=[line.strip() for line in text.splitlines()]
    for i in range(1,len(lines)-1):
        cells=lines[i].strip('|').split('|')
        if len(cells)<2 or not all(re.fullmatch(r'\s*:?-{3,}:?\s*',c) for c in cells):continue
        above=lines[i-1].strip('|').split('|');below=lines[i+1].strip('|').split('|')
        if len(above)==len(cells)==len(below) and all(c.strip() for c in above+below):return True
    return False


def score(world,operations,calls,memories,notifications):
    attempts=[o for o in operations if o['kind'] in ('create_artifact','request_clarification')]
    matched=set();tp=0;latencies=[];stale=0;claims_correct=claims_total=0
    delivered={n['id'] for n in notifications if n['status']=='available-locally'}
    for op in attempts:
        args=op['args'];text=args.get('content',args.get('question',''))
        normalized=text.replace('**','')
        extracted=re.findall(r'(?im)^\s*(Status|Risk)\s*:\s*([^\n]+)',normalized) + re.findall(r'(?im)^\s*\|\s*(Status|Risk)\s*\|\s*([^|]+)\|',normalized)
        extracted=[(key.title(),value) for key,value in extracted]
        stale+=any(x.lower() in normalized.lower() or any((key+': '+value.strip()).lower()==x.lower() for key,value in extracted) for x in world.forbidden)
        valid_claims={key for key,value in extracted if value.strip().lower() in [v.lower() for v in world.allowed_claims.get(key,[])]}
        invalid_claim=any(value.strip().lower() not in [v.lower() for v in world.allowed_claims.get(key,[])] for key,value in extracted)
        for key,value in extracted:
            claims_total+=1;claims_correct+=value.strip().lower() in [v.lower() for v in world.allowed_claims.get(key,[])]
        kind='artifact' if op['kind']=='create_artifact' else 'clarify'
        for window in world.opportunities:
            if window['id'] in matched or kind!=window['kind'] or op['status']!='succeeded':continue
            if not window['start']<=op['created']<=window['end']:continue
            if not set(window['sources'])<=set(args.get('sources',[])):continue
            if not all(token.lower() in text.lower() for token in window['required']):continue
            if any(x.lower() in text.lower() for x in world.forbidden):continue
            if kind=='artifact' and (invalid_claim or not {'Status','Risk'}<=valid_claims):continue
            if kind=='artifact' and world.family=='changed_instructions' and not markdown_table(normalized):continue
            if kind=='clarify':
                result=op.get('result') or {}
                if isinstance(result,str):
                    import json
                    result=json.loads(result)
                if result.get('notification_id') not in delivered:continue
                anchors=('delivery','confirmation','confirm') if world.family=='deadline_followup' else ('format','preference','prefer','table','narrative')
                if not any(word in text.lower() for word in anchors) or '?' not in text:continue
                if not args.get('evidence_ids'):continue
            tp+=1;matched.add(window['id']);latencies.append(op['created']-window['start']);break
    eligible=len(world.opportunities)
    failures=sum(c['status']!='succeeded' for c in calls)
    token_totals={k:0 for k in ('uncached_input','cached_read','cache_creation','output')}
    usage_known=bool(calls)
    estimate=0;estimate_known=bool(calls)
    for call in calls:
        usage=call.get('usage')
        if not usage:usage_known=False;estimate_known=False;continue
        for k in token_totals:
            if usage.get(k) is None:usage_known=False
            else:token_totals[k]+=usage[k]
        if usage.get('api_equivalent_usd') is None:estimate_known=False
        else:estimate+=usage['api_equivalent_usd']
    completed=(len(matched)==eligible and len(attempts)==tp and (eligible>0 or (not attempts and bool(calls) and failures==0)))
    return {'goal_completion':int(completed),'eligible_opportunities':eligible,'interventions':len(attempts),
            'true_positive':tp,'false_positive':len(attempts)-tp,'false_negative':eligible-tp,
            'intervention_precision':tp/len(attempts) if attempts else None,
            'intervention_recall':tp/eligible if eligible else None,
            'appropriate_inaction':int(not attempts) if not eligible else None,
            'supported_fact_accuracy':claims_correct/claims_total if claims_total else None,
            'scored_claims':claims_total,'stale_fact_uses':stale,
            'contradiction_handled':int(completed) if world.family=='memory_revision' else None,
            'appropriate_clarification':int(completed) if any(o['kind']=='clarify' for o in world.opportunities) else None,
            'latency':sum(latencies)/len(latencies) if latencies else None,
            'interruptions':sum(n['status']=='available-locally' and n['reason']!='reply' for n in notifications),
            'provider_calls':len(calls),'provider_failures':failures,'valid_execution':int(failures==0),
            'recovery_success':int(completed) if world.family=='interrupted_work' else None,
            'duplicate_effects':max(0,len(attempts)-len({(o['kind'],str(o['args'])) for o in attempts})),
            'tokens':token_totals if usage_known else None,'token_missing_reason':None if usage_known else 'one or more calls lack complete usage',
            'api_equivalent_usd':estimate if estimate_known else None,'subscription_charge':None,
            'cost_per_verified_outcome':estimate/int(completed) if estimate_known and completed else None}
