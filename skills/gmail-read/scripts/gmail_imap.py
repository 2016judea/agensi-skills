#!/usr/bin/env python3
"""Read your own Gmail over IMAP with an app password. Python 3 stdlib only. Opens the mailbox READ-ONLY
(EXAMINE + BODY.PEEK), so nothing is marked read, moved or deleted.

Credentials (SKILL.md "Route 3"): env GMAIL_ADDRESS + GMAIL_APP_PASSWORD, or ~/.config/gmail-read/imap.json
  {"address": "you@example.com", "app_password": "<16-char app password>"}   (chmod 600)
Use:
  gmail_imap.py search 'from:billing@example.com newer_than:30d' [-n 20] [--json]
  gmail_imap.py read <message-id>        # ids are Gmail's hex ids, the same ones the API and web UI use
  gmail_imap.py thread <thread-or-message-id> [--quoted]
  gmail_imap.py export <thread-or-message-id> out.md [--quoted]
  gmail_imap.py labels
  gmail_imap.py attachments <message-id> [--save DIR] [--name SUBSTR]
Config dir override: GMAIL_READ_DIR=/path."""
import email, email.policy, imaplib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mailtext

HOST = "imap.gmail.com"
DIR = os.path.expanduser(os.environ.get("GMAIL_READ_DIR", "~/.config/gmail-read"))

def die(msg): sys.exit(f"gmail_imap: {msg}")

def creds():
    a, p = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    f = os.path.join(DIR, "imap.json")
    if not (a and p) and os.path.exists(f):
        c = json.load(open(f)); a, p = a or c.get("address"), p or c.get("app_password")
    if not (a and p): die(f"set GMAIL_ADDRESS and GMAIL_APP_PASSWORD, or write {f} (SKILL.md, Route 3)")
    return a, p.replace(" ", "")

def utf7_decode(s):
    """IMAP modified UTF-7 folder names (RFC 3501) -> str."""
    def dec(m):
        b = m.group(1)
        if not b: return "&"
        b = b.replace(",", "/"); b += "=" * (-len(b) % 4)
        import base64; return base64.b64decode(b).decode("utf-16-be")
    return re.sub(r"&([A-Za-z0-9+,]*)-", dec, s)

def connect():
    a, p = creds()
    M = imaplib.IMAP4_SSL(HOST)
    try:
        M.login(a, p)
    except imaplib.IMAP4.error as e:
        die(f"login refused ({e}). Use a 16-character APP password, not your account password; it needs "
            "2-Step Verification on, and IMAP must be allowed (Workspace admins can switch it off).")
    return M

def folders(M):
    out = []
    for line in M.list()[1]:
        m = re.match(rb'\((?P<flags>[^)]*)\) "(?P<d>[^"]*)" (?P<name>.+)', line)
        if m: out.append((m["flags"].decode(), m["name"].decode().strip('"')))
    return out

def open_all_mail(M):
    """'[Gmail]/All Mail' is localised ('[Google Mail]/Alle Nachrichten'...): find it by its \\All flag."""
    name = next((n for f, n in folders(M) if "\\All" in f), None)
    if not name: die("no \\All folder. Turn on 'Show in IMAP' for All Mail in Gmail settings > Labels.")
    typ, _ = M.select(f'"{name}"', readonly=True)
    if typ != "OK": die(f"cannot open {name}")

def uid_search(M, *crit):
    typ, d = M.uid("SEARCH", *crit)
    if typ != "OK": die(f"search failed: {d}")
    return d[0].split()

def raw_search(M, q):
    if q.isascii():
        return uid_search(M, "X-GM-RAW", '"' + q.replace("\\", "\\\\").replace('"', '\\"') + '"')
    M.literal = q.encode("utf-8")                       # non-ASCII queries go as a literal
    return uid_search(M, "CHARSET", "UTF-8", "X-GM-RAW")

META = re.compile(rb"X-GM-THRID (\d+) X-GM-MSGID (\d+)|X-GM-MSGID (\d+) X-GM-THRID (\d+)")

