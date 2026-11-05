"""Score model outputs against a gold split. One arm (--pred) gives a report; --fewshot and --tuned together give the pass-mark comparison."""
import argparse
import json
import sys
from pathlib import Path

from sponsor_scout.score import aggregate, compare, score_all


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_preds(path, gold_ids):
    rows = read_jsonl(path)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        sys.exit(f"{path}: duplicate ids")
    if set(ids) != set(gold_ids):
        missing, extra = set(gold_ids) - set(ids), set(ids) - set(gold_ids)
        sys.exit(f"{path}: ids do not match gold ({len(missing)} missing, {len(extra)} unexpected)")
    return {r["id"]: r["output"] for r in rows}


def single_report(gold, outs):
    per = score_all(gold, outs)
    report = {"all": aggregate(per)}
    held = [p for g, p in zip(gold, per) if g.get("slice") == "held_out"]
    if held:
        report["held_out"] = aggregate(held)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold", required=True, help="split JSONL from make_adverts.py")
    ap.add_argument("--pred", help="single arm: JSONL with id and output (raw model text)")
    ap.add_argument("--fewshot", help="comparison: the few-shot arm's JSONL")
    ap.add_argument("--tuned", help="comparison: the tuned arm's JSONL (the difference is tuned minus few-shot)")
    ap.add_argument("--out", help="write the JSON report here")
    args = ap.parse_args(argv)

    if bool(args.pred) == bool(args.fewshot or args.tuned) or bool(args.fewshot) != bool(args.tuned):
        sys.exit("give either --pred, or both --fewshot and --tuned")
    gold = read_jsonl(args.gold)
    ids = [g["id"] for g in gold]
    if args.pred:
        report = single_report(gold, load_preds(args.pred, ids))
    else:
        report = compare(gold, load_preds(args.tuned, ids), load_preds(args.fewshot, ids))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)


if __name__ == "__main__":
    main()
