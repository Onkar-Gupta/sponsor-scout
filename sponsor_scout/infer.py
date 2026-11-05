"""Inference for the evaluation arms (protocol section 2). Every arm gets the same advert text, the same greedy
decoding and the same max_new_tokens from config.yaml. No arm sees the gold label or the slice field."""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .prompts import few_shot_messages, fewshot_style, pick_fewshot, zero_shot_messages

ARMS = ("zero_shot", "few_shot", "tuned", "constrained")
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"
DROP_KEYS = {"$schema", "title", "format"}


def load_hf(base_model, adapter=None):
    """The base model in 4-bit NF4 (as in scripts/gpu_smoke.py), optionally wrapped with a LoRA adapter."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                               bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(base_model, quantization_config=quant, device_map={"": 0},
                                                 torch_dtype=torch.bfloat16)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return model, tok


def generate_hf(model, tok, messages, max_new_tokens):
    """Greedy, batch size 1. Returns (new text without special tokens, latency in ms)."""
    import torch

    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    torch.cuda.synchronize()
    start = time.perf_counter()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    torch.cuda.synchronize()
    ms = (time.perf_counter() - start) * 1000
    new = out[0][inputs["input_ids"].shape[1]:]
    return tok.decode(new, skip_special_tokens=True).strip(), ms


def ollama_schema(path=SCHEMA_PATH):
    """schema.json without the keywords Ollama's grammar builder does not need ($schema, title, format)."""
    def clean(node):
        if isinstance(node, dict):
            # property names (the values under "properties") are kept even when they match a dropped keyword
            return {k: ({n: clean(v) for n, v in val.items()} if k == "properties" else clean(val))
                    for k, val in node.items() if k not in DROP_KEYS}
        if isinstance(node, list):
            return [clean(v) for v in node]
        return node
    return clean(json.loads(Path(path).read_text(encoding="utf-8")))


def ollama_body(messages, schema, cfg):
    inf = cfg["inference"]
    return {"model": inf["ollama_model"], "messages": messages, "stream": False, "format": schema,
            "options": {"temperature": 0, "seed": 0, "num_predict": inf["max_new_tokens"]}}


def generate_ollama(messages, schema, cfg):
    """One constrained call. Returns (message content, latency in ms)."""
    body = json.dumps(ollama_body(messages, schema, cfg)).encode("utf-8")
    url = cfg["inference"]["ollama_url"].rstrip("/") + "/api/chat"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"cannot reach Ollama at {url} ({e}). Start it with `ollama serve`.") from e
    return data["message"]["content"], (time.perf_counter() - start) * 1000


def unload_ollama(cfg):
    """Ask Ollama to free the GPU. Without this it keeps the model for minutes and slows the next local arm."""
    body = json.dumps({"model": cfg["inference"]["ollama_model"], "keep_alive": 0}).encode("utf-8")
    url = cfg["inference"]["ollama_url"].rstrip("/") + "/api/generate"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except (urllib.error.URLError, OSError):
        pass  # best effort: the run itself has already finished


def build_generator(arm, cfg, adapter=None):
    """Returns generate(messages) -> (text, ms) for the arm."""
    if arm == "constrained":
        schema = ollama_schema()
        return lambda messages: generate_ollama(messages, schema, cfg)
    model, tok = load_hf(cfg["base_model"], adapter if arm == "tuned" else None)
    return lambda messages: generate_hf(model, tok, messages, cfg["inference"]["max_new_tokens"])


def messages_for(arm, text, examples, style="repeat"):
    return few_shot_messages(text, examples, style) if arm == "few_shot" else zero_shot_messages(text)


def _done_ids(path):
    if not Path(path).exists():
        return set()
    with open(path, encoding="utf-8") as f:
        return {json.loads(line)["id"] for line in f if line.strip()}


def run_arm(arm, records, out_path, cfg, adapter=None, fewshot_version=1, resume=False, log=print, generate=None):
    """Write one JSON line per advert: {"id", "output", "latency_ms", "arm"}. Only the advert text reaches the model.

    `generate` is for tests: a callable(messages) -> (text, ms). Returns the number of adverts run.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; choose from {ARMS}")
    if arm == "tuned" and not adapter:
        raise ValueError("the tuned arm needs an adapter")
    examples, style = [], "repeat"
    if arm == "few_shot":
        style = fewshot_style(fewshot_version)
        with open(Path(cfg.get("data_dir", "data")) / "train.jsonl", encoding="utf-8") as f:
            examples = pick_fewshot([json.loads(x) for x in f if x.strip()], fewshot_version)
    done = _done_ids(out_path) if resume else set()
    todo = [r for r in records if r["id"] not in done]
    gen = generate or build_generator(arm, cfg, adapter)
    start = time.perf_counter()
    with open(out_path, "a" if resume else "w", encoding="utf-8", newline="\n") as f:
        for i, rec in enumerate(todo, 1):
            text, ms = gen(messages_for(arm, rec["text"], examples, style))
            row = {"id": rec["id"], "output": text, "latency_ms": round(ms, 1), "arm": arm}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            el = time.perf_counter() - start
            sys.stderr.write(f"\r{arm}: {i}/{len(todo)}  elapsed {el:.0f}s  remaining ~{el / i * (len(todo) - i):.0f}s ")
            sys.stderr.flush()
    sys.stderr.write("\n")
    if arm == "constrained" and generate is None:
        unload_ollama(cfg)
    log(f"{arm}: wrote {len(todo)} outputs to {out_path} ({len(done)} already there)")
    return len(todo)
