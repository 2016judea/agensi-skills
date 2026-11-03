#!/usr/bin/env python3
"""Read the macOS Contacts (AddressBook) database, read-only, on-device.

Usage:
  contacts.py search <text>          name / org / nickname / email / phone digits
  contacts.py lookup <phone|email>   reverse lookup: who owns this number or address
  contacts.py list                   everyone, sorted by name
  contacts.py export --csv FILE | --vcf FILE [--query TEXT]
  common flags: --country 1 (default calling code for 10-digit numbers), --json
"""
import argparse, csv, glob, json, os, re, sqlite3, sys

BASE = os.path.expanduser("~/Library/Application Support/AddressBook")


def databases():
    # One DB per account under Sources/; the root file is the local "On My Mac" store.
    dbs = glob.glob(os.path.join(BASE, "Sources", "*", "AddressBook-v22.abcddb"))
    root = os.path.join(BASE, "AddressBook-v22.abcddb")
    return dbs + ([root] if os.path.exists(root) else [])


def e164(raw, country="1"):
    """Normalise a phone string to E.164 (+15551234567). Returns None if it has no digits."""
    if not raw:
        return None
    raw = raw.strip()
    d = re.sub(r"\D", "", raw)
    if not d:
        return None
    if raw.startswith("+"):
        return "+" + d
    if d.startswith("00"):
        return "+" + d[2:]
    if country == "1":
        if len(d) == 10:
            return "+1" + d
        if len(d) == 11 and d.startswith("1"):
            return "+" + d
    elif d.startswith("0"):
        return "+" + country + d.lstrip("0")
    return ("+" + country + d) if len(d) <= 10 else "+" + d


def label(l):
    # Apple stores built-in labels as _$!<Mobile>!$_
    m = re.match(r"_\$!<(.*)>!\$_", l or "")
    return (m.group(1) if m else (l or "")).lower()


def load(country="1"):
    people = {}
    for path in databases():
        try:
            c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            ent = c.execute("SELECT Z_ENT FROM Z_PRIMARYKEY WHERE Z_NAME='ABCDContact'").fetchone()
            if not ent:
                continue
            recs = c.execute("""SELECT Z_PK, ZFIRSTNAME, ZMIDDLENAME, ZLASTNAME, ZNICKNAME, ZORGANIZATION,
                                ZJOBTITLE, ZBIRTHDAY FROM ZABCDRECORD WHERE Z_ENT=?""", ent).fetchall()
            phones, emails, notes, addrs = {}, {}, {}, {}
            for o, n, l in c.execute("SELECT ZOWNER, ZFULLNUMBER, ZLABEL FROM ZABCDPHONENUMBER"):
                if n:
                    phones.setdefault(o, []).append({"raw": n, "e164": e164(n, country), "label": label(l)})
            for o, a, l in c.execute("SELECT ZOWNER, ZADDRESS, ZLABEL FROM ZABCDEMAILADDRESS"):
                if a:
                    emails.setdefault(o, []).append({"address": a.strip(), "label": label(l)})
            for o, t in c.execute("SELECT ZCONTACT, ZTEXT FROM ZABCDNOTE"):
                if t:
                    notes[o] = t
            for o, st, ci, sa, z, co in c.execute(
                    "SELECT ZOWNER, ZSTREET, ZCITY, ZSTATE, ZZIPCODE, ZCOUNTRYNAME FROM ZABCDPOSTALADDRESS"):
                addrs.setdefault(o, []).append(", ".join(x for x in (st, ci, sa, z, co) if x))
        except sqlite3.Error as e:
            print(f"warn: {path}: {e}", file=sys.stderr)
            continue
        for pk, fn, mn, ln, nick, org, job, bday in recs:
            name = " ".join(x for x in (fn, mn, ln) if x) or org or nick or ""
            if not name and pk not in phones and pk not in emails:
                continue
            p = {"name": name, "first": fn, "last": ln, "nickname": nick, "organization": org,
                 "job_title": job, "phones": phones.get(pk, []), "emails": emails.get(pk, []),
                 "addresses": addrs.get(pk, []), "note": notes.get(pk)}
            # The same person usually appears once per account (iCloud + Google...): merge them.
            key = name.lower() or (p["phones"][0]["e164"] if p["phones"] else p["emails"][0]["address"].lower())
            if key in people:
                q = people[key]
                have = {x["e164"] for x in q["phones"]}
                q["phones"] += [x for x in p["phones"] if x["e164"] not in have]
                have = {x["address"].lower() for x in q["emails"]}
                q["emails"] += [x for x in p["emails"] if x["address"].lower() not in have]
                for k in ("organization", "job_title", "nickname", "note"):
                    q[k] = q[k] or p[k]
                q["addresses"] = q["addresses"] or p["addresses"]
            else:
                people[key] = p
    return sorted(people.values(), key=lambda p: p["name"].lower())


