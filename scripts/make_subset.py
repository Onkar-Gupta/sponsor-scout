"""Write the fixed 50-advert test subset (25 in-style, 25 held-out) as a list of ids. Seed 0. Run once, before any test output."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = [json.loads(x) for x in (ROOT / "data" / "test.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
rng = random.Random(0)
ids = []
for s in ("in_style", "held_out"):
    ids += rng.sample([r["id"] for r in rows if r["slice"] == s], 25)
order = {r["id"]: i for i, r in enumerate(rows)}
out = ROOT / "data" / "test_subset50.json"
out.write_text(json.dumps(sorted(ids, key=order.get)) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {len(ids)} ids to {out}")
