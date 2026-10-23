#!/usr/bin/env python3
"""OAuth flow for calendar + tasks scopes, using your desktop OAuth client.

Writes to ~/.config/gcal/tokens-calendar-tasks.json — deliberately NOT the
google-calendar-mcp token file, so the MCP's own auth keeps working untouched.
"""
import http.server, json, os, secrets, threading, urllib.parse, urllib.request, webbrowser

CLIENT = os.path.expanduser('~/.config/gcal/oauth-client.json')
OUT = os.path.expanduser('~/.config/gcal/tokens-calendar-tasks.json')
PORT = 3517
SCOPES = 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/tasks'

cli = json.load(open(CLIENT))['installed']
state = secrets.token_urlsafe(16)
result = {}
done = threading.Event()


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'code' in q and q.get('state', [None])[0] == state:
            result['code'] = q['code'][0]
            body = b"<h2>Authorized. You can close this tab.</h2>"
        else:
            result['error'] = q.get('error', ['state mismatch'])[0]
            body = b"<h2>Authorization failed. Check the terminal.</h2>"
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        done.set()

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(('127.0.0.1', PORT), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
    'client_id': cli['client_id'],
    'redirect_uri': f'http://localhost:{PORT}',
    'response_type': 'code',
    'scope': SCOPES,
    'access_type': 'offline',
    'prompt': 'consent',
    'state': state,
})
print('Opening browser for consent (calendar + tasks)...')
print(auth_url)
webbrowser.open(auth_url)

if not done.wait(timeout=240):
    raise SystemExit('Timed out waiting for consent.')
srv.shutdown()
if 'code' not in result:
    raise SystemExit(f"Auth failed: {result.get('error')}")

data = urllib.parse.urlencode({
    'code': result['code'],
    'client_id': cli['client_id'],
    'client_secret': cli['client_secret'],
    'redirect_uri': f'http://localhost:{PORT}',
    'grant_type': 'authorization_code',
}).encode()
tok = json.load(urllib.request.urlopen('https://oauth2.googleapis.com/token', data))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f:
    json.dump(tok, f)
os.chmod(OUT, 0o600)
print('scopes granted:', tok.get('scope'))
print('refresh_token:', 'yes' if tok.get('refresh_token') else 'NO — re-run with prompt=consent')
print('saved ->', OUT)
