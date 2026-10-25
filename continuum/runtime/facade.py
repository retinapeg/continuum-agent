"""Memory-only v1 interface. No runtime loop, dynamics, model or tool execution."""
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID
from .common import FileLock, canonical, digest, uid
from .database import Database
from .memory import Memory

VERSION = 'leo.continuum.v1'


class MemoryFacade:
    def __init__(self, directory):
        self.lock = FileLock(directory / 'memory.lock')
        self.db = Database(directory / 'memory.sqlite')
        self.memory = Memory(self.db)
        self.db.db.executescript('''
          CREATE TABLE IF NOT EXISTS facade_requests(id TEXT PRIMARY KEY, hash TEXT NOT NULL, response TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS confirmations(proposal_id TEXT PRIMARY KEY, binding TEXT NOT NULL,
            decision_ref TEXT NOT NULL, approved INTEGER NOT NULL, memory_id TEXT);
        ''')
        self.db.recover(uid(), time.time())

    def close(self):
        self.db.close()
        self.lock.close()

    def row(self, mid):
        rows = self.db.rows('SELECT * FROM memories WHERE id=?', (mid,))
        if not rows:
            raise ValueError('unknown memory')
        row = rows[0]
        row['provenance'] = json.loads(row['provenance'])
        # Status is mutable; binding covers immutable proposal terms only.
        row['binding'] = digest({k: row[k] for k in ('id', 'kind', 'subject', 'content', 'provenance', 'supersedes', 'private')})
        return row

    def handle(self, request):
        if set(request) != {'version', 'request_id', 'op', 'args'} or request['version'] != VERSION:
            raise ValueError('unsupported envelope')
        UUID(request['request_id'])
        op, args = request['op'], request['args']
        fields = {'health': set(), 'snapshot': set(), 'observe': {'source_id', 'text'},
                  'propose': {'source_id', 'kind', 'subject', 'content'},
                  'decide': {'proposal_id', 'binding', 'approve', 'decision_ref'},
                  'retrieve': {'query'}, 'events': {'after'}}
        if op not in fields or not isinstance(args, dict) or set(args) != fields[op]:
            raise ValueError('unknown operation or fields')
        if op in ('health', 'snapshot', 'events'):
            return {'version': VERSION, 'request_id': request['request_id'], 'result': self.perform(op, args)}
        with self.db.transaction() as tx:
            old = tx.execute('SELECT * FROM facade_requests WHERE id=?', (request['request_id'],)).fetchone()
            fingerprint = digest(request)
            if old:
                if old['hash'] != fingerprint:
                    raise ValueError('changed-content replay')
                return json.loads(old['response'])
            value = self.perform(op, args)
            response = {'version': VERSION, 'request_id': request['request_id'], 'result': value}
            tx.execute('INSERT INTO facade_requests VALUES(?,?,?)', (request['request_id'], fingerprint, canonical(response)))
            return response

    def perform(self, op, a):
        if op == 'health':
            return {'status': 'ok', 'mode': 'memory-only', 'pid': os.getpid()}
        if op == 'snapshot':
            return {'memories': [self.row(r['id']) for r in self.db.rows(
                "SELECT id FROM memories WHERE status IN ('proposed','confirmed','conflicted') ORDER BY observed DESC LIMIT 20")]}
        if op == 'observe':
            UUID(a['source_id'])
            if not isinstance(a['text'], str) or not 1 <= len(a['text']) <= 12000:
                raise ValueError('bounded source text required')
            return {'source_id': self.db.observe(time.time(), 'leo.conversation', {'text': a['text']},
                                                  source='leo-os', event_id=a['source_id'])}
        if op == 'propose':
            rows = self.db.rows('SELECT content FROM observations WHERE id=? AND source=?', (a['source_id'], 'leo-os'))
            if not rows or a['kind'] not in ('preference', 'fact'):
                raise ValueError('known source and supported kind required')
            # First slice is user-selected, verbatim evidence, not model inference.
            if not isinstance(a['content'], str) or not a['content'].strip() or a['content'] not in json.loads(rows[0]['content'])['text']:
                raise ValueError('proposal must quote its source')
            if not isinstance(a['subject'], str) or not 1 <= len(a['subject']) <= 200:
                raise ValueError('bounded subject required')
            mid = self.memory.add(a['kind'], a['subject'], a['content'], time.time(), [a['source_id']], private=True)
            return self.row(mid)
        if op == 'decide':
            if type(a['approve']) is not bool:
                raise ValueError('explicit boolean decision required')
            UUID(a['decision_ref'])
            row = self.row(a['proposal_id'])
            if row['binding'] != a['binding']:
                raise ValueError('stale proposal binding')
            old = self.db.rows('SELECT * FROM confirmations WHERE proposal_id=?', (row['id'],))
            if old:
                if bool(old[0]['approved']) != a['approve']:
                    raise ValueError('decision conflict')
                return {'proposal_id': row['id'], 'memory_id': old[0]['memory_id'], 'approved': a['approve']}
            if row['status'] != 'proposed':
                raise ValueError('pending proposal required')
            mid = self.memory.confirm(row['id'], time.time(), a['decision_ref']) if a['approve'] else None
            if not a['approve']:
                self.db.db.execute("UPDATE memories SET status='rejected' WHERE id=?", (row['id'],))
                self.db.event('memory.rejected', refs=[row['id'], a['decision_ref']])
            self.db.db.execute('INSERT INTO confirmations VALUES(?,?,?,?,?)',
                               (row['id'], a['binding'], a['decision_ref'], int(a['approve']), mid))
            return {'proposal_id': row['id'], 'memory_id': mid, 'approved': a['approve']}
        if op == 'retrieve':
            if not isinstance(a['query'], str) or not 1 <= len(a['query']) <= 500:
                raise ValueError('bounded query required')
            memories = self.memory.retrieve(a['query'], time.time(), include_private=True, confirmed_only=True)
            for memory in memories:
                memory['provenance'] = json.loads(memory['provenance'])
            return {'memories': memories}
        if op == 'events':
            if type(a['after']) is not int or a['after'] < 0:
                raise ValueError('invalid cursor')
            return {'events': self.db.rows('SELECT seq,kind,data FROM events WHERE seq>? ORDER BY seq LIMIT 20', (a['after'],))}
        raise ValueError('unsupported operation')


def main():
    os.umask(0o077)
    facade = MemoryFacade(Path(sys.argv[1]).resolve())
    try:
        while line := sys.stdin.buffer.readline(262145):
            try:
                if len(line) > 262144:
                    raise ValueError('message too large')
                request = json.loads(line)
                result = facade.handle(request)
            except Exception as error:
                result = {'error': str(error)[:240]}
            print(canonical(result), flush=True)
    finally:
        facade.close()


if __name__ == '__main__':
    main()
