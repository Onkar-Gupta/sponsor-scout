# Evaluation protocol (pre-registered)

Written 5 Nov 2026 by Onkar Gupta. This file is committed together with `schema.json` and `eval/labelling_guide.md`, BEFORE any data, code or model run exists in this repo.

Pass marks in this file never move after a result exists. If a rule turns out to be wrong, the change goes in the Amendments section with its date and reason, and both the old and the new result are reported.

---

## 1. Purpose and headline claim

The repo turns a UK job advert into one JSON record, including a visa sponsorship stance, using a small open model. This protocol measures whether fine-tuning the model is worth it compared with a carefully built prompt.

**Single headline claim, tested here:** on held-out synthetic UK adverts, a LoRA-tuned model (QLoRA, 4-bit base) gets a higher mean field accuracy than the same base model with a strong few-shot prompt, by at least 5.0 points with a paired 95 percent interval above zero, while losing no more than 2.0 points on a fixed MMLU sample.

Everything else is reported next to the headline, with intervals, whether its target is met or not. If tuning does not beat the prompt, that is the result.

## 2. Arms

All arms use the same base weights, greedy decoding, the same schema text, the same parser and the same maximum output length.

| Arm | What it does | Pass mark |
|---|---|---|
| 1. Base zero-shot | Schema and labelling instructions only | No |
| 2. Base few-shot | Same, plus 5 fixed examples from the train split (covering all four sponsorship classes and null fields). Up to 5 prompt versions are tried on dev. | Yes (the baseline for marks 1 to 5) |
| 3. Tuned | Base plus a LoRA adapter, zero-shot prompt | Yes |
| 4. Constrained decoding | Base through Ollama with the JSON schema in the `format` field, no tuning. Different engine and quantisation, so it is reported beside the table, not inside the claim. | No |

**Base model:** microsoft/Phi-4-mini-instruct (MIT). Fallback order: Qwen/Qwen3-4B, then HuggingFaceTB/SmolLM3-3B. A switch is made only by a dated Amendment written before any test result.

## 3. Data

| Item | What exists |
|---|---|
| Schema | `schema.json`, 9 scalar fields plus `skills`. |
| Labelling | `eval/labelling_guide.md`, frozen before generation. |
| Generation | Synthetic, from a generator in this repo with exact labels by construction. No text is copied from any job board. Fictional employers, real UK town names. |
| Train | 2,000 adverts |
| Dev | 300 adverts, in-style |
| Test | 600 adverts: 300 in-style and 300 held-out styles and phrasings |
| Held-out slice | Style families and sponsorship phrasings never used in train or dev. Job families and towns are also held out from train. |
| Class mix | About 30 percent offers, 25 excludes, 30 not_stated, 15 unclear, in every split. |
| Private set | 30 to 50 real adverts the author is already reading. Text kept in a gitignored folder, never committed. Labelled by the author with the guide before any model sees them. |
| Counts | See the F1 Amendment in section 8 and `reports/data_check.json`. |

Licences: generator code MIT, generated data CC0. MMLU is downloaded at run time and not committed.

## 4. Metrics

All definitions are fixed here.

- **JSON validity:** the output parses and matches `schema.json`, checked by an own validator.
- **Per-field accuracy:** share of adverts where the field matches the label. Text fields after casefold, trim and collapse spaces. Salary and years exact. Invalid JSON scores 0 on every field. A null label matches only a null output, so inventing a value for an empty field counts as wrong.
- **Mean field accuracy:** micro-average over the 9 scalar fields (all fields except `skills`).
- **Skills set F1:** after normalisation, reported apart.
- **Sponsorship accuracy and macro-F1:** over the four classes, with a confusion matrix.
- **Invented-value rate:** share of truly null labelled fields for which the model gives a non-null value.
- **Whole-record exact match:** every field correct, skills as an exact set.
- **MMLU accuracy:** fixed sample of 1,000 questions from the test split, seed 0, zero-shot, answer chosen by highest log-likelihood over A to D. Base and tuned, paired.
- **Latency:** median and 90th percentile per advert. **Peak GPU memory** during training.
- **Intervals:** Wilson 95 percent for proportions. Paired bootstrap over adverts for differences: 10,000 resamples, seed 0, 95 percent percentile interval.

