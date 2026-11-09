"""Download the current UK register of licensed sponsors (workers) to data/register/register.csv (gitignored).

    python scripts/download_register.py

The register is published by the Home Office on GOV.UK under the Open Government Licence v3.0 and changes often,
so it is fetched at run time and never committed.
"""
import json
import urllib.request
from pathlib import Path

PAGE = "https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers"
OUT = Path(__file__).resolve().parent.parent / "data" / "register" / "register.csv"

with urllib.request.urlopen(PAGE, timeout=30) as r:
    url = json.load(r)["details"]["attachments"][0]["url"]
OUT.parent.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(url, timeout=120) as r:
    OUT.write_bytes(r.read())
print(f"saved {OUT} ({OUT.stat().st_size // 1024} KB) from {url}")
