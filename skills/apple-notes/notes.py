#!/usr/bin/env python3
"""Read & search Apple Notes from the local NoteStore.sqlite (read-only)."""
import argparse, datetime, gzip, os, re, sqlite3, sys

DB = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
)
APPLE_EPOCH = datetime.datetime(2001, 1, 1)

def _read_varint(b, i):
    shift = result = 0
    while True:
        byte = b[i]; i += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, i
        shift += 7

def _field(b, want):
    """Return raw bytes of the first length-delimited (wtype 2) field `want`."""
    i, n = 0, len(b)
    while i < n:
        tag, i = _read_varint(b, i)
        fnum, wtype = tag >> 3, tag & 7
        if wtype == 2:
            ln, i = _read_varint(b, i)
            chunk = b[i:i+ln]; i += ln
            if fnum == want:
                return chunk
        elif wtype == 0:
            _, i = _read_varint(b, i)
        elif wtype == 1:
            i += 8
        elif wtype == 5:
            i += 4
        else:
            break
    return None

def note_text(blob):
    """Apple Notes proto: Document(2) -> Note(3) -> note_text(2)."""
    raw = gzip.decompress(blob)
    doc = _field(raw, 2)
    if doc is None: return ""
    note = _field(doc, 3)
    if note is None: return ""
    txt = _field(note, 2)
    if txt is None: return ""
    return txt.decode("utf-8", "ignore")

def rows():
    con = sqlite3.connect(f"file:{DB}?immutable=1", uri=True)
    cur = con.execute("""
        SELECT n.ZTITLE1, d.ZDATA, n.ZMODIFICATIONDATE1
        FROM ZICNOTEDATA d
        JOIN ZICCLOUDSYNCINGOBJECT n ON n.ZNOTEDATA = d.Z_PK
        WHERE d.ZDATA IS NOT NULL
    """)
    for title, blob, mod in cur.fetchall():
        try:
            body = note_text(blob)
        except Exception:
            continue
        when = (APPLE_EPOCH + datetime.timedelta(seconds=mod)) if mod else None
        yield (title or "", body, when)

def main():
    ap = argparse.ArgumentParser(description="Search/read Apple Notes (read-only).")
    ap.add_argument("query", nargs="?", help="case-insensitive search term")
    ap.add_argument("--full", action="store_true", help="print full matching note bodies")
    ap.add_argument("--list", action="store_true", help="list all note titles (newest first)")
    a = ap.parse_args()

    items = sorted(rows(), key=lambda r: r[2] or APPLE_EPOCH, reverse=True)

    if a.list:
        for t, _, w in items:
            print(f"{w:%Y-%m-%d}  {t}" if w else f"            {t}")
        return

    if not a.query:
        ap.error("provide a search term, or use --list")

    q = a.query.lower()
    hits = [(t, b, w) for t, b, w in items if q in t.lower() or q in b.lower()]
    print(f"{len(hits)} match(es) for {a.query!r}\n")
    for t, b, w in hits:
        print("=" * 64)
        print(f"TITLE: {t}    ({w:%Y-%m-%d %H:%M})" if w else f"TITLE: {t}")
        if a.full:
            print("\n" + b.strip() + "\n")
        else:
            m = re.search(re.escape(a.query), b, re.I)
            if m:
                s, e = max(0, m.start()-120), min(len(b), m.start()+200)
                print("…" + b[s:e].strip().replace("\n", " ") + "…")

if __name__ == "__main__":
    main()
