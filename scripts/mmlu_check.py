"""MMLU forgetting check (protocol sections 4 and 5, mark 6). Base and tuned on the same 1,000 questions.

    python scripts/mmlu_check.py --adapter outputs/adapters/r16_lr2e-4_e2 --out reports/mmlu.json --official

Questions: 1,000 drawn with random.Random(0) from the cais/mmlu "all" test split, zero-shot, plain prompt, the answer
is the letter (A to D) with the highest next-token log-likelihood. The base answers are taken from the same loaded
model with the adapter switched off. Needs a clean git tree and a new output file (same rule as run_arm.py).
Set HF_HOME in the shell to keep downloads outside the repo.
"""
import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import yaml

from sponsor_scout.score import _pct, wilson

ROOT = Path(__file__).resolve().parent.parent
LETTERS = "ABCD"


def prompt(row):
    opts = "\n".join(f"{L}. {c}" for L, c in zip(LETTERS, row["choices"]))
    return ("The following is a multiple choice question. Answer with the letter of the correct option.\n\n"
            f"{row['question']}\n{opts}\nAnswer:")


def paired_report(base, tuned, resamples=10000, seed=0):
    """base, tuned: lists of 0/1 correctness on the same questions. Mark 6: tuned no more than 2.0 points below base."""
    n = len(base)
    diff = [t - b for b, t in zip(base, tuned)]
    rng = random.Random(seed)
    boots = sorted(sum(diff[i] for i in rng.choices(range(n), k=n)) / n for _ in range(resamples))
    point = sum(diff) / n
    return {"n": n, "base_accuracy": sum(base) / n, "tuned_accuracy": sum(tuned) / n,
            "base_wilson": wilson(sum(base), n), "tuned_wilson": wilson(sum(tuned), n),
            "difference_tuned_minus_base": point, "difference_interval": (_pct(boots, 0.025), _pct(boots, 0.975)),
            "mark_6_pass": point >= -0.02}


def tree_is_dirty():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    return bool(out.stdout.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, help="dry run on the first N questions; not for --official")
    ap.add_argument("--official", action="store_true")
    args = ap.parse_args(argv)
    if args.official:
        if args.limit:
            sys.exit("refused: --limit is for dry runs only")
        if tree_is_dirty():
            sys.exit("refused: git tree is not clean; commit first so the run is tied to a commit")
        if Path(args.out).exists():
            sys.exit(f"refused: {args.out} already exists; an official output is never overwritten")
    import torch
    from datasets import load_dataset

    from sponsor_scout.infer import load_hf

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    data = load_dataset("cais/mmlu", "all", split="test")
    idx = sorted(random.Random(0).sample(range(len(data)), 1000))[: args.limit]
    model, tok = load_hf(cfg["base_model"], args.adapter)
    ids = [tok.encode(" " + L, add_special_tokens=False)[-1] for L in LETTERS]

    def answer(row):
        enc = tok(prompt(row), return_tensors="pt").to(model.device)
        with torch.no_grad():
            logits = model(**enc).logits[0, -1]
        return int(logits[ids].argmax())

    base, tuned, start = [], [], time.perf_counter()
    for n, i in enumerate(idx, 1):
        row = data[i]
        with model.disable_adapter():
            base.append(int(answer(row) == row["answer"]))
        tuned.append(int(answer(row) == row["answer"]))
        if n % 20 == 0 or n == len(idx):
            el = time.perf_counter() - start
            sys.stderr.write(f"\rmmlu: {n}/{len(idx)}  elapsed {el:.0f}s  remaining ~{el / n * (len(idx) - n):.0f}s ")
    sys.stderr.write("\n")
    report = paired_report(base, tuned)
    report.update(sample_indices=idx, base_correct=base, tuned_correct=tuned, adapter=args.adapter)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    report["commit"] = commit
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print({k: v for k, v in report.items() if k not in ("sample_indices", "base_correct", "tuned_correct")})


if __name__ == "__main__":
    main()