## 5. Pass marks

Fixed now, before any data exists. Exactly six.

| # | Claim | Pass mark |
|---|---|---|
| 1 | Tuned beats few-shot | Mean field accuracy on the full test: tuned minus few-shot at least +5.0 points AND the paired 95 percent interval lower bound above 0 |
| 2 | Holds on unseen styles | Same difference on the held-out-style slice, interval lower bound above 0 |
| 3 | Sponsorship | Tuned sponsorship macro-F1 at least few-shot's, and the interval of the difference above 0 |
| 4 | Valid JSON | Tuned JSON validity at least 0.99 on the full test |
| 5 | No added guessing | Tuned invented-value rate at most few-shot's (point estimate), interval reported |
| 6 | Forgetting | Tuned MMLU accuracy no more than 2.0 points below base (point estimate), paired interval reported |

**Reported without a pass mark:** base zero-shot, the constrained-decoding arm, the per-field table, skills F1, whole-record exact match, latency, peak training memory and the private real-advert counts. Any failed mark is published as failed.

## 6. Freeze points and run-once rule

- **F0:** this protocol, the schema, the labelling guide, the generator, the scorer and the data checker are committed before any data exists.
- **F1:** data generated once. A freeze-guard test hashes every split, the prompts and the schema.
- **F2:** tuning on dev only, with equal budgets. Few-shot: up to 5 prompt versions. LoRA: up to 5 training runs, rank 8 or 16, learning rate 1e-4 or 2e-4, 1 to 3 epochs. Selection: highest dev mean field accuracy; tie-break smaller rank, then fewer epochs. Every dev run is kept.
- **F3:** an Amendment records the chosen prompt, the adapter settings and the commit.
- **Run once:** scoring all arms on test, the MMLU check and the private real-advert check. A rerun needs a dated reason, and every run is kept and reported.

## 7. Contamination checks

1. No record (all field values together) appears in two splits.
2. Templates and sponsorship phrasings of the held-out style families never appear in train or dev. The generator enforces this and a test checks it.
3. The share of test 8-grams found in train is reported, per slice.
4. The base model was released before this data was generated, so model-side leakage is not tested.

## 8. Amendments

- 5 Nov 2026: protocol written before any data, code or model run existed; no result existed.
- 5 Nov 2026, scorer definitions (written when the scorer was built, before any data was generated and before any model output existed; no result existed). These fix points the protocol left open:
  1. **Valid output.** After stripping surrounding whitespace and one optional markdown code fence, the text must be a single JSON object that passes `schema.json`. Prose before or after the object, or a second object, makes it invalid. A repeated skill alone does not make an output invalid (the schema has no uniqueness rule); skills are scored as a set.
  2. **Invalid outputs.** Score 0 on every scalar field. For skills F1 an invalid output counts as an empty set (its gold skills are false negatives, no false positives). For sponsorship it is a miss for its true class and a false positive for none.
  3. **Invented-value rate.** Counted over the eight scalar fields that can be null (sponsorship never is), over valid outputs only; the number of invalid outputs is reported beside it. It is 0.0 when there are no null fields.
  4. **Macro-F1.** F1 is 0 for a class with no true and no predicted cases.
  5. **Intervals.** Percentile intervals use linear interpolation between order statistics at 2.5 and 97.5. In each bootstrap resample, ratio metrics are recomputed from the resampled sums.
  6. **Marks.** Mark 1 and 2 "+5.0 points" means a difference of at least 0.05 on a 0 to 1 scale. Mark 3 "at least few-shot's" is a point difference of at least 0 and an interval lower bound above 0. Mark 5 compares the two point estimates only; the interval is reported. The held-out slice is the adverts whose `slice` field is `held_out`.
  7. **Comparison direction.** Differences are tuned minus few-shot. `scripts/score_run.py` takes `--fewshot` and `--tuned` so the arms cannot be swapped by position.
