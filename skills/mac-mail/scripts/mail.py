#!/usr/bin/env python3
"""Read Apple Mail's local store: search the Envelope Index, read bodies from .emlx files. Read-only.

Usage:
  mail.py mailboxes                                        every mailbox with message counts
  mail.py search [--from X] [--to X] [--subject X] [--text X] [--mailbox X]
                 [--since D] [--until D] [--unread] [--attachments] [--limit 25]
  mail.py read <id> [--html]                               headers + body of one message
  mail.py attachments <id> [--save DIR]                    list (or copy out) its attachments
  mail.py thread <id> [--md FILE]                          the whole conversation, oldest first
<id> is the number in the first column of `search`. Dates are YYYY-MM-DD.
"""
import argparse, email, email.policy, glob, html, os, re, shutil, sqlite3, sys
from datetime import datetime
from urllib.parse import unquote

MAIL = os.path.expanduser("~/Library/Mail")


def mail_root():
    vs = sorted(glob.glob(os.path.join(MAIL, "V[0-9]*")), key=lambda p: int(re.sub(r"\D", "", os.path.basename(p))))
    if not vs:
        sys.exit("No ~/Library/Mail/V* folder. Is Mail.app set up, and does your terminal have Full Disk Access?")
    return vs[-1]  # V10 on macOS 14-26; the number bumps with major Mail rewrites


ROOT = None
def db():
    global ROOT
    ROOT = mail_root()
    p = os.path.join(ROOT, "MailData", "Envelope Index")
    try:
        c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        c.execute("SELECT 1 FROM messages LIMIT 1")
        return c
    except sqlite3.Error as e:
        sys.exit(f"Cannot open Envelope Index ({e}). Grant Full Disk Access to your terminal (see SKILL.md).")


def mbox_name(url):
    # imap://<account-uuid>/%5BGmail%5D/All%20Mail -> [Gmail]/All Mail ; ews://, local:// alike
    return unquote(re.sub(r"^\w+://[^/]+/?", "", url or ""))


BASE = """SELECT m.ROWID, m.date_received, a.address, a.comment, s.subject, mb.url, m.read, m.flagged,
                  m.conversation_id, su.summary
           FROM messages m
           LEFT JOIN addresses a ON a.ROWID = m.sender
           LEFT JOIN subjects s ON s.ROWID = m.subject
           LEFT JOIN mailboxes mb ON mb.ROWID = m.mailbox
           LEFT JOIN summaries su ON su.ROWID = m.summary
           WHERE m.deleted = 0"""


def search(c, a):
    q, args = [BASE], []
    if a.sender:
        q.append("AND (a.address LIKE ? OR a.comment LIKE ?)"); args += [f"%{a.sender}%"] * 2
    if a.to:
        q.append("""AND m.ROWID IN (SELECT r.message FROM recipients r JOIN addresses ra ON ra.ROWID=r.address
                    WHERE ra.address LIKE ? OR ra.comment LIKE ?)"""); args += [f"%{a.to}%"] * 2
    if a.subject:
        q.append("AND s.subject LIKE ?"); args.append(f"%{a.subject}%")
    if a.text:  # summary = the first lines of the body Mail keeps for the preview
        q.append("AND (s.subject LIKE ? OR su.summary LIKE ?)"); args += [f"%{a.text}%"] * 2
    if a.mailbox:
        q.append("AND mb.url LIKE ?"); args.append(f"%{a.mailbox.replace(' ', '%20')}%")
    if a.since:
        q.append("AND m.date_received >= ?"); args.append(datetime.strptime(a.since, "%Y-%m-%d").timestamp())
    if a.until:
        q.append("AND m.date_received < ?"); args.append(datetime.strptime(a.until, "%Y-%m-%d").timestamp() + 86400)
    if a.unread:
        q.append("AND m.read = 0")
    if a.attachments:
        q.append("AND m.ROWID IN (SELECT message FROM attachments)")
    q.append("ORDER BY m.date_received DESC LIMIT ?"); args.append(a.limit)
    rows = c.execute(" ".join(q), args).fetchall()
    for rid, d, addr, nm, subj, url, rd, fl, conv, summ in rows:
        mark = ("*" if not rd else " ") + ("!" if fl else " ")
        who = f"{nm} <{addr}>" if nm else (addr or "?")
        print(f"{rid:>7} {mark} {datetime.fromtimestamp(d):%Y-%m-%d %H:%M}  {who[:40]:40}  {(subj or '')[:70]}  [{mbox_name(url)}]")
    print(f"-- {len(rows)} message(s)  (* unread, ! flagged)", file=sys.stderr)


_INDEX = None
def emlx_path(rid):
    """Messages/<ROWID>.emlx (full) or <ROWID>.partial.emlx (attachments stored beside it)."""
    global _INDEX
    if _INDEX is None:
        _INDEX = {}
        for p in glob.glob(os.path.join(ROOT, "*", "**", "Messages", "*.emlx"), recursive=True):
            n = os.path.basename(p).split(".")[0]
            if n not in _INDEX or not p.endswith(".partial.emlx"):
                _INDEX[n] = p
    return _INDEX.get(str(rid))


def load(rid):
    p = emlx_path(rid)
    if not p:
        return None, None
    raw = open(p, "rb").read()
    nl = raw.index(b"\n")
    n = int(raw[:nl].strip())  # first line = byte length of the RFC 822 message; an Apple plist follows
    return email.message_from_bytes(raw[nl + 1:nl + 1 + n], policy=email.policy.default), p


