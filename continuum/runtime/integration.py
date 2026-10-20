"""Project-local contract; not an implementation of A2A or MCP."""
import json
from pathlib import Path
import urllib.request
from urllib.parse import urlparse
from .common import ROOT, canonical, digest, uid, utc
from .contracts import validate

KINDS = ('task.requested', 'task.progress', 'task.completed', 'task.failed',
         'task.cancel.requested', 'task.cancelled', 'approval.requested')
SCHEMA = {
 '$schema':'https://json-schema.org/draft/2020-12/schema', 'type':'object',
 'additionalProperties':False,
 'required':['schema_version','message_id','trace_id','correlation_id','causation_id','source','target',
             'kind','created_at','deadline_at','idempotency_key','payload'],
 'properties': {
  'schema_version':{'const':'leo.integration.v1'},
  **{k:{'type':'string','minLength':1,'maxLength':200} for k in ('message_id','trace_id','correlation_id','source','target','idempotency_key')},
  'causation_id':{'type':['string','null']}, 'kind':{'enum':list(KINDS)},
  'created_at':{'type':'string','format':'date-time','pattern':'Z$'},
  'deadline_at':{'anyOf':[{'type':'null'},{'type':'string','format':'date-time','pattern':'Z$'}]},
  'payload':{'type':'object','maxProperties':20}
 }}


def envelope(kind, payload, target='exchange-local-stub'):
    mid = uid()
    return {'schema_version':'leo.integration.v1','message_id':mid,'trace_id':uid(),'correlation_id':mid,
            'causation_id':None,'source':'continuum','target':target,'kind':kind,'created_at':utc(),
            'deadline_at':None,'idempotency_key':mid,'payload':payload}


def receive(db, message):
    validate(SCHEMA, message)
    fingerprint = digest(message)
    with db.transaction() as tx:
        old = tx.execute('SELECT hash,cursor FROM inbox WHERE source=? AND message_id=?', (message['source'],message['message_id'])).fetchone()
        if old:
            if old['hash'] != fingerprint:
                raise ValueError('message ID reused with different content')
            return {'duplicate':True,'cursor':old['cursor']}
        cursor = db.get('receiving_cursor',0)+1
        tx.execute('INSERT INTO inbox VALUES (?,?,?,?)',(message['source'],message['message_id'],fingerprint,cursor))
        db.set('receiving_cursor',cursor,tx)
        db.event('integration.received', {'message':message,'cursor':cursor},tx=tx)
        return {'duplicate':False,'cursor':cursor}


class HTTPExchangeAdapter:
    """Loopback contract test adapter. Production/external sending is disabled."""
    def __init__(self, base_url):
        parsed = urlparse(base_url)
        if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.username or parsed.password:
            raise ValueError('only loopback HTTP stubs permitted')
        self.url = base_url

    def deliver(self, message):
        validate(SCHEMA,message)
        req = urllib.request.Request(self.url,canonical(message).encode(),{'Content-Type':'application/json'},method='POST')
        # Disable redirects: an untrusted loopback response cannot redirect externally.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):
                return None
        with urllib.request.build_opener(NoRedirect).open(req,timeout=3) as response:
            return json.loads(response.read(32000))
