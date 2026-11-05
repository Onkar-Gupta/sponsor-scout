"""sponsor-scout extract: turn one advert (file or stdin) into JSON."""
import argparse
import json
import sys
from pathlib import Path

import yaml

from .infer import ARMS, build_generator, messages_for
from .prompts import pick_fewshot
from .score import parse_output

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sponsor-scout")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("extract", help="extract the JSON record from one advert")
    ex.add_argument("--file", help="advert text file (default: stdin)")
    ex.add_argument("--arm", choices=ARMS, default="few_shot")
    ex.add_argument("--adapter", help="LoRA adapter folder (for --arm tuned)")
    args = ap.parse_args(argv)

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    examples = []
    if args.arm == "few_shot":
        lines = (ROOT / cfg["data_dir"] / "train.jsonl").read_text(encoding="utf-8").splitlines()
        examples = pick_fewshot([json.loads(x) for x in lines if x.strip()], 1)
    output, _ = build_generator(args.arm, cfg, args.adapter)(messages_for(args.arm, text, examples))
    record = parse_output(output)
    if record is None:
        print("Note: the model output is not valid JSON for the schema. Raw text follows.\n" + output)
        return 1
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
