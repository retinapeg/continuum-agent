from typing import Protocol
from .common import canonical, uid, redact


class Channel(Protocol):
    def publish(self, message: dict) -> dict: ...


class LocalChannel:
    def publish(self, message):
        return {'status': 'available-locally', 'message_id': message['id']}


class Notifications:
    def __init__(self, db, cooldown=30, hourly_budget=8, quiet_hours=()):
        self.db, self.cooldown, self.budget, self.quiet = db, cooldown, hourly_budget, quiet_hours

    def offer(self, text, topic, reason, evidence, at, *, reply=False):
        text,topic=redact(text),redact(topic)
        if not text.strip():
            return None
        suppressed = None
        if topic in self.db.get('muted_topics', []):
            suppressed = 'topic_muted'
        elif not reply and reason not in ('new_evidence', 'deadline', 'blocked', 'conflict'):
            suppressed = 'no_usefulness_criterion'
        elif not reply and not evidence:
            suppressed = 'no_evidence'
        elif not reply and int(at // 3600) % 24 in self.quiet:
            suppressed = 'quiet_period'
        recent = self.db.rows("SELECT created FROM outbox WHERE status='available-locally' AND reason!='reply' AND created>?", (at - 3600,))
        if not reply and len(recent) >= self.budget:
            suppressed = suppressed or 'interruption_budget'
        if not reply and recent and at - max(r['created'] for r in recent) < self.cooldown:
            suppressed = suppressed or 'cooldown'
        if self.db.rows('SELECT id FROM outbox WHERE topic=? AND content=?', (topic, text)):
            self.db.event('notification.suppressed', {'topic': topic, 'reason': 'duplicate'})
            return None
        oid = uid()
        with self.db.transaction() as tx:
            tx.execute('INSERT INTO outbox VALUES (?,?,?,?,?,?,?,?,?)',
                       (oid, topic, text, reason, canonical(evidence), 'suppressed' if suppressed else 'available-locally',
                        suppressed, at, None if suppressed else at))
            self.db.event('notification.suppressed' if suppressed else 'notification.delivered',
                          {'id': oid, 'reason': suppressed or reason, 'channel': 'local'}, refs=evidence, tx=tx)
        return oid
