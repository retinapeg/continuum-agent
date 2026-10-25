import uuid
import pytest
from continuum.runtime.facade import MemoryFacade, VERSION


def request(op, **args):
    return {'version': VERSION, 'request_id': str(uuid.uuid4()), 'op': op, 'args': args}


def proposal(f):
    source = str(uuid.uuid4())
    f.handle(request('observe', source_id=source, text='I prefer three concise interview bullets.'))
    return f.handle(request('propose', source_id=source, kind='preference', subject='interview preparation',
                            content='I prefer three concise interview bullets.'))['result']


def test_atomic_confirmation_replay_and_restart(tmp_path, monkeypatch):
    f = MemoryFacade(tmp_path)
    p = proposal(f)
    assert f.handle(request('retrieve', query='interview'))['result']['memories'] == []
    decision = request('decide', proposal_id=p['id'], binding=p['binding'], approve=True, decision_ref=str(uuid.uuid4()))
    event = f.db.event
    def fail(kind, *args, **kw):
        if kind == 'memory.confirmed':
            raise RuntimeError('crash before commit')
        return event(kind, *args, **kw)
    monkeypatch.setattr(f.db, 'event', fail)
    with pytest.raises(RuntimeError):
        f.handle(decision)
    assert f.row(p['id'])['status'] == 'proposed'
    assert len(f.db.rows('SELECT * FROM memories')) == 1
    monkeypatch.setattr(f.db, 'event', event)
    accepted = f.handle(decision)
    f.close()
    f = MemoryFacade(tmp_path)
    try:
        assert f.handle(decision) == accepted
        recall = f.handle(request('retrieve', query='interview'))['result']['memories']
        assert len(recall) == 1 and recall[0]['id'] == accepted['result']['memory_id']
        assert p['provenance'][0] in recall[0]['provenance']
        assert len(f.db.rows('SELECT * FROM confirmations')) == 1
        altered = {**decision, 'args': {**decision['args'], 'approve': False}}
        with pytest.raises(ValueError, match='changed-content'):
            f.handle(altered)
        with pytest.raises(ValueError, match='stale'):
            f.handle(request('decide', **{**decision['args'], 'binding': 'bad'}))
    finally:
        f.close()


def test_evidence_scope_and_owner_lock(tmp_path):
    f = MemoryFacade(tmp_path)
    try:
        with pytest.raises(RuntimeError):
            MemoryFacade(tmp_path)
        with pytest.raises(ValueError):
            f.handle(request('propose', source_id=str(uuid.uuid4()), kind='fact', subject='invented', content='unknown'))
        with pytest.raises(ValueError):
            f.handle({**request('health'), 'version': 'v2'})
    finally:
        f.close()
