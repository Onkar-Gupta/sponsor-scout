"""Synthetic UK job-advert generator. Labels are exact by construction: a record is drawn first, then rendered.

Held-out style families, sponsorship phrasings, job families and towns are used only in the held-out slice of the
test split. Output is fully deterministic for a given seed.
"""
import csv
import json
import random
import string
from datetime import date, timedelta
from pathlib import Path
from string import Formatter

import yaml

from . import banks
from .schema import date_forms, has_word, text_problems, to_annual, validate

ROOT = Path(__file__).resolve().parent.parent
SALARY_KINDS = ["range", "single", "up_to", "from", "hourly", "hourly_range", "daily", "pro_rata", "competitive",
                "negotiable", "absent"]
SALARY_WEIGHTS = [28, 12, 8, 6, 8, 5, 5, 3, 8, 4, 13]
MAX_ATTEMPTS = 200


def load_config():
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["generator"]


def load_register(path):
    """Casefolded names from the UK sponsor register CSV, or None when the file is absent."""
    if not path or not Path(path).exists():
        return None
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {" ".join(row["Organisation Name"].split()).casefold() for row in csv.DictReader(f)}


# ------------------------------------------------------------------------------------------- pools
def _pools(held):
    return {
        "styles": [s for s in banks.STYLE_NAMES if (s in banks.HELD_OUT_STYLES) == held],
        "families": [f for f in banks.JOB_FAMILIES if (f in banks.HELD_OUT_FAMILIES) == held],
        "towns": [t for t in banks.TOWNS if (t in banks.HELD_OUT_TOWNS) == held],
    }


def _phrase_ids(cls, held):
    return [p for p, (c, _, h) in banks.SPONSOR_PHRASES.items() if c == cls and h == held]


