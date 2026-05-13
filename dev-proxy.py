"""Local dev stand-in for worker/worker.js.
Mirrors POST /api/claude -> api.anthropic.com/v1/messages with CORS.
Reads ANTHROPIC_API_KEY from worker/.dev.vars. Run: python dev-proxy.py"""
import json, os, sys, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8787
HERE = os.path.dirname(os.path.abspath(__file__))
DEV_VARS = os.path.join(HERE, 'worker', '.dev.vars')

def load_key():
    if not os.path.exists(DEV_VARS):
        return None
    with open(DEV_VARS, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('ANTHROPIC_API_KEY='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    return None

KEY = load_key()
if not KEY:
    print('[dev-proxy] no ANTHROPIC_API_KEY in worker/.dev.vars', file=sys.stderr)
    sys.exit(1)

CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

class H(BaseHTTPRequestHandler):
    def _send(self, status, body, ct='application/json'):
        if not isinstance(body, (bytes, bytearray)):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', str(len(body)))
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/claude':
            return self._send(404, json.dumps({'error': {'message': 'Not found'}}))
        n = int(self.headers.get('Content-Length', '0'))
        try:
            body = json.loads(self.rfile.read(n) or b'{}')
        except Exception as e:
            return self._send(400, json.dumps({'error': {'message': f'bad json: {e}'}}))
        api_key = (body.get('apiKey') or '').strip() or KEY
        payload = {
            'model': body.get('model'),
            'max_tokens': body.get('max_tokens'),
            'system': body.get('system'),
            'messages': body.get('messages'),
        }
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return self._send(r.status, r.read())
        except urllib.error.HTTPError as e:
            return self._send(e.code, e.read())
        except Exception as e:
            return self._send(500, json.dumps({'error': {'message': str(e)}}))

    def log_message(self, fmt, *args):
        sys.stderr.write('[proxy] ' + (fmt % args) + '\n')

if __name__ == '__main__':
    print(f'[dev-proxy] listening on http://localhost:{PORT}')
    HTTPServer(('127.0.0.1', PORT), H).serve_forever()
