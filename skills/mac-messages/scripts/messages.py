#!/usr/bin/env python3
"""Read Apple Messages (iMessage, SMS, RCS) from ~/Library/Messages/chat.db. Read-only, on-device.

Usage:
  messages.py chats [--limit 30]                      conversations, newest first, with a chat number
  messages.py thread <who> [--since D] [--until D] [--limit N] [--deleted]
  messages.py search <text> [--who W] [--since D] [--until D] [--deleted] [--limit N]
  messages.py attachments <who> [--since D]
  messages.py export <who> --md FILE [--since D] [--until D]
  messages.py archive sync | archive search <text>   optional never-prune copy (see SKILL.md)

<who> is a chat number from `chats` (#123), a phone in any format, an email, a group name,
or a contact name (resolved through the Contacts database). Dates are YYYY-MM-DD.
"""
import argparse, glob, os, re, sqlite3, sys, time
from datetime import datetime

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")
AB = os.path.expanduser("~/Library/Application Support/AddressBook")
ARCHIVE = os.path.expanduser("~/Library/Application Support/mac-messages-archive/archive.db")
APPLE = 978307200  # 2001-01-01 in unix seconds


# ---------- body decoding ----------
def decode_body(blob):
    """Plain text out of an attributedBody NSKeyedArchiver/typedstream blob.

    Layout after the class name: ... 'NSString' 0x01 0x94 0x84 0x01 '+' <len> <utf-8 bytes>.
    <len> is one byte, or 0x81 + uint16 LE, or 0x82 + uint32 LE. Reading the length
    instead of regex-trimming keeps emoji, newlines and long messages intact."""
    if not blob:
        return None
    i = blob.find(b"NSString")
    if i < 0:
        return None
    j = blob.find(b"+", i + 8)
    if j < 0:
        return None
    n, k = blob[j + 1], j + 2
    if n == 0x81:
        n, k = int.from_bytes(blob[k:k + 2], "little"), k + 2
    elif n == 0x82:
        n, k = int.from_bytes(blob[k:k + 4], "little"), k + 4
    return blob[k:k + n].decode("utf-8", "replace")


def body(text, blob):
    t = text if text else decode_body(blob)
    return (t or "").replace("￼", "[attachment]").strip()


def ts(v):
    if not v:
        return None
    v = v / 1e9 if v > 1e12 else v  # nanoseconds since macOS 10.13, seconds before
    return datetime.fromtimestamp(v + APPLE)


def apple_ns(day):
    return int((datetime.strptime(day, "%Y-%m-%d").timestamp() - APPLE) * 1e9)


# ---------- contacts ----------
def e164(raw, country="1"):
    d = re.sub(r"\D", "", raw or "")
    if not d:
        return None
    if raw.strip().startswith("+"):
        return "+" + d
    if len(d) == 10 and country == "1":
        return "+1" + d
    if len(d) == 11 and d.startswith("1") and country == "1":
        return "+" + d
    return "+" + d


_BOOK = None
def book():
    """{normalised phone or lowercased email: name} from every AddressBook source."""
    global _BOOK
    if _BOOK is not None:
        return _BOOK
    _BOOK = {}
    paths = glob.glob(os.path.join(AB, "Sources", "*", "AddressBook-v22.abcddb")) + [os.path.join(AB, "AddressBook-v22.abcddb")]
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            names = {pk: " ".join(x for x in (f, l) if x) or (o or "")
                     for pk, f, l, o in c.execute("SELECT Z_PK, ZFIRSTNAME, ZLASTNAME, ZORGANIZATION FROM ZABCDRECORD")}
            for o, n in c.execute("SELECT ZOWNER, ZFULLNUMBER FROM ZABCDPHONENUMBER"):
                if names.get(o) and e164(n):
                    _BOOK.setdefault(e164(n), names[o])
            for o, a in c.execute("SELECT ZOWNER, ZADDRESS FROM ZABCDEMAILADDRESS"):
                if names.get(o) and a:
                    _BOOK.setdefault(a.strip().lower(), names[o])
        except sqlite3.Error:
            pass
    return _BOOK