- 5 Nov 2026, F1 reached: the official data was generated once (commit d95ca03, `scripts/make_adverts.py --official`, seeds 1, 2 and 3 from `config.yaml`): train 2,000, dev 300, test 600 (300 in-style, 300 held-out). The checker (`reports/data_check.json`) found 0 failures: class mix exactly 30, 25, 30 and 15 percent in every split, and the share of test 8-grams found in train is 0.2917 for the in-style slice and 0.1165 for the held-out slice. SHA-256 hashes of the three splits and `schema.json` are in `data/SHA256SUMS.json` and guarded by `tests/test_freeze_guard.py`. No model output existed. The data is not regenerated without a dated Amendment giving the reason.
- 5 Nov 2026, inference batch size (written during step 10 dev tuning; it touches speed only and moves no pass mark):
  1. **What was run.** Few-shot v1, few-shot v2, the first few-shot v3 attempt (57 of 300 rows, stopped) and LoRA run 1 (`r16_lr2e-4_e2`) all ran at batch size 1, the `config.yaml` default. Their output rows have no `batch_size` field because it was added later. Rows from this point on record it.
  2. **Batch 8 check on the tuned model.** The first 30 dev adverts were run at batch size 8 (`outputs/check_batch8_tuned.jsonl`). All 30 outputs are identical text to the batch size 1 outputs of the same adapter. Mean latency per row fell from 9,332 ms to 1,355 ms. This covers one adapter and 30 adverts, not every setting.
  3. **Batch 8 on few-shot v3.** A batch size 8 run of v3 (`outputs/dev_fewshot_v3_b8.jsonl`) had a mean latency of 25,464 ms per row over its first 16 rows, against 9,762 ms at batch size 1 over 57 rows. The few-shot prompt is long, and eight padded copies appear to overload the 8 GiB card; the memory spill itself was not confirmed. A rerun of v3 is the same prompt version, not a new one, so it does not use up the budget of 5.
  4. **Rule.** Every few-shot run uses batch size 1. Tuned runs may use batch size 8 for speed, with the size stated in the report. Latency is not compared across batch sizes. When latency is reported per arm (section 9), both arms are timed at batch size 1.
  5. **Kept files.** `dev_fewshot_v3.jsonl` (57 rows) and `dev_fewshot_v3_b8.jsonl` (16 rows) are partial runs and are not scored. The scored v3 run is `dev_fewshot_v3_b1.jsonl` (300 rows, batch size 1), report `reports/dev_score_fewshot_v3.json`.
- 6 Nov 2026, dev tuning stopped early on purpose (written before any test output existed; no pass mark moves):
  1. **Budget used.** The protocol allows up to 5 few-shot prompt versions and up to 5 LoRA runs. Used: 3 prompt versions (v1, v2, v3, all scored on the 300 dev adverts at batch size 1) and 1 LoRA run (`r16_lr2e-4_e2`). The budget is a ceiling, not a target.
  2. **Dev results.** Mean field accuracy: few-shot v1 0.757, v2 0.641, v3 0.750; LoRA run 1 0.994. Few-shot v3 had the best JSON validity (0.887) but the lowest sponsorship accuracy (0.553).
  3. **Why stop.** LoRA run 1 is close to the ceiling on dev (JSON valid 1.000, sponsorship accuracy 1.000), so further runs are unlikely to change the choice. Dev is synthetic, so this says nothing about real adverts; that is covered by the private check and the limits in section 9.
  4. **Fairness.** The few-shot arm had 3 tries and the tuned arm 1, so the unspent budget does not favour the tuned arm.
  5. **Selection rule unchanged.** Highest dev mean field accuracy, tie-break smaller rank, then fewer epochs. Which settings are chosen is recorded in the freeze Amendment (step 11), not here.

