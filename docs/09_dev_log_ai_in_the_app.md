# AI + team check, "Analyse your recipe" and swaps — 20 November 2026

## Objective

Give the AI a real, visible job in the app. Until now the 25 recipes were fixed and their ingredients
were matched by hand, so the user never needed the matcher. Two changes:

1. **Weekly plan, "AI + team check"**: the LLM proposes the Agribalyse food for every recipe ingredient
   (precomputed, notebook 09) and the team label confirms or corrects it. Panel *"What did the AI do?"*.
2. **Analyse your recipe** (new tab): the user writes any recipe (EN/ES/CA) and gets its kg CO₂e and
   **what to change to reduce it**. The matcher benchmark (logs 05–08) is the technical justification.

## 1. Where the matcher stands (TEST, 50 ingredients, `data/results_*_test.csv`)

| Method | Correct food | CO₂e OK (±25%) | Uncertain (no number) | Confident errors |
|---|---:|---:|---:|---:|
| RapidFuzz | 7 | — | 20 | — |
| Embeddings `bge-m3` (log 07) | 12 | 19 | 14 | 25 |
| LLM Qwen 2.5 7B | 23 | 31 | 5 | 23 |
| **LLM Qwen 2.5 14B + verify** | **29** | **39** | 9 | **14** |

- "Correct food" is strict: *Pork loin, raw* vs *Pork, loin, raw* (two Agribalyse rows for the same food),
  *Chicken, meat* vs *chicken breast*, *Tomato, in season* vs *Tomato, raw* count as wrong. For the user,
  **CO₂e OK** is what matters: 39/50 (78%).
- Of the 11 not CO₂e-OK, 7 are flagged uncertain (safe: a person chooses). Only **4 are dangerous**
  (wrong food with a number): *lamb* → saddle, *cordero* → leg (label ambiguity: which cut?),
  *patates* → boiled potato, *xai* → shrimp.
- Most remaining failures are **Catalan** (pastanaga, all, vedella, carbassó, xai, mongetes, patates).

## 2. Matcher changes (compared on TUNE only)

- `--fewshot`: the NORMALISE step gets 6 worked examples, **all from the TUNE split** (llenties, lluç,
  tonyina, ou, pebrot, judías blancas), plus the hint that Catalan words often look nothing like Spanish.
  A test checks that every example word is a TUNE word.
- `--tune-only` in `evaluate_matching.py`: compare configurations **without touching TEST**.
- `--provider ollama` also accepted by the evaluator (free model on a laptop).

**Protocol (decided before running, notebook 10):**
1. On TUNE: Qwen 14B + verify (current) vs Qwen 14B + verify + fewshot.
2. Keep fewshot only if TUNE **CO₂e OK** improves; tie → fewer confident errors.
3. If it wins: run it ONCE on TEST, report it here whatever the result, and re-run notebook 09
   (`precompute_matches.py --verify --fewshot`) so the app uses it.

| Configuration | TUNE CO₂e OK | TUNE confident errors | TEST (chosen one only) |
|---|---:|---:|---:|
| Qwen 14B + verify | _to fill_ | _to fill_ | 39/50 CO₂e OK (already known) |
| Qwen 14B + verify + fewshot | _to fill_ | _to fill_ | _only if chosen_ |

Honesty note: the few-shot words come only from TUNE, but the *idea* of fixing Catalan came from looking at
the TEST errors of section 1, so any TEST gain is reported as **exploratory** (as in log 08).

## 3. "Analyse your recipe": what was added on top of the first version

| Part | File | What it does |
|---|---|---|
| Flexible reader | `own_recipe.parse_recipe` | Grams/kg/ml, and also pieces and spoons in EN/ES/CA (`2 huevos`, `2 cucharadas`, `mig kg`, `tomàquet 400 g`). Estimated weights are shown to the user. A title like "(4 personas)" sets the servings. |
| Simple plurals | `RecipeAnalyser.resolve` | "cebollas" uses the team label of "cebolla" |
| AI candidates first | `RecipeAnalyser.candidates(first=...)` | When the live AI is not sure, its own candidates are shown first in "you choose" |
| Memory of choices | `RecipeAnalyser.remember` | The food a user chooses is saved in `data/user_confirmations.csv` (git-ignored); next time it is automatic. **Never used to score the AI.** |
| Swaps | `own_recipe.suggest_swaps`, `apply_swaps` | For foods above 4 kg CO₂e/kg: alternatives with the same role (red meat → lentil, chickpea, chicken; pork → chicken, white bean, tofu; shellfish → hake, tofu; butter → olive oil; cheese → half). Saving in kg and %, tick to see the new footprint. |
| Live AI | `app.live_ai` | Ollama + verify + fewshot |

Example (default recipe, *lasaña de la abuela*, 400 g ternera picada): swapping the beef for lentils removes
about **80%** of the recipe's known footprint.

| Real | Declared |
|---|---|
| LLM matching + verify, CO₂e formula, Agribalyse values, swap savings | Piece/spoon weights (1 egg = 60 g, 1 onion = 150 g, 1 tbsp = 14 g...), same-weight swaps, the swap table (team rule) |

## 4. Story for the presentation

Problem (people cook their own recipes, in their own language) → why simple methods fail (RapidFuzz 7/50,
embeddings 12/50) → our solution: LLM + verification (39/50 CO₂e OK, only 4 dangerous errors) + a person
confirms the rest (team in the planner, user in their own recipe) → demo: *lasaña de la abuela* → swap
beef for lentils → −80% → weekly planner with *"What did the AI do?"*.

## 5. Next steps

- [ ] Notebook 09 (precompute AI matches) → commit `data/ingredient_matches_llm.csv` (without it the
      "AI + team check" option is hidden).
- [ ] Notebook 10 (TUNE comparison) → fill the table of section 2.
- [ ] Each member fixes `git config user.email` (the last commit is still signed "TU_EMAIL_REAL").
- [ ] Code freeze 29 Nov, rehearsal 1 Dec.
