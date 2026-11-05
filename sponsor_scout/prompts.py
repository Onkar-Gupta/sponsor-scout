"""Prompt text shared by training and inference, so the tuned model is trained on exactly what it is asked at test time.

The instructions are a compact version of eval/labelling_guide.md. Step 8 adds the few-shot prompt on top of this.
"""
import json

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
