#!/usr/bin/env python3
"""
Discover which Melville's Marginalia Online volume/DocId contains a given
Shakespeare play, its page range within that volume, and how many marks
Melville actually left in that range (some plays have ZERO -- check before
investing time in the alignment step).

Usage:
    python3 list_plays.py                  # list every play in every volume
    python3 list_plays.py --play macbeth   # just the volume(s) matching a name

The Dramatic Works set is DocId 25-31 (Vol. 1-7); DocId 32 is a separate
volume, the Sonnets (different edition, 1865). Discovered while building
a King Lear edition.
"""
import argparse
import re
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://melvillesmarginalia.org"
UA = "Mozilla/5.0 (personal research script)"
DRAMATIC_WORKS_DOC_IDS = list(range(25, 32))  # Vol. 1-7


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req).read().decode("utf-8", errors="replace")


def plays_in_volume(doc_id):
    html = fetch(f"{BASE}/Viewer.aspx?did={doc_id}")
    # Static HTML contains: <span class="navlink">Play Name (pp. 3-108)</span>
    return re.findall(r'<span class="navlink">([^(<]+)\(pp\. (\d+)-(\d+)\)</span>', html)


def mark_count(doc_id, page_start, page_end):
    xml_text = fetch(f"{BASE}/XmlDownload.ashx?DocId={doc_id}&Stage=False")
    root = ET.fromstring(xml_text)
    count = 0
    for div in root.iter("div"):
        page = div.get("page")
        if not page:
            continue
        try:
            pnum = int(page.split(".")[-1])
        except ValueError:
            continue
        if page_start <= pnum <= page_end:
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--play", help="substring to filter play titles, e.g. 'macbeth'")
    ap.add_argument("--skip-counts", action="store_true", help="skip the mark-count preflight (faster)")
    args = ap.parse_args()

    for doc_id in DRAMATIC_WORKS_DOC_IDS:
        for title, start, end in plays_in_volume(doc_id):
            title = title.strip()
            if args.play and args.play.lower() not in title.lower():
                continue
            start, end = int(start), int(end)
            if args.skip_counts:
                print(f"DocId {doc_id:>2}  pp.{start:>4}-{end:<4}  {title}")
            else:
                n = mark_count(doc_id, start, end)
                flag = "  <-- NO MARKS, skip" if n == 0 else ""
                print(f"DocId {doc_id:>2}  pp.{start:>4}-{end:<4}  {n:>3} marks  {title}{flag}")


if __name__ == "__main__":
    main()
