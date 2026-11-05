"""Prompt text shared by training and inference, so the tuned model is trained on exactly what it is asked at test time.

The instructions are a compact version of eval/labelling_guide.md. Step 8 adds the few-shot prompt on top of this.
"""
import json
from pathlib import Path

INSTRUCTIONS = """You turn one UK job advert into one JSON record. Reply with the JSON object only.

Fields: title, employer, location, salary_min, salary_max, work_pattern, skills, years_experience_min, closing_date, sponsorship.
Use null when the advert does not state a value. Label only what the advert says.
- title: the job title only. employer: the hiring organisation (null if hidden). location: a UK town, or "remote" if fully remote.
- salary_min, salary_max: pounds per year as numbers. "up to 45k" gives min null, max 45000. A single figure gives both. "competitive" gives both null. Hourly = rate x 37.5 x 52. Daily = rate x 230.
- work_pattern: "on-site", "hybrid", "remote" or null.
- skills: tools and skills asked of the candidate, lower case. No benefits, no soft-skill filler.
- years_experience_min: the lowest years required, as an integer, or null.
- closing_date: the application deadline only, as yyyy-mm-dd, or null.
- sponsorship: "offers", "excludes", "not_stated" or "unclear". Explicit refusal, or only a right-to-work requirement, is "excludes". Explicit offer is "offers". Hedged or contradictory wording is "unclear". No mention is "not_stated"."""


def zero_shot_messages(advert_text):
    return [{"role": "user", "content": f"{INSTRUCTIONS}\n\nAdvert:\n{advert_text}"}]


def target_text(label):
    """The exact answer the model is trained to produce."""
    return json.dumps(label, ensure_ascii=False)


# ------------------------------------------------------------------------------------------ few-shot (step 8)
FEWSHOT_DIR = Path(__file__).resolve().parent.parent / "prompts"


REMINDER = (
    "

Reminder: include all ten keys every time. Use null (never words like competitive or negotiable) for a missing "
    "salary, closing date, years or employer, [] when there are no skills, and one of the four sponsorship words."
)


def few_shot_messages(advert_text, examples, style="repeat"):
    """Each example is a prior user turn and an assistant turn (same answer format).

    style "repeat" (v1): every user turn carries the full instructions.
    style "reminder" (v3): as "repeat", plus REMINDER at the end of every user turn.
    style "once" (v2): the instructions appear in the first turn only; later turns hold just the advert.
    """
    messages = []
    if style == "once":
        for i, ex in enumerate(examples):
            user = zero_shot_messages(ex["text"])[0]["content"] if i == 0 else f"Advert:\n{ex['text']}"
            messages += [{"role": "user", "content": user}, {"role": "assistant", "content": target_text(ex["label"])}]
        return messages + [{"role": "user", "content": f"Advert:\n{advert_text}"}]
    tail = REMINDER if style == "reminder" else ""
    for ex in examples:
        user = zero_shot_messages(ex["text"])[0]["content"] + tail
        messages += [{"role": "user", "content": user}, {"role": "assistant", "content": target_text(ex["label"])}]
    return messages + [{"role": "user", "content": zero_shot_messages(advert_text)[0]["content"] + tail}]


def fewshot_style(version):
    """"repeat" unless prompts/fewshot_v{version}.json says otherwise."""
    path = FEWSHOT_DIR / f"fewshot_v{version}.json"
    return json.loads(path.read_text(encoding="utf-8")).get("style", "repeat") if path.exists() else "repeat"


def pick_fewshot(train_records, version):
    """The train records named in prompts/fewshot_v{version}.json, in file order."""
    path = FEWSHOT_DIR / f"fewshot_v{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"no few-shot prompt version {version}: {path} does not exist")
    ids = json.loads(path.read_text(encoding="utf-8"))["example_ids"]
    by_id = {r["id"]: r for r in train_records}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise ValueError(f"few-shot v{version} names ids that are not in the train split: {missing}")
    return [by_id[i] for i in ids]