def name_for(handle):
    if not handle:
        return "?"
    key = handle.lower() if "@" in handle else e164(handle)
    return book().get(key) or handle


# ---------- chat.db ----------
def db():
    if not os.access(CHAT_DB, os.R_OK):
        sys.exit("Cannot read chat.db. Grant Full Disk Access to your terminal app (see SKILL.md).")
    try:
        return sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        sys.exit(f"{e}: grant Full Disk Access to your terminal app (see SKILL.md).")


def chat_label(c, chat_id):
    dn, ident = c.execute("SELECT display_name, chat_identifier FROM chat WHERE ROWID=?", (chat_id,)).fetchone()
    members = [name_for(h) for (h,) in c.execute(
        "SELECT h.id FROM chat_handle_join j JOIN handle h ON h.ROWID=j.handle_id WHERE j.chat_id=?", (chat_id,))]
    if dn:
        return dn
    return ", ".join(sorted(set(members))) or name_for(ident)


def resolve(c, who):
    """-> list of chat ROWIDs for a chat number, phone, email, group name or contact name."""
    who = who.strip()
    if re.fullmatch(r"#?\d{1,6}", who):
        return [int(who.lstrip("#"))]
    keys = set()
    if "@" in who:
        keys.add(who.lower())
    elif len(re.sub(r"\D", "", who)) >= 7:
        keys.add(e164(who))
    else:
        wl = who.lower()
        keys |= {k for k, n in book().items() if wl in n.lower()}
        hit = [r for (r,) in c.execute("SELECT ROWID FROM chat WHERE display_name LIKE ?", (f"%{who}%",))]
        if hit and not keys:
            return hit
    out = set()
    for hid, ident in c.execute("SELECT ROWID, id FROM handle"):
        k = ident.lower() if "@" in ident else e164(ident)
        if k in keys:
            # 1:1 chats only for a person; group chats are listed by `chats`
            for (cid,) in c.execute("""SELECT j.chat_id FROM chat_handle_join j JOIN chat ch ON ch.ROWID=j.chat_id
                                       WHERE j.handle_id=? AND ch.style=45""", (hid,)):
                out.add(cid)
    if not out:
        sys.exit(f"No conversation found for {who!r}. Try `messages.py chats` and use the #number.")
    return sorted(out)


MSG_SQL = """
SELECT m.ROWID, m.date, m.is_from_me, h.id, m.text, m.attributedBody, m.cache_has_attachments,
       COALESCE(cm.chat_id, r.chat_id) AS chat_id, r.delete_date, m.associated_message_type
FROM message m
LEFT JOIN chat_message_join cm ON cm.message_id = m.ROWID
LEFT JOIN chat_recoverable_message_join r ON r.message_id = m.ROWID
LEFT JOIN handle h ON h.ROWID = m.handle_id
WHERE 1=1 {where}
ORDER BY m.date {order} LIMIT ?"""


def fetch(c, chats=None, since=None, until=None, deleted=False, text=None, limit=200, newest=True):
    where, args = [], []
    if chats:
        where.append(f"COALESCE(cm.chat_id, r.chat_id) IN ({','.join('?' * len(chats))})"); args += chats
    if since:
        where.append("m.date >= ?"); args.append(apple_ns(since))
    if until:
        where.append("m.date < ?"); args.append(apple_ns(until) + int(86400e9))
    if not deleted:
        where.append("r.message_id IS NULL")
    where.append("COALESCE(m.associated_message_type,0)=0")  # drop tapbacks/reactions
    sql = MSG_SQL.format(where="".join(" AND " + w for w in where), order="DESC" if newest else "ASC")
    rows = []
    # text search must run after decoding: most bodies live only in attributedBody
    for r in c.execute(sql, args + [limit if not text else 10 ** 9]):
        b = body(r[4], r[5])
        if text and text.lower() not in b.lower():
            continue
        rows.append({"id": r[0], "at": ts(r[1]), "me": bool(r[2]), "handle": r[3], "text": b,
                     "has_attachment": bool(r[6]), "chat": r[7], "deleted_at": ts(r[8])})
        if len(rows) >= limit:
            break
    return rows if newest is False else list(reversed(rows))


