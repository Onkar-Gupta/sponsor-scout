"""Scorer for model outputs. Metric definitions follow eval/protocol.md section 4; pass marks follow section 5.

An output is raw model text. It is valid only if it parses (see parse_output) and passes schema.validate.
"""
import json
import math
import random
import re
from collections import Counter

from .schema import validate

SCALARS = ["title", "employer", "location", "salary_min", "salary_max", "work_pattern", "years_experience_min",
           "closing_date", "sponsorship"]
CLASSES = ["offers", "excludes", "not_stated", "unclear"]
INVALID = "invalid"
FENCE = re.compile(r"^```(?:json)?[ \t]*\n?(.*?)\n?[ \t]*```$", re.DOTALL)


# ------------------------------------------------------------------------------------------ parsing
def parse_output(text):
    """Return the record, or None when the output is invalid.

    Rule: strip surrounding whitespace and ONE optional markdown code fence; the rest must be a single JSON object
    that passes schema.validate. Prose, a second object or trailing text make it invalid.
    """
    if not isinstance(text, str):
        return None
    body = text.strip()
    m = FENCE.match(body)
    if m:
        body = m.group(1).strip()
    try:
        record = json.loads(body)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    # schema.json has no uniqueItems rule, so a repeated skill alone does not make an output invalid
    errors = [e for e in validate(record) if not e.endswith("duplicate items")]
    return record if not errors else None


def norm(value):
    """Casefold, trim and collapse spaces for strings. Numbers and None are unchanged."""
    return " ".join(value.split()).casefold() if isinstance(value, str) else value


def _skills(items):
    return {norm(s) for s in items}


# ------------------------------------------------------------------------------------------ one advert
def score_record(gold_label, output_text):
    """Score one output against one gold label."""
    pred = parse_output(output_text)
    valid = pred is not None
    fields = {f: valid and norm(pred[f]) == norm(gold_label[f]) for f in SCALARS}
    gold_sk = _skills(gold_label["skills"])
    pred_sk = _skills(pred["skills"]) if valid else set()
    tp = len(gold_sk & pred_sk)
    return {
        "valid": valid,
        "fields": fields,
        "skills_tp": tp,
        "skills_fp": len(pred_sk) - tp,
        "skills_fn": len(gold_sk) - tp,
        "skills_exact": valid and gold_sk == pred_sk,
        "true_sponsorship": gold_label["sponsorship"],
        "pred_sponsorship": pred["sponsorship"] if valid else INVALID,
        # sponsorship is never null, so only the other eight scalars can be invented
        "invented": {f: pred[f] is not None for f in SCALARS if gold_label[f] is None} if valid else {},
        "null_fields": sum(1 for f in SCALARS if gold_label[f] is None),
        "exact": valid and all(fields.values()) and gold_sk == pred_sk,
    }


# ------------------------------------------------------------------------------------------ metrics
def _f1(tp, fp, fn):
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def _macro_f1(pairs):
    """pairs: iterable of (true, pred). An invalid pred is a miss for its true class and a false positive for none."""
    c = Counter(pairs)
    scores = []
    for k in CLASSES:
        tp = c[(k, k)]
        fp = sum(v for (t, p), v in c.items() if p == k and t != k)
        fn = sum(v for (t, p), v in c.items() if t == k and p != k)
        scores.append(_f1(tp, fp, fn))
    return sum(scores) / len(CLASSES)


def _ratio(num, den):
    return num / den if den else 0.0


def aggregate(per):
    """Aggregate metrics over a list of score_record results."""
    n = len(per)
    valid = [p for p in per if p["valid"]]
    tp, fp, fn = (sum(p[k] for p in per) for k in ("skills_tp", "skills_fp", "skills_fn"))
    pairs = [(p["true_sponsorship"], p["pred_sponsorship"]) for p in per]
    matrix = {t: {c: 0 for c in CLASSES + [INVALID]} for t in CLASSES}
    for t, q in pairs:
        matrix[t][q] += 1
    nulls = sum(p["null_fields"] for p in valid)
    invented = sum(sum(p["invented"].values()) for p in valid)
    per_field = {f: _ratio(sum(p["fields"][f] for p in per), n) for f in SCALARS}
    return {
        "n": n,
        "json_validity": _ratio(len(valid), n),
        "per_field_accuracy": per_field,
        "mean_field_accuracy": _ratio(sum(sum(p["fields"].values()) for p in per), len(SCALARS) * n),
        "skills_f1": _f1(tp, fp, fn),
        "sponsorship_accuracy": _ratio(sum(t == q for t, q in pairs), n),
        "sponsorship_macro_f1": _macro_f1(pairs),
        "sponsorship_confusion": matrix,
        "invented_value_rate": _ratio(invented, nulls),
        "invented_counted_on_valid_only": {"valid_outputs": len(valid), "invalid_outputs": n - len(valid),
                                           "null_fields": nulls, "invented": invented},
        "exact_match": _ratio(sum(p["exact"] for p in per), n),
    }


def wilson(k, n, z=1.96):
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p, z2 = k / n, z * z
    denom = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / denom
    return (0.0 if k == 0 else max(0.0, centre - half), 1.0 if k == n else min(1.0, centre + half))


# ------------------------------------------------------------------------------------------ bootstrap
METRICS = ("mean_field_accuracy", "sponsorship_macro_f1", "invented_value_rate", "json_validity")


