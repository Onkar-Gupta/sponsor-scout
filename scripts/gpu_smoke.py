"""GPU smoke test (plan step 7). Loads the base model in 4-bit, adds a LoRA adapter and runs a few training steps.

    python scripts/gpu_smoke.py [--steps 20] [--max-length 1024] [--rank 16]

A development check, not part of the pre-registered test. Writes reports/gpu_smoke.json with peak memory, speed and loss.
Set HF_HOME to keep the model download outside the repo.
"""
import argparse
import json
import time
from pathlib import Path

import torch
import yaml
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

from sponsor_scout.prompts import target_text, zero_shot_messages

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--accum", type=int, default=16)
    args = ap.parse_args()
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    name = cfg["base_model"]

    rows = [json.loads(x) for x in (ROOT / "data" / "train.jsonl").read_text(encoding="utf-8").splitlines()[:200]]
    data = Dataset.from_list([{"prompt": zero_shot_messages(r["text"]),
                               "completion": [{"role": "assistant", "content": target_text(r["label"])}]} for r in rows])

    tok = AutoTokenizer.from_pretrained(name)
    chat = [zero_shot_messages(r["text"]) + [{"role": "assistant", "content": target_text(r["label"])}] for r in rows]
    lengths = [len(tok(tok.apply_chat_template(c, tokenize=False))["input_ids"]) for c in chat]
    print(f"token lengths over {len(rows)} train adverts: max {max(lengths)}, mean {sum(lengths) / len(lengths):.0f}", flush=True)

    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                               bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(name, quantization_config=quant, device_map={"": 0},
                                                 torch_dtype=torch.bfloat16)
    print(f"model loaded, GPU memory {torch.cuda.memory_allocated() / 2**30:.2f} GiB", flush=True)
    lora = LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                      target_modules=["qkv_proj", "o_proj", "gate_up_proj", "down_proj"])
    train_cfg = SFTConfig(output_dir=str(ROOT / "outputs" / "smoke"), max_steps=args.steps, per_device_train_batch_size=1,
                          gradient_accumulation_steps=args.accum, max_length=args.max_length, gradient_checkpointing=True,
                          bf16=True, learning_rate=2e-4, logging_steps=1, save_strategy="no", report_to="none", seed=cfg["seed"])
    trainer = SFTTrainer(model=model, args=train_cfg, train_dataset=data, processing_class=tok, peft_config=lora)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    trainer.train()
    secs = time.perf_counter() - start
    losses = [h["loss"] for h in trainer.state.log_history if "loss" in h]
    report = {"model": name, "steps": args.steps, "accumulation": args.accum, "max_length": args.max_length, "rank": args.rank,
              "seconds": round(secs, 1), "seconds_per_step": round(secs / args.steps, 2),
              "peak_gpu_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
              "gpu_total_gib": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2),
              "max_tokens_seen": max(lengths), "loss_first": losses[0] if losses else None, "loss_last": losses[-1] if losses else None,
              "torch": torch.__version__}
    out = ROOT / "reports" / "gpu_smoke.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
