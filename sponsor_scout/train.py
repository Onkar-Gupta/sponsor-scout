"""QLoRA training on the train split only (plan step 9). Heavy imports stay inside `train` so the rest is testable.

Every real run is kept as reports/dev_train_<name>.json, and the number of runs is capped by the F2 budget in
config.yaml. A smoke run (few steps) writes nothing to reports/ and does not use up the budget.
"""
import json
import subprocess
import time
from pathlib import Path

from .prompts import target_text, zero_shot_messages

ROOT = Path(__file__).resolve().parent.parent


def validate_settings(rank, learning_rate, epochs, cfg):
    """Only the values pre-registered in the protocol are allowed. A new value needs a dated Amendment first."""
    allowed = cfg["training"]["allowed"]
    for key, value in (("rank", rank), ("learning_rate", learning_rate), ("epochs", epochs)):
        if value not in allowed[key]:
            raise ValueError(f"{key}={value} is not in the pre-registered grid {allowed[key]}")


def existing_runs(reports_dir):
    return sorted(Path(reports_dir).glob("dev_train_*.json"))


def check_budget(name, reports_dir, cfg):
    """Refuse a reused name or a sixth run. Every dev run is kept, so nothing is overwritten."""
    runs = existing_runs(reports_dir)
    if any(p.name == f"dev_train_{name}.json" for p in runs):
        raise ValueError(f"a run called {name!r} already exists; every dev run is kept")
    if len(runs) >= cfg["training"]["max_dev_runs"]:
        raise ValueError(f"the dev budget of {cfg['training']['max_dev_runs']} training runs is used up; "
                         "more needs a dated Amendment in eval/protocol.md first")


def training_rows(path):
    """Prompt and completion for each train advert: the same zero-shot prompt the tuned arm is asked at test time."""
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return [{"prompt": zero_shot_messages(r["text"]),
             "completion": [{"role": "assistant", "content": target_text(r["label"])}]} for r in rows]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=False, capture_output=True, text=True).stdout.strip()


def train(name, rank, learning_rate, epochs, cfg, max_steps=None):
    """Train one adapter. With max_steps (a smoke run) nothing is written to reports/."""
    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import SFTConfig, SFTTrainer

    t = cfg["training"]
    validate_settings(rank, learning_rate, epochs, cfg)
    reports = ROOT / cfg["reports_dir"]
    if max_steps is None:
        check_budget(name, reports, cfg)
    out_dir = ROOT / t["adapter_dir"] / (f"smoke_{name}" if max_steps else name)
    data = Dataset.from_list(training_rows(ROOT / cfg["data_dir"] / "train.jsonl"))

    tok = AutoTokenizer.from_pretrained(cfg["base_model"])
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
                               bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(cfg["base_model"], quantization_config=quant, device_map={"": 0},
                                                 torch_dtype=torch.bfloat16)
    lora = LoraConfig(r=rank, lora_alpha=t["alpha_factor"] * rank, lora_dropout=t["dropout"], task_type="CAUSAL_LM",
                      target_modules=t["target_modules"])
    args = SFTConfig(output_dir=str(out_dir), num_train_epochs=epochs, max_steps=max_steps or -1,
                     per_device_train_batch_size=t["batch_size"], gradient_accumulation_steps=t["accumulation"],
                     max_length=t["max_length"], gradient_checkpointing=True, bf16=True, learning_rate=learning_rate,
                     lr_scheduler_type=t["scheduler"], warmup_steps=t["warmup"], logging_steps=5,
                     save_strategy="no", report_to="none", seed=cfg["seed"])
    trainer = SFTTrainer(model=model, args=args, train_dataset=data, processing_class=tok, peft_config=lora)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    trainer.train()
    seconds = time.perf_counter() - start
    trainer.save_model(str(out_dir))
    losses = [h["loss"] for h in trainer.state.log_history if "loss" in h]
    report = {"name": name, "smoke": bool(max_steps), "base_model": cfg["base_model"], "rank": rank,
              "learning_rate": learning_rate, "epochs": epochs, "alpha": t["alpha_factor"] * rank,
              "accumulation": t["accumulation"], "train_examples": len(data), "optimiser_steps": trainer.state.global_step,
              "seconds": round(seconds, 1), "peak_gpu_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
              "loss_first": losses[0] if losses else None, "loss_last": losses[-1] if losses else None,
              "losses": losses, "adapter": str(out_dir), "commit": git("rev-parse", "--short", "HEAD"),
              "working_tree_dirty": bool(git("status", "--porcelain")), "torch": torch.__version__}
    if not max_steps:
        reports.mkdir(exist_ok=True)
        (reports / f"dev_train_{name}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8",
                                                        newline="\n")
    return report
