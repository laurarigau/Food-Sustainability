# AI Matcher Revision 2 and Review Fixes — 13 November 2026

## Objective

Record the result of the AI matcher revision 2 (notebook 05), and fix the problems found when
the whole repository was run from a clean environment using only the README.

## 1. AI matcher revision 2: result

- Search on the **TUNE split only**: 5 models × 3 candidate filters × 2 passage texts
  (`data/ai_rev2_tune_search.csv`). Best: `BAAI/bge-m3`, candidates `all`, passage `en`, threshold 0.60,
  tune accuracy 28%. (`all`, `light` and `strict` tied at 28%; the notebook rule takes the first one.)
- **TEST (run once): 12/50 (24%)** — English 8/23, Spanish 2/14, Catalan 2/13.
  RapidFuzz: 7/50. Revision 1: 11/50.
- **Decision rule (dev logs 03–05): met.** The AI reaches the minimum of 12/50 (+10 percentage points).

### Error analysis (test, threshold 0.60)

| Outcome | n | Meaning |
|---|---:|---|
| Correct | 12 | Right Agribalyse code, or "uncertain" when there is no match |
| Uncertain (wrong but no number shown) | 13 | Safe: the app shows "uncertain" |
| **Confident error** (wrong food with a CO₂e number) | **25** | The dangerous case for the user |

- Not all confident errors are equal. Of the 24 with a labelled answer, 7 are within ±25% of the right
  CO₂e (same food, different state: *beef, braised* vs *beef, minced, raw*; *potato, boiled* vs *raw*),
  and 10 are off by more than ×2 (*cerdo* → lamb, 6.6 → 41.3 kg CO₂e/kg; *ternera* → fish terrine;
  *merluza* → meringue; *all* (garlic) → candies).
- Most serious errors are Spanish/Catalan words or composed dishes/sweets.

### Decision

The AI **passes the benchmark** but 25/50 confident errors are too many to compute CO₂e without review.
Therefore:
- The planner and the demo use the **team-verified labels** by default. This is declared in the app
  and in the presentation; it is not presented as AI performance.
- The AI is shown as an evaluated component (12/50 vs 7/50) and as an option in the app, marked as
  experimental and not verified.
- Proposed use for the AI after the demo: suggest the top candidates for a new ingredient and let a
  person confirm (this is how our labels were built).

## 2. Review fixes (run from a clean environment)

| Problem found | Fix |
|---|---|
| The app crashed on the first click: default method was AI (`No module named 'faiss'`) | Default is now `labels`; the AI option only appears if `requirements-ai.txt` is installed |
| `streamlit` was missing from `requirements.txt` (log 06 said it was added) | Added `streamlit>=1.50`; README explains `streamlit run src/app.py` |
| RapidFuzz in the app used threshold 60, not the 75 chosen on TUNE | `DEFAULT_THRESHOLD = 75` in `src/matching.py` |
| Automatic matches were shown as "All ingredient matches are available" (green) even when wrong (e.g. *black bean* → black pepper) | Green only for verified labels; automatic methods show a "not verified" note, and every meal shows which Agribalyse food was used per ingredient |
| Savings were "Not calculated" whenever any meal in the week was incomplete (Mushroom Risotto), even for a beef → lentils swap | Savings now compare only the changed meals (`swap_savings` in `planner.py`): unchanged meals cancel out |
| Changing the number of people needed a new plan | Totals update immediately |
| `main_protein = "none"` was treated as a protein (Tomato Pasta and Vegetable Stir Fry could never be in the same week) | Recipes without a main protein can repeat |
| Goal "low carbon" could prefer incomplete recipes (they look lower because ingredients are missing) | Complete estimates are ranked first |
| `run_demo.py` swapped meals even with no saving ("Saved: -0.00") | Only swaps when there is a lower-CO₂e complete alternative |
| Threshold chosen only to maximise accuracy, which penalises saying "uncertain" | New option `--objective safe` in `evaluate_matching.py` (correct − confident errors); also reports confident errors. Not yet run with the AI model |
| Rev 2 CSVs were in `src/` and the result was in no log | Moved to `data/`; added to `data/matching_summary.csv` and this log |
| README described the original proposal (recipe recommendation, P@5, files that do not exist) | README rewritten to describe the current system |

Smoke test extended: savings calculation and the Streamlit page (generate a plan + replace a meal)
are now tested automatically. All tests pass from a clean environment.

## Next steps

- [ ] Run in Colab, decided before looking at TEST: `python src/evaluate_matching.py --matcher ai --candidates strict --objective safe` and log the result (correct / uncertain / confident errors).
- [ ] Save notebooks 04 and 05 **with outputs** as evidence.
- [ ] External smoke test (another team, README only) — see log 04, work 7.
- [ ] Optional: deploy the app (Streamlit Community Cloud or Hugging Face Spaces).

## Evidence

`src/app.py`, `src/planner.py`, `src/matching.py`, `src/evaluate_matching.py`, `src/run_demo.py`,
`tests/test_smoke.py`, `data/results_ai_rev2_test.csv`, `data/ai_rev2_tune_search.csv`,
`data/matching_summary.csv`.
