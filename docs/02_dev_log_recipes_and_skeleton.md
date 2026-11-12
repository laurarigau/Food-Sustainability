### Recipe Dataset and First End-to-End Skeleton — [DATE, between 28 Oct and 11 Nov 2026]

**Objective:** Create a first curated recipe dataset and get the full pipeline running from start to end, even if some parts are still stubs or done by hand.

**Work completed:**
- Created an initial recipe dataset (`notebooks/03_recipe_preparation.ipynb`): 5 recipes, 2 servings each, with a dietary tag (vegan, vegetarian, omnivore).
- Created a recipe–ingredient table with quantities in grams: 20 ingredient entries, 12 unique ingredients.
- Validated the data: no missing values, no invalid quantities, no unknown or duplicated recipe IDs.
- Standardized ingredient names (lowercase, trimmed, singular forms such as "lentils" → "lentil").
- Joined Open Food Facts products with Agribalyse CO2e values.
- Implemented the CO2e calculation: grams × kg CO2e per kg, summed per meal and per week.
- Built a first simple page that shows the totals.

**Status of each component (real vs. faked):**

| Component | Status | What it does now |
|---|---|---|
| Open Food Facts data | Real | Loaded and filtered |
| CO2e values (Agribalyse) | Real | Downloaded and joined to the products |
| Recipes | Faked | 5 recipes written by hand |
| Ingredient matching (AI) | Stub | Only works when the ingredient name is exactly the same as in Agribalyse |
| CO2e calculation | Real | Grams × kg CO2e per kg, per meal and per week |
| Weekly planner | Faked | The 7 meals are chosen by hand |
| Interface | Stub | One simple page that shows the totals |

**Results:**
- We reached Level 2: the skeleton runs end to end (a recipe goes in, a carbon number comes out on a page).

**Decisions and rationale:**
- Riskiest question: *Can we match each recipe ingredient to the right food in Agribalyse, so that its CO2e is correct?* If not, every carbon number in the planner is wrong.
- Stack agreed (see "Our stack"): DuckDB + pandas for data, RapidFuzz as baseline, multilingual sentence-transformers + FAISS for the AI matching, Streamlit on Hugging Face Spaces for the interface, Google Sheets + scikit-learn for evaluation.
- Four tools are new to every member (sentence-transformers + FAISS, DuckDB, Streamlit on HF Spaces, RapidFuzz). We will ask for coaching first on sentence-transformers + FAISS and DuckDB, then on Streamlit closer to the demo.

**Challenges and limitations:**
- Only 5 recipes; we need 20–30.
- Exact-name matching fails as soon as the recipe name differs from the Agribalyse name (plural, language, synonym).
- Code still lives in Colab notebooks; `src/` and `tests/` are empty. The notebook saves CSV files inside Colab instead of in `data/`, and some cells are duplicated.

**Next steps:**
- Replace the exact-match stub with RapidFuzz (baseline).
- Label 100 ingredients by hand: 50 to tune the method, 50 kept for the final test.
- Build the AI model (multilingual sentence-transformers + FAISS) with an "uncertain" output when confidence is low.
- Add simple planner rules: respect the diet, do not repeat the main protein.

**Evidence:** `notebooks/03_recipe_preparation.ipynb`, "First Steps", "Real vs Fake", "Our stack" documents. [ADD commit links]
