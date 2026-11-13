
# Development Log — Weekly Meal Planner

## Log Entries

| #  | Date        | Entry                                                                              |
|----|-------------|------------------------------------------------------------------------------------|
| 01 | 28 Oct 2026 | [Data Cleaning](01_dev_log_cleaning_data.md)                                       |
| 02 | 12 Nov 2026 | [Recipe Dataset and First End-to-End Skeleton](02_dev_log_recipes_and_skeleton.md) |
| 03 | 12 Nov 2026 | [Change of Direction: Where the AI Is Used](03_dev_log_change_of_direction_ai.md)  |
| 04 | 11 Nov 2026 | [Planning to Demo Day](04_dev_log_session3_planning.md)                            |
| 05 | 12 Nov 2026 | [Recipes, Ingredient Labels and RapidFuzz Baseline](05_dev_log_recipes_labels_baseline.md) |
| 06 | 13 Nov 2026 | [Streamlit Interface and User Experience](06_dev_log_streamlit_interface.md)       |
| 07 | 13 Nov 2026 | [AI Matcher Revision 2 and Review Fixes](07_dev_log_ai_rev2_and_review_fixes.md)   |

## Current Status (updated 13 Nov 2026)

- **Level:** 3. The core pipeline is implemented, including recipe matching, CO₂e calculations and rule-based weekly planning. The Streamlit interface runs end to end (generate a plan, swap a meal, see the savings) and is covered by the smoke test (entry 07).
- **Real:** Open Food Facts-derived recipe data, Agribalyse CO₂e values, ingredient-level emissions calculations and implemented matching methods.
- **AI:** Multilingual embedding-based ingredient matching with FAISS retrieval. The second version (`BAAI/bge-m3`) achieved 12/50 correct matches (24%) on the test set, meeting the team's minimum threshold. It still makes 25/50 confident errors, so the demo uses the team-verified labels by default (entry 07).
- **Planner:** Rule-based weekly planning, respecting dietary preferences and avoiding repeated main proteins.
- **Interface:** Streamlit app in `src/app.py` (`streamlit run src/app.py`), connecting the existing backend functions.
- **Remaining validation**: recipe-level carbon validation, AI run with `--objective safe` (entry 07), external smoke test.
- **Main risk**: Ingredient-matching accuracy and the reliability of the resulting carbon estimates.
- **Next milestone:** external smoke test and rehearsal (see entries 04 and 07).

---

## Initial Project Decisions

**Objective:** Build a meal planning tool that helps households choose practical weekly menus with a lower estimated food footprint.

**Initial scope:**
- A curated recipe dataset.
- Preference-based recipe matching. *(Changed: see entry 03. The AI now does ingredient matching; the planner uses rules.)*
- Estimated emissions calculations.
- A seven-day menu.

## Initial Assumptions

- A small recipe dataset is sufficient to demonstrate the end-to-end workflow.
- Ingredient names and quantities can be mapped to compatible environmental impact factors.
- Embeddings may improve recipe matching compared with a keyword-based baseline. *(Revised: we now test whether embeddings improve **ingredient** matching compared with RapidFuzz; see entry 03.)*

## Main Technical Risk

Ingredient quantities and environmental impact factors may not be sufficiently consistent to produce reliable estimates.

## Planned First Milestone

Build a working pipeline using a small dataset before expanding the recipe collection or developing the interface. *(Reached: see entry 02.)*

## Open Questions

- ~~Which impact-factor source and system boundary will we use?~~ Agribalyse (kg CO2e per kg), joined to Open Food Facts. [ADD system boundary if decided]
- How will we handle missing ingredient data? *(Partly answered: if the matcher is not confident enough, the app shows "uncertain" instead of a number.)*
- ~~Which embedding model will we evaluate?~~ Several multilingual sentence-transformers models with FAISS search; best: `BAAI/bge-m3` (entry 07).
- How will we divide responsibilities across the team? *(See milestones and owners in entry 04.)*

## Next Steps

- [x] Set up the GitHub repository and task board.
- [x] Curate and expand the recipe dataset to 25 recipes.
- [x] Implement ingredient level CO2e calculations.
- [x] Test the end-to-end pipeline. (Level 2 skeleton)
- [X] Build the RapidFuzz baseline. 
- [X] Label 100 ingredients 
- [X] Implement the rule-based weekly planner.
- [X] Build and evaluate embeddings + FAISS matcher.
- [X] Move code from notebooks to `src/` and add a smoke test in `tests/`.
- [X] Develop the initial Streamlit interface.
- [X] Update the README and fix the issues found running from a clean environment (entry 07).
- [ ] External smoke test (another team, README only), rehearsal and final demo (2 Dec). 
