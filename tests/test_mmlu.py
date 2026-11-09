"""MMLU check: prompt layout and the mark 6 arithmetic. No GPU, no download."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("mmlu_check", ROOT / "scripts" / "mmlu_check.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_prompt_lists_four_lettered_options_and_ends_with_answer():
    text = mod.prompt({"question": "Q?", "choices": ["w", "x", "y", "z"]})
    assert "Q?\nA. w\nB. x\nC. y\nD. z\nAnswer:" in text and text.endswith("Answer:")


def test_mark_6_passes_at_exactly_two_points_below_and_fails_beyond():
    base = [1] * 100
    ok = mod.paired_report(base, [1] * 98 + [0] * 2, resamples=200)
    bad = mod.paired_report(base, [1] * 97 + [0] * 3, resamples=200)
    assert round(ok["difference_tuned_minus_base"], 6) == -0.02 and ok["mark_6_pass"]
    assert not bad["mark_6_pass"]
