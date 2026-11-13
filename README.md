# Weekly Meal Planner — Food Sustainability

A tool that plans a 7-day menu for a household's diet and estimates the carbon footprint
(kg CO₂e) of each meal, so the user can swap meals for lower-carbon alternatives.

Course project for *Perspectives of AI* (Esade). Final demo: 2 December 2026.

## How it works

```
recipes (25, grams)  ──►  ingredient matching  ──►  CO₂e per recipe  ──►  weekly planner  ──►  swap + savings
                          ingredient → Agribalyse      grams × kg CO₂e/kg     diet filter,          Streamlit app
                          food (3 methods)                                    no repeated protein
```

| Part | File | Status |
|---|---|---|
| Recipes: 25 recipes, 112 ingredient rows in grams, 2 servings each | `data/recipes.csv`, `data/recipe_ingredients.csv` | Curated by the team |
| Environmental data: Agribalyse 3.2 synthese (kg CO₂e per kg) | `data/agribalyse_synthese.csv` | Real data |
| Ingredient matching (see below) | `src/co2e.py`, `src/matching.py`, `src/ai_matching.py` | 3 methods |
| CO₂e calculation | `src/co2e.py` | Real |
| Weekly planner: diet filter + no repeated main protein + lowest-CO₂e or variety goal | `src/planner.py` | Rule-based |
| Interface | `src/app.py` | Streamlit |

### Where the AI is used: ingredient matching

Every recipe ingredient must be linked to the right Agribalyse food, otherwise its CO₂e is wrong.
This is the riskiest step, so the AI is used here (see dev log 03).

| Method | What it does | Test result (50 hand-labelled ingredients, EN/ES/CA) |
|---|---|---|
| `labels` | Team-verified mapping (`data/ingredient_labels.csv`) | Reference (ground truth) |
| `rapidfuzz` | Most similar name, letter by letter (baseline) | **7/50** |
| `ai` rev 1 | Multilingual sentence embeddings + FAISS | **11/50** |
| `ai` rev 2 | `BAAI/bge-m3` + FAISS | **12/50** (meets the ≥12/50 decision rule) |

12/50 beats the baseline but still means many wrong matches, so **the app uses the
team-verified labels by default** and shows the automatic methods only for comparison.
Details and error analysis: `docs/07_dev_log_ai_rev2_and_review_fixes.md`.

## How to run

```bash
pip install -r requirements.txt
streamlit run src/app.py                                # the app (opens in the browser)

python src/run_demo.py                                  # terminal demo: weekly plan + swap (backup for the demo)
python src/run_demo.py --diet vegan --goal low_carbon   # diets: vegan, vegetarian, pescatarian, omnivore
python src/evaluate_matching.py                         # RapidFuzz accuracy on the test set
python tests/test_smoke.py                              # run before every merge (also tests the app)
```

Optional, AI matcher (large model, best in Google Colab):

```bash
pip install -r requirements-ai.txt
python src/evaluate_matching.py --matcher ai
python src/evaluate_matching.py --matcher ai --candidates strict --objective safe   # fewer confident errors
```

The AI option only appears in the app when these packages are installed.

## Repository structure

```text
data/        recipes, Agribalyse, labelled ingredients, evaluation results (results_*.csv)
docs/        development log (index: docs/development_log.md)
notebooks/   01–03 data exploration/cleaning/recipes, 04–05 AI matcher experiments (Colab)
src/         matching.py, ai_matching.py, co2e.py, planner.py, app.py, run_demo.py, evaluate_matching.py
tests/       test_smoke.py
```

## Limitations

- Estimates use one meal per day and the Agribalyse system boundary; they are estimates, not measurements.
- Some ingredients have no exact Agribalyse equivalent (mushroom: no match; black bean: declared proxy).
  Meals with an unmatched ingredient are marked as *incomplete* and excluded from savings comparisons.
- Automatic matching (RapidFuzz and AI) makes confident mistakes; their CO₂e numbers are not verified.
- A lower estimated footprint is not, by itself, proof of a real environmental impact.

## Team

Silvia, Laura, Carla and Martina. Contributions are tracked in the repository history and the dev log.