def matches(p, q, country):
    ql = q.lower()
    hay = " ".join(str(p[k] or "") for k in ("name", "nickname", "organization")).lower()
    if ql in hay or any(ql in e["address"].lower() for e in p["emails"]):
        return True
    qd = re.sub(r"\D", "", q)
    return len(qd) >= 4 and any(qd in re.sub(r"\D", "", x["e164"] or "") for x in p["phones"])


def lookup(people, ident, country="1"):
    """Exact reverse lookup of a phone (any format) or email -> list of people."""
    if "@" in ident:
        return [p for p in people if any(e["address"].lower() == ident.lower() for e in p["emails"])]
    n = e164(ident, country)
    return [p for p in people if any(x["e164"] == n for x in p["phones"])]


def show(p):
    line = p["name"] + (f"  ({p['organization']})" if p["organization"] and p["organization"] != p["name"] else "")
    print(line)
    for x in p["phones"]:
        print(f"   {x['label'] or 'phone':8} {x['e164']}")
    for e in p["emails"]:
        print(f"   {e['label'] or 'email':8} {e['address']}")


def vcard(p):
    esc = lambda s: (s or "").replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
    out = ["BEGIN:VCARD", "VERSION:3.0", f"FN:{esc(p['name'])}", f"N:{esc(p['last'])};{esc(p['first'])};;;"]
    if p["organization"]:
        out.append(f"ORG:{esc(p['organization'])}")
    out += [f"TEL;TYPE={(x['label'] or 'voice').upper()}:{x['e164']}" for x in p["phones"]]
    out += [f"EMAIL;TYPE=INTERNET:{e['address']}" for e in p["emails"]]
    if p["note"]:
        out.append(f"NOTE:{esc(p['note'])}")
    return "\r\n".join(out + ["END:VCARD"]) + "\r\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["search", "lookup", "list", "export"])
    ap.add_argument("q", nargs="?")
    ap.add_argument("--country", default="1")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--vcf")
    ap.add_argument("--query")
    a = ap.parse_args()
    if not databases():
        sys.exit("No AddressBook database found. Grant Full Disk Access to your terminal (see SKILL.md).")
    people = load(a.country)
    if a.cmd == "search":
        res = [p for p in people if matches(p, a.q or "", a.country)]
    elif a.cmd == "lookup":
        res = lookup(people, a.q or "", a.country)
    elif a.cmd == "list":
        res = people
    else:
        res = [p for p in people if not a.query or matches(p, a.query, a.country)]
        if a.csv:
            with open(a.csv, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "organization", "phones", "emails"])
                for p in res:
                    w.writerow([p["name"], p["organization"] or "", ";".join(x["e164"] for x in p["phones"]),
                                ";".join(e["address"] for e in p["emails"])])
        if a.vcf:
            with open(a.vcf, "w") as f:
                f.writelines(vcard(p) for p in res)
        print(f"exported {len(res)} contacts")
        return
    if a.json:
        print(json.dumps(res, indent=1, default=str))
    else:
        for p in res:
            show(p)
        print(f"-- {len(res)} contact(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
