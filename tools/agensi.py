#!/usr/bin/env python3
"""Minimal Agensi MCP client. Token lives in ~/.config/agensi/oauth.json (never in this repo).
Usage: agensi.py <tool> '<json args>'"""
import json, os, sys, time, urllib.request, urllib.parse
P = os.path.expanduser('~/.config/agensi/oauth.json')
URL = 'https://mcp.agensi.io/mcp'

def tok():
    d = json.load(open(P))
    if time.time() > d.get('obtained', 0) + d.get('expires_in', 3600) - 120:
        body = urllib.parse.urlencode(dict(grant_type='refresh_token', refresh_token=d['refresh_token'],
                                           client_id=d['client_id'])).encode()
        n = json.load(urllib.request.urlopen(urllib.request.Request('https://mcp.agensi.io/oauth/token', body)))
        d.update(n); d['obtained'] = time.time()
        open(P, 'w').write(json.dumps(d)); os.chmod(P, 0o600)
    return d['access_token']

def call(name, args):
    req = urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args}}).encode(), headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'Authorization': 'Bearer ' + tok(), 'User-Agent': 'curl/8'})
    raw = urllib.request.urlopen(req, timeout=120).read().decode()
    for line in raw.splitlines():
        if line.startswith('data: '):
            raw = line[6:]
    r = json.loads(raw)
    if 'error' in r: return r
    res = r['result']
    return res.get('structuredContent') or '\n'.join(c.get('text', '') for c in res.get('content', []))

if __name__ == '__main__':
    out = call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
    print(out if isinstance(out, str) else json.dumps(out, indent=1))
