"""Freeze guard (protocol F1). The official splits and the schema must never change silently.

The hashes in data/SHA256SUMS.json were written once, when the data was generated. If this test fails, either a
file changed by accident (restore it) or a change is intended: log a dated Amendment in eval/protocol.md first,
then regenerate the hashes with `python tests/test_freeze_guard.py --write`.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUMS = ROOT / "data" / "SHA256SUMS.json"
FILES = ["data/train.jsonl", "data/dev.jsonl", "data/test.jsonl", "schema.json"]


def digest(rel):
    """SHA-256 of a file with Windows line endings folded to Unix ones, so a CRLF checkout hashes the same."""
    return hashlib.sha256((ROOT / rel).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_official_files_match_the_recorded_hashes():
    recorded = json.loads(SUMS.read_text(encoding="utf-8"))
    assert sorted(recorded) == sorted(FILES)
    changed = [rel for rel in FILES if digest(rel) != recorded[rel]]
    assert not changed, f"frozen files changed: {changed}"


def test_split_sizes_are_the_protocol_sizes():
    sizes = {s: len((ROOT / "data" / f"{s}.jsonl").read_text(encoding="utf-8").splitlines()) for s in ("train", "dev", "test")}
    assert sizes == {"train": 2000, "dev": 300, "test": 600}


if __name__ == "__main__":
    if "--write" in sys.argv:
        SUMS.write_text(json.dumps({rel: digest(rel) for rel in FILES}, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {SUMS}")
