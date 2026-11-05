"""Label validation (reads schema.json) and the text-recoverability check shared by the generator and the checker."""
import json
import math
import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from . import banks

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PATTERN_WORDS = {
    "on-site": ("on-site", "on site", "office based", "office-based"),
    "hybrid": ("hybrid",),
    "remote": ("remote",),
}
NO_PATTERN_WORDS = ("hybrid", "remote", "on-site", "on site", "office based", "office-based", "work from home",
                    "working from home")
NO_SPONSOR_WORDS = ("sponsor", "visa", "right to work")


# ------------------------------------------------------------------------------------------ validation
def _type_ok(value, name):
    if name == "null":
        return value is None
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if isinstance(value, bool):
        return False
    if name == "integer":
        return isinstance(value, int)
    return name == "number" and isinstance(value, (int, float)) and not math.isnan(value)


def _value_errors(key, value, rule):
    if "enum" in rule:
        return [] if value in rule["enum"] else [f"{key}: {value!r} not in {rule['enum']}"]
    names = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
    if not any(_type_ok(value, n) for n in names):
        return [f"{key}: {value!r} is not of type {names}"]
    errs = []
    if isinstance(value, list):
        for item in value:
            errs += _value_errors(f"{key}[]", item, rule["items"])
        if len(set(map(str, value))) != len(value):
            errs.append(f"{key}: duplicate items")
    if isinstance(value, str) and "pattern" in rule:
        if not re.search(rule["pattern"], value):
            errs.append(f"{key}: {value!r} does not match {rule['pattern']}")
        else:
            try:
                date.fromisoformat(value)
            except ValueError:
                errs.append(f"{key}: {value!r} is not a real date")
    return errs


def validate(label, schema=None):
    """Return a list of error strings for a label dict. An empty list means valid."""
    schema = schema or json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(label, dict):
        return ["label is not an object"]
    errs = [f"missing key: {k}" for k in schema["required"] if k not in label]
    errs += [f"extra key: {k}" for k in label if k not in schema["properties"]]
    for key, rule in schema["properties"].items():
        if key in label:
            errs += _value_errors(key, label[key], rule)
    return errs


# ------------------------------------------------------------------------------ text recoverability
def to_annual(amount, unit):
    """Guide conversion to pounds a year: hourly x 37.5 x 52, daily x 230, annual as printed. Nearest pound."""
    factor = {"year": 1, "hour": Decimal("37.5") * 52, "day": 230}[unit]
    return int((Decimal(str(amount)) * factor).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def date_forms(iso):
    """Every way the generator may print an ISO date."""
    d = date.fromisoformat(iso)
    ordinal = "th" if 10 <= d.day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(d.day % 10, "th")
    month = MONTHS[d.month - 1]
    return [f"{d.day} {month} {d.year}", f"{d.day} {month[:3]} {d.year}", f"{d.day:02d}/{d.month:02d}/{d.year}",
            f"{d.day}{ordinal} {month} {d.year}"]


def _salary_candidates(low):
    """Annual figures a reader following the guide could take from the text."""
    per_hour = re.search(r"per hour|an hour|/hr|hourly", low)
    per_day = re.search(r"per day|a day|daily", low)
    found = set()
    for num, k in re.findall(r"£\s?(\d[\d,]*(?:\.\d+)?)(k?)", low):
        value = Decimal(num.replace(",", "")) * (1000 if k else 1)
        found.add(to_annual(value, "year"))
        if per_hour:
            found.add(to_annual(value, "hour"))
        if per_day:
            found.add(to_annual(value, "day"))
    return found


def has_word(term, low):
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", low) is not None


def text_problems(rec):
    """Check that every non-null label value is recoverable from the text and null fields are not stated."""
    label, low = rec["label"], rec["text"].casefold()
    errs = []
    if not has_word(label["title"], low):
        errs.append("title not in text")
    if label["employer"] and not has_word(label["employer"], low):
        errs.append("employer not in text")
    loc = label["location"]
    if loc is None and any(has_word(t, low) for t in banks.TOWNS):
        errs.append("location is null but a town is stated")
    if loc and not has_word(loc, low):
        errs.append("location not in text")
    pattern = label["work_pattern"]
    if pattern is None and any(w in low for w in NO_PATTERN_WORDS):
        errs.append("work_pattern is null but the text states one")
    if pattern and not any(w in low for w in PATTERN_WORDS[pattern]):
        errs.append("work_pattern not in text")
    cands = _salary_candidates(low)
    errs += [f"{k} {label[k]} not recoverable" for k in ("salary_min", "salary_max")
             if label[k] is not None and label[k] not in cands]
    errs += [f"skill not in text: {s}" for s in label["skills"] if not has_word(s, low)]
    n = label["years_experience_min"]
    if n is not None and not re.search(rf"(?<!\d){n}(?!\d)[^.\n]{{0,25}}year", low):
        errs.append("years_experience_min not in text")
    if label["closing_date"] and not any(f.casefold() in low for f in date_forms(label["closing_date"])):
        errs.append("closing_date not in text")
    return errs + _sponsor_problems(rec, low)


def _sponsor_problems(rec, low):
    cls = rec["label"]["sponsorship"]
    pid = rec["sponsorship_phrase_id"]
    if cls == "not_stated":
        bad = [w for w in NO_SPONSOR_WORDS if w in low]
        return ["not_stated but text mentions " + ",".join(bad)] if bad else []
    if pid not in banks.SPONSOR_PHRASES or banks.SPONSOR_PHRASES[pid][0] != cls:
        return [f"phrase id {pid} does not belong to class {cls}"]
    return [f"sponsorship part missing: {p}" for p in banks.SPONSOR_PHRASES[pid][1] if p.casefold() not in low]