def fetch(M, uids, what):
    """-> list of (thrid_hex, msgid_hex, labels_bytes, payload_bytes) in UID order."""
    out = []
    for i in range(0, len(uids), 100):
        typ, d = M.uid("FETCH", b",".join(uids[i:i + 100]), f"(X-GM-THRID X-GM-MSGID X-GM-LABELS {what})")
        for item in d:
            if not isinstance(item, tuple): continue
            m = META.search(item[0])
            thr, mid = (m[1], m[2]) if m and m[1] else ((m[4], m[3]) if m else (b"0", b"0"))
            lab = re.search(rb"X-GM-LABELS \(([^)]*)\)", item[0])
            out.append((f"{int(thr):x}", f"{int(mid):x}", lab[1] if lab else b"", item[1]))
    return out

def by_msgid(M, hexid):
    try: dec = str(int(hexid, 16))
    except ValueError: die(f"'{hexid}' is not a Gmail hex id (search prints them)")
    return dec

def read_raw(M, hexid):
    uids = uid_search(M, "X-GM-MSGID", by_msgid(M, hexid))
    if not uids: die(f"no message with id {hexid}")
    return mailtext.parse(fetch(M, uids[:1], "BODY.PEEK[]")[0][3])

def thread(M, hexid):
    dec = by_msgid(M, hexid)
    uids = uid_search(M, "X-GM-THRID", dec)
    if not uids:                                        # given a message id: find its thread
        mu = uid_search(M, "X-GM-MSGID", dec)
        if not mu: die(f"no thread or message with id {hexid}")
        uids = uid_search(M, "X-GM-THRID", str(int(fetch(M, mu[:1], "UID")[0][0], 16)))
    return [mailtext.parse(r[3]) for r in fetch(M, uids, "BODY.PEEK[]")]

def main(a):
    if not a or a[0] in ("-h", "--help"): sys.exit(__doc__)
    cmd, flag = a[0], (lambda f: f in a)
    def opt(f, d=None): return a[a.index(f) + 1] if f in a else d
    M = connect()
    try:
        if cmd == "labels":
            for f, n in sorted(folders(M), key=lambda x: x[1]): print(f"{utf7_decode(n):<40} {f}")
            return
        open_all_mail(M)
        if cmd == "search":
            n = int(opt("-n", 20))
            uids = raw_search(M, a[1])[::-1][:n]           # newest first
            hdr = "BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)]"
            rows = []
            for thr, mid, lab, payload in fetch(M, uids, hdr):
                h = email.message_from_bytes(payload, policy=email.policy.default)
                rows.append({"id": mid, "threadId": thr, "date": str(h["Date"] or ""), "from": str(h["From"] or ""),
                             "subject": str(h["Subject"] or ""), "labels": lab.decode("utf-8", "replace")})
            rows.sort(key=lambda r: int(r["id"], 16), reverse=True)
            if flag("--json"): print(json.dumps(rows, indent=1)); return
            for r in rows: print(f"{r['id']}  thread {r['threadId']}  {r['date'][:31]}\n  {r['from']}\n  {r['subject']}\n")
            print(f"{len(rows)} message(s)", file=sys.stderr)
        elif cmd == "read": print(mailtext.as_text(read_raw(M, a[1])))
        elif cmd in ("thread", "export"):
            md = mailtext.thread_markdown(thread(M, a[1]), quoted=flag("--quoted"))
            if cmd == "thread": print(md)
            else: open(a[2], "w").write(md); print(f"wrote {a[2]}", file=sys.stderr)
        elif cmd == "attachments":
            m = read_raw(M, a[1])
            if flag("--save"):
                for p in mailtext.save_attachments(m, opt("--save"), opt("--name")): print("saved", p)
            else:
                for x in m["attachments"]: print(f"{x['size']:>10} B  {x['mime']:<32} {x['filename']}")
                print(f"{len(m['attachments'])} attachment(s)", file=sys.stderr)
        else: sys.exit(__doc__)
    finally:
        try: M.logout()
        except Exception: pass

if __name__ == "__main__":
    main(sys.argv[1:])
