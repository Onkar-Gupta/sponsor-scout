"""The Colab notebook is valid JSON and every repo script or command it calls exists. It cannot be run in CI (needs a GPU)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB = json.loads((ROOT / "notebooks" / "colab.ipynb").read_text(encoding="utf-8"))


def test_notebook_has_code_cells_and_calls_only_scripts_that_exist():
    code = "\n".join("".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "code")
    scripts = set(re.findall(r"scripts/\w+\.py", code))
    assert {"scripts/train.py", "scripts/run_arm.py", "scripts/score_run.py"} <= scripts
    assert all((ROOT / s).exists() for s in scripts)
    assert "sponsor-scout extract" in code


def test_notebook_training_settings_match_the_frozen_ones():
    code = "\n".join("".join(c["source"]) for c in NB["cells"] if c["cell_type"] == "code")
    assert "--rank 16 --lr 0.0002 --epochs 2" in code
