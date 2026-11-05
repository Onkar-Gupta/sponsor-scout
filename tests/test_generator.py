import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

from sponsor_scout import banks
from sponsor_scout.generator import generate, load_config, render
from sponsor_scout.schema import date_forms, text_problems, to_annual, validate

ROOT = Path(__file__).resolve().parent.parent
CFG = load_config()
EM_DASH = chr(0x2014)


def _load_script(relpath, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


check_data = _load_script("eval/check_data.py", "check_data")
make_adverts = _load_script("scripts/make_adverts.py", "make_adverts")


@pytest.fixture(scope="module")
def data():
    return {
        "train": generate("train", 400, CFG["seeds"]["train"], config=CFG),
        "dev": generate("dev", 100, CFG["seeds"]["dev"], config=CFG),
        "test": generate("test", 300, CFG["seeds"]["test"], config=CFG),
    }


def test_deterministic_for_a_seed():
    assert generate("dev", 60, 2, config=CFG) == generate("dev", 60, 2, config=CFG)
    assert generate("dev", 60, 2, config=CFG) != generate("dev", 60, 5, config=CFG)


def test_no_label_in_two_splits(data):
    keys = [{json.dumps(r["label"], sort_keys=True) for r in rows} for rows in data.values()]
    assert not (keys[0] & keys[1]) and not (keys[0] & keys[2]) and not (keys[1] & keys[2])


def test_held_out_items_stay_in_the_held_out_slice(data):
    for split, rows in data.items():
        for r in rows:
            hits = check_data.held_out_hits(r)
            if r["slice"] == "in_style":
                assert not hits, (split, r["id"], hits)
            else:
                assert split == "test" and not check_data.not_held_out(r), r["id"]
    assert Counter(r["slice"] for r in data["test"]) == {"in_style": 150, "held_out": 150}


def test_held_out_things_are_used_somewhere_in_the_held_out_slice(data):
    held = [r for r in data["test"] if r["slice"] == "held_out"]
    assert {r["style"] for r in held} == set(banks.HELD_OUT_STYLES)
    assert {r["job_family"] for r in held} == set(banks.HELD_OUT_FAMILIES)
    assert {r["label"]["location"] for r in held} >= set(banks.HELD_OUT_TOWNS[:5])


def test_checker_passes_on_1000_drafts(tmp_path):
    sizes = {"train": 600, "dev": 150, "test": 250}
    for split, n in sizes.items():
        rows = generate(split, n, CFG["seeds"][split], config=CFG)
        (tmp_path / f"{split}.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert sum(sizes.values()) == 1000
    assert check_data.main(["--dir", str(tmp_path)]) == 0


def test_class_mix_within_tolerance(data):
    for rows in data.values():
        counts = Counter(r["label"]["sponsorship"] for r in rows)
        for cls, share in CFG["class_mix"].items():
            assert abs(100 * counts[cls] / len(rows) - 100 * share) <= CFG["class_tolerance_points"]


def test_guide_worked_examples():
    assert to_annual("22.50", "hour") == 43875
    assert to_annual(350, "day") == 80500
    assert (to_annual(18, "hour"), to_annual(20, "hour")) == (35100, 39000)
    assert to_annual(45000, "year") == 45000


def test_no_em_dash_anywhere(data):
    for rows in data.values():
        assert all(EM_DASH not in r["text"] for r in rows)
    bank_text = json.dumps([banks.STYLES, banks.SPONSOR_PHRASES, banks.BENEFITS, banks.FILLER, banks.JOB_FAMILIES],
                           ensure_ascii=False)
    assert EM_DASH not in bank_text


def test_text_under_the_cap(data):
    assert all(len(r["text"]) <= CFG["max_text_chars"] for rows in data.values() for r in rows)


def test_record_keys_and_labels(data):
    keys = {"id", "text", "label", "slice", "style", "template_id", "sponsorship_phrase_id", "job_family"}
    for rows in data.values():
        for r in rows:
            assert set(r) == keys and not validate(r["label"])


def test_validate_catches_bad_records():
    good = generate("dev", 1, 2, config=CFG)[0]["label"]
    assert validate(good) == []
    assert validate({k: v for k, v in good.items() if k != "title"})
    assert validate({**good, "sponsorship": "maybe"})
    assert validate({**good, "extra": 1})
    assert validate({**good, "closing_date": "2026-13-45"})
    assert validate({**good, "closing_date": "14 December 2026"})
    assert validate({**good, "salary_min": True})
    assert validate({**good, "years_experience_min": 2.5})
    assert validate({**good, "skills": ["sql", "sql"]})


def test_text_problems_catch_a_wrong_label(data):
    rec = json.loads(json.dumps(data["dev"][0]))
    rec["label"]["title"] = "Astronaut"
    assert text_problems(rec)


def test_templates_always_state_the_title_and_cover_every_field():
    empty = {n: "" for n in ("employer", "town", "pattern", "salary", "skills", "skills_bullets", "exp", "closing",
                             "start", "posted", "interview", "ref", "sponsor_1", "sponsor_2", "benefit_1",
                             "benefit_2", "about", "filler", "agency")}
    full = {**empty, "title": "TITLE", "org": "our client", "Org": "Our client"}
    required = {"title", "town", "pattern", "salary", "exp", "closing", "sponsor_1", "sponsor_2"}
    for style, templates in banks.STYLES.items():
        assert len(templates) >= 3
        for t in templates:
            assert "TITLE" in render(t, full), style
            used = " ".join(t)
            assert all("{" + name + "}" in used for name in required), (style, required)
            assert "{skills}" in used or "{skills_bullets}" in used
            assert "{employer}" in used or "{org}" in used or "{Org}" in used


def test_banks_shape():
    assert len(banks.STYLES) >= 12 and len(banks.HELD_OUT_STYLES) == 4
    assert len(banks.JOB_FAMILIES) == 16 and len(banks.HELD_OUT_FAMILIES) == 4
    assert len(set(banks.TOWNS)) == 40 and len(banks.HELD_OUT_TOWNS) == 10
    for cls in ("offers", "excludes", "unclear"):
        flags = [h for c, _, h in banks.SPONSOR_PHRASES.values() if c == cls]
        assert len(flags) >= 12 and sum(flags) == len(flags) // 3
    for fam in banks.JOB_FAMILIES.values():
        skills = fam["skills"]
        assert len(skills) == len(set(skills))
        assert not [s for s in skills for t in skills if s != t and s in t]
        assert not [s for s in skills for t in fam["titles"] if s in t.casefold()]


def test_dates_use_four_forms():
    assert date_forms("2026-12-14") == ["14 December 2026", "14 Dec 2026", "14/12/2026", "14th December 2026"]


def test_make_adverts_refuses_data_dir_without_official(tmp_path):
    frozen = ROOT / "data" / "dev.jsonl"
    before = frozen.read_bytes() if frozen.exists() else None
    with pytest.raises(SystemExit):
        make_adverts.main(["--split", "dev", "--n", "5", "--out", str(frozen)])
    assert (frozen.read_bytes() if frozen.exists() else None) == before  # the refusal left the file alone
    out = tmp_path / "d.jsonl"
    make_adverts.main(["--split", "dev", "--n", "5", "--out", str(out)])
    assert len(out.read_text(encoding="utf-8").splitlines()) == 5


def test_register_names_are_avoided(tmp_path):
    names = {r["label"]["employer"] for r in generate("dev", 40, 2, config=CFG) if r["label"]["employer"]}
    reg = tmp_path / "reg.csv"
    reg.write_text("Organisation Name,Town\n" + "\n".join(f"  {n.upper()}  ,X" for n in names), encoding="utf-8")
    again = {r["label"]["employer"] for r in generate("dev", 40, 2, register_path=reg, config=CFG)}
    assert not (names & again)
    assert generate("dev", 5, 2, register_path=tmp_path / "missing.csv", config=CFG) == generate(
        "dev", 5, 2, config=CFG)


def test_checker_fails_on_a_leak_and_a_bad_label(tmp_path):
    for split, n in {"train": 40, "dev": 20, "test": 20}.items():
        rows = generate(split, n, CFG["seeds"][split], config=CFG)
        if split == "train":
            rows[0]["label"]["salary_min"] = 1  # not recoverable from the text
            rows[1]["style"] = banks.HELD_OUT_STYLES[0]  # held-out style leaked into train
        (tmp_path / f"{split}.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    assert check_data.main(["--dir", str(tmp_path)]) == 1
