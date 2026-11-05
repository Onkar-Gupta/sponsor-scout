"""Check the three split files (or three drafts). Prints a JSON report and exits non-zero on any failure.

Usage: python eval/check_data.py [--dir data] [--train P --dev P --test P]
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from sponsor_scout import banks
from sponsor_scout.generator import load_config
from sponsor_scout.schema import text_problems, validate

SPLITS = ("train", "dev", "test")
MAX_SHOWN = 20


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def grams(text, n=8):
    words = re.findall(r"\w+", text.casefold())
    return [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]


def held_out_hits(rec):
    """Names the held-out things this record uses."""
    hits = []
    if rec["style"] in banks.HELD_OUT_STYLES:
        hits.append(f"style {rec['style']}")
    if banks.SPONSOR_PHRASES.get(rec["sponsorship_phrase_id"], (0, 0, False))[2]:
        hits.append(f"phrase {rec['sponsorship_phrase_id']}")
    if rec["job_family"] in banks.HELD_OUT_FAMILIES:
        hits.append(f"job family {rec['job_family']}")
    if rec["label"]["location"] in banks.HELD_OUT_TOWNS:
        hits.append(f"town {rec['label']['location']}")
    return hits


def record_problems(rec):
    problems = [f"label: {e}" for e in validate(rec["label"])] + text_problems(rec)
    if not rec["template_id"].startswith(rec["style"] + "-"):
        problems.append("template_id does not belong to style")
    return problems


def not_held_out(rec):
    """What a held-out record uses that is NOT held out (it should be nothing)."""
    pid, town = rec["sponsorship_phrase_id"], rec["label"]["location"]
    bad = []
    if rec["style"] not in banks.HELD_OUT_STYLES:
        bad.append(f"style {rec['style']}")
    if rec["job_family"] not in banks.HELD_OUT_FAMILIES:
        bad.append(f"job family {rec['job_family']}")
    if pid != "none" and not banks.SPONSOR_PHRASES[pid][2]:
        bad.append(f"phrase {pid}")
    if town not in (None, "remote") and town not in banks.HELD_OUT_TOWNS:
        bad.append(f"town {town}")
    return bad


def leak_problems(split, rec):
    """Held-out items must stay in the held-out slice; that slice must use only held-out items."""
    if rec["slice"] == "held_out":
        if split != "test":
            return ["held_out slice outside test"]
        return [f"held_out record uses in-style {b}" for b in not_held_out(rec)]
    return [f"held-out item in {split}/in_style: {h}" for h in held_out_hits(rec)]


def overlap(train, rows):
    seen = {g for r in train for g in grams(r["text"])}
    total = hits = 0
    for r in rows:
        g = grams(r["text"])
        total += len(g)
        hits += sum(x in seen for x in g)
    return {"records": len(rows), "grams": total, "share_in_train": round(hits / total, 4) if total else None}


def check(data, cfg):
    report, failures = {"counts": {}, "class_mix": {}, "ngram_overlap_with_train": {}}, []
    keys = {}
    for split, rows in data.items():
        report["counts"][split] = dict(Counter(r["slice"] for r in rows)) | {"total": len(rows)}
        mix = Counter(r["label"]["sponsorship"] for r in rows)
        report["class_mix"][split] = {c: round(100 * mix[c] / len(rows), 1) if rows else 0 for c in cfg["class_mix"]}
        for c, share in cfg["class_mix"].items():
            if rows and abs(report["class_mix"][split][c] - 100 * share) > cfg["class_tolerance_points"]:
                failures.append(f"{split}: class {c} is {report['class_mix'][split][c]} percent, target {100 * share}")
        for rec in rows:
            failures += [f"{rec['id']}: {p}" for p in record_problems(rec) + leak_problems(split, rec)]
            keys.setdefault(json.dumps(rec["label"], sort_keys=True), set()).add(split)
    failures += [f"label appears in splits {sorted(s)}: {k[:80]}" for k, s in keys.items() if len(s) > 1]
    for sl in ("in_style", "held_out"):
        rows = [r for r in data["test"] if r["slice"] == sl]
        report["ngram_overlap_with_train"][sl] = overlap(data["train"], rows)
    report["failure_count"] = len(failures)
    report["failures_shown"] = failures[:MAX_SHOWN]
    report["ok"] = not failures
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="data")
    for s in SPLITS:
        ap.add_argument(f"--{s}", help=f"path to the {s} file (default: <dir>/{s}.jsonl)")
    args = ap.parse_args(argv)
    paths = {s: Path(getattr(args, s) or Path(args.dir) / f"{s}.jsonl") for s in SPLITS}
    report = check({s: load(p) for s, p in paths.items()}, load_config())
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
