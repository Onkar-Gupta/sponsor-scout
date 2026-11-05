"""Train one LoRA adapter on the train split.

    python scripts/train.py --name r16_lr2e-4_e2 --rank 16 --lr 0.0002 --epochs 2
    python scripts/train.py --name check --rank 16 --lr 0.0002 --epochs 1 --smoke     (5 steps, uses no budget)

Values must be in the pre-registered grid (config.yaml, training.allowed). Set HF_HOME in the shell first.
The adapter is saved under outputs/adapters/, outside git. Each real run writes reports/dev_train_<name>.json.
"""
import argparse
import json

import yaml

from sponsor_scout.train import ROOT, train


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--lr", type=float, required=True)
    ap.add_argument("--epochs", type=int, required=True)
    ap.add_argument("--smoke", action="store_true", help="5 steps only; writes no report and uses no run of the budget")
    args = ap.parse_args(argv)
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    report = train(args.name, args.rank, args.lr, args.epochs, cfg, max_steps=5 if args.smoke else None)
    print(json.dumps({k: v for k, v in report.items() if k != "losses"}, indent=1))


if __name__ == "__main__":
    main()
