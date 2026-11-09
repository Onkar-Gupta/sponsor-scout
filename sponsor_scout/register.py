"""Look an employer up on the UK Home Office register of licensed sponsors (workers). Run time only, never part of the
pre-registered test. A licence shows the employer CAN sponsor; it does not show that a given job is sponsored.

Exact match on a normalised name first; if none, close matches (difflib, ratio >= 0.9) are listed as possibilities only.
Register: https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers (OGL v3.0, see README).
"""
import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher

SUFFIXES = {"ltd", "limited", "plc", "llp", "llc", "inc", "uk", "the"}


def normalise(name):
    """Casefold, '&' to 'and', drop punctuation and company-form words (ltd, limited, plc, llp, llc, inc, uk, the)."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.casefold().replace("&", " and ")).split()
    return " ".join(w for w in words if w not in SUFFIXES)


def load_register(path):
    """Returns {normalised name: [{"name", "town", "rating", "route"}]}. One organisation has one row per route."""
    index = defaultdict(list)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row["Organisation Name"].strip()
            index[normalise(name)].append({"name": name, "town": row["Town/City"].strip(),
                                           "rating": row["Type & Rating"].strip(), "route": row["Route"].strip()})
    return index


def _summary(rows):
    return {"name": rows[0]["name"], "towns": sorted({r["town"] for r in rows if r["town"]}),
            "ratings": sorted({r["rating"] for r in rows}),
            "skilled_worker": any(r["route"] == "Skilled Worker" for r in rows)}


def lookup(employer, index, cutoff=0.9):
    """{"match": "exact" | "close" | "none", "organisations": [...]}. employer may be None (a hidden client)."""
    key = normalise(employer or "")
    if not key:
        return {"match": "none", "organisations": []}
    if key in index:
        return {"match": "exact", "organisations": [_summary(index[key])]}
    first = key.split()[0]
    close = [k for k in index if k.split()[:1] == [first] and SequenceMatcher(None, key, k).ratio() >= cutoff]
    return {"match": "close" if close else "none", "organisations": [_summary(index[k]) for k in sorted(close)[:5]]}
