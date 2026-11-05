"""Write synthetic adverts as JSONL. Drafts only, unless --official is passed (step 5 uses that for data/)."""
import argparse
import json
import sys
from pathlib import Path

import yaml

from sponsor_scout.generator import ROOT, generate, load_config


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=["train", "dev", "test"])
    ap.add_argument("--n", type=int, help="record count (default: size from config.yaml)")
    ap.add_argument("--out", required=True, help="output .jsonl path")
    ap.add_argument("--register", help="optional UK sponsor register CSV (column 'Organisation Name')")
    ap.add_argument("--official", action="store_true", help="allow writing into the frozen data/ folder")
    args = ap.parse_args(argv)

    cfg = load_config()
    out = Path(args.out).resolve()
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        data_dir = (ROOT / yaml.safe_load(f)["data_dir"]).resolve()
    if out.is_relative_to(data_dir) and not args.official:
        sys.exit(f"Refusing to write into {data_dir} without --official. Write drafts elsewhere.")

    records = generate(args.split, args.n or cfg["sizes"][args.split], cfg["seeds"][args.split], args.register, cfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(rec, ensure_ascii=False) + "\n" for rec in records)
    print(f"wrote {len(records)} {args.split} records to {out}")


if __name__ == "__main__":
    main()