def _slices(split, n):
    if split == "test":
        return [("in_style", n - n // 2), ("held_out", n // 2)]
    return [("in_style", n)]


def _class_plan(n, mix, rng):
    """Exact class quotas (largest remainder), shuffled, so every split hits the mix."""
    counts = {c: int(n * p) for c, p in mix.items()}
    for c in sorted(mix, key=lambda c: counts[c] - n * mix[c])[: n - sum(counts.values())]:
        counts[c] += 1
    plan = [c for c in mix for _ in range(counts[c])]
    rng.shuffle(plan)
    return plan


# ------------------------------------------------------------------------------------ small drawers
def _core_name(rng):
    return rng.choice(banks.NAME_START) + rng.choice(banks.NAME_MIDDLE) + rng.choice(banks.NAME_END)


def _employer(rng, style, register):
    suffixes = banks.SUFFIXES.get(style, banks.SUFFIXES["default"])
    while True:
        core = _core_name(rng)
        name = f"University of {core}" if style == "university" else f"{core} {rng.choice(suffixes)}"
        if register is None or name.casefold() not in register:
            return name


def _money(v):
    return f"£{v:,}"


def _kay(v):
    return f"£{v // 1000}k"


def _rate(pence):
    return f"£{pence // 100}" if pence % 100 == 0 else f"£{pence / 100:.2f}"


def _salary(rng, band):
    """Return (text, salary_min, salary_max) following the labelling guide."""
    kind = rng.choices(SALARY_KINDS, SALARY_WEIGHTS)[0]
    lo_b, hi_b = band
    step = 1000 if rng.random() < 0.6 else 500
    if kind == "range":
        lo = rng.randrange(lo_b, hi_b - 5000, step)
        hi = lo + rng.choice([4000, 5000, 6000, 8000, 10000, 15000])
        forms = [f"{_money(lo)} - {_money(hi)}", f"{_money(lo)} to {_money(hi)}"]
        if lo % 1000 == 0 and hi % 1000 == 0:
            forms += [f"{_kay(lo)}-{_kay(hi)} DOE", f"{_kay(lo)} - {_kay(hi)}"]
        return rng.choice(forms), lo, hi
    if kind in ("single", "up_to", "from"):
        v = rng.randrange(lo_b, hi_b, step if kind == "single" else 1000)
        prefix = {"single": "", "up_to": "up to ", "from": "from "}[kind]
        forms = [f"{prefix}{_money(v)}"]
        if v % 1000 == 0:
            forms.append(f"{prefix}{_kay(v)}")
        if kind == "single":
            forms += [f"{_money(v)} per annum", f"{_money(v)} plus 8% pension"]
        return rng.choice(forms), None if kind == "up_to" else v, None if kind == "from" else v
    annual = rng.randrange(lo_b, hi_b)
    if kind == "hourly":
        pence = min(6000, max(1150, round(annual / 1950 * 4) * 25))
        v = to_annual(pence / 100, "hour")
        return rng.choice([f"{_rate(pence)} per hour", f"{_rate(pence)} an hour", f"{_rate(pence)}/hr"]), v, v
    if kind == "hourly_range":
        lo = max(12, round(annual / 1950))
        hi = lo + rng.choice([1, 2, 3])
        join = rng.choice([" - ", " to "])
        return f"£{lo}{join}£{hi} per hour", to_annual(lo, "hour"), to_annual(hi, "hour")
    if kind == "daily":
        rate = max(100, round(annual / 230 / 10) * 10)
        v = to_annual(rate, "day")
        return rng.choice([f"£{rate} per day", f"£{rate} a day"]), v, v
    if kind == "pro_rata":
        v = rng.randrange(lo_b // 2, lo_b, 500)
        return rng.choice([f"{_money(v)} pro rata for 3 days a week", f"{_money(v)} pro rata"]), v, v
    if kind == "competitive":
        return rng.choice(["competitive", "competitive, depending on experience"]), None, None
    if kind == "negotiable":
        return rng.choice(["negotiable", "negotiable depending on experience"]), None, None
    return "", None, None


def _show_skill(skill, mode):
    words = skill.split(" ")
    return " ".join(w.upper() if w in banks.ACRONYM_WORDS else (w.capitalize() if mode == "title" else w)
                    for w in words)


def _join(items):
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _ref(rng):
    if rng.random() < 0.5:
        return "".join(rng.choices(string.ascii_uppercase, k=3)) + f"-{rng.randint(1000, 9999)}"
    return ""


def _years(rng):
    n = rng.randint(1, 8)
    return n, rng.choice([f"{n}+ years", f"at least {n} years", f"minimum {n} years", f"{n} to {n + 2} years"])


# ------------------------------------------------------------------------------------------ drawing
def _dates(rng, closing):
    base = date(2026, 11, 16) + timedelta(rng.randint(0, 110))
    other = {
        "posted": date(2026, 11, 2) + timedelta(rng.randint(0, 12)),
        "start": base + timedelta(rng.randint(21, 100)),
        "interview": base + timedelta(rng.randint(7, 20)),
    }
    return (base if closing else None), other


def _draw_label(rng, pools, cls, style, register):
    """Draw the label plus the text-side choices that are not part of it."""
    family = rng.choice(pools["families"])
    fam = banks.JOB_FAMILIES[family]
    pattern = rng.choices(["on-site", "hybrid", "remote", None], [35, 30, 15, 20])[0]
    if pattern == "remote":
        location = "remote"
    else:
        location = rng.choice(pools["towns"]) if rng.random() < 0.9 else None
    text, smin, smax = _salary(rng, fam["band"])
    count = rng.choices(range(9), [1, 2, 3, 4, 4, 3, 2, 1, 1])[0]
    years = _years(rng) if rng.random() < 0.6 else (None, "")
    hidden = rng.random() < banks.HIDE_EMPLOYER.get(style, banks.HIDE_EMPLOYER_DEFAULT)
    closing, others = _dates(rng, rng.random() < 0.75)
    label = {
        "title": rng.choice(fam["titles"]),
        "employer": None if hidden else _employer(rng, style, register),
        "location": location,
        "salary_min": smin,
        "salary_max": smax,
        "work_pattern": pattern,
        "skills": rng.sample(fam["skills"], count),
        "years_experience_min": years[0],
        "closing_date": closing.isoformat() if closing else None,
        "sponsorship": cls,
    }
    return family, label, {"salary": text, "exp": years[1], "dates": others}


def _slots(rng, label, family, extra, pid):
    """Every slot a template may use. An empty string means the field is not stated."""
    fam = banks.JOB_FAMILIES[family]
    fmt = rng.randrange(4)

    def show(iso):
        return date_forms(iso)[fmt] if iso else ""

    mode = rng.choice(["lower", "title"])
    skills = [_show_skill(s, mode) for s in label["skills"]]
    emp = label["employer"]
    benefits = rng.sample(banks.BENEFITS, 2) if rng.random() < 0.85 else ["", ""]
    parts = banks.SPONSOR_PHRASES[pid][1] if pid != "none" else ()
    pattern = label["work_pattern"]
    others = {k: show(v.isoformat()) if rng.random() < p else ""
              for (k, v), p in zip(extra["dates"].items(), (0.5, 0.5, 0.3))}
    slots = {
        "title": label["title"], "employer": emp or "", "org": emp or "our client", "Org": emp or "Our client",
        "agency": f"{_core_name(rng)} {rng.choice(banks.AGENCY_SUFFIXES)}",
        "town": label["location"] if label["location"] not in (None, "remote") else "",
        "pattern": rng.choice(banks.PATTERNS[pattern]) if pattern else "",
        "salary": extra["salary"], "skills": _join(skills), "skills_bullets": "\n".join(f"- {s}" for s in skills),
        "exp": extra["exp"], "closing": show(label["closing_date"]), **others,
        "ref": _ref(rng),
        "sponsor_1": parts[0] if parts else "", "sponsor_2": parts[1] if len(parts) > 1 else "",
        "benefit_1": benefits[0], "benefit_2": benefits[1],
        "filler": rng.choice(banks.FILLER) if rng.random() < 0.5 else "",
    }
    slots["about"], extras = _about(rng, slots, fam, label["skills"], mode)
    return slots, extras


def _about(rng, slots, fam, asked, mode):
    """Company history years (not a requirement) and skills named only in the about-us text (not asked)."""
    sentences, named = [], []
    if rng.random() < 0.8:
        sentences.append(rng.choice(banks.ABOUT_HISTORY).format(
            Org=slots["Org"], org=slots["org"], n=rng.randint(12, 60), m=rng.randint(40, 900)))
    unasked = [s for s in fam["skills"] if s not in asked]
    if unasked and rng.random() < 0.4:
        named = rng.sample(unasked, min(len(unasked), rng.randint(1, 2)))
        sentences.append(rng.choice(banks.ABOUT_SKILLS).format(x=_join([_show_skill(s, mode) for s in named])))
    return " ".join(sentences), named


def render(template, slots):
    """Keep a line only if every slot it uses is non-empty."""
    kept = []
    for line in template:
        names = [f for _, f, _, _ in Formatter().parse(line) if f]
        if all(slots[n] != "" for n in names):
            kept.append(line.format(**slots))
    return "\n".join(kept)


def _draw(rng, pools, cls, held, register):
    style = rng.choice(pools["styles"])
    idx = rng.randrange(len(banks.STYLES[style]))
    family, label, extra = _draw_label(rng, pools, cls, style, register)
    pid = rng.choice(_phrase_ids(cls, held)) if cls != "not_stated" else "none"
    slots, named = _slots(rng, label, family, extra, pid)
    rec = {"id": "", "text": render(banks.STYLES[style][idx], slots), "label": label,
           "slice": "held_out" if held else "in_style", "style": style, "template_id": f"{style}-{idx + 1}",
           "sponsorship_phrase_id": pid, "job_family": family}
    return rec, named


def self_check(rec, named, max_chars):
    """Problems that make a drawn record unusable. The generator redraws until this list is empty."""
    label, low = rec["label"], rec["text"].casefold()
    errs = validate(label) + text_problems(rec)
    if len(rec["text"]) > max_chars:
        errs.append("text too long")
    stray = [s for s in banks.JOB_FAMILIES[rec["job_family"]]["skills"] if s not in label["skills"]]
    errs += [f"unasked skill in text: {s}" for s in stray if s not in named and has_word(s, low)]
    return errs


def generate(split, n, seed, register_path=None, config=None):
    """Return n records for a split. Same arguments, same output."""
    cfg = config or load_config()
    rng = random.Random(seed)
    register = load_register(register_path)
    out, seen = [], set()
    for slice_name, count in _slices(split, n):
        held = slice_name == "held_out"
        pools = _pools(held)
        for cls in _class_plan(count, cfg["class_mix"], rng):
            for _ in range(MAX_ATTEMPTS):
                rec, named = _draw(rng, pools, cls, held, register)
                key = json.dumps(rec["label"], sort_keys=True)
                if key not in seen and not self_check(rec, named, cfg["max_text_chars"]):
                    break
            else:
                raise RuntimeError(f"no valid record after {MAX_ATTEMPTS} draws for class {cls}")
            seen.add(key)
            rec["id"] = f"{split}-{len(out):04d}"
            out.append(rec)
    return out
