from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse, parse_qs
from .common import canonical, confined, uid


class Dashboard:
    def __init__(self, runtime, host='127.0.0.1', port=8787):
        if host != '127.0.0.1':
            raise ValueError('dashboard is loopback-only')
        self.runtime = runtime
        token_file = runtime.directory / 'control-token'
        if token_file.exists():
            self.token = token_file.read_text()
        else:
            self.token = secrets.token_urlsafe(32)
            token_file.write_text(self.token)
            token_file.chmod(0o600)
        dashboard = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def send(self, code, value, content_type='application/json'):
                body = canonical(value).encode() if content_type == 'application/json' else value.encode()
                self.send_response(code)
                self.send_header('Content-Type',content_type)
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)
            def authorized(self, control=False):
                expected = f'127.0.0.1:{dashboard.server.server_port}'
                if self.headers.get('Host') != expected:
                    return False
                if not hmac.compare_digest(self.headers.get('Authorization',''), 'Bearer '+dashboard.token):
                    return False
                # All modifying calls require exact same-origin, including CLI.
                return not control or self.headers.get('Origin') == 'http://'+expected
            def do_GET(self):
                path = urlparse(self.path).path
                if path in ('/','/app.js','/style.css'):
                    name = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                    content = (Path(__file__).parent/'ui'/name).read_text()
                    mime = {'/':'text/html','/app.js':'text/javascript','/style.css':'text/css'}[path]
                    return self.send(200,content,mime)
                if not self.authorized():
                    return self.send(401,{'error':'authentication required'})
                if path=='/api/status':
                    return self.send(200,runtime.status())
                if path=='/api/events':
                    try: after=int(parse_qs(urlparse(self.path).query).get('after',['0'])[0])
                    except ValueError: return self.send(400,{'error':'invalid cursor'})
                    rows = runtime.db.rows('SELECT seq,kind,data FROM events WHERE seq>? ORDER BY seq LIMIT 100',(after,))
                    return self.send(200,{'events':[{'seq':r['seq'],'kind':r['kind'],**json.loads(r['data'])} for r in rows]})
                if path=='/api/artifact':
                    aid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
                    rows=runtime.db.rows('SELECT * FROM artifacts WHERE id=?',(aid,))
                    if not rows:return self.send(404,{'error':'artifact absent'})
                    from .common import digest
                    try:
                        artifact=confined(runtime.directory/'artifacts',rows[0]['path'],exists=True)
                        data=artifact.read_bytes()
                        if digest(data)!=rows[0]['checksum']:raise ValueError('artifact checksum mismatch')
                    except (ValueError,OSError) as exc:return self.send(409,{'error':str(exc)})
                    return self.send(200,{'path':rows[0]['path'],'content':data.decode(),'checksum':rows[0]['checksum']})
                if path=='/api/experiments':
                    from .common import ROOT
                    reports=[]
                    for p in sorted((ROOT/'experiments/v02').glob('*/report.json')):
                        reports.append({'name':p.parent.name,'report':json.loads(p.read_text())})
                    return self.send(200,{'experiments':reports})
                return self.send(404,{'error':'not found'})
            def do_POST(self):
                if not self.authorized(True):
                    return self.send(403,{'error':'authenticated same-origin control required'})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=20000:
                        raise ValueError('bounded JSON body required')
                    if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                        raise ValueError('JSON required')
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict): raise ValueError('object required')
                    path=urlparse(self.path).path
                    if path=='/api/message':
                        if not isinstance(body.get('text'),str) or not body['text'].strip(): raise ValueError('message required')
                        result={'id':runtime.observe('user.message',{'text':body['text']})}
                    elif path=='/api/goal':
                        result={'id':runtime.goal(body['title'],body.get('deadline'))}
                    elif path=='/api/control':
                        runtime.control(body['action']); result={'control':runtime.db.get('control')}
                    elif path=='/api/fact':
                        oid=runtime.observe('fact.corrected',{'private_update':True} if body.get('private',False) else {'subject':body['subject'],'content':body['content']})
                        result={'id':runtime.memory.add(body.get('kind','fact'),body['subject'],body['content'],runtime.clock.now(),[oid],confirmed=True,supersedes=body.get('supersedes'),private=body.get('private',False))}
                    elif path=='/api/forget':
                        runtime.cancel.set(); runtime.memory.forget(body['id']); result={'forgotten':body['id']}
                    elif path=='/api/mute':
                        topics=runtime.db.get('muted_topics'); topics.append(body['topic']); runtime.db.set('muted_topics',sorted(set(topics))); result={'muted':body['topic']}
                    elif path=='/api/revoke':
                        runtime.revoke(body['capability']); result={'revoked':body['capability']}
                    elif path=='/api/cancel':
                        runtime.cancel_goal(body['id']); result={'cancelled':body['id']}
                    elif path=='/api/approve':
                        op=runtime.db.rows("SELECT * FROM operations WHERE id=? AND status='waiting-for-approval'",(body['id'],))
                        if not op: raise ValueError('approval target absent')
                        # Only owner authenticated control can grant one concrete operation.
                        from .contracts import CAPABILITIES
                        name=op[0]['kind']
                        if name not in CAPABILITIES: raise ValueError('unknown capability')
                        with runtime.db.transaction() as tx:
                            approved=runtime.db.get('approved_operations',[]); runtime.db.set('approved_operations',sorted(set(approved+[body['id']])),tx)
                            tx.execute("UPDATE operations SET status='queued' WHERE id=?",(body['id'],))
                            runtime.db.event('approval.granted',{'operation_id':body['id'],'by':'authenticated_owner'},tx=tx)
                        runtime.wake.set(); result={'approved':body['id']}
                    else:
                        return self.send(404,{'error':'not found'})
                    self.send(200,result)
                except (ValueError,KeyError,TypeError) as exc:
                    self.send(400,{'error':str(exc)[:300]})
        self.server=ThreadingHTTPServer((host,port),Handler)
        self.server.daemon_threads=True

    def serve(self):
        self.server.serve_forever(poll_interval=.2)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
