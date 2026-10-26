'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const colors = ['#77b9ff', '#edbd73', '#b8a0f5', '#8fe3c0'];
  const names = ['Fixed period', 'Event / deadline', 'Original hybrid', 'Uncertainty'];
  const descriptions = ['Observe at a fixed interval', 'Respond to events and deadlines', 'Preserved continuous-state equations', 'Observe when uncertainty warrants it'];
  let state = null, selected = null, busy = false, formInitialized = false;
  let lastPaint = 0, shownPosition = 0, targetPosition = 0, renderedState = "", truthHidden = false;
  const truthVisible = () => !!state?.revealed && !truthHidden;
  const number = (x, digits = 2) => typeof x === 'number' && Number.isFinite(x) ? x.toFixed(digits) : '—';
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const node = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; };
  function error(message) { $('error').textContent = message || ''; $('error').hidden = !message; }
  async function request(path, body) {
    const options = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
    const response = await fetch('/api/' + path, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || ('Request failed (' + response.status + ')'));
    return result;
  }
  async function act(path, body = {}) {
    if (busy) return;
    busy = true; document.body.classList.add('busy'); error('');
    try { state = await request(path, body); render(); }
    catch (e) { error(e.message); }
    finally { busy = false; document.body.classList.remove('busy'); }
  }
  function policyIndex(policy) { return Math.max(0, state.policies.findIndex(p => p.id === policy.id)); }
  function shortName(policy, index) { return names[index] || policy.label || policy.id; }
  function eventKind(event) { return String(event.kind || '').split('.').pop(); }
  function policyEvents(policy) { return (policy.events || []).filter(e => ['observe','think','alert'].includes(eventKind(e))); }
  function receipt(event, policy) {
    $('receipt-title').textContent = (policy.label || policy.id) + ' · ' + (event.kind || 'operation');
    $('receipt-summary').textContent = 'Simulation t = ' + number(event.time, 1) + ' s · status: ' + (event.status || 'unrecorded') + '. This is the recorded outcome, not a proposed effect.';
    $('receipt-json').textContent = JSON.stringify(event, null, 2);
    $('receipt-refs').replaceChildren();
    if (event.refs?.length) { $('receipt-refs').append(node('span', '', 'Evidence: ')); event.refs.forEach(ref => { const sourcePolicy = state.policies.find(p => (p.events || []).some(e => e.id === ref)); const source = sourcePolicy?.events.find(e => e.id === ref); if (source) { const button = node('button', 'reference-button', ref); button.addEventListener('click', () => receipt(source, sourcePolicy)); $('receipt-refs').append(button); } else { $('receipt-refs').append(node('span', '', ref + ' (not in this view)')); } }); }
    $('receipt-dialog').showModal();
  }
  function makeBudget(label, used, limit, color) {
    const group = node('div');
    const line = node('div', 'budget-line'); line.append(node('span', '', label), node('strong', '', (used ?? 0) + ' / ' + (limit ?? '—')));
    const track = node('div', 'budget-track'), fill = node('i'); fill.style.width = (limit ? Math.min(100, 100 * (used || 0) / limit) : 0) + '%'; fill.style.background = color; track.append(fill); group.append(line, track); return group;
  }
  function renderPolicies() {
    const container = $('policy-cards'); container.replaceChildren();
    state.policies.forEach((p, i) => {
      const card = node('button', 'policy-card' + (p.id === selected ? ' selected' : ''));
      card.type = 'button'; card.style.setProperty('--policy-color', colors[i]); card.setAttribute('aria-pressed', p.id === selected ? 'true' : 'false');
      card.title = i === 2 ? 'Oscillator adaptation using preserved v0.2 scheduling equations; this is a new task, not the historical experiment.' : (p.label || p.id);
      const heading = node('div', 'policy-name'); heading.append(node('span', '', shortName(p, i)), node('i', 'policy-dot'));
      const last = (p.history || []).at(-1), budget = p.budget || {};
      const activity = state.status === 'completed' ? 'Run complete' : last?.activity === 'sleep' ? 'Sleeping' : last?.activity === 'observe' ? 'Observing' : last?.activity === 'think' ? 'Estimating' : 'Ready';
      card.append(heading, node('div', 'policy-description', descriptions[i] || ''), node('div', 'policy-state', activity));
      card.append(makeBudget('Observations', budget.observations, budget.observation_limit, colors[i]));
      card.append(makeBudget('Inferences', budget.inferences, budget.inference_limit, colors[i]));
      const actions = node('div', 'budget-line'); actions.append(node('span', '', 'Actions'), node('strong', '', (budget.actions || 0) + ' / ' + (budget.action_limit ?? '—'))); card.append(actions);
      if (p.metrics) { const stats = node('div', 'policy-quality'); stats.textContent = '95% coverage ' + (finite(p.metrics.coverage95) ? number(p.metrics.coverage95 * 100, 0) + '%' : '—'); card.append(stats); }
      const failures = p.metrics?.failures ?? (p.events || []).filter(e => !['succeeded','sleep','success'].includes(e.status)).length;
      if (failures) card.append(node('div', 'policy-failure', failures + ' failed operation' + (failures === 1 ? '' : 's') + ' · inspect timeline'));
      card.addEventListener('click', () => { selected = p.id; renderPolicies(); renderBelief(); paintChart(); });
      container.append(card);
    });
  }
  function renderTimeline() {
    const container = $('timeline'); container.replaceChildren(); let count = 0;
    state.policies.forEach((p, i) => {
      const row = node('div', 'timeline-row'); row.append(node('span', 'timeline-name', ['Periodic','Event','Hybrid','Uncertainty'][i] || p.id));
      const track = node('div', 'timeline-track');
      policyEvents(p).forEach(e => {
        const kind = eventKind(e), failed = !['succeeded','success'].includes(e.status);
        const mark = node('button', 'timeline-mark ' + kind + (failed ? ' failed' : ''));
        mark.style.left = Math.max(0, Math.min(100, 100 * e.time / state.horizon)) + '%';
        mark.title = shortName(p, i) + ': ' + kind + ' · ' + number(e.time, 1) + 's · ' + e.status;
        mark.setAttribute('aria-label', mark.title); mark.addEventListener('click', () => receipt(e, p)); track.append(mark);
      });
      count += (p.events || []).length; row.append(track); container.append(row);
    });
    $('receipt-count').textContent = count + ' operations';
  }
  function renderBelief() {
    const p = state.policies.find(p => p.id === selected) || state.policies[0]; if (!p) return;
    const b = p.belief || {}, i = policyIndex(p);
    $('belief-policy').textContent = shortName(p, i); $('belief-policy').style.color = colors[i];
    $('belief-position').textContent = number(b.x, 3); $('belief-velocity').textContent = number(b.v, 3);
    $('belief-uncertainty').textContent = number(b.std ?? Math.sqrt(b.variance), 3);
    const lastObservation = typeof b.last_observation === 'object' ? b.last_observation?.time : b.last_observation;
    $('belief-age').textContent = finite(lastObservation) ? number(Math.max(0, state.time - lastObservation), 1) + 's' : '—';
    const event = (p.events || []).at(-1), detail = event?.detail;
    const reason = typeof detail === 'string' ? detail : detail?.reason || detail?.message || detail?.decision;
    $('belief-reason').textContent = reason || (event ? event.kind + ' · ' + event.status + ' at ' + number(event.time, 1) + 's. Select a timeline mark for the full receipt.' : 'No policy decision yet.');
    if (finite(b.x)) targetPosition = b.x;
    $('physical-label').textContent = truthVisible() ? 'Revealed true displacement' : shortName(p, i) + ' estimate';
    if (truthVisible() && state.truth?.length) targetPosition = state.truth.at(-1).x;
    $('spring').style.stroke = truthVisible() ? '#f0f6ff' : colors[i]; $('mass').style.stroke = truthVisible() ? '#f0f6ff' : colors[i];
  }
  function renderMetrics() {
    const specs = [
      ['Prediction error', 'rmse', 'RMSE ↓', 'Lower is better; scored against hidden position.'],
      ['Detection delay', 'detection_delay', 'seconds ↓', 'Missed changes remain separate from detected delays.'],
      ['False alarms', 'false_alarms', 'count ↓', 'Alerts with no matching hidden change.'],
      ['Resource cost', 'cost', 'units ↓', 'Observation, inference and action costs.']
    ];
    $('metrics').replaceChildren();
    specs.forEach(([label, key, unit, note]) => {
      const group = node('div', 'metric-group'), heading = node('div', 'metric-title', label); heading.append(node('small', '', unit)); group.append(heading);
      const max = Math.max(1e-9, ...state.policies.map(p => finite(p.metrics?.[key]) ? p.metrics[key] : 0));
      state.policies.forEach((p, i) => {
        const value = p.metrics?.[key], row = node('div', 'metric-bar-row'); row.append(node('span', 'metric-abbr', ['P','E','H','U'][i]));
        const track = node('div', 'metric-track'), fill = node('i'); fill.style.background = colors[i]; fill.style.width = finite(value) ? Math.max(0, value / max * 100) + '%' : '0%'; track.append(fill);
        row.append(track, node('span', 'metric-value', number(value, key === 'false_alarms' ? 0 : 2))); group.append(row);
      }); group.append(node('div', 'metric-note', note)); $('metrics').append(group);
    });
    const detail = $('scoring-detail'); detail.replaceChildren();
    if (state.status === 'completed') {
      const table = node('table'), head = node('thead'), headings = node('tr'); ['Calibration / reliability','95% coverage','NLL','Missed changes','Failures'].forEach(label => headings.append(node('th','',label))); head.append(headings); table.append(head);
      const body = node('tbody'); state.policies.forEach((p,i) => {const row = node('tr'), m=p.metrics||{}; row.append(node('td','',shortName(p,i)),node('td','',finite(m.coverage95)?number(m.coverage95*100,1)+'%':'—'),node('td','',number(m.nll,3)),node('td','',String(m.missed_changes??'—')),node('td',m.failures?'failure-cell':'',String(m.failures??'—')));body.append(row);});table.append(body);detail.append(table);
    }
    $('metrics-note').textContent = state.status === 'completed' ? 'Independent scorer · this exploratory run is not the frozen held-out campaign.' : 'Scores appear after the run. No hidden truth is sent to policies.';
    $('result-label').textContent = state.status === 'completed' ? 'MEASURED' : 'AWAITING RUN';
  }
  function renderLegend() {
    $('chart-legend').replaceChildren(); state.policies.forEach((p,i) => {const item=node('span','legend-item'), line=node('i','legend-line');line.style.background=colors[i];item.append(line,node('span','',shortName(p,i)));$('chart-legend').append(item);});
    if (truthVisible()) {const item=node('span','legend-item'),line=node('i','legend-line');line.style.background='#f0f6ff';item.append(line,node('span','','Truth'));$('chart-legend').append(item);}
  }
  function render() {
    if (!state || !Array.isArray(state.policies)) return;
    renderedState = JSON.stringify(state);
    if (!state.revealed) truthHidden = false;
    $('connection-dot').parentElement.classList.add('connected'); $('connection-label').textContent = 'Local simulator connected';
    if (!selected || !state.policies.some(p=>p.id===selected)) selected=state.policies.at(-1)?.id;
    if (!formInitialized) { const c=state.config||{}; Object.entries({'scenario':c.scenario,'seed':c.seed,'duration':state.horizon,'observation-budget':c.observation_budget,'inference-budget':c.inference_budget,'noise':c.noise,'damping':c.damping}).forEach(([id,value])=>{if(value!==undefined)$(id).value=value;});formInitialized=true; }
    $('sim-time').textContent=number(state.time,1); $('sim-horizon').textContent=number(state.horizon,0);$('run-status').textContent=state.status;
    $('play').textContent=state.status==='running'?'Ⅱ Pause':state.status==='completed'?'↺ Run again':'▶ Run';
    $('step').disabled=state.status==='running'||state.status==='completed';$('inject').disabled=state.status==='completed';
    $('reveal').disabled=state.status!=='completed';$('reveal').checked=truthVisible();$('reveal-note').textContent=state.status==='completed'?'scored independently':'after run';
    $('mode-label').textContent=state.mode==='replay'?'Deterministic replay':state.mode==='live'?'Live Claude pilot':'Deterministic experiment';
    $('mode-detail').textContent=state.mode==='live'?'Actual CLI receipts · bounded calls':state.mode==='replay'?'Recorded world · no model calls':'Classical estimation · no model calls';
    $('live-status').textContent=state.live?.status==='not_run'?'Explicit opt-in required':state.live?.status||'Explicit opt-in required';
    $('live-detail').textContent=state.live?.message||'This screen makes no live model calls. Deterministic calculations are labelled as such.';
    $('run-id').textContent='RUN '+(state.run_id||'—')+' · SEED '+(state.config?.seed??'—');
    $('chart-empty').hidden=state.policies.some(p=>(p.history||[]).length>1);
    $('world-explainer').textContent=truthVisible()?'White is the recorded hidden trajectory. Coloured lines are policy estimates; the selected band is its 95% uncertainty.':'Shaded bands show 95% estimated uncertainty. The world’s true position stays hidden until the run ends.';
    renderPolicies();renderTimeline();renderBelief();renderMetrics();renderLegend();paintChart();
  }
  function paintChart() {
    const canvas=$('trajectory'),box=canvas.getBoundingClientRect(); if (!box.width||!box.height) return;
    const dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);
    const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);const w=box.width,h=box.height,left=42,right=20,top=35,bottom=29,plotW=w-left-right,plotH=h-top-bottom;
    const policies=state?.policies||[],horizon=state?.horizon||120;
    let range=1.3;
    policies.forEach(p=>(p.history||[]).forEach(r=>{if(finite(r.x))range=Math.max(range,Math.abs(r.x)+Math.min(2,(r.std||0)*1.96));if(finite(r.observation?.value))range=Math.max(range,Math.abs(r.observation.value));}));
    if(truthVisible())(state.truth||[]).forEach(r=>{range=Math.max(range,Math.abs(r.x));});range=Math.min(8,Math.ceil(range*2)/2);
    const x=t=>left+(t/horizon)*plotW,y=v=>top+plotH/2-(v/range)*plotH/2;
    ctx.font='9px ui-monospace, monospace';ctx.lineWidth=1;ctx.textBaseline='middle';
    [-1,-.5,0,.5,1].forEach(f=>{const yy=y(f*range);ctx.beginPath();ctx.strokeStyle=f===0?'#34414c':'#202a35';ctx.setLineDash(f===0?[]:[2,4]);ctx.moveTo(left,yy);ctx.lineTo(w-right,yy);ctx.stroke();ctx.fillStyle='#526476';ctx.textAlign='right';ctx.fillText((f*range).toFixed(1),left-9,yy);});ctx.setLineDash([]);
    for(let i=0;i<=6;i++){const t=horizon*i/6,xx=x(t);ctx.beginPath();ctx.strokeStyle='#1c2732';ctx.moveTo(xx,top);ctx.lineTo(xx,h-bottom);ctx.stroke();ctx.fillStyle='#526476';ctx.textAlign='center';ctx.fillText(number(t,0),xx,h-12);}
    const active=policies.find(p=>p.id===selected),rows=(active?.history||[]).filter(r=>finite(r.x)&&finite(r.std));
    if(rows.length>1){const color=colors[policies.indexOf(active)];ctx.beginPath();rows.forEach((r,i)=>{if(i===0)ctx.moveTo(x(r.time),y(r.x+1.96*r.std));else ctx.lineTo(x(r.time),y(r.x+1.96*r.std));});[...rows].reverse().forEach(r=>ctx.lineTo(x(r.time),y(r.x-1.96*r.std)));ctx.closePath();ctx.fillStyle=color+'18';ctx.fill();}
    const line=(rows,color,width,dash=[])=>{ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);rows.forEach((r,i)=>{if(i===0)ctx.moveTo(x(r.time),y(r.x));else ctx.lineTo(x(r.time),y(r.x));});ctx.stroke();ctx.setLineDash([]);};
    ctx.save();ctx.beginPath();ctx.rect(left,top,plotW,plotH);ctx.clip();
    policies.forEach((p,i)=>line((p.history||[]).filter(r=>finite(r.x)),colors[i]+(p.id===selected?'':'90'),p.id===selected?1.9:1.2));
    if(truthVisible())line(state.truth||[],'#f0f6ff',1.6,[4,4]);
    (active?.history||[]).forEach(r=>{const obs=r.observation;if(obs&&finite(obs.value)){ctx.beginPath();ctx.arc(x(r.time),y(obs.value),2.8,0,Math.PI*2);ctx.fillStyle=String(obs.status).includes('rejected')?'#ff8e8e':colors[policies.indexOf(active)];ctx.fill();ctx.strokeStyle='#11171e';ctx.lineWidth=1;ctx.stroke();}});ctx.restore();
    if(state&&state.time>0){ctx.beginPath();ctx.strokeStyle='#586975';ctx.lineWidth=1;ctx.setLineDash([3,4]);ctx.moveTo(x(state.time),top);ctx.lineTo(x(state.time),h-bottom);ctx.stroke();ctx.setLineDash([]);const r=(active?.history||[]).at(-1);if(r&&finite(r.x)){ctx.beginPath();ctx.arc(x(r.time),y(r.x),3.5,0,Math.PI*2);ctx.fillStyle=colors[policies.indexOf(active)];ctx.fill();}}
  }
  function animate(now){if(now-lastPaint>25){shownPosition+=(targetPosition-shownPosition)*.16;const center=110+Math.max(-1.6,Math.min(1.6,shownPosition))*30;const start=24,end=center,segments=12,step=(end-start)/segments;let d='M16 25H24';for(let i=1;i<segments;i++)d+='L'+(start+i*step)+' '+(i%2?16:34);d+='L'+end+' 25';$('spring').setAttribute('d',d);$('mass').setAttribute('x',String(center));lastPaint=now;}requestAnimationFrame(animate);}
  $('setup-form').addEventListener('submit',event=>{event.preventDefault();$('injection-status').textContent='Interactive runs are exploratory.';act('start',{scenario:$('scenario').value,seed:Number($('seed').value),horizon:Number($('duration').value),observation_budget:Number($('observation-budget').value),inference_budget:Number($('inference-budget').value),noise:Number($('noise').value),damping:Number($('damping').value)});});
  $('play').addEventListener('click',async()=>{if(!state)return;if(state.status==='completed'){await act('replay');if(state.status!=='completed')await act('control',{action:'resume',speed:Number($('speed').value)});}else await act('control',{action:state.status==='running'?'pause':'resume',speed:Number($('speed').value)});});
  $('step').addEventListener('click',()=>act('step'));
  $('replay').addEventListener('click',()=>act('replay'));
  $('speed').addEventListener('change',()=>{if(state?.status==='running')act('control',{action:'resume',speed:Number($('speed').value)});});
  $('inject').addEventListener('click',async()=>{await act('inject',{kind:$('injection').value==='event'?'event':'change',omega:1.4,damping:0.03});if(!$('error').textContent)$('injection-status').textContent='Injection recorded for all four policies.';});
  $('reveal').addEventListener('change',()=>{truthHidden=!$('reveal').checked;if(!truthHidden&&!state.revealed)act('reveal');else render();});
  $('close-receipt').addEventListener('click',()=>$('receipt-dialog').close());$('receipt-dialog').addEventListener('click',e=>{if(e.target===$('receipt-dialog'))$('receipt-dialog').close();});
  new ResizeObserver(paintChart).observe($('trajectory'));
  async function poll(){if(!busy){try{state=await request('state');if(JSON.stringify(state)!==renderedState)render();}catch(e){$('connection-dot').parentElement.classList.remove('connected');$('connection-label').textContent='Simulator disconnected';error(e.message);}}setTimeout(poll,350);}
  requestAnimationFrame(animate);poll();
})();