- 9 Nov 2026, F3 freeze (written before any test output existed; no pass mark moves). The final settings are:
  1. **Few-shot arm:** prompt version 1, `prompts/fewshot_v1.json`, SHA-256 `a1690a6176bc43aee2ad542732f2b3afe342bd785ead268df5768024697f4ea8`. Dev mean field accuracy 0.757 (v2 0.641, v3 0.750). Runs at batch size 1.
  2. **Tuned arm:** LoRA run 1, `r16_lr2e-4_e2` (rank 16, alpha 32, learning rate 2e-4, 2 epochs, dropout 0.05, base `microsoft/Phi-4-mini-instruct`). Dev mean field accuracy 0.994. Adapter weights `adapter_model.safetensors` SHA-256 `fe2eb0e21d61a85ed54c29556ff03f774b203963b240d11bd2164a0b38fa182b`; `adapter_config.json` SHA-256 `d5e79416ee32bbff97b61d569bbd9602215ef0652fcb74bebf808240e34669da`. The weights stay outside git.
  3. **Selection:** by the F2 rule (highest dev mean field accuracy), applied to every dev run kept in `reports/`. No tie occurred.
  4. **Code state:** the tuning ran at commit `40767d2`. The freeze commit follows it and changes only this file.
  5. **From here:** no prompt edit, no new training run and no setting change before the test run. Any change needs a dated Amendment first and is reported. The test, MMLU and private checks run once (section 6); the official data hashes in `data/SHA256SUMS.json` are unchanged.

- 9 Nov 2026, private real-advert set (written before any model has seen these adverts; no pass mark moves):
  1. **Size.** 10 real UK adverts, not the 30 to 50 planned in section 3. The private check has no pass mark (section 5), so this breaks no mark. It is a smoke check, not evidence that results hold on real adverts in general. More adverts may be added only before the test run; after it, none.
  2. **Source.** All 10 were copied by the author from LinkedIn job pages (one employer is an agency that hides its client). Page furniture was removed (buttons, dates, applicant counts, "people you can reach out to"). The header lines (company, title, place, work-pattern badge) were kept because the model sees them. Where the header and the body disagree, the body decides the label. One Amsterdam advert was rejected as outside the UK scope. Text and labels stay in the gitignored `data/private/`.
  3. **Who labelled.** The labels were drafted from `eval/labelling_guide.md` and then checked by the author, advert by advert, before any model output existed. This is a weaker design than labelling by the author alone, and it is added to the limits in section 9.
  4. **Coverage gaps.** All 10 have `closing_date` null and none has an hourly or daily rate, so those rules are untested on real text. Sponsorship labels: `not_stated` 6, `offers` 1, `unclear` 1, `excludes` 1. All 10 are from LinkedIn, so the style range is narrow.
  5. **Judgement calls fixed now.** Nice-to-have skills are excluded; the title is the page heading; a relocation allowance is not sponsorship; a stated work permit is `offers`; hedged "visa assistance (conditions apply)" is `unclear`; a line "Authorized to work in United Kingdom" alone is `excludes`; several towns or countries give a null location.
  6. **Freeze.** SHA-256 of `data/private/adverts.jsonl` (text and labels): `b13e81776832252d54786015729a89c2ea9d27e615ce8b591be8edde6e432a24`. `scripts/check_private.py` passes (10 records, 0 problems). The labels are not edited after model output exists.

- 9 Nov 2026, official run procedure (written before any test, MMLU or private output exists; no pass mark moves):
  1. **Code state.** Every official output is produced from one clean commit, recorded in each report. The scripts refuse a dirty tree and refuse to overwrite an output. `scripts/run_arm.py` now accepts `--split private` (file `data/private/adverts.jsonl`) under the same `--official` guard as test. `scripts/mmlu_check.py` is new.
  2. **Test arms.** Zero-shot, few-shot (prompt v1, `--fewshot-version 1`, batch size 1), tuned (adapter `r16_lr2e-4_e2`, batch size 8 allowed, stated in the report) and constrained (Ollama, `phi4-mini:3.8b`), each once on the 600 test adverts. The same four arms run once on the 10 private adverts.
  3. **MMLU definition (section 4 left details open).** 1,000 questions drawn with `random.Random(0).sample` from the `cais/mmlu` "all" test split, sorted by index. Plain zero-shot prompt (`scripts/mmlu_check.py`, function `prompt`), no chat template. The answer is the letter A to D with the highest next-token logit. Base answers come from the same loaded model with the adapter switched off, so base and tuned see identical questions and identical quantisation. Mark 6: tuned minus base at least -0.02; the paired bootstrap interval (10,000 resamples, seed 0) is reported.
  4. **Dry run, disclosed.** Before this Amendment, `mmlu_check.py` was run once with `--limit 20` to a scratch file to confirm it works (base 0.65, tuned 0.60 on those 20; 5 seconds). That output is not an official result, was not kept in the repo, and the official run covers all 1,000 questions including those 20. It moves no pass mark.
  5. **Order.** Test arms, then private arms, then MMLU. All outputs are kept. A rerun needs a dated reason (section 6).

