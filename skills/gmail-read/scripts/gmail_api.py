#!/usr/bin/env python3
"""Read your own Gmail through the Gmail API. Python 3 stdlib only. Scope: gmail.readonly (cannot send,
delete or modify anything).

Setup once (SKILL.md "Route 2"): put your OAuth Desktop client at ~/.config/gmail-read/credentials.json, then
  gmail_api.py auth                      # opens Google's consent page once; caches token.json (chmod 600)
Use:
  gmail_api.py search 'from:billing@example.com newer_than:30d' [-n 20] [--json]
  gmail_api.py read <message-id>         # clean text: headers, body, attachment list
  gmail_api.py thread <thread-or-message-id> [--quoted]        # whole thread as markdown, oldest first
  gmail_api.py export <thread-or-message-id> out.md [--quoted]
  gmail_api.py labels
  gmail_api.py attachments <message-id> [--save DIR] [--name SUBSTR]
Config dir override: GMAIL_READ_DIR=/path."""
import base64, hashlib, http.server, json, os, secrets, sys, threading, time, urllib.error, urllib.parse, urllib.request
import webbrowser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mailtext

DIR = os.path.expanduser(os.environ.get("GMAIL_READ_DIR", "~/.config/gmail-read"))
CREDS, TOKEN = os.path.join(DIR, "credentials.json"), os.path.join(DIR, "token.json")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

def die(msg): sys.exit(f"gmail_api: {msg}")

def client():
    if not os.path.exists(CREDS):
        die(f"no OAuth client at {CREDS}. Create a Desktop OAuth client (SKILL.md, Route 2) and save its JSON there.")
    c = json.load(open(CREDS)); c = c.get("installed") or c.get("web") or c
    return c["client_id"], c.get("client_secret", "")

def save_token(t):
    os.makedirs(DIR, exist_ok=True)
    fd = os.open(TOKEN, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(t, f)
    os.chmod(TOKEN, 0o600)

def post(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode(), method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if "invalid_grant" in body:
            die("refresh token rejected (invalid_grant). A consent screen left in Testing mode expires refresh "
                "tokens after 7 days, and a password change or revoked access kills them too. Run: gmail_api.py auth")
        die(f"token endpoint HTTP {e.code}: {body[:300]}")

def auth(open_browser=True):
    cid, csec = client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state, got = secrets.token_urlsafe(16), {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state: got.update({k: v[0] for k, v in q.items()})
            self.send_response(200); self.send_header("Content-Type", "text/plain"); self.end_headers()
            self.wfile.write(b"gmail-read: done. You can close this tab.")
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    print("Open this URL, pick your account, allow read-only access:\n\n" + url + "\n", file=sys.stderr)
    if open_browser: webbrowser.open(url)
    t = threading.Thread(target=lambda: [srv.handle_request() for _ in range(5) if "code" not in got and "error" not in got])
    t.start(); t.join(300); srv.server_close()
    if "code" not in got: die(f"no authorization code ({got.get('error', 'timed out after 5 min')})")
    tok = post(TOKEN_URL, {"code": got["code"], "client_id": cid, "client_secret": csec, "redirect_uri": redirect,
                           "grant_type": "authorization_code", "code_verifier": verifier})
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    save_token(tok); print(f"token saved to {TOKEN} (scope: {tok.get('scope')})", file=sys.stderr)

def access_token():
    if not os.path.exists(TOKEN): die("not authorised yet. Run: gmail_api.py auth")
    t = json.load(open(TOKEN))
    if t.get("expires_at", 0) > time.time(): return t["access_token"]
    if not t.get("refresh_token"): die("token has no refresh_token. Run: gmail_api.py auth")
    cid, csec = client()
    n = post(TOKEN_URL, {"client_id": cid, "client_secret": csec, "refresh_token": t["refresh_token"],
                         "grant_type": "refresh_token"})
    t.update(n); t["expires_at"] = time.time() + n.get("expires_in", 3600) - 60
    save_token(t); return t["access_token"]

def get(path, **params):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token()}"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 503) and attempt < 3: time.sleep(2 ** attempt); continue
            if e.code == 403 and ("accessNotConfigured" in body or "has not been used" in body):
                die("Gmail API is not enabled on your Cloud project. Enable it (SKILL.md, Route 2 step 2).")
            if e.code == 404: die(f"not found: {path} (wrong id? thread ids and message ids are different things)")
            die(f"HTTP {e.code} on {path}: {body[:300]}")

def search(q, n):
    ids, page = [], None
    while len(ids) < n:
        r = get("messages", q=q, maxResults=min(500, n - len(ids)), **({"pageToken": page} if page else {}))
        ids += r.get("messages", []); page = r.get("nextPageToken")
        if not page: break
    rows = []
    for m in ids[:n]:
        d = get(f"messages/{m['id']}", format="metadata", metadataHeaders=["From", "Subject", "Date"])
        h = {x["name"].lower(): x["value"] for x in d.get("payload", {}).get("headers", [])}
        rows.append({"id": d["id"], "threadId": d["threadId"], "date": h.get("date", ""), "from": h.get("from", ""),
                     "subject": h.get("subject", ""), "labels": d.get("labelIds", []), "snippet": d.get("snippet", "")})
    return rows

def raw_message(mid):
    r = get(f"messages/{mid}", format="raw")
    return mailtext.parse(base64.urlsafe_b64decode(r["raw"] + "=" * (-len(r["raw"]) % 4))), r

def thread_messages(tid):
    try:
        t = get(f"threads/{tid}", format="minimal")
    except SystemExit:
        t = get(f"threads/{get(f'messages/{tid}', format='minimal')['threadId']}", format="minimal")
    return [raw_message(m["id"])[0] for m in t.get("messages", [])]

def main(a):
    if not a or a[0] in ("-h", "--help"): sys.exit(__doc__)
    cmd, flag = a[0], (lambda f: f in a)
    def opt(f, d=None): return a[a.index(f) + 1] if f in a else d
    if cmd == "auth": auth(open_browser=not flag("--no-browser"))
    elif cmd == "search":
        rows = search(a[1], int(opt("-n", 20)))
        if flag("--json"): print(json.dumps(rows, indent=1)); return
        for r in rows: print(f"{r['id']}  thread {r['threadId']}  {r['date'][:31]}\n  {r['from']}\n  {r['subject']}\n")
        print(f"{len(rows)} message(s)", file=sys.stderr)
    elif cmd == "read": print(mailtext.as_text(raw_message(a[1])[0]))
    elif cmd in ("thread", "export"):
        md = mailtext.thread_markdown(thread_messages(a[1]), quoted=flag("--quoted"))
        if cmd == "thread": print(md)
        else: open(a[2], "w").write(md); print(f"wrote {a[2]}", file=sys.stderr)
    elif cmd == "labels":
        for l in sorted(get("labels").get("labels", []), key=lambda l: (l["type"], l["name"])):
            print(f"{l['type']:<6} {l['id']:<28} {l['name']}")
    elif cmd == "attachments":
        m = raw_message(a[1])[0]
        if flag("--save"):
            for p in mailtext.save_attachments(m, opt("--save"), opt("--name")): print("saved", p)
        else:
            for x in m["attachments"]: print(f"{x['size']:>10} B  {x['mime']:<32} {x['filename']}")
            print(f"{len(m['attachments'])} attachment(s)", file=sys.stderr)
    else: sys.exit(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
