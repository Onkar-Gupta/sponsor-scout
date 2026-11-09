"""Check the private real-advert labels against schema.json. Prints counts only, never advert text."""
import json
import sys
from pathlib import Path

from sponsor_scout.schema import validate

path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/private/adverts.jsonl")
rows, bad, ids = 0, 0, set()
for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
    if not line.strip():
        continue
    rows += 1
    try:
        r = json.loads(line)
        errs = validate(r["label"]) + ([] if r.get("text", "").strip() else ["empty text"])
        errs += ["duplicate id"] if r["id"] in ids else []
        ids.add(r["id"])
    except (ValueError, KeyError) as e:
        errs = [f"bad record: {e!r}"]
    if errs:
        bad += 1
        print(f"line {n}: {'; '.join(errs)}")
print(f"{rows} records, {bad} with problems (target 50, 0 problems)")
sys.exit(1 if bad or rows != 50 else 0)
