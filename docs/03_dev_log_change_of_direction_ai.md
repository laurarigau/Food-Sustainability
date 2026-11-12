### Change of Direction: Where the AI Is Used — [DATE, same period as entry 02]

**Objective:** Record why the AI component moved from recipe recommendation to ingredient matching.

**What we planned before (Final Idea):**
- AI used for recipe matching: pretrained text embeddings rank recipes according to user preferences.
- Evaluation: embedding-based ranking vs. keyword matching, measured with precision at 5 (P@5).

**What we do now:**
- AI used for ingredient matching: each recipe ingredient is matched to the closest Agribalyse food using multilingual sentence-transformers + FAISS.
- Baseline: RapidFuzz string matching (most similar name, letter by letter).
- Evaluation: accuracy on 50 hand-labelled test ingredients, same set for both methods.

**Decisions and rationale:**
- Ingredient matching is our riskiest question: if a match is wrong, the carbon number is wrong, and the whole project fails. Putting the AI there attacks the main risk directly.
- With only 20–30 recipes, recipe recommendation adds little value; simple rules (diet filter, no repeated main protein) are enough for the weekly planner.
- Multilingual embeddings can match ingredients written in Spanish or Catalan, which string matching cannot.

**Decision rule (continue / revise / stop):**
- Continue: the AI model gets at least 10 percentage points more correct matches than RapidFuzz on the 50 test ingredients by **[DATE, e.g. 24 Nov 2026]**.
- Revise: it only beats the baseline for some ingredient types → use AI for those, RapidFuzz for the rest, and declare it.
- Stop: not met by the date → the demo uses RapidFuzz, and we declare it in the log and in the presentation.
- When the AI is not confident enough (threshold to be chosen on the 50 tuning ingredients), the app shows "uncertain" instead of a number.

**Impact on scope:**
- Recipe recommendation with embeddings → moved to Won't (out of scope for 2 December).
- Weekly planner → rule-based.
