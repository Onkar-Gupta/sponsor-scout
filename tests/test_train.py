import json

import pytest
import yaml

from sponsor_scout import train
from sponsor_scout.prompts import target_text, zero_shot_messages

with open(train.ROOT / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)


@pytest.mark.parametrize("rank,lr,epochs", [(8, 0.0001, 1), (16, 0.0002, 3), (16, 0.0001, 2)])
def test_grid_values_are_accepted(rank, lr, epochs):
    train.validate_settings(rank, lr, epochs, CFG)


@pytest.mark.parametrize("rank,lr,epochs", [(32, 0.0002, 1), (16, 0.0005, 1), (16, 0.0002, 5), (4, 0.0001, 2)])
def test_values_outside_the_pre_registered_grid_are_refused(rank, lr, epochs):
    with pytest.raises(ValueError, match="pre-registered grid"):
        train.validate_settings(rank, lr, epochs, CFG)


def test_budget_refuses_a_reused_name_and_a_sixth_run(tmp_path):
    train.check_budget("a", tmp_path, CFG)
    for i in range(CFG["training"]["max_dev_runs"] - 1):
        (tmp_path / f"dev_train_run{i}.json").write_text("{}", encoding="utf-8")
    train.check_budget("a", tmp_path, CFG)  # four runs exist, a fifth is still allowed
    with pytest.raises(ValueError, match="already exists"):
        train.check_budget("run0", tmp_path, CFG)
    (tmp_path / "dev_train_last.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="budget"):
        train.check_budget("new", tmp_path, CFG)


def test_training_rows_use_the_zero_shot_prompt_and_the_label_as_the_answer(tmp_path):
    rec = {"id": "x", "text": "Job: Analyst in Leeds.", "label": {"title": "Analyst"}}
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    (row,) = train.training_rows(path)
    assert row["prompt"] == zero_shot_messages(rec["text"])
    assert row["completion"] == [{"role": "assistant", "content": target_text(rec["label"])}]


def test_training_reads_only_the_train_split():
    source = (train.ROOT / "sponsor_scout" / "train.py").read_text(encoding="utf-8")
    assert "dev.jsonl" not in source and "test.jsonl" not in source