def line(m, labels=None):
    who = "me" if m["me"] else name_for(m["handle"])
    flag = " [DELETED]" if m["deleted_at"] else ""
    chat = f" ({labels[m['chat']]})" if labels else ""
    return f"[{m['at']:%Y-%m-%d %H:%M}]{chat} {who}{flag}: {m['text']}"


def cmd_chats(c, a):
    rows = c.execute("""SELECT ch.ROWID, ch.style, ch.service_name, max(m.date), count(*)
        FROM chat ch JOIN chat_message_join cm ON cm.chat_id=ch.ROWID JOIN message m ON m.ROWID=cm.message_id
        GROUP BY ch.ROWID ORDER BY max(m.date) DESC LIMIT ?""", (a.limit,)).fetchall()
    for cid, style, svc, last, n in rows:
        kind = "group" if style == 43 else "1:1"
        print(f"#{cid:<5} {ts(last):%Y-%m-%d}  {n:>6} msgs  {kind:5} {svc or '':8} {chat_label(c, cid)}")


def cmd_thread(c, a, export=None):
    chats = resolve(c, a.who)
    rows = fetch(c, chats, a.since, a.until, a.deleted, limit=a.limit)
    if export:
        title = chat_label(c, chats[0])
        with open(export, "w") as f:
            f.write(f"# Messages with {title}\n\n")
            day = None
            for m in rows:
                if m["at"].date() != day:
                    day = m["at"].date(); f.write(f"\n## {day:%A %Y-%m-%d}\n\n")
                who = "**me**" if m["me"] else f"**{name_for(m['handle'])}**"
                f.write(f"- {m['at']:%H:%M} {who}: {m['text']}\n")
        print(f"wrote {len(rows)} messages to {export}")
        return
    for m in rows:
        print(line(m))
    hint = "" if a.deleted else " (add --deleted to include Recently Deleted)"
    print(f"-- {len(rows)} message(s){hint}", file=sys.stderr)


def cmd_search(c, a):
    chats = resolve(c, a.who) if a.who else None
    rows = fetch(c, chats, a.since, a.until, a.deleted, text=a.q, limit=a.limit)
    labels = {cid: chat_label(c, cid) for cid in {m["chat"] for m in rows if m["chat"]}}
    labels[None] = "?"
    for m in rows:
        print(line(m, labels))
    hint = "" if a.deleted else " (add --deleted to include Recently Deleted)"
    print(f"-- {len(rows)} match(es){hint}", file=sys.stderr)


def cmd_attachments(c, a):
    chats = resolve(c, a.who)
    q = f"""SELECT m.date, m.is_from_me, at.transfer_name, COALESCE(at.mime_type, at.uti), at.total_bytes, at.filename
        FROM attachment at JOIN message_attachment_join ma ON ma.attachment_id=at.ROWID
        JOIN message m ON m.ROWID=ma.message_id JOIN chat_message_join cm ON cm.message_id=m.ROWID
        WHERE cm.chat_id IN ({','.join('?' * len(chats))}) {'AND m.date >= ?' if a.since else ''}
        ORDER BY m.date"""
    args = chats + ([apple_ns(a.since)] if a.since else [])
    for d, me, name, mime, size, fn in c.execute(q, args):
        path = os.path.expanduser(fn) if fn else ""
        state = "" if path and os.path.exists(path) else "  (not downloaded to this Mac)"
        print(f"[{ts(d):%Y-%m-%d}] {'me' if me else 'them'}  {mime or '?':24} {(size or 0)//1024:>7} KB  {path}{state}")


