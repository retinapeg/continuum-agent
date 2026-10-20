from __future__ import annotations
import json
import os
from pathlib import Path
import time
from .common import canonical, confined, digest, uid, redact
from .contracts import CAPABILITIES, validate


class Capabilities:
    def __init__(self, db, memory, notifications, fixture_root: Path, cancel):
        self.db, self.memory, self.notifications = db, memory, notifications
        self.fixture_root, self.cancel = fixture_root.resolve(), cancel
        self.artifact_root = db.path.parent / 'artifacts'
        self.artifact_root.mkdir(exist_ok=True)
        self.allowed_docs = {}

    def describe(self):
        return {name: {'schema': schema, 'timeout_seconds': 3,
                       'scope': 'approved_fixture_documents' if name == 'read_document' else 'current_run_local_only'}
                for name, schema in CAPABILITIES.items()}

    def queue(self, action, trace, at):
        name, args = action['capability'], redact(action['args'])
        validate(CAPABILITIES[name], args)
        opid = digest({'run': self.db.run_id, 'capability': name, 'args': args,
                       'read_revision': trace if name in ('read_document','search_memory','inspect_events') else None})
        permitted = name in self.db.get('permissions')
        with self.db.transaction() as tx:
            tx.execute('INSERT OR IGNORE INTO operations VALUES (?,?,?,?,?,NULL,NULL,NULL,0,?,?)',
                       (opid, trace, name, canonical(args), 'queued' if permitted else 'waiting-for-approval',
                        self.db.get('permission_version'), at))
            self.db.event('permission.checked', {'operation_id': opid, 'capability': name, 'allowed': permitted},
                          trace=trace, status='succeeded' if permitted else 'waiting-for-approval', tx=tx)
        return opid

    def execute(self, opid, at, evidence_ids, crash=None):
        with self.db.lock:
            return self._execute(opid,at,evidence_ids,crash)

    def _execute(self, opid, at, evidence_ids, crash=None):
        if self.cancel.is_set() or self.db.get('control') != 'running':
            return
        with self.db.transaction() as tx:
            row = tx.execute('SELECT * FROM operations WHERE id=?', (opid,)).fetchone()
            if not row or row['status'] != 'queued':
                return
            if row['kind'] not in self.db.get('permissions') and opid not in self.db.get('approved_operations', []):
                tx.execute("UPDATE operations SET status='waiting-for-approval' WHERE id=?", (opid,))
                return
            tx.execute("UPDATE operations SET status='running',lease_owner=?,lease_until=?,attempt=attempt+1 WHERE id=?",
                       (self.db.get('owner'), at + 5, opid))
            self.db.event('action.claimed', {'operation_id': opid}, trace=row['trace_id'], status='running', tx=tx)
        if crash:
            crash('claimed')
        name, args = row['kind'], json.loads(row['args'])
        version = self.db.get('permission_version')
        start = time.monotonic()
        try:
            # Tests can inject a delayed fixture; waits remain cancellable and bounded.
            delay = min(3, self.db.get('fixture_tool_delay', 0))
            if delay and self.cancel.wait(delay):
                raise InterruptedError('cancelled during tool delay')
            if time.monotonic() - start >= 3:
                raise TimeoutError('capability deadline exceeded')
            if self.cancel.is_set() or version != self.db.get('permission_version') or (name not in self.db.get('permissions') and opid not in self.db.get('approved_operations', [])):
                raise InterruptedError('permission revoked or cancelled')
            sources = args.get('sources', args.get('evidence_ids', []))
            if any(s not in evidence_ids for s in sources):
                raise ValueError('unknown or private evidence reference')
            if name == 'read_document':
                if args['path'] not in self.allowed_docs:
                    raise ValueError('document not announced/approved')
                path = confined(self.fixture_root, args['path'], exists=True)
                if path.stat().st_size > 16000:
                    raise ValueError('document too large')
                content = redact(path.read_text())
                result = {'id': self.allowed_docs[args['path']], 'path': args['path'], 'content': content, 'checksum': digest(content.encode())}
            elif name == 'search_memory':
                result = {'matches': self.memory.retrieve(args['query'], at, 4000)}
            elif name == 'inspect_events':
                result = {'observations': self.db.rows('SELECT id,kind,content FROM observations ORDER BY at DESC LIMIT ?', (args['limit'],))}
            elif name == 'update_plan':
                with self.db.transaction() as tx:
                    cur = tx.execute('UPDATE goals SET plan=?,updated=? WHERE id=? AND status!=?', (args['plan'], at, args['goal_id'], 'cancelled'))
                    if not cur.rowcount:
                        raise ValueError('active goal missing')
                result = {'updated': args['goal_id']}
            elif name == 'create_artifact':
                if not sources or not args['content'].strip():
                    raise ValueError('artifact requires evidence and content')
                if not self.db.rows("SELECT id FROM goals WHERE id=? AND status NOT IN ('cancelled','failed')", (args['goal_id'],)):
                    raise ValueError('active goal missing')
                path = confined(self.artifact_root, args['path'])
                if path.suffix not in ('.md', '.txt', '.json'):
                    raise ValueError('only non-executable local artifacts allowed')
                body = args['content'] + '\n\nSources: ' + ', '.join(sources) + '\n'
                checksum = digest(body.encode())
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists():
                    if digest(path.read_bytes()) != checksum:
                        raise ValueError('artifact exists with different content; choose a revision filename')
                else:
                    # Exclusive create prevents overwrite. Unknown partial effect is retained on crash.
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(fd, 'w') as handle:
                        handle.write(body)
                        handle.flush()
                        os.fsync(handle.fileno())
                if crash:
                    crash('effect')
                with self.db.transaction() as tx:
                    tx.execute('INSERT OR IGNORE INTO artifacts VALUES (?,?,?,?,?)', (opid, args['path'], checksum, canonical(sources), at))
                result = {'path': args['path'], 'checksum': checksum, 'sources': sources}
            elif name == 'request_clarification':
                oid = self.notifications.offer(args['question'], args['topic'], 'blocked', sources, at)
                result = {'notification_id': oid, 'channel': 'local'}
            elif name == 'draft_task':
                result = {'draft_only': True, 'task': args, 'sent': False}
            else:
                raise ValueError('unknown capability')
            if crash:
                crash('recorded_effect')
            with self.db.transaction() as tx:
                tx.execute("UPDATE operations SET status='succeeded',result=?,lease_owner=NULL,lease_until=NULL WHERE id=?", (canonical(redact(result)), opid))
                self.db.event('action.completed', {'operation_id': opid, 'capability': name, 'result': result},
                              trace=row['trace_id'], refs=sources, tx=tx)
            if name in ('read_document','search_memory','inspect_events'):
                self.db.observe(at, 'action.result', {'operation_id':opid,'capability':name}, source='capability', event_id=opid+'-result')
        except (ValueError, OSError, TimeoutError, InterruptedError) as exc:
            status = 'cancelled' if isinstance(exc, InterruptedError) else 'failed'
            with self.db.transaction() as tx:
                tx.execute('UPDATE operations SET status=?,result=?,lease_owner=NULL,lease_until=NULL WHERE id=?',
                           (status, canonical({'error': str(exc)}), opid))
                self.db.event('action.failed', {'operation_id': opid, 'error': str(exc)}, trace=row['trace_id'], status=status, tx=tx)