def _ratio_vectors(per, metric):
    if metric == "mean_field_accuracy":
        return [sum(p["fields"].values()) for p in per], [len(SCALARS)] * len(per)
    if metric == "json_validity":
        return [int(p["valid"]) for p in per], [1] * len(per)
    # invented_value_rate: valid outputs only
    return ([sum(p["invented"].values()) for p in per],
            [p["null_fields"] if p["valid"] else 0 for p in per])


def _pct(sorted_vals, q):
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def _bootstrap(per_a, per_b, metric, resamples=10000, seed=0):
    """Paired bootstrap of metric(b) - metric(a) over adverts. Returns (difference, low, high)."""
    if metric not in METRICS:
        raise ValueError(f"unknown metric {metric}")
    n = len(per_a)
    rng = random.Random(seed)
    if metric == "sponsorship_macro_f1":
        ta = [(p["true_sponsorship"], p["pred_sponsorship"]) for p in per_a]
        tb = [(p["true_sponsorship"], p["pred_sponsorship"]) for p in per_b]

        def stat(idx):
            return _macro_f1([tb[i] for i in idx]) - _macro_f1([ta[i] for i in idx])
        point = _macro_f1(tb) - _macro_f1(ta)
    else:
        (na, da), (nb, db) = _ratio_vectors(per_a, metric), _ratio_vectors(per_b, metric)

        def stat(idx):
            return (_ratio(sum(map(nb.__getitem__, idx)), sum(map(db.__getitem__, idx)))
                    - _ratio(sum(map(na.__getitem__, idx)), sum(map(da.__getitem__, idx))))
        point = _ratio(sum(nb), sum(db)) - _ratio(sum(na), sum(da))
    diffs = sorted(stat(rng.choices(range(n), k=n)) for _ in range(resamples))
    return point, _pct(diffs, 0.025), _pct(diffs, 0.975)


def _align(gold, outs):
    """Outputs as a list in gold order. outs may be a dict id -> text or a list already in order."""
    if isinstance(outs, dict):
        if set(outs) != {g["id"] for g in gold}:
            raise ValueError("output ids do not match gold ids")
        return [outs[g["id"]] for g in gold]
    if len(outs) != len(gold):
        raise ValueError("output count does not match gold count")
    return list(outs)


def score_all(gold, outs):
    return [score_record(g["label"], o) for g, o in zip(gold, _align(gold, outs))]


def paired_bootstrap(gold, outs_a, outs_b, metric, resamples=10000, seed=0):
    """Resample adverts with replacement (same indices for both arms) and return metric(b) - metric(a) as
    {"difference", "low", "high"}: the point difference and the 2.5 and 97.5 percentile interval."""
    d, lo, hi = _bootstrap(score_all(gold, outs_a), score_all(gold, outs_b), metric, resamples, seed)
    return {"difference": d, "low": lo, "high": hi}


# ------------------------------------------------------------------------------------------ pass marks
def _diff(per_a, per_b, metric, resamples, seed):
    d, lo, hi = _bootstrap(per_a, per_b, metric, resamples, seed)
    return {"difference": d, "low": lo, "high": hi}


def compare(gold_records, outputs_tuned, outputs_fewshot, held_out_ids=None, resamples=10000, seed=0):
    """Pass marks 1 to 5 of eval/protocol.md section 5. Mark 6 (MMLU) is a later step. Failures are reported."""
    tuned, few = score_all(gold_records, outputs_tuned), score_all(gold_records, outputs_fewshot)
    if held_out_ids is None:
        held_out_ids = {g["id"] for g in gold_records if g.get("slice") == "held_out"}
    keep = [i for i, g in enumerate(gold_records) if g["id"] in set(held_out_ids)]
    if not keep:
        raise ValueError("no held-out adverts to score")
    ho_t, ho_f = [tuned[i] for i in keep], [few[i] for i in keep]

    # difference is tuned minus few-shot, so few-shot is arm "a"
    m1 = _diff(few, tuned, "mean_field_accuracy", resamples, seed)
    m1["met"] = m1["difference"] >= 0.05 and m1["low"] > 0
    m2 = _diff(ho_f, ho_t, "mean_field_accuracy", resamples, seed)
    m2["met"] = m2["difference"] >= 0.05 and m2["low"] > 0
    m3 = _diff(few, tuned, "sponsorship_macro_f1", resamples, seed)
    m3["tuned"] = aggregate(tuned)["sponsorship_macro_f1"]
    m3["fewshot"] = aggregate(few)["sponsorship_macro_f1"]
    m3["met"] = m3["tuned"] >= m3["fewshot"] and m3["low"] > 0
    at, af = aggregate(tuned), aggregate(few)
    k = round(at["json_validity"] * at["n"])
    m4 = {"validity": at["json_validity"], "wilson_95": wilson(k, at["n"]), "met": at["json_validity"] >= 0.99}
    m5 = _diff(few, tuned, "invented_value_rate", resamples, seed)
    m5.update(tuned=at["invented_value_rate"], fewshot=af["invented_value_rate"],
              met=at["invented_value_rate"] <= af["invented_value_rate"])
    m1.update(tuned=at["mean_field_accuracy"], fewshot=af["mean_field_accuracy"])
    m2.update(tuned=aggregate(ho_t)["mean_field_accuracy"], fewshot=aggregate(ho_f)["mean_field_accuracy"],
              n=len(keep))
    return {
        "mark_1_full_test_mean_field_accuracy": m1,
        "mark_2_held_out_mean_field_accuracy": m2,
        "mark_3_sponsorship_macro_f1": m3,
        "mark_4_tuned_json_validity": m4,
        "mark_5_invented_value_rate": m5,
        "marks_met_of_5": sum(m["met"] for m in (m1, m2, m3, m4, m5)),
    }
