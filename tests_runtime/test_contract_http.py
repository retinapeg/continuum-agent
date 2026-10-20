import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import threading
from test_core import Base
from continuum.runtime.integration import HTTPExchangeAdapter,envelope,receive
from continuum.runtime.common import canonical


class ContractHTTPTests(Base):
    def test_local_stub_and_duplicate(self):
        r=self.runtime()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result=receive(r.db,payload);body=canonical(result).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);t=threading.Thread(target=server.serve_forever);t.start()
        try:
            adapter=HTTPExchangeAdapter(f'http://127.0.0.1:{server.server_port}')
            msg=envelope('task.requested',{'title':'Fictional document work'})
            self.assertFalse(adapter.deliver(msg)['duplicate']);self.assertTrue(adapter.deliver(msg)['duplicate'])
            self.assertEqual(r.db.get('receiving_cursor'),1)
        finally:server.shutdown();server.server_close();t.join(2)
    def test_external_address_rejected(self):
        for url in ('https://example.com','http://127.0.0.1@example.com','file:///etc/passwd'):
            with self.assertRaises(ValueError):HTTPExchangeAdapter(url)
