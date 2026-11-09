"""Run one evaluation arm over a split and write one JSON line per advert.

    python scripts/run_arm.py --arm few_shot --split dev --out outputs/dev_few_shot.jsonl [--limit 5] [--resume]

The test and private splits are refused unless --official is given. --official also needs a clean git tree and a new output file.
Set HF_HOME in the shell to keep the model download outside the repo.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from sponsor_scout.infer import ARMS, run_arm

ROOT = Path(__file__).resolve().parent.parent


def tree_is_dirty():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True)
    return bool(out.stdout.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", required=True, choices=ARMS)
    ap.add_argument("--split", required=True, choices=["train", "dev", "test", "private"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--adapter")
    ap.add_argument("--fewshot-version", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids-file", help="JSON list of advert ids; only these are run (the fixed test subset)")
    ap.add_argument("--batch-size", type=int, help="adverts per GPU batch; overrides config.yaml (inference.batch_size)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--official", action="store_true", help="the one scored run on test or private")
    args = ap.parse_args(argv)

    if args.split in ("test", "private") and not args.official:
        sys.exit(f"refused: the {args.split} split is run once, at the official step, with --official")
    if args.official:
        if args.split not in ("test", "private"):
            sys.exit("refused: --official is for the test and private splits only")
        if tree_is_dirty():
            sys.exit("refused: git tree is not clean; commit first so the run is tied to a commit")
        if Path(args.out).exists():
            sys.exit(f"refused: {args.out} already exists; an official output is never overwritten")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    if args.batch_size:
        cfg["inference"]["batch_size"] = args.batch_size
    cfg["data_dir"] = str(ROOT / cfg["data_dir"])
    data = Path(cfg["data_dir"]) / ("private/adverts.jsonl" if args.split == "private" else f"{args.split}.jsonl")
    with open(data, encoding="utf-8") as f:
        records = [json.loads(x) for x in f if x.strip()][: args.limit]
    if args.ids_file:
        keep = set(json.loads(Path(args.ids_file).read_text(encoding="utf-8")))
        records = [r for r in records if r["id"] in keep]
        assert len(records) == len(keep), "ids file names adverts that are not in the split"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    run_arm(args.arm, records, args.out, cfg, adapter=args.adapter, fewshot_version=args.fewshot_version,
            resume=args.resume)


if __name__ == "__main__":
    main()
