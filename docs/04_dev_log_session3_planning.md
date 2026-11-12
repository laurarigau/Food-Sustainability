### Session 3: Planning to Demo Day — 11 November 2026

**Objective:** Use the Session 3 tools to find our bottlenecks, fix the scope, name our risks and agree milestones and team rules until the demo on 2 December.

> Fields marked [TO COMPLETE] must be filled with what the team produced in class. Items marked *(proposal)* are suggestions to confirm as a team.

---

#### Work 1: Hill chart and dependency wall

| Component | Position on the hill | Depends on |
|---|---|---|
| Data (OFF + Agribalyse) | Downhill (real, loaded and joined) | — |
| Recipes (20–30) | Downhill (we know how; it’s just work) | Data |
| Ingredient matching (AI) | Uphill (we don’t know if embeddings beat RapidFuzz) | Data, labelled ingredients |
| CO2e calculation | Downhill (real) | Ingredient matching |
| Weekly planner | Top of the hill (rules are clear, not coded yet) | Recipes, CO2e |
| Interface (Streamlit) | Uphill (nobody has used Streamlit on HF Spaces) | Output format of the planner |

- **Bottleneck (red dot):** ingredient matching. The CO2e calculation, the planner and the interface all depend on its output.
- **Mitigation** *(proposal)*: agree the output format of the matcher now (`ingredient → agribalyse_code, co2e_per_kg, confidence`), and keep RapidFuzz as a working stub so the rest of the pipeline is never blocked.
- Photo of the wall: [ADD]

#### Work 2: Press release

- **Headline:** Households can now plan a week of meals that fits their diet and see its carbon footprint, meal by meal.
- **Problem:** People want to eat more sustainably, but they don’t know which meals have a high or low footprint, and checking ingredient by ingredient takes too long.
- **Solution:** Our planner takes your diet, builds a 7-day menu from 25 recipes and shows the estimated kg CO2e of each meal and the whole week. You can swap a meal and see the total change. Ingredients are matched to Agribalyse automatically, even in Spanish or Catalan.
- **User quote:** “I swapped two beef dinners for lentils and saw my week drop by more than half. I didn’t have to look anything up.”
- **FAQs:**
  - Data: Open Food Facts and Agribalyse (kg CO2e per kg), with 25 hand-curated recipes and their quantities in grams.
  - Model accuracy: On 50 hand-labelled ingredients, our matcher gets [X]/50 right, against [Y]/50 for simple string matching. When it is not sure, it shows “uncertain” instead of a number.
  - What is still faked: The recipes are curated by hand, and the planner uses simple rules, not AI.
- Photo of the A3: [ADD]
- This press release is the first draft of our 2 December script.

#### Work 3: Buy a feature, final scope

| Feature | Price | Done when | Tokens received | Result |
|---|---|---|---|---|
| [TO COMPLETE] | | | | Must / Should / Could / Won't |

- **Cut list:** recipe recommendation with embeddings, grocery list, price optimisation.
- **Spike cards (time-boxed):** [TO COMPLETE, e.g. "Can embeddings beat RapidFuzz by 10 points? Time-box: until 24 Nov"]

#### Work 4 and 5: Pre-mortem with red team

| Risk | Likelihood | Impact | Fallback | Decision rule |
|---|---|---|---|---|
| [TO COMPLETE: risk 1, e.g. AI matching not better than baseline] | | | [e.g. RapidFuzz, declared] | [e.g. not +10 points by 24 Nov: stop] |
| [TO COMPLETE: risk 2] | | | | |
| [TO COMPLETE: risk 3] | | | | |

- Red team: [TEAM NAME]

#### Work 6: Milestones and team rules

**Milestones** *(proposal, confirm dates and owners)*:

| Date | Milestone | Done when | Owner |
|---|---|---|---|
| Sun 15 Nov | Base data | 20–30 recipes in `data/recipes.csv`; 100 ingredients labelled (50 tune / 50 test) | [NAME] |
| Wed 18 Nov | Real skeleton in `src/` | `python src/run_demo.py` returns a 7-day menu with CO2e using RapidFuzz; planner rules work; README explains how to run it | [NAME] |
| Tue 24 Nov | AI decision | Embeddings + FAISS vs RapidFuzz on the 50 test ingredients; "uncertain" threshold chosen; decision logged | [NAME] |
| Fri 27 Nov | Code freeze | Streamlit app live on HF Spaces; only fixes after this date | [NAME] |
| Sun 29 Nov | Rehearsal | Someone outside the team runs the demo using only the README | [NAME] |
| Wed 2 Dec | Demo day | Another team uses our planner | All |

**Team rules** (one option per row):

| Area | Our choice |
|---|---|
| Branches | [TO COMPLETE, e.g. one per task, merged in 1–2 days] |
| Review | [TO COMPLETE, e.g. every merge reviewed by another member] |
| Integration | [TO COMPLETE, e.g. merge into main twice a week] |
| Testing | [TO COMPLETE, e.g. smoke test of the demo path before every merge] |

#### Work 7: Smoke test swap

- Team that tested our repo: [TEAM NAME]
- **Result:** [TO COMPLETE: could they run the demo path with one product? yes / no]

| Where they got stuck | Who fixes it | By when |
|---|---|---|
| [TO COMPLETE, e.g. README has no run instructions] | | |
| [TO COMPLETE, e.g. code only in notebooks, `src/` empty] | | |

---

**Decisions and rationale:**
- Fixed time (2 December), variable scope: anything not bought in Work 3 goes to Won't or is faked and declared.
- [TO COMPLETE: any other decision taken in class]

**Next steps:**
- Fix the smoke test points before the next milestone.
- Start with what blocks everything else: labelling the 100 ingredients and expanding the recipes.
- Update the hill chart every week in this log.

**Evidence:** photos of the wall and the A3, buy-a-feature cards, pre-mortem grid. [ADD]
