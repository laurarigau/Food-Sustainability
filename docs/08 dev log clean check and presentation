# Clean-Environment Check and Presentation — 18 November 2026


## Objective

Check that the whole project still runs end to end from a clean environment, using only the README,
run the pending AI evaluation with `--objective safe`, and prepare the presentation and the guide slide for the logs for the final demo (2 December).

All results below come from real runs of our code on 18 November; nothing is simulated.

## 1. What was checked

Fresh Python virtual environment, `pip install -r requirements.txt`, code from `main` (last merge: PR #9, 13 Nov).

| Check | Command | Result |
|---|---|---|
| Install | `pip install -r requirements.txt` | OK, no errors |
| Smoke test | `python tests/test_smoke.py` | Passed |
| Baseline evaluation | `python src/evaluate_matching.py` | RapidFuzz 7/50 on TEST, same as log 05 |
| Demo, 4 diets × 2 goals | `python src/run_demo.py --diet <diet> --goal <goal>` | 8/8 runs without errors (table below) |
| Streamlit app | `streamlit run src/app.py` | Generate plan + replace a meal works; screenshots taken |
| AI matcher, safer threshold | `python src/evaluate_matching.py --matcher ai --candidates strict --objective safe` (Google Colab) | 2/50 correct, 50 uncertain, 0 confident errors (section 2) |

### Demo results (1 person, 1 meal per day, team-verified labels)

| Diet | Goal | Weekly total (kg CO₂e) | Swap | Saving (kg CO₂e) |
|---|---|---:|---|---:|
| Vegan | variety | 2.73 → 2.28 | yes | 0.45 |
| Vegan | low carbon | 2.14 | no lower alternative | — |
| Vegetarian | variety | 2.88 → 2.50 | yes | 0.39 |
| Vegetarian | low carbon | 1.91 | no lower alternative | — |
| Pescatarian | variety | 3.79 → 2.68 | yes | 1.12 |
| Pescatarian | low carbon | 1.91 | no lower alternative | — |
| Omnivore | variety | 8.01 → 2.45 | yes | 5.56 |
| Omnivore | low carbon | 1.91 | no lower alternative | — |

In the app (Omnivore, More variety), replacing Thursday's Beef Burger (5.69 kg) with the Lentil Salad
(0.14 kg) gives the same result: 8.01 → 2.45 kg CO₂e per week. **This is the case we will show in the demo.**

## 2. AI with `--objective safe` (pending since log 07)

Run in Google Colab on 18 November with `BAAI/bge-m3`, candidates `strict`, passage `en`, penalty 1.0.
The threshold was chosen on the TUNE split only.

| Setting | Threshold (chosen on TUNE) | TEST correct | Uncertain | Confident errors |
|---|---:|---:|---:|---:|
| Log 07: objective `accuracy` | 0.60 | 12/50 | 13 | 25 |
| This run: objective `safe` | 0.90 | 2/50 | 50 | 0 |

By language (safe): English 1/23, Spanish 0/14, Catalan 1/13.
Results: `data/results_ai_bge-m3_strict_en_safe_test.csv`.

**What it means:** the safer threshold removes all confident errors, but only because the AI then
answers "uncertain" for all 50 ingredients. The 2 correct cases are ingredients whose right answer is
"no match" (they are counted as correct when the system says uncertain). With this threshold the AI
never gives a CO₂e number, so it is safe but not useful. The model's confidence score does not
separate right matches from wrong ones.

**Honesty note:** this run was done after we had already seen the TEST results of log 07, so it is
reported as **exploratory**. It does not change the decision of log 07; it supports it:
the planner keeps the team-verified labels, and the AI's best future use is to suggest candidates
that a person confirms.

## 3. Issues found

| Issue | Impact | Proposed action |
|---|---|---|
| Before any change, the app shows "Change vs original plan: -0.00 kg" with a green arrow | Cosmetic, looks odd in the demo | Show 0.00 with no arrow when nothing has changed |
| With goal "low carbon", vegetarian, pescatarian and omnivore give the same plan (1.91 kg, all plant-based) | Correct by the rule, but someone may ask why there is no fish or meat | Explain it in the demo, or add a rule to keep at least one meal of the chosen diet |
| Placeholders still in logs 02 and 03 (`[DATE]`, `[ADD commit links]`, `[ADD system boundary]`) | The logs look unfinished | Fill them in before 2 December |
| Some commits are signed with placeholder git identities ("TU_EMAIL_REAL", "review / r@x") | These commits are not linked to a team member | Each member checks `git config user.name` and `user.email` |

## 4. Presentation

Added to `docs/presentation/`:

- `Weekly_Meal_Planner_Group3.pptx`: 11 slides with speaker notes (problem, how it works, riskiest
  question, data, AI benchmark, decision, demo, real vs declared, logs, lessons and next steps).
- `Logs_slide_Group3.pptx`: the one slide the course asks for as a guide to our logs (decisions and
  changes, scope, risks and rules, milestones, smoke test).

All numbers in the slides come from logs 01–07 and from this check (slide 6 includes the safe-threshold result).

## 5. Next steps

- [ ] External smoke test with another team, README only (planned 26 Nov)
- [x] Run the AI with `--objective safe` in Colab and add the result to the presentation
- [x] Fill the placeholders in logs 02 and 03
- [ ] Code freeze (29 Nov) and rehearsal (1 Dec)
