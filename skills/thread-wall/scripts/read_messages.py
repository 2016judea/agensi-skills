#!/usr/bin/env python3
"""Read recent iMessage/SMS history with a contact.

Usage: read_messages.py <+1number> [limit]
Prints oldest-first: [timestamp] ME/THEM: text
Decodes the attributedBody blob (modern macOS leaves the `text` column NULL).
Read-only; stays on-device.
"""
import sqlite3, os, re, sys

def decode(blob, text):
    if text:
        return text
    if not blob:
        return ''
    s = blob.decode('utf-8', 'ignore')
    i = s.find('NSString')
    if i == -1:
        return ''
    seg = s[i + len('NSString'):]
    m = re.search(r'[\x01-\x06].{0,3}([ -~\n\t ].*)', seg, re.S)
    out = m.group(1) if m else seg
    out = re.split(r'\x86|NSDictionary|NSNumber|iI\x01', out)[0]
    return out.strip()

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: read_messages.py <+1number> [limit]")
    num = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    db = os.path.expanduser('~/Library/Messages/chat.db')
    c = sqlite3.connect(db)
    hids = [r[0] for r in c.execute("SELECT ROWID FROM handle WHERE id=?", (num,))]
    if not hids:
        sys.exit(f"no handle found for {num}")
    ph = ",".join("?" * len(hids))
    q = (f"SELECT datetime(date/1000000000+978307200,'unixepoch','localtime'),"
         f"is_from_me,text,attributedBody FROM message "
         f"WHERE handle_id IN ({ph}) ORDER BY date DESC LIMIT ?")
    rows = c.execute(q, hids + [limit]).fetchall()
    for ts, me, text, blob in reversed(rows):
        who = 'ME  ' if me else 'THEM'
        print(f"[{ts}] {who}: {decode(blob, text)}")

if __name__ == '__main__':
    main()