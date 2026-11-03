#!/usr/bin/env python3
"""Shared, stdlib-only parsing for gmail-read: raw RFC 822 bytes -> clean text, attachments, markdown.
Both routes (Gmail API format=raw, IMAP RFC822) hand this module the same bytes, so one parser serves both.
Run directly on a .eml to test:  python3 mailtext.py message.eml [--md] [--save-attachments DIR]"""
import email, email.policy, html, os, re, sys
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser

class _Text(HTMLParser):
    BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "blockquote", "hr"}
    SKIP = {"script", "style", "head", "title"}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.skip = 0; self.href = None
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self.skip += 1
        elif tag in self.BLOCK: self.out.append("\n")
        if tag == "li": self.out.append("- ")
        if tag == "a": self.href = dict(attrs).get("href")
    def handle_endtag(self, tag):
        if tag in self.SKIP: self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK: self.out.append("\n")
        if tag == "a" and self.href and self.href.startswith("http"):
            self.out.append(f" <{self.href}>"); self.href = None
    def handle_data(self, data):
        if not self.skip: self.out.append(data)

def html_to_text(s):
    p = _Text(); p.feed(s); p.close()
    t = "".join(p.out).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return re.sub(r"\n\n(?=- )", "\n", t).strip()

def _decode(part):
    try:
        return part.get_content()
    except (LookupError, UnicodeDecodeError, AssertionError):
        raw = part.get_payload(decode=True) or b""
        return raw.decode(part.get_content_charset() or "utf-8", "replace")

def strip_quoted(text):
    """Cut the quoted history a reply drags along ('On ... wrote:' and '>' lines). Thread export uses it."""
    lines, out = text.splitlines(), []
    for i, l in enumerate(lines):
        if re.match(r"^On .{4,200}wrote:\s*$", l) or re.match(r"^-{2,} ?Original Message ?-{2,}", l, re.I):
            break
        if re.match(r"^On .{4,200}$", l) and i + 1 < len(lines) and lines[i + 1].strip().endswith("wrote:"):
            break
        if not l.startswith(">"): out.append(l)
    return "\n".join(out).rstrip()

def parse(raw: bytes):
    """-> dict: headers, date (ISO), body (clean text), attachments [{filename, mime, size, part}]."""
    msg = email.message_from_bytes(raw, policy=email.policy.default)
    plain, htm, atts = [], [], []
    for part in msg.walk():
        if part.is_multipart(): continue
        disp = part.get_content_disposition()
        ctype = part.get_content_type()
        fname = part.get_filename()
        if disp == "attachment" or (fname and disp != "inline") or (fname and not ctype.startswith("text/")):
            payload = part.get_payload(decode=True) or b""
            atts.append({"filename": safe_name(fname or "unnamed"), "mime": ctype, "size": len(payload), "part": part})
        elif ctype == "text/plain": plain.append(_decode(part))
        elif ctype == "text/html": htm.append(_decode(part))
    body = "\n\n".join(plain).strip() if plain else html_to_text("\n".join(htm))
    body = re.sub(r"\r\n?", "\n", body)
    try:
        dt = parsedate_to_datetime(msg["Date"]); date, ts = dt.isoformat(), dt.timestamp()
    except (TypeError, ValueError, IndexError): date, ts = str(msg["Date"] or ""), 0.0
    h = lambda k: str(msg[k] or "")
    return {"from": h("From"), "to": h("To"), "cc": h("Cc"), "subject": h("Subject"), "date": date, "ts": ts,
            "message_id": h("Message-ID"), "in_reply_to": h("In-Reply-To"), "references": h("References"),
            "body": body, "attachments": atts}

def safe_name(n):
    n = os.path.basename(n.replace("\\", "/")) or "unnamed"
    return re.sub(r"[\x00-\x1f/:]", "_", n)[:200]

def save_attachments(m, outdir, only=None):
    os.makedirs(outdir, exist_ok=True); saved = []
    for a in m["attachments"]:
        if only and only not in a["filename"]: continue
        p = os.path.join(outdir, safe_name(a["filename"])); base, ext = os.path.splitext(p); k = 1
        while os.path.exists(p): p = f"{base}-{k}{ext}"; k += 1
        open(p, "wb").write(a["part"].get_payload(decode=True) or b""); saved.append(p)
    return saved

def as_text(m):
    head = [f"From: {m['from']}", f"To: {m['to']}"] + ([f"Cc: {m['cc']}"] if m["cc"] else []) + \
           [f"Date: {m['date']}", f"Subject: {m['subject']}"]
    if m["attachments"]:
        head.append("Attachments: " + ", ".join(f"{a['filename']} ({a['mime']}, {a['size']} B)" for a in m["attachments"]))
    return "\n".join(head) + "\n\n" + m["body"]

def thread_markdown(msgs, quoted=False):
    """msgs: parsed dicts, any order. Oldest first, one section per message, quoted history cut by default."""
    msgs = sorted(msgs, key=lambda m: m["ts"])   # parsed time, not the string: offsets differ
    subj = msgs[0]["subject"] if msgs else "(empty thread)"
    people = sorted({n or a for n, a in getaddresses([m["from"] for m in msgs])})
    out = [f"# {subj}", "", f"{len(msgs)} message{'s' if len(msgs) != 1 else ''} · {msgs[0]['date'][:10] if msgs else ''} to "
           f"{msgs[-1]['date'][:10] if msgs else ''} · {', '.join(people)}", ""]
    for m in msgs:
        out += [f"## {m['from']} — {m['date']}", ""]
        if m["attachments"]:
            out += ["Attachments: " + ", ".join(f"`{a['filename']}`" for a in m["attachments"]), ""]
        out += [m["body"] if quoted else strip_quoted(m["body"]), ""]
    return "\n".join(out).rstrip() + "\n"

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    m = parse(open(args[0], "rb").read())
    print(thread_markdown([m]) if "--md" in args else as_text(m))
    if "--save-attachments" in args:
        for p in save_attachments(m, args[args.index("--save-attachments") + 1]): print("saved", p)