# ---------- optional never-prune archive ----------
def archive_sync(c):
    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    out = sqlite3.connect(ARCHIVE)
    out.executescript("""CREATE TABLE IF NOT EXISTS messages(guid TEXT PRIMARY KEY, chat_label TEXT, handle TEXT,
        is_from_me INT, sent_at TEXT, text TEXT, deleted_at TEXT, first_seen TEXT, last_seen TEXT, gone_from_mac TEXT);
        CREATE INDEX IF NOT EXISTS ix_sent ON messages(sent_at);""")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    labels = {}
    for g, cid, h, me, d, t, b, dd in c.execute("""SELECT m.guid, COALESCE(cm.chat_id, r.chat_id), h.id, m.is_from_me,
            m.date, m.text, m.attributedBody, r.delete_date FROM message m
            LEFT JOIN chat_message_join cm ON cm.message_id=m.ROWID
            LEFT JOIN chat_recoverable_message_join r ON r.message_id=m.ROWID
            LEFT JOIN handle h ON h.ROWID=m.handle_id"""):
        if cid is not None and cid not in labels:
            labels[cid] = chat_label(c, cid)
        fmt = lambda v: ts(v).strftime("%Y-%m-%d %H:%M:%S") if v else None
        out.execute("""INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,NULL) ON CONFLICT(guid) DO UPDATE SET
            text=COALESCE(excluded.text, messages.text), deleted_at=COALESCE(excluded.deleted_at, messages.deleted_at),
            last_seen=excluded.last_seen, gone_from_mac=NULL""",
            (g, labels.get(cid), h, me, fmt(d), body(t, b) or None, fmt(dd), now, now))
    out.execute("UPDATE messages SET gone_from_mac=? WHERE last_seen<? AND gone_from_mac IS NULL", (now, now))
    out.commit()
    tot, dele, gone = out.execute("SELECT count(*), sum(deleted_at IS NOT NULL), sum(gone_from_mac IS NOT NULL) FROM messages").fetchone()
    print(f"archived {tot}  in Recently Deleted {dele or 0}  purged from Mac but kept {gone or 0}  -> {ARCHIVE}")


def archive_search(q):
    out = sqlite3.connect(f"file:{ARCHIVE}?mode=ro", uri=True)
    for r in out.execute("""SELECT sent_at, chat_label, CASE WHEN is_from_me THEN 'me' ELSE handle END,
            CASE WHEN gone_from_mac IS NOT NULL THEN 'PURGED' WHEN deleted_at IS NOT NULL THEN 'DELETED' ELSE '' END, text
            FROM messages WHERE text LIKE ? ORDER BY sent_at DESC LIMIT 200""", (f"%{q}%",)):
        print(" | ".join(str(x or "") for x in r))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["chats", "thread", "search", "attachments", "export", "archive"])
    ap.add_argument("who", nargs="?", help="who / search text / archive action")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--who", dest="who_flag")
    ap.add_argument("--since"); ap.add_argument("--until")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--deleted", action="store_true", help="include Recently Deleted messages")
    ap.add_argument("--md", help="export: markdown output path")
    a = ap.parse_args()
    if a.cmd == "archive":
        if a.who == "search":
            return archive_search(" ".join(a.rest))
        return archive_sync(db())
    c = db()
    if a.cmd == "chats":
        a.limit = a.limit or 30; return cmd_chats(c, a)
    if not a.who:
        ap.error("missing argument")
    if a.cmd == "search":
        a.q, a.who, a.limit = " ".join([a.who] + a.rest), a.who_flag, a.limit or 100
        return cmd_search(c, a)
    if a.cmd == "attachments":
        return cmd_attachments(c, a)
    a.limit = a.limit or (10 ** 9 if a.cmd == "export" else 60)
    if a.cmd == "export" and not a.md:
        ap.error("export needs --md FILE")
    cmd_thread(c, a, export=a.md if a.cmd == "export" else None)


if __name__ == "__main__":
    main()
