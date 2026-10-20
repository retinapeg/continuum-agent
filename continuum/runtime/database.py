from __future__ import annotations
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
from .common import canonical, digest, redact, uid, utc


class Database:
    def __init__(self, path: Path, run_id=None, policy='D'):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          PRAGMA journal_mode=WAL;
          PRAGMA synchronous=FULL;
          PRAGMA foreign_keys=ON;
          PRAGMA secure_delete=ON;
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL, trace_id TEXT NOT NULL,
            kind TEXT NOT NULL, data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, at REAL NOT NULL,
            kind TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL, processed INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT NOT NULL,
            content TEXT NOT NULL, provenance TEXT NOT NULL, observed REAL NOT NULL, applicable REAL,
            confidence REAL NOT NULL, status TEXT NOT NULL, supersedes TEXT, private INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS retrievals(id TEXT PRIMARY KEY, at REAL NOT NULL, receipt TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS goals(id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
            deadline REAL, plan TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, kind TEXT NOT NULL,
            args TEXT NOT NULL, status TEXT NOT NULL, result TEXT, lease_owner TEXT, lease_until REAL,
            attempt INTEGER NOT NULL DEFAULT 0, permission_version INTEGER NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY, topic TEXT NOT NULL, content TEXT NOT NULL,
            reason TEXT NOT NULL, evidence TEXT NOT NULL, status TEXT NOT NULL, suppressed_reason TEXT,
            created REAL NOT NULL, delivered REAL, UNIQUE(topic,content));
          CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL,
            checksum TEXT NOT NULL, sources TEXT NOT NULL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY, provider TEXT NOT NULL,
            requested_model TEXT, reported_model TEXT, status TEXT NOT NULL, input_hash TEXT NOT NULL,
            output_hash TEXT, usage TEXT, error TEXT, elapsed REAL, created REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS inbox(source TEXT NOT NULL, message_id TEXT NOT NULL, hash TEXT NOT NULL,
            cursor INTEGER NOT NULL, PRIMARY KEY(source,message_id));
        ''')
        self.run_id = self.get('run_id', run_id or uid())
        self.policy = policy
        for key, value in {'schema': 2, 'run_id': self.run_id, 'control': 'running', 'epoch': 0,
                           'permission_version': 0, 'permissions': ['read_document', 'search_memory',
                           'inspect_events', 'update_plan', 'create_artifact', 'request_clarification'],
                           'muted_topics': [], 'next_at': 0.0, 'checkpoint_version': 0}.items():
            if self.get(key) is None:
                self.set(key, value)
        if self.get('schema') != 2:
            raise ValueError('unsupported runtime schema')

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield self.db
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args)]

    def get(self, key, default=None):
        with self.lock:
            row = self.db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set(self, key, value, tx=None):
        with self.lock:
            (tx or self.db).execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, canonical(value)))

    def event(self, kind, payload=None, *, trace=None, status='succeeded', provider=None,
              requested=None, reported=None, workflow=None, node=None, attempt=0, refs=(), tx=None):
        event_id = uid()
        trace = trace or self.run_id
        data = {'schema_version': 'continuum.event.v2', 'event_id': event_id, 'utc': utc(),
                'run_id': self.run_id, 'trace_id': trace, 'span_id': event_id, 'parent_span': None,
                'workflow_id': workflow, 'node_id': node, 'attempt_id': str(attempt),
                'policy': self.policy, 'provider': provider, 'requested_model': requested,
                'reported_model': reported, 'status': status, 'evidence_refs': list(refs),
                'payload': redact(payload or {})}
        with self.lock:
            cur = (tx or self.db).execute('INSERT INTO events(event_id,created_at,trace_id,kind,data) VALUES (?,?,?,?,?)',
                                         (event_id, data['utc'], trace, kind, canonical(data)))
            # Sequence is both queryable and in the serialized event envelope.
            data['sequence'] = cur.lastrowid
            (tx or self.db).execute('UPDATE events SET data=? WHERE event_id=?', (canonical(data), event_id))
        return event_id

    def observe(self, at, kind, content, source='owner', event_id=None):
        event_id = event_id or uid()
        content = redact(content)
        with self.transaction() as tx:
            old = tx.execute('SELECT kind,content,source FROM observations WHERE id=?', (event_id,)).fetchone()
            if old:
                if tuple(old) != (kind, canonical(content), source):
                    raise ValueError('conflicting observation ID')
                return event_id
            tx.execute('INSERT INTO observations VALUES (?,?,?,?,?,0)', (event_id, at, kind, canonical(content), source))
            self.event('observation', {'id': event_id, 'kind': kind, 'content': content, 'source': source}, refs=[event_id], tx=tx)
        return event_id

    def control(self, action, at):
        if action not in ('paused', 'running', 'stopped'):
            raise ValueError('invalid control')
        with self.transaction() as tx:
            self.set('control', action, tx)
            self.set('epoch', self.get('epoch') + 1, tx)
            self.event('control', {'action': action, 'at': at}, tx=tx)

    def recover(self, owner, at):
        """After exclusive process ownership: no old running operation may be alive."""
        with self.transaction() as tx:
            for op in tx.execute("SELECT * FROM operations WHERE status='running'").fetchall():
                # Local content-addressed artifacts can be reconciled; other uncertain effects stay unknown.
                status = 'outcome-unknown'
                if op['kind'] == 'create_artifact':
                    found = tx.execute('SELECT path,checksum FROM artifacts WHERE id=?', (op['id'],)).fetchone()
                    if found:
                        path = self.path.parent / 'artifacts' / found['path']
                        if path.is_file() and digest(path.read_bytes()) == found['checksum']:
                            status = 'succeeded'
                tx.execute('UPDATE operations SET status=?,lease_owner=NULL,lease_until=NULL WHERE id=?', (status, op['id']))
                self.event('recovery', {'operation_id': op['id'], 'status': status, 'previous_owner': op['lease_owner']}, status=status, tx=tx)
            unknown = tx.execute("UPDATE calls SET status='outcome-unknown',error='process restarted before receipt' WHERE status='running'").rowcount
            if unknown and self.get('control') != 'stopped':
                self.set('control','paused',tx)
            self.set('owner', owner, tx)
            self.set('checkpoint_version', self.get('checkpoint_version') + 1, tx)

    def close(self):
        with self.lock:
            self.db.close()
