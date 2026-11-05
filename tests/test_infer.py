"""Step 8 tests: few-shot prompt, Ollama request, run_arm and the run_arm.py guards. No GPU and no Ollama needed."""
import importlib.util
import json
import urllib.request
from pathlib import Path

import pytest
import yaml

from sponsor_scout import infer
from sponsor_scout.prompts import INSTRUCTIONS, few_shot_messages, pick_fewshot, target_text

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def read(split):
    return [json.loads(x) for x in (ROOT / "data" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]


TRAIN, DEV = read("train"), read("dev")


def load_script():
    spec = importlib.util.spec_from_file_location("run_arm_script", ROOT / "scripts" / "run_arm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------------------ few-shot prompt
def test_few_shot_has_five_train_examples_covering_all_classes():
    ex = pick_fewshot(TRAIN, 1)
    assert len(ex) == 5
    assert {e["id"] for e in ex} <= {r["id"] for r in TRAIN}
    assert {e["label"]["sponsorship"] for e in ex} == {"offers", "excludes", "not_stated", "unclear"}
    assert any(e["label"]["salary_min"] is None for e in ex)


def test_few_shot_messages_use_the_same_instructions_and_answer_format():
    ex = pick_fewshot(TRAIN, 1)
    msgs = few_shot_messages("THE ADVERT", ex)
    assert [m["role"] for m in msgs] == ["user", "assistant"] * 5 + ["user"]
    assert all(m["content"].startswith(INSTRUCTIONS) for m in msgs if m["role"] == "user")
    assert [m["content"] for m in msgs if m["role"] == "assistant"] == [target_text(e["label"]) for e in ex]
    assert msgs[-1]["content"].endswith("Advert:\nTHE ADVERT")


def test_pick_fewshot_errors_on_a_missing_version():
    with pytest.raises(FileNotFoundError, match="version 99"):
        pick_fewshot(TRAIN, 99)


# ------------------------------------------------------------------------------------------ Ollama request
class FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return json.dumps({"message": {"role": "assistant", "content": "{}"}}).encode()


def test_ollama_request_carries_schema_and_temperature_zero(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["url"], seen["body"] = req.full_url, json.loads(req.data)
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    text, ms = infer.generate_ollama([{"role": "user", "content": "x"}], infer.ollama_schema(), CFG)
    body = seen["body"]
    assert text == "{}" and ms >= 0
    assert seen["url"].endswith("/api/chat") and body["stream"] is False
    assert body["options"] == {"temperature": 0, "seed": 0, "num_predict": CFG["inference"]["max_new_tokens"]}
    assert body["format"]["required"] and "sponsorship" in body["format"]["properties"]
    assert not {"$schema", "title"} & set(body["format"])
    assert "format" not in body["format"]["properties"]["closing_date"]
    assert "title" in body["format"]["properties"] and "title" in body["format"]["required"]


def test_ollama_down_gives_a_clear_error(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="Ollama"):
        infer.generate_ollama([], {}, CFG)


# ------------------------------------------------------------------------------------------ run_arm
def gold_answer(messages):
    """A fake model that finds the advert in the last user turn and answers with its gold label."""
    advert = messages[-1]["content"].split("Advert:\n", 1)[1]
    return json.dumps(next(r["label"] for r in DEV if r["text"] == advert)), 1.5


def cfg_here():
    return {**CFG, "data_dir": str(ROOT / "data")}


def test_run_arm_writes_resumes_and_hides_the_gold(tmp_path):
    out, recs, calls = tmp_path / "o.jsonl", DEV[:5], []

    def gen(messages):
        calls.append(json.dumps(messages))
        return gold_answer(messages)

    infer.run_arm("zero_shot", recs[:3], out, cfg_here(), generate=gen, log=lambda m: None)
    infer.run_arm("zero_shot", recs, out, cfg_here(), resume=True, generate=gen, log=lambda m: None)
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in rows] == [r["id"] for r in recs]
    assert set(rows[0]) == {"id", "output", "latency_ms", "arm"} and rows[0]["arm"] == "zero_shot"
    assert len(calls) == 5
    for rec, call in zip(recs, calls):
        assert json.dumps(rec["label"]) not in call and rec["slice"] not in call.replace(rec["text"], "")
        assert '"label"' not in call and '"slice"' not in call


def test_run_arm_few_shot_sends_five_examples(tmp_path):
    seen = []
    infer.run_arm("few_shot", DEV[:1], tmp_path / "o.jsonl", cfg_here(), log=lambda m: None,
                  generate=lambda m: (seen.append(m), ("{}", 1.0))[1])
    assert len(seen[0]) == 11


def test_run_arm_output_feeds_score_run(tmp_path, capsys):
    out, recs = tmp_path / "o.jsonl", DEV[:5]
    infer.run_arm("zero_shot", recs, out, cfg_here(), generate=gold_answer, log=lambda m: None)
    gold = tmp_path / "gold.jsonl"
    gold.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("score_run_script", ROOT / "scripts" / "score_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(["--gold", str(gold), "--pred", str(out)])
    report = json.loads(capsys.readouterr().out)
    assert report["all"]["n"] == 5 and report["all"]["json_validity"] == 1.0
    assert report["all"]["mean_field_accuracy"] == 1.0


# ------------------------------------------------------------------------------------------ scripts/run_arm.py
def test_run_arm_script_refuses_test_without_official(tmp_path):
    with pytest.raises(SystemExit, match="refused"):
        load_script().main(["--arm", "zero_shot", "--split", "test", "--out", str(tmp_path / "t.jsonl")])


def test_run_arm_script_refuses_a_dirty_tree(tmp_path, monkeypatch):
    mod = load_script()
    monkeypatch.setattr(mod, "tree_is_dirty", lambda: True)
    with pytest.raises(SystemExit, match="not clean"):
        mod.main(["--arm", "zero_shot", "--split", "test", "--out", str(tmp_path / "t.jsonl"), "--official"])


def test_run_arm_script_refuses_to_overwrite(tmp_path, monkeypatch):
    mod = load_script()
    monkeypatch.setattr(mod, "tree_is_dirty", lambda: False)
    existing = tmp_path / "t.jsonl"
    existing.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit, match="already exists"):
        mod.main(["--arm", "zero_shot", "--split", "test", "--out", str(existing), "--official"])
    assert existing.read_text(encoding="utf-8") == "x"


def test_unload_ollama_sends_keep_alive_zero(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout=None):
        sent["url"], sent["body"] = req.full_url, json.loads(req.data)

    monkeypatch.setattr(infer.urllib.request, "urlopen", fake_urlopen)
    infer.unload_ollama({"inference": {"ollama_url": "http://x:1/", "ollama_model": "m"}})
    assert sent == {"url": "http://x:1/api/generate", "body": {"model": "m", "keep_alive": 0}}