- 9 Nov 2026, test subset of 50 (written before any test output exists; supersedes item 2 of the official run procedure above where it says 600 test adverts; no pass mark moves):
  1. **Decision.** At the author's request the scored test run uses 50 of the 600 test adverts, to save GPU time. The pass marks, their wording and the metrics are unchanged.
  2. **Subset.** 25 in-style and 25 held-out adverts, drawn with `random.Random(0)` by `scripts/make_subset.py`, stored as a list of ids in `data/test_subset50.json` (SHA-256 `0ec125650615b4a038a309913293b41dc3e6aa3ac2ddf2fcd5cd6efaaa043d00`). The draw ignores labels. It happens to hold sponsorship `not_stated` 15, `unclear` 14, `excludes` 11, `offers` 10. `run_arm.py` and `score_run.py` take `--ids-file`. The other 550 test adverts are not run and not looked at.
  3. **What it costs.** Intervals are much wider than at 600, and sponsorship macro-F1 over 50 adverts is noisy. A mark can fail for lack of data and not because the tuning failed; if so it is published as failed with the interval, not explained away. Mark 2 rests on 25 adverts.
  4. **No top-up.** The 50-advert result is final. Running the other 550 after seeing it would be choosing when to stop by the result, so it is not done under this protocol.
  5. **Unchanged.** The 10 private adverts and the MMLU check (1,000 questions) run as described above. The README states "50 of 600 test adverts".

- 9 Nov 2026, official run complete (all arms once; nothing rerun). Produced from commit `2658b1d` (recorded in `reports/mmlu.json`; the tree was clean for every run). Reports: `reports/test_{zero_shot,few_shot,tuned,constrained}.json`, `reports/test_marks.json`, `reports/private_*.json`, `reports/mmlu.json`. Output files stay in the gitignored `outputs/`; first 12 hex characters of their SHA-256: test constrained `69f04fa41f39`, few-shot `a1b65004d576`, tuned `15696fd810ea`, zero-shot `9e035f2853a8`; private constrained `08a3c0d5ad8b`, few-shot `4a0855d70949`, tuned `cc90448d6109`, zero-shot `5baaa25f3f7d`. Facts found while reading the results (no mark moves):
  1. **Zero-shot scores 0.0 JSON validity on all 50 test and all 10 private adverts.** Checked by hand: the outputs are fenced JSON (a fence is allowed), but each breaks the schema, for example `skills` as one comma-separated string and `work_pattern` values such as "office based", "Hybrid" or "full-time". It is a real failure of the untuned model under the schema, not a parsing fault.
  2. **Tuned private run: 9 of 10 valid.** The one invalid output used the capitalised value "Hybrid" for `work_pattern`, which the schema does not allow.
  3. **Batch sizes:** few-shot, zero-shot and constrained at batch size 1; tuned at batch size 8 on the test subset (latency not comparable) and batch size 1 on the private set.

## 9. Known biases and limits

- Synthetic adverts are cleaner and more regular than real ones, so test scores will flatter real use.
- The author wrote the generator and the labelling guide. The private labels were drafted from the guide and checked by the author, and the private set is only 10 adverts. This is a self-test, not an independent one.
- One base model and one seed.
- MMLU is one narrow measure of general ability.
- "Unclear" is a judgement class, and its rules are ours.
- The UK sponsor register shows that an employer holds a licence, not that a given job is sponsored.
- Fairness trap: the few-shot prompt is longer, so it is slower. Latency is reported per arm.
- Constrained decoding runs on a different engine and quantisation, so its numbers are context only.
