### Recipes, Ingredient Labels and RapidFuzz Baseline — 12 November 2026

**Objective:** Remove the main blockers for the AI evaluation: expand the recipes, build the hand-verified test set and get a baseline number.

**Work completed:**
- Expanded the recipe dataset from 5 to 25 recipes (`data/recipes.csv`, `data/recipe_ingredients.csv`): 9 vegan, 5 vegetarian, 4 pescatarian, 7 omnivore; 112 ingredient rows, 48 unique ingredients, quantities in grams for 2 servings.
- Added a `main_protein` column so the weekly planner can apply the "no repeated main protein" rule. Every diet has at least 7 distinct main proteins, so a 7-day menu is always possible.
- Downloaded Agribalyse synthese v3.2 (`data/agribalyse_synthese.csv`, from data.gouv.fr). We use `Code AGB`, `LCI Name` (English name) and `Changement climatique` (kg CO2e per kg).
- Built the labelled set (`data/ingredient_labels.csv`): 100 ingredients = 48 in English + 52 Spanish/Catalan variants. Split 50 tune / 50 test, balanced by language, fixed seed.
- Implemented the RapidFuzz baseline (`src/matching.py`) and the evaluation script (`src/evaluate_matching.py`).

**How the labels were made:**
- Labels were pre-filled with an AI assistant from Agribalyse synthese, then verified row by row by Silvia, Laura, Carla and Martina.
- Result of the review: 0/100 codes changed; 1 note clarified (noodles: dry vs cooked weight).

**Labelling criteria (team decisions):**
- Choose the food in the state that matches the recipe weight: raw or dry when weights are raw/dry (rice, pasta, split peas); canned, drained for 240 g of legumes (one drained can); lentils cooked.
- Mushroom: **no match** (button mushroom is not in Agribalyse; only morel exists). The correct answer for the matcher is "uncertain".
- Black bean: **proxy** = haricot bean, canned (same species). Declared.
- Noodles: only cooked Asian noodles exist; the recipe uses dry weight. The CO2e calculation must convert to cooked weight.
- Chickpea: canned (2.2 kg CO2e/kg) chosen over cooked from dry (0.6). This choice changes the result by ~3.6x.

**Results — RapidFuzz baseline:**
- Scorer: WRatio (best of 5 RapidFuzz scorers tested on the tune split).
- "Uncertain" threshold chosen on tune only: 75.
- **Test: 7/50 correct (14%)** — English 6/23, Spanish 0/14, Catalan 1/13.
- Typical errors: "tomato" → *Tomato sauce for pizza base*; "lamb" → *Lamb's lettuce*; "pollo" → *Alaska pollock*; "chorizo" → *Pizza, chorizo or salami*.

**Decision rule (updated with the real number):**
- The AI model (multilingual sentence-transformers + FAISS) must get **at least 12/50 (24%)** on the same test set by 24th of November to be kept. Otherwise the demo uses RapidFuzz and we declare it.

**Challenges and limitations:**
- String matching fails on other languages and on names that look similar but mean different foods.
- Some ingredients have no exact Agribalyse equivalent (mushroom, black bean), so part of the error is in the data, not in the method.

**Next steps:**
- Build the rule-based weekly planner (diet filter + no repeated main protein).
- Build the AI matcher with the same output format as `RapidFuzzMatcher`.
- Write the README run instructions (fix from the smoke test).

**Evidence:** `src/matching.py`, `src/evaluate_matching.py`, `data/results_rapidfuzz_test.csv`.
