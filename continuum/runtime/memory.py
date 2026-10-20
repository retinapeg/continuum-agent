from __future__ import annotations
import json
import math
import re
from .common import canonical, redact, uid


def terms(text):
    return set(re.findall(r'[a-z0-9]{2,}', text.lower()))


class Memory:
    def __init__(self, db):
        self.db = db

    def add(self, kind, subject, content, at, provenance, *, confirmed=False,
            supersedes=None, confidence=0.7, applicable=None, private=False):
        if kind not in ('episode', 'fact', 'preference', 'goal', 'question'):
            raise ValueError('invalid memory kind')
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('invalid confidence')
        subject,content = redact(subject),redact(content)
        if len(content) > 12000 or not content.strip() or not provenance:
            raise ValueError('bounded content and provenance required')
        mid = uid()
        status = 'confirmed' if confirmed else 'proposed'
        with self.db.transaction() as tx:
            if supersedes:
                old = tx.execute('SELECT * FROM memories WHERE id=?', (supersedes,)).fetchone()
                if not old or old['status'] == 'forgotten':
                    raise ValueError('superseded memory missing')
                if confirmed:
                    tx.execute("UPDATE memories SET status='superseded' WHERE id=?", (supersedes,))
                else:
                    # A model cannot silently revoke an owner's assertion.
                    status = 'proposed'
            elif kind in ('fact', 'preference'):
                conflicts = tx.execute("SELECT * FROM memories WHERE subject=? AND kind=? AND status='confirmed' AND content!=?",
                                       (subject, kind, content)).fetchall()
                if conflicts and confirmed:
                    status = 'conflicted'
                    tx.execute("UPDATE memories SET status='conflicted' WHERE subject=? AND kind=? AND status='confirmed'", (subject, kind))
                    self.db.event('memory.conflict', {'subject': subject, 'ids': [r['id'] for r in conflicts]}, tx=tx)
            tx.execute('INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (mid, kind, subject, content, canonical(provenance), at, applicable,
                        confidence, status, supersedes, int(private)))
            self.db.event('memory.updated', {'id': mid, 'kind': kind, 'status': status, 'supersedes': supersedes}, refs=provenance, tx=tx)
        return mid

    def retrieve(self, query, at, budget=5000, include_private=False):
        if budget < 0 or budget > 32000:
            raise ValueError('invalid retrieval budget')
        rows = self.db.rows("SELECT * FROM memories WHERE status IN ('confirmed','conflicted','proposed') ORDER BY observed DESC,id")
        q = terms(query)
        ranked, excluded = [], []
        for row in rows:
            if row['private'] and not include_private:
                excluded.append({'id': row['id'], 'reason': 'private'})
                continue
            words = terms(row['subject'] + ' ' + row['content'])
            score = len(q & words) / max(1, len(q | words))
            if not score:
                excluded.append({'id': row['id'], 'reason': 'no_lexical_overlap'})
                continue
            ranked.append((score, row))
        ranked.sort(key=lambda x: (-x[0], -x[1]['observed'], x[1]['id']))
        selected, used = [], 0
        for score, row in ranked:
            item = {k: row[k] for k in ('id', 'kind', 'subject', 'content', 'status', 'confidence', 'provenance')}
            item['score'] = score
            size = len(canonical(item))
            if used + size > budget:
                excluded.append({'id': row['id'], 'reason': 'context_budget'})
                continue
            selected.append(item)
            used += size
        receipt = {'query': redact(query), 'selected': [{'id': x['id'], 'score': x['score']} for x in selected],
                   'budget_chars': budget, 'used_chars': used, 'exclusions': excluded,
                   'method': 'lexical_jaccard_v1'}
        with self.db.transaction() as tx:
            tx.execute('INSERT INTO retrievals VALUES (?,?,?)', (uid(), at, canonical(receipt)))
            self.db.event('memory.retrieved', receipt, tx=tx)
        return selected

    def forget(self, mid):
        rows = self.db.rows('SELECT * FROM memories WHERE id=?', (mid,))
        if not rows:
            raise ValueError('unknown memory')
        target = rows[0]
        # Conservative policy: remove all derived run context, not a speculative textual
        # dependency graph. Original unrelated assertions remain, episodic/derived content goes.
        with self.db.transaction() as tx:
            tx.execute("UPDATE memories SET content='',subject='',provenance='[]',status='forgotten',confidence=0 WHERE id=?", (mid,))
            tx.execute("UPDATE memories SET content='',subject='',provenance='[]',status='forgotten',confidence=0 WHERE kind='episode' OR status='proposed' OR supersedes=?", (mid,))
            tx.execute("UPDATE memories SET content='',subject='',provenance='[]',status='forgotten',confidence=0 WHERE subject=? OR content=?", (target['subject'],target['content']))
            tx.execute('DELETE FROM retrievals')
            tx.execute("UPDATE observations SET content='{}',processed=1")
            for event in tx.execute('SELECT event_id,data FROM events').fetchall():
                data = json.loads(event['data'])
                data['payload'] = {'retention': 'purged'}
                data['evidence_refs'] = []
                tx.execute('UPDATE events SET data=? WHERE event_id=?', (canonical(data), event['event_id']))
            tx.execute("UPDATE operations SET args='{}',result=NULL,status=CASE WHEN status IN ('queued','running','waiting-for-approval') THEN 'cancelled' ELSE status END")
            tx.execute("UPDATE outbox SET content='[removed by retention policy] ' || id,evidence='[]'")
            tx.execute("UPDATE goals SET plan='',title='[purged by retention policy]'")
            tx.execute("UPDATE calls SET error=NULL,input_hash='',output_hash=NULL")
            for artifact in tx.execute('SELECT path FROM artifacts').fetchall():
                from .common import confined
                path = confined(self.db.path.parent / 'artifacts', artifact['path'])
                if path.is_file():
                    path.unlink()
            tx.execute('DELETE FROM artifacts')
            self.db.set('epoch', self.db.get('epoch') + 1, tx)
            self.db.set('pending_proposal',None,tx)
            self.db.set('retention_generation', self.db.get('retention_generation',0)+1, tx)
            self.db.event('memory.forgotten', {'id': mid, 'policy': 'conservative_derived_purge_v1'}, tx=tx)
        # Secure-delete plus checkpoint removes old WAL pages; not a forensic SSD guarantee.
        with self.db.lock:
            self.db.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            self.db.db.execute('VACUUM')
