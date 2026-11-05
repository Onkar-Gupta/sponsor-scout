"""Known-answer tests for the scorer. Every expected number is worked out by hand in the comment above it."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from sponsor_scout.score import (
    CLASSES,
    SCALARS,
    aggregate,
    compare,
    norm,
    paired_bootstrap,
    parse_output,
    score_record,
    wilson,
)

ROOT = Path(__file__).resolve().parent.parent
BASE = {"title": "Data Analyst", "employer": "Acme Ltd", "location": "Leeds", "salary_min": 40000,
        "salary_max": 50000, "work_pattern": "hybrid", "skills": ["python", "sql"], "years_experience_min": 3,
        "closing_date": "2026-12-14", "sponsorship": "offers"}


def label(**kw):
    return {**BASE, **kw}


def out(**kw):
    return json.dumps(label(**kw))


def spec_load(relpath, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


score_run = spec_load("scripts/score_run.py", "score_run")


# ------------------------------------------------------------------------------------------ parse_output
def test_plain_json_is_valid():
    assert parse_output(out()) == BASE


def test_surrounding_whitespace_is_stripped():
    assert parse_output("\n  " + out() + " \n\n") == BASE


@pytest.mark.parametrize("fence", ["```json\n{}\n```", "```\n{}\n```", "```json{}```"])
def test_one_code_fence_is_allowed(fence):
    assert parse_output(fence.format(out())) == BASE


def test_prose_before_the_object_is_invalid():
    assert parse_output("Here is the record:\n" + out()) is None


def test_trailing_text_is_invalid():
    assert parse_output(out() + "\nHope that helps") is None


def test_two_objects_are_invalid():
    assert parse_output(out() + "\n" + out()) is None


def test_fence_with_prose_inside_is_invalid():
    assert parse_output("```json\nSure!\n" + out() + "\n```") is None


def test_extra_key_and_missing_key_are_invalid():
    assert parse_output(json.dumps({**BASE, "salary_currency": "GBP"})) is None
    assert parse_output(json.dumps({k: v for k, v in BASE.items() if k != "skills"})) is None


def test_non_object_and_non_string_are_invalid():
    assert parse_output("[1, 2]") is None
    assert parse_output("") is None
    assert parse_output(None) is None


def test_bad_enum_value_is_invalid():
    assert parse_output(out(sponsorship="maybe")) is None


# ------------------------------------------------------------------------------------------ norm and fields
def test_norm():
    assert norm("  Data   ANALYST ") == "data analyst"
    assert norm(40000) == 40000
    assert norm(None) is None


def test_perfect_output_scores_everything():
    s = score_record(BASE, out())
    assert s["valid"] and s["exact"] and all(s["fields"].values())
    assert (s["skills_tp"], s["skills_fp"], s["skills_fn"]) == (2, 0, 0)


def test_casefold_and_whitespace_still_match():
    s = score_record(BASE, out(title="  data   ANALYST", location="LEEDS", skills=["SQL", " Python "]))
    assert s["fields"]["title"] and s["fields"]["location"] and s["exact"]


def test_wrong_text_field_is_wrong_only_for_that_field():
    s = score_record(BASE, out(employer="Beta Ltd"))
    assert not s["fields"]["employer"] and sum(s["fields"].values()) == 8 and not s["exact"]


def test_null_matches_null_only():
    gold = label(employer=None)
    assert score_record(gold, out(employer=None))["fields"]["employer"]
    assert not score_record(label(), out(employer=None))["fields"]["employer"]


def test_null_label_with_value_is_wrong_and_invented():
    s = score_record(label(salary_min=None), out(salary_min=30000))
    assert not s["fields"]["salary_min"]
    assert s["invented"] == {"salary_min": True} and s["null_fields"] == 1


def test_null_label_with_null_output_is_not_invented():
    assert score_record(label(salary_min=None), out(salary_min=None))["invented"] == {"salary_min": False}


def test_salary_must_be_exact():
    assert not score_record(BASE, out(salary_min=40001))["fields"]["salary_min"]
    assert score_record(BASE, out(salary_min=40000.0))["fields"]["salary_min"]


def test_years_compared_as_numbers():
    assert not score_record(BASE, out(years_experience_min=4))["fields"]["years_experience_min"]


def test_skills_are_a_set_ignoring_order_and_case():
    assert score_record(BASE, out(skills=["SQL", "Python"]))["exact"]


def test_extra_skill_makes_the_set_wrong():
    # gold {python, sql}; output {python, sql, excel}: tp 2, fp 1, fn 0
    s = score_record(BASE, out(skills=["python", "sql", "excel"]))
    assert (s["skills_tp"], s["skills_fp"], s["skills_fn"]) == (2, 1, 0)
    assert not s["exact"] and all(s["fields"].values())


def test_missing_skill_counts_as_false_negative():
    s = score_record(BASE, out(skills=["python"]))
    assert (s["skills_tp"], s["skills_fp"], s["skills_fn"]) == (1, 0, 1)


def test_invalid_output_scores_zero_on_every_field():
    s = score_record(BASE, "not json")
    assert not s["valid"] and not any(s["fields"].values()) and not s["exact"]
    assert s["pred_sponsorship"] == "invalid" and s["invented"] == {}
    assert (s["skills_tp"], s["skills_fp"], s["skills_fn"]) == (0, 0, 2)


def test_nine_scalar_fields_exclude_skills():
    assert len(SCALARS) == 9 and "skills" not in SCALARS


# ------------------------------------------------------------------------------------------ aggregates
def test_mean_field_accuracy_is_micro_average():
    # advert 1 perfect: 9 correct. advert 2 has 2 wrong scalars: 7 correct. advert 3 invalid: 0 correct.
    # (9 + 7 + 0) / (9 x 3) = 16 / 27
    per = [score_record(BASE, out()), score_record(BASE, out(title="x", location="y")), score_record(BASE, "{")]
    agg = aggregate(per)
    assert agg["mean_field_accuracy"] == pytest.approx(16 / 27)
    assert agg["json_validity"] == pytest.approx(2 / 3)
    assert agg["per_field_accuracy"]["title"] == pytest.approx(1 / 3)
    assert agg["exact_match"] == pytest.approx(1 / 3)


def test_skills_f1_is_pooled_over_adverts():
    # advert 1: tp 2 fp 0 fn 0. advert 2: output [python, excel]: tp 1 fp 1 fn 1. advert 3 invalid: fn 2.
    # pooled tp 3, fp 1, fn 3: F1 = 2x3 / (2x3 + 1 + 3) = 6 / 10 = 0.6
    per = [score_record(BASE, out()), score_record(BASE, out(skills=["python", "excel"])),
           score_record(BASE, "nope")]
    assert aggregate(per)["skills_f1"] == pytest.approx(0.6)


def test_sponsorship_confusion_and_macro_f1():
    # (true, predicted): O>O, O>O, O>E, E>E, E>invalid, N>N, U>O, U>U. Eight adverts, five right.
    # offers:     tp 2, fp 1 (the U>O), fn 1 (the O>E)  -> F1 = 4 / 6 = 2/3
    # excludes:   tp 1, fp 1 (the O>E), fn 1 (E>invalid) -> F1 = 2 / 4 = 0.5   (invalid adds no false positive)
    # not_stated: tp 1, fp 0, fn 0                       -> F1 = 1
    # unclear:    tp 1, fp 0, fn 1 (the U>O)             -> F1 = 2 / 3
    # macro = (2/3 + 0.5 + 1 + 2/3) / 4 = 0.708333...
    pairs = [("offers", "offers")] * 2 + [("offers", "excludes"), ("excludes", "excludes"), ("excludes", None),
                                         ("not_stated", "not_stated"), ("unclear", "offers"), ("unclear", "unclear")]
    per = [score_record(label(sponsorship=t), out(sponsorship=p) if p else "bad") for t, p in pairs]
    agg = aggregate(per)
    assert agg["sponsorship_accuracy"] == pytest.approx(5 / 8)
    assert agg["sponsorship_macro_f1"] == pytest.approx((2 / 3 + 0.5 + 1 + 2 / 3) / 4)
    m = agg["sponsorship_confusion"]
    assert m["offers"] == {"offers": 2, "excludes": 1, "not_stated": 0, "unclear": 0, "invalid": 0}
    assert m["excludes"]["invalid"] == 1 and m["unclear"]["offers"] == 1
    assert sum(sum(row.values()) for row in m.values()) == 8
    assert set(m) == set(CLASSES)


def test_invented_value_rate_uses_valid_outputs_only():
    # gold has employer and salary_min null (2 null fields per advert).
    # advert 1 valid: employer invented, salary_min null -> 1 invented of 2.
    # advert 2 invalid: left out of numerator and denominator. Rate = 1 / 2.
    gold = label(employer=None, salary_min=None)
    per = [score_record(gold, out(employer="Acme", salary_min=None)), score_record(gold, "garbage")]
    agg = aggregate(per)
    assert agg["invented_value_rate"] == pytest.approx(0.5)
    assert agg["invented_counted_on_valid_only"] == {"valid_outputs": 1, "invalid_outputs": 1, "null_fields": 2,
                                                     "invented": 1}


def test_invented_rate_is_zero_when_no_null_fields():
    assert aggregate([score_record(BASE, out())])["invented_value_rate"] == 0.0


# ------------------------------------------------------------------------------------------ wilson
def test_wilson_half():
    lo, hi = wilson(50, 100)
    assert lo == pytest.approx(0.404, abs=0.001) and hi == pytest.approx(0.596, abs=0.001)


def test_wilson_zero_successes():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.278, abs=0.001)


def test_wilson_all_successes_upper_is_one():
    assert wilson(10, 10)[1] == 1.0


# ------------------------------------------------------------------------------------------ bootstrap
def adverts(n=30):
    """n gold adverts cycling through the four classes; second half is the held-out slice."""
    return [{"id": f"a{i}", "text": "", "slice": "held_out" if i >= n // 2 else "in_style",
             "label": label(sponsorship=CLASSES[i % 4])} for i in range(n)]


def perfect(gold):
    return {g["id"]: json.dumps(g["label"]) for g in gold}


def broken(gold):
    return {g["id"]: "no" for g in gold}


@pytest.mark.parametrize("metric", ["mean_field_accuracy", "sponsorship_macro_f1", "invented_value_rate",
                                    "json_validity"])
def test_identical_arms_give_a_zero_interval(metric):
    gold = adverts()
    r = paired_bootstrap(gold, perfect(gold), perfect(gold), metric, resamples=200)
    assert r["difference"] == 0 and r["low"] <= 0 <= r["high"]


def test_bootstrap_is_deterministic_for_a_seed():
    gold = adverts()
    a = {g["id"]: (json.dumps(g["label"]) if i % 3 else "x") for i, g in enumerate(gold)}
    r1 = paired_bootstrap(gold, a, perfect(gold), "mean_field_accuracy", resamples=300, seed=5)
    r2 = paired_bootstrap(gold, a, perfect(gold), "mean_field_accuracy", resamples=300, seed=5)
    assert r1 == r2


def test_clearly_better_arm_has_a_positive_interval():
    # arm a is invalid everywhere (0), arm b is perfect (1), so every resample gives exactly +1.
    gold = adverts()
    r = paired_bootstrap(gold, broken(gold), perfect(gold), "mean_field_accuracy", resamples=200)
    assert r["difference"] == pytest.approx(1.0) and r["low"] == pytest.approx(1.0)


def test_unknown_metric_is_rejected():
    gold = adverts()
    with pytest.raises(ValueError):
        paired_bootstrap(gold, perfect(gold), perfect(gold), "bogus", resamples=5)


def test_mismatched_ids_are_rejected():
    gold = adverts()
    with pytest.raises(ValueError):
        paired_bootstrap(gold, {"zzz": "x"}, perfect(gold), "json_validity", resamples=5)


# ------------------------------------------------------------------------------------------ compare
def test_compare_marks_met_when_tuned_is_clearly_better():
    gold = adverts()
    c = compare(gold, perfect(gold), broken(gold), resamples=200)
    assert c["mark_1_full_test_mean_field_accuracy"]["met"]
    assert c["mark_2_held_out_mean_field_accuracy"]["met"] and c["mark_2_held_out_mean_field_accuracy"]["n"] == 15
    assert c["mark_3_sponsorship_macro_f1"]["met"]
    assert c["mark_4_tuned_json_validity"]["met"] and c["mark_5_invented_value_rate"]["met"]
    assert c["marks_met_of_5"] == 5


def test_compare_flags_equal_arms_as_not_met():
    # identical arms: difference 0 fails marks 1 to 3 (interval low is not above 0); marks 4 and 5 still hold.
    gold = adverts()
    c = compare(gold, perfect(gold), perfect(gold), resamples=200)
    assert not c["mark_1_full_test_mean_field_accuracy"]["met"]
    assert not c["mark_2_held_out_mean_field_accuracy"]["met"]
    assert not c["mark_3_sponsorship_macro_f1"]["met"]
    assert c["mark_4_tuned_json_validity"]["met"] and c["mark_5_invented_value_rate"]["met"]
    assert c["marks_met_of_5"] == 2


def test_compare_flags_low_validity():
    # 2 of 30 tuned outputs invalid: validity 28 / 30 = 0.933 < 0.99
    gold = adverts()
    tuned = perfect(gold)
    tuned["a0"] = tuned["a1"] = "oops"
    c = compare(gold, tuned, broken(gold), resamples=100)
    assert not c["mark_4_tuned_json_validity"]["met"]
    assert c["mark_4_tuned_json_validity"]["validity"] == pytest.approx(28 / 30)


def test_compare_flags_more_invention_in_tuned():
    # gold employer is null. tuned invents it on every advert, few-shot leaves it null: 1 / 1 versus 0 / 1 per advert.
    gold = [{"id": f"a{i}", "slice": "held_out", "text": "", "label": label(employer=None)} for i in range(10)]
    tuned = {g["id"]: out(employer="Made Up Ltd") for g in gold}
    few = {g["id"]: out(employer=None) for g in gold}
    c = compare(gold, tuned, few, resamples=100)
    m5 = c["mark_5_invented_value_rate"]
    assert m5["tuned"] == pytest.approx(1.0) and m5["fewshot"] == 0.0 and not m5["met"]


def test_compare_does_not_report_mark_6():
    gold = adverts()
    c = compare(gold, perfect(gold), broken(gold), resamples=50)
    assert not any("6" in k.split("_")[1] for k in c if k.startswith("mark_"))


def test_compare_accepts_explicit_held_out_ids():
    gold = adverts()
    c = compare(gold, perfect(gold), broken(gold), held_out_ids=["a0", "a1", "a2"], resamples=50)
    assert c["mark_2_held_out_mean_field_accuracy"]["n"] == 3


# ------------------------------------------------------------------------------------------ score_run
def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_score_run_single_arm(tmp_path, capsys):
    gold = adverts(8)
    write_jsonl(tmp_path / "g.jsonl", gold)
    write_jsonl(tmp_path / "p.jsonl", [{"id": g["id"], "output": json.dumps(g["label"])} for g in gold])
    score_run.main(["--gold", str(tmp_path / "g.jsonl"), "--pred", str(tmp_path / "p.jsonl"),
                    "--out", str(tmp_path / "r.json")])
    report = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert report["all"]["mean_field_accuracy"] == 1.0 and report["held_out"]["n"] == 4
    assert "mean_field_accuracy" in capsys.readouterr().out


def test_score_run_two_arms(tmp_path):
    gold = adverts(8)
    write_jsonl(tmp_path / "g.jsonl", gold)
    write_jsonl(tmp_path / "a.jsonl", [{"id": g["id"], "output": "no"} for g in gold])
    write_jsonl(tmp_path / "b.jsonl", [{"id": g["id"], "output": json.dumps(g["label"])} for g in gold])
    score_run.main(["--gold", str(tmp_path / "g.jsonl"), "--fewshot", str(tmp_path / "a.jsonl"),
                    "--tuned", str(tmp_path / "b.jsonl"), "--out", str(tmp_path / "r.json")])
    report = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert report["mark_1_full_test_mean_field_accuracy"]["met"]


@pytest.mark.parametrize("case", ["missing", "extra", "duplicate"])
def test_score_run_exits_nonzero_on_mismatched_ids(tmp_path, case):
    gold = adverts(6)
    write_jsonl(tmp_path / "g.jsonl", gold)
    rows = [{"id": g["id"], "output": "x"} for g in gold]
    rows = {"missing": rows[:-1], "extra": rows + [{"id": "zzz", "output": "x"}], "duplicate": rows + rows[:1]}[case]
    write_jsonl(tmp_path / "p.jsonl", rows)
    with pytest.raises(SystemExit) as e:
        score_run.main(["--gold", str(tmp_path / "g.jsonl"), "--pred", str(tmp_path / "p.jsonl")])
    assert e.value.code not in (0, None)


def test_score_run_needs_one_mode(tmp_path):
    write_jsonl(tmp_path / "g.jsonl", adverts(2))
    with pytest.raises(SystemExit):
        score_run.main(["--gold", str(tmp_path / "g.jsonl")])


def test_duplicate_skills_in_an_output_are_valid_and_scored_as_a_set():
    label = adverts(1)[0]["label"]
    label["skills"] = ["python", "sql"]
    out = json.dumps({**label, "skills": ["python", "sql", "python"]})
    assert parse_output(out) is not None
    r = score_record(label, out)
    assert r["valid"] and r["skills_tp"] == 2 and r["skills_fp"] == 0 and r["skills_exact"]
