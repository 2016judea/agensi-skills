#!/usr/bin/env python3
"""
Download the two source files needed to build a Melville-annotated edition
of a Shakespeare play:
  1. The marginalia volume's TEI-XML from Melville's Marginalia Online.
  2. The play's plain text from Folger Digital Texts (CC BY-NC 4.0).

Usage:
    python3 fetch_sources.py --doc-id 31 --folger-slug king-lear --outdir .

Find --doc-id (and confirm the play actually has marks) with list_plays.py
first. --folger-slug is the slug Folger uses in its download URL, e.g.
"king-lear", "macbeth", "hamlet" -- check
https://shakespeare.folger.edu/shakespeares-works/<slug>/ if unsure.
"""
import argparse
import os
import urllib.request

UA = "Mozilla/5.0 (personal research script)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-id", type=int, required=True)
    ap.add_argument("--folger-slug", required=True, help='e.g. "king-lear"')
    ap.add_argument("--outdir", default=".")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    xml_url = f"https://melvillesmarginalia.org/XmlDownload.ashx?DocId={args.doc_id}&Stage=False"
    xml_path = os.path.join(args.outdir, f"vol{args.doc_id}_raw.xml")
    print("fetching", xml_url)
    open(xml_path, "wb").write(fetch(xml_url))
    print("wrote", xml_path)

    # Folger's download URL redirects through a short-link + S3; let urllib
    # follow redirects itself (it does, by default).
    txt_url = f"https://shakespeare.folger.edu/downloads/txt/{args.folger_slug}_TXT_FolgerShakespeare.txt"
    txt_path = os.path.join(args.outdir, f"{args.folger_slug}_folger.txt")
    print("fetching", txt_url)
    open(txt_path, "wb").write(fetch(txt_url))
    print("wrote", txt_path)


if __name__ == "__main__":
    main()