def text_of(msg, want_html=False):
    part = msg.get_body(preferencelist=("html", "plain") if want_html else ("plain", "html"))
    if part is None:
        return ""
    try:
        s = part.get_content()
    except Exception:
        s = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
    if part.get_content_type() == "text/html" and not want_html:
        s = re.sub(r"(?is)<(script|style).*?</\1>", "", s)
        s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", s)
        s = html.unescape(re.sub(r"<[^>]+>", "", s))
        s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


def header_row(c, rid):
    r = c.execute(BASE + " AND m.ROWID=?", (rid,)).fetchone()
    if not r:
        sys.exit(f"No message {rid} in the Envelope Index.")
    return r


def read(c, rid, want_html):
    r = header_row(c, rid)
    msg, p = load(rid)
    print(f"Date:    {datetime.fromtimestamp(r[1]):%Y-%m-%d %H:%M}\nMailbox: {mbox_name(r[5])}")
    if msg is None:
        print(f"From:    {r[3] or ''} <{r[2]}>\nSubject: {r[4]}\n\n[body not downloaded to this Mac; preview only]\n{r[9] or ''}")
        return
    for h in ("From", "To", "Cc", "Subject"):
        if msg[h]:
            print(f"{h + ':':8} {msg[h]}")
    print("\n" + text_of(msg, want_html))


def attachments(c, rid, save):
    header_row(c, rid)
    msg, p = load(rid)
    found = []
    if msg is not None:
        for part in msg.iter_attachments():
            data = part.get_payload(decode=True)
            if data:
                found.append((part.get_filename() or "unnamed", data, None))
    if p and p.endswith(".partial.emlx"):
        # Mail strips big parts out of .partial.emlx into .../Attachments/<ROWID>/<part>/<file>
        base = os.path.join(os.path.dirname(os.path.dirname(p)), "Attachments", str(rid))
        for f in glob.glob(os.path.join(glob.escape(base), "*", "*")):  # Gmail paths contain [Gmail]
            found.append((os.path.basename(f), None, f))
    names = [n for (n,) in c.execute("SELECT name FROM attachments WHERE message=?", (rid,))]
    if not found and names:
        print("Attachments not downloaded to this Mac:", ", ".join(names)); return
    for name, data, path in found:
        size = len(data) if data is not None else os.path.getsize(path)
        print(f"{size // 1024:>7} KB  {name}" + (f"  {path}" if path else ""))
        if save:
            os.makedirs(save, exist_ok=True)
            dst = os.path.join(save, os.path.basename(name))
            if data is not None:
                open(dst, "wb").write(data)
            else:
                shutil.copy2(path, dst)
    if save:
        print(f"saved {len(found)} file(s) to {save}")


def thread(c, rid, md):
    conv = header_row(c, rid)[8]
    rows = c.execute(BASE + " AND m.conversation_id=? ORDER BY m.date_received", (conv,)).fetchall() if conv else [header_row(c, rid)]
    seen, out = set(), []
    for r in rows:
        msg, _ = load(r[0])
        key = (msg["Message-ID"] if msg is not None else None) or r[0]
        if key in seen:  # Gmail files one message under several labels/mailboxes
            continue
        seen.add(key)
        body = text_of(msg) if msg is not None else (r[9] or "[not downloaded]")
        body = re.split(r"\n(?:On .{5,120} wrote:|-----Original Message-----)", body)[0].strip()  # drop quoted history
        out.append((datetime.fromtimestamp(r[1]), f"{r[3] or ''} <{r[2]}>".strip(), r[4], body))
    if md:
        with open(md, "w") as f:
            f.write(f"# {out[0][2] if out else ''}\n\n")
            for d, who, subj, body in out:
                f.write(f"## {d:%Y-%m-%d %H:%M} | {who}\n\n{body}\n\n")
        print(f"wrote {len(out)} message(s) to {md}")
    else:
        for d, who, subj, body in out:
            print(f"=== {d:%Y-%m-%d %H:%M}  {who}\n{body}\n")


def mailboxes(c):
    for url, n, unread in c.execute("""SELECT mb.url, count(m.ROWID), sum(m.read=0) FROM mailboxes mb
            LEFT JOIN messages m ON m.mailbox=mb.ROWID AND m.deleted=0 GROUP BY mb.ROWID ORDER BY 2 DESC"""):
        print(f"{n:>7} msgs {unread or 0:>6} unread  {url.split('://')[0]:6} {mbox_name(url)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["mailboxes", "search", "read", "attachments", "thread"])
    ap.add_argument("id", nargs="?", type=int)
    ap.add_argument("--from", dest="sender"); ap.add_argument("--to"); ap.add_argument("--subject")
    ap.add_argument("--text"); ap.add_argument("--mailbox"); ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--unread", action="store_true"); ap.add_argument("--attachments", action="store_true")
    ap.add_argument("--limit", type=int, default=25); ap.add_argument("--html", action="store_true")
    ap.add_argument("--save"); ap.add_argument("--md")
    a = ap.parse_args()
    c = db()
    if a.cmd == "mailboxes":
        return mailboxes(c)
    if a.cmd == "search":
        return search(c, a)
    if a.id is None:
        ap.error("needs a message id from `search`")
    {"read": lambda: read(c, a.id, a.html), "attachments": lambda: attachments(c, a.id, a.save),
     "thread": lambda: thread(c, a.id, a.md)}[a.cmd]()


if __name__ == "__main__":
    main()
