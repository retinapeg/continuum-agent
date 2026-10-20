from __future__ import annotations
import json
import math
from pathlib import Path
import threading
import time
from .capabilities import Capabilities
from .common import ROOT, FileLock, WallClock, canonical, digest, uid, utc, redact
from .contracts import PROPOSAL, validate
from .database import Database
from .dynamics import AnalyticDynamics, DiscreteDynamics, State, deadline_urgency
from .memory import Memory
from .notifications import Notifications
from .providers import ProviderError

POLICIES = ('A', 'B', 'C', 'D', 'E')


class Runtime:
    def __init__(self, directory: Path, provider, *, policy='D', clock=None, fixtures=None,
                 reflection=60, period=30, context_budget=18000, memory_enabled=True, schedule=None):
        if policy not in POLICIES or reflection < 5 or period < 5:
            raise ValueError('invalid policy or cadence')
        self.directory = directory.resolve()
        fixtures = (fixtures or ROOT / 'fixtures/documents').resolve()
        if not self.directory.is_relative_to(ROOT) or not fixtures.is_relative_to(ROOT):
            raise ValueError('runtime and approved documents must remain inside repository')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ownership = FileLock(self.directory / 'runtime.lock')
        self.db = Database(self.directory / 'agent.sqlite', policy=policy)
        self.provider, self.policy = provider, policy
        self.clock = clock or WallClock(self.db.get('last_clock'))
        self.reflection, self.period, self.context_budget = reflection, period, context_budget
        self.memory_enabled, self.schedule = memory_enabled, schedule
        self.cancel = threading.Event()
        self.wake = threading.Event()
        self.closed = False
        self.memory = Memory(self.db)
        self.notifications = Notifications(self.db)
        self.capabilities = Capabilities(self.db, self.memory, self.notifications, fixtures, self.cancel)
        self.dynamics = DiscreteDynamics() if policy == 'E' else AnalyticDynamics()
        self.db.recover(uid(), self.clock.now())
        self.db.event('runtime.started', {'clock': type(self.clock).__name__, 'restart_gap': getattr(self.clock, 'gap', 0)})
        self.activity = 'idle'

    def observe(self, kind, content, source='owner', event_id=None):
        oid = self.db.observe(self.clock.now(), kind, content, source, event_id)
        self.wake.set()
        return oid

    def goal(self, title, deadline=None, goal_id=None):
        if not isinstance(title,str) or not title.strip() or len(title)>4000:
            raise ValueError('bounded nonempty goal title required')
        if deadline is not None and (not isinstance(deadline,(int,float)) or not math.isfinite(deadline)):
            raise ValueError('finite deadline required')
        title=redact(title)
        gid = goal_id or uid()
        with self.db.transaction() as tx:
            tx.execute("INSERT INTO goals VALUES (?,?,'queued',?,'',?)", (gid, title, deadline, self.clock.now()))
            self.db.event('goal.created', {'id': gid, 'title': title, 'deadline': deadline}, tx=tx)
        self.observe('goal.created', {'id': gid, 'title': title, 'deadline': deadline})
        return gid

    def control(self, action):
        if action in ('paused', 'stopped'):
            self.cancel.set()
        self.db.control(action, self.clock.now())
        if action == 'running':
            self.cancel.clear()
            self.observe('runtime.resume', {})
        self.wake.set()

    def revoke(self, capability):
        self.cancel.set()
        with self.db.transaction() as tx:
            allowed = self.db.get('permissions')
            self.db.set('permissions', [x for x in allowed if x != capability], tx)
            self.db.set('permission_version', self.db.get('permission_version') + 1, tx)
            revoked_ids = {r['id'] for r in tx.execute('SELECT id FROM operations WHERE kind=?', (capability,)).fetchall()}
            self.db.set('approved_operations', [x for x in self.db.get('approved_operations', []) if x not in revoked_ids], tx)
            self.db.set('epoch', self.db.get('epoch') + 1, tx)
            self.db.event('permission.revoked', {'capability': capability}, tx=tx)
        self.wake.set()

    def cancel_goal(self, gid):
        self.cancel.set()
        with self.db.transaction() as tx:
            tx.execute("UPDATE goals SET status='cancelled',updated=? WHERE id=?", (self.clock.now(), gid))
            for op in tx.execute("SELECT id,args FROM operations WHERE status IN ('queued','waiting-for-approval')").fetchall():
                if json.loads(op['args']).get('goal_id') == gid:
                    tx.execute("UPDATE operations SET status='cancelled' WHERE id=?", (op['id'],))
            self.db.set('epoch', self.db.get('epoch') + 1, tx)
        self.observe('goal.cancelled', {'id': gid})

    def context(self, at):
        observations = self.db.rows('SELECT * FROM observations ORDER BY at DESC,rowid DESC LIMIT 12')
        for row in observations:
            row['content'] = json.loads(row['content'])
        observations.reverse()
        goals = self.db.rows('SELECT * FROM goals ORDER BY updated DESC LIMIT 12')
        query = ' '.join(g['title'] for g in goals) + ' ' + ' '.join(canonical(o['content']) for o in observations[-3:])
        memories = self.memory.retrieve(query, at, min(5000, self.context_budget // 3)) if self.memory_enabled else []
        announced = self.db.rows("SELECT * FROM observations WHERE kind='document.available' ORDER BY at")
        docs = []
        self.capabilities.allowed_docs = {}
        for row in announced:
            content = json.loads(row['content'])
            if not content.get('path'):
                continue
            self.capabilities.allowed_docs[content['path']] = row['id']
            docs = [d for d in docs if d['path'] != content['path']]
            docs.append({'id': row['id'], **content})
        actions = self.db.rows('SELECT id,kind,args,result,status FROM operations ORDER BY created DESC LIMIT 10')
        for action in actions:
            action['args'] = json.loads(action['args'])
            action['result'] = json.loads(action['result']) if action['result'] else None
            if action['kind'] == 'read_document' and action['status'] == 'succeeded' and action['args'].get('path') and action['result']:
                for doc in docs:
                    if doc['path'] == action['args']['path'] and not doc.get('content') and doc['id'] == action['result'].get('id'):
                        doc.update(action['result'])
        raw = self.db.get('state')
        state = self.dynamics.evolve(State(**raw) if raw else State(at=at), at)
        payload = {'now': at, 'observations': observations, 'goals': goals, 'memories': memories,
                   'documents': docs, 'recent_actions': actions,
                   'state': None if self.policy == 'E' else state.to_dict(),
                   'capabilities': self.capabilities.describe(),
                   'recent_notifications': self.db.rows('SELECT topic,content,status FROM outbox ORDER BY created DESC LIMIT 5')}
        # Structural removal, never invalid JSON/string slicing. Record exclusions.
        excluded = []
        for key in ('observations', 'recent_actions', 'memories', 'documents'):
            while len(canonical(payload)) > self.context_budget and payload[key]:
                removed = payload[key].pop(0)
                excluded.append({'section': key, 'id': removed.get('id'), 'reason': 'context_budget'})
        if len(canonical(payload)) > self.context_budget:
            raise ValueError('context budget too small for control schema')
        self.db.event('context.selected', {'input_hash': digest(payload), 'memory_ids': [m['id'] for m in payload['memories']],
                                          'model_visible_state': payload['state'], 'chars': len(canonical(payload)),
                                          'budget': self.context_budget, 'excluded': excluded})
        return payload

    def due(self, at, unprocessed):
        if self.schedule is not None:
            return at in self.schedule and at != self.db.get('last_activation')
        if self.policy == 'A':
            return any(r['source'] == 'owner' and r['kind'] in ('user.message', 'goal.created', 'fact.corrected', 'runtime.resume') for r in unprocessed)
        if self.policy == 'B':
            return at >= self.db.get('next_at', 0)
        # C is a strong timestamp/event baseline; D/E add bounded state-triggered reflection.
        relevant = any(r['kind'] != 'distractor' for r in unprocessed)
        return relevant or at >= self.db.get('next_at', 0)

    def tick(self):
        at = self.clock.now()
        if self.db.get('control') != 'running':
            self.activity = self.db.get('control')
            return False
        self.cancel.clear()
        if self.db.get('pending_proposal'):
            self.apply_pending()
        unprocessed = self.db.rows('SELECT * FROM observations WHERE processed=0 ORDER BY at,rowid')
        raw = self.db.get('state')
        state = State(**raw) if raw else State(at=at)
        active = self.db.rows("SELECT * FROM goals WHERE status NOT IN ('succeeded','cancelled','failed')")
        for obs in unprocessed:
            state = self.dynamics.observe(state, max(state.at, min(at, obs['at'])), obs['kind'], len(active))
        derived = self.db.rows("SELECT seq,kind FROM events WHERE seq>? AND kind IN ('memory.conflict','action.failed','notification.delivered') ORDER BY seq", (self.db.get('state_event_cursor',0),))
        for event in derived:
            state = self.dynamics.observe(state, max(state.at,at), event['kind'], len(active))
        state = self.dynamics.evolve(state, max(state.at, at))
        should = self.due(at, unprocessed)
        with self.db.transaction() as tx:
            tx.executemany('UPDATE observations SET processed=1 WHERE id=?', [(r['id'],) for r in unprocessed])
            self.db.set('state', state.to_dict(), tx)
            if derived:self.db.set('state_event_cursor',derived[-1]['seq'],tx)
            self.db.set('last_clock', at, tx)
        # Execute queued, previously validated work even after a restart, without new inference.
        context = None
        queued = self.db.rows("SELECT id FROM operations WHERE status='queued' ORDER BY created")
        if queued:
            context = self.context(at)
            for op in queued:
                self.capabilities.execute(op['id'], at, self.evidence(context))
        if not should:
            return bool(queued)
        if self.schedule is None and not active and not unprocessed:
            self.db.set('next_at', at + self.reflection)
            return False
        # No periodic deliberation while waiting for owner/approval and nothing new.
        if self.schedule is None and not unprocessed and active and all(g['status'] == 'waiting-for-input' for g in active):
            self.db.set('next_at', at + self.reflection)
            return False
        context = context or self.context(at)
        trace, call_id = uid(), uid()
        epoch = self.db.get('epoch')
        self.activity = 'deliberating'
        with self.db.transaction() as tx:
            self.db.set('last_activation',at,tx)
            tx.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (call_id, self.provider.name, self.provider.model, None, 'running', digest(context), None, None, None, None, at))
            self.db.event('deliberation.started', {'call_id': call_id, 'input_hash': digest(context)}, trace=trace,
                          provider=self.provider.name, requested=self.provider.model, status='running', tx=tx)
        self.db.set('next_at', at + self.reflection)
        try:
            def progress(event):
                with self.db.transaction() as tx:
                    if epoch == self.db.get('epoch') and not self.cancel.is_set():
                        self.db.event('provider.progress', event, trace=trace, provider=self.provider.name, requested=self.provider.model, status='running',tx=tx)
            response = self.provider.propose(context, self.cancel, progress)
            # Accounting is independent of accepting or executing the returned proposal.
            with self.db.transaction() as tx:
                self._record_provider_receipt(tx, call_id, trace, response)
            validate(PROPOSAL, response.proposal)
            response.proposal=redact(response.proposal)
            if self.cancel.is_set() or epoch != self.db.get('epoch') or self.db.get('control') != 'running':
                self.db.event('proposal.discarded', {'reason':'control_epoch_changed','call_id':call_id},status='cancelled')
                with self.db.transaction() as tx:
                    tx.execute("UPDATE calls SET status='cancelled' WHERE id=?",(call_id,))
                return True
            with self.db.transaction() as tx:
                if epoch != self.db.get('epoch') or self.cancel.is_set() or self.db.get('control') != 'running':
                    raise ProviderError('control changed before response persistence','cancelled')
                self.db.set('pending_proposal', {'proposal':response.proposal,'context':context,'trace':trace,'at':at,'epoch':epoch,'reply_ids':[o['id'] for o in unprocessed if o['kind']=='user.message']}, tx)
                tx.execute("UPDATE calls SET status='succeeded',reported_model=?,output_hash=?,usage=?,elapsed=? WHERE id=?",
                           (response.reported_model, digest(response.proposal), canonical(response.usage), response.elapsed, call_id))
            if self.cancel.is_set() or epoch != self.db.get('epoch') or self.db.get('control') != 'running':
                self.db.event('proposal.discarded', {'reason': 'control_epoch_changed', 'call_id': call_id}, trace=trace, status='cancelled')
                return True
            self.apply_pending()
        except Exception as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            status = exc.status if isinstance(exc, ProviderError) else 'failed'
            with self.db.transaction() as tx:
                self._record_provider_receipt(tx, call_id, trace, exc)
                tx.execute('UPDATE calls SET status=?,error=? WHERE id=?', (status, redact(str(exc))[:800], call_id))
                self.db.event('deliberation.failed', {'call_id': call_id, 'error': str(exc)[:800],
                              'known_unsent': getattr(exc, 'known_unsent', False)}, trace=trace,
                              provider=self.provider.name, requested=self.provider.model, status=status, tx=tx)
            # No automatic resend of ambiguous provider requests. New observation/owner resumes.
            if status == 'outcome-unknown' and self.db.get('control') != 'stopped':
                self.db.control('paused', at)
        finally:
            self.activity = 'idle' if self.db.get('control') == 'running' else self.db.get('control')
        return True

    def _record_provider_receipt(self, tx, call_id, trace, receipt):
        usage = getattr(receipt, 'usage', None)
        model = getattr(receipt, 'reported_model', None)
        elapsed = getattr(receipt, 'elapsed', None)
        output_bytes = getattr(receipt, 'output_bytes', None)
        if all(value is None for value in (usage, model, elapsed, output_bytes)):
            return
        tx.execute('UPDATE calls SET reported_model=COALESCE(?,reported_model),usage=COALESCE(?,usage),elapsed=COALESCE(?,elapsed) WHERE id=?',
                   (model, canonical(redact(usage)) if usage is not None else None, elapsed, call_id))
        self.db.event('provider.receipt', {'call_id': call_id, 'usage': usage, 'elapsed': elapsed,
                      'output_bytes': output_bytes, 'terminal_subtype': getattr(receipt, 'terminal_subtype', None)},
                      trace=trace, provider=self.provider.name, requested=self.provider.model,
                      reported=model, status=getattr(receipt, 'status', 'succeeded'), tx=tx)

    def apply_pending(self):
        with self.db.lock:
            self._apply_pending()

    def _apply_pending(self):
        pending=self.db.get('pending_proposal')
        if pending and pending['epoch']==self.db.get('epoch') and self.db.get('control')=='running':
            self.apply(pending['proposal'],pending['context'],pending['trace'],pending['at'],pending['epoch'],set(pending['reply_ids']))
        self.db.set('pending_proposal',None)

    @staticmethod
    def evidence(context):
        return {r['id'] for key in ('observations', 'memories', 'documents', 'recent_actions') for r in context[key]}

    def apply(self, proposal, context, trace, at, epoch=None, reply_ids=None):
        with self.db.lock:
            return self._apply(proposal,context,trace,at,epoch,reply_ids)

    def _apply(self, proposal, context, trace, at, epoch=None, reply_ids=None):
        epoch = self.db.get('epoch') if epoch is None else epoch
        def cancelled():
            return self.cancel.is_set() or epoch != self.db.get('epoch') or self.db.get('control') != 'running'
        evidence = self.evidence(context)
        if cancelled():return
        self.db.event('proposal.validated', {'proposal': proposal}, trace=trace)
        for update in proposal['memory_updates']:
            if cancelled(): return
            if not update['evidence_ids'] or not set(update['evidence_ids']) <= evidence:
                raise ValueError('unsupported memory proposal')
            if self.db.rows('SELECT id FROM memories WHERE subject=? AND content=? AND provenance=?', (update['subject'],update['content'],canonical(update['evidence_ids']))):
                continue
            self.memory.add(update['kind'], update['subject'], update['content'], at, update['evidence_ids'],
                            confirmed=False, supersedes=update['supersedes'])
        for action in proposal['actions']:
            if cancelled(): return
            opid = self.capabilities.queue(action, trace, at)
            self.capabilities.execute(opid, at, evidence)
        for goal in proposal['goal_updates']:
            if cancelled(): return
            if not set(goal['evidence_ids']) <= evidence:
                raise ValueError('unsupported goal update')
            if goal['status'] == 'succeeded':
                successful = {r['id'] for r in self.db.rows("SELECT id,args FROM operations WHERE status='succeeded' AND kind='create_artifact'") if json.loads(r['args']).get('goal_id') == goal['id']}
                if not successful.intersection(goal['evidence_ids']):
                    self.db.event('goal.update_rejected', {'id': goal['id'], 'reason': 'completion requires artifact receipt'}, trace=trace)
                    continue
            with self.db.transaction() as tx:
                tx.execute("UPDATE goals SET status=?,updated=? WHERE id=? AND status!='cancelled'", (goal['status'], at, goal['id']))
        if cancelled(): return
        message = proposal['message']
        if set(message['evidence_ids']) <= evidence:
            is_reply = message['reason'] == 'reply' and bool(set(message['evidence_ids']) & (reply_ids or set()))
            self.notifications.offer(message['text'], message['topic'], message['reason'], message['evidence_ids'], at, reply=is_reply)
        delay = self.period if self.policy == 'B' else max(5, min(self.reflection, proposal['next_delay']))
        deadlines = [g['deadline'] for g in context['goals'] if g['deadline'] is not None and g['deadline'] > at]
        if self.policy in ('C', 'D', 'E') and deadlines:
            delay = min(delay, max(5, min(deadlines) - at))
        if self.policy == 'D':
            state = self.db.get('state') or State(at=at).to_dict()
            drive = state['pressure'] + state['uncertainty'] + state['staleness'] + deadline_urgency(at, deadlines)
            delay = max(5, min(self.reflection, delay * (1 + state['cooldown']) / (1 + drive)))
        with self.db.transaction() as tx:
            self.db.set('next_at', at + delay, tx)
            self.db.set('checkpoint_version', self.db.get('checkpoint_version') + 1, tx)
            self.db.event('schedule.updated', {'at': at, 'next_at': at + delay, 'reason': 'policy_and_explicit_deadline',
                                             'summary': proposal['summary']}, trace=trace, tx=tx)

    def serve(self, seconds=None):
        start = time.monotonic()
        from .watcher import FixtureWatcher
        watcher = FixtureWatcher(self)
        while self.db.get('control') != 'stopped' and (seconds is None or time.monotonic() - start < seconds):
            try:
                watcher.poll()
                self.tick()
            except Exception as exc:
                self.db.event('runtime.error', {'error': str(exc)}, status='failed')
                self.control('paused')
            self.wake.wait(min(1.0, max(.1, self.db.get('next_at', 0) - self.clock.now())))
            self.wake.clear()
        self.db.event('runtime.loop_ended', {'elapsed_seconds': time.monotonic() - start})

    def status(self):
        return {'run_id': self.db.run_id, 'control': self.db.get('control'), 'activity': self.activity,
                'policy': self.policy, 'provider': self.provider.name, 'requested_model': self.provider.model,
                'last_real_activity': (self.db.rows('SELECT created_at FROM events ORDER BY seq DESC LIMIT 1') or [{}])[0].get('created_at'),
                'next_at': self.db.get('next_at'), 'checkpoint_version': self.db.get('checkpoint_version'),
                'retention_generation': self.db.get('retention_generation',0),
                'state': self.db.get('state'), 'goals': self.db.rows('SELECT * FROM goals ORDER BY updated DESC'),
                'operations': self.db.rows('SELECT id,kind,status,result FROM operations ORDER BY created DESC LIMIT 30'),
                'notifications': self.db.rows('SELECT * FROM outbox ORDER BY created DESC LIMIT 30'),
                'calls': self.db.rows('SELECT * FROM calls ORDER BY created DESC LIMIT 30'),
                'memories': self.db.rows('SELECT * FROM memories ORDER BY observed DESC LIMIT 50'),
                'artifacts': self.db.rows('SELECT * FROM artifacts ORDER BY created DESC'),
                'conversation': [{'id':r['id'],'at':r['at'],'text':json.loads(r['content']).get('text','')} for r in self.db.rows("SELECT id,at,content FROM observations WHERE kind='user.message' ORDER BY at DESC LIMIT 30")]}

    def close(self):
        if not self.closed:
            self.cancel.set()
            self.db.close()
            self.ownership.close()
            self.closed = True
