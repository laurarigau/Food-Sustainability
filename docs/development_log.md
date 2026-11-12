
# Development Log — Weekly Meal Planner

## Log Entries

| # | Date | Entry |
|---|---|---|
| 01 | 28 Oct 2026 | [Data Cleaning](01_dev_log_cleaning_data.md) |
| 02 | [DATE] | [Recipe Dataset and First End-to-End Skeleton](02_dev_log_recipes_and_skeleton.md) |
| 03 | [DATE] | [Change of Direction: Where the AI Is Used](03_dev_log_change_of_direction_ai.md) |
| 04 | 11 Nov 2026 | [Session 3: Planning to Demo Day](04_dev_log_session3_planning.md) |

## Current Status (updated 12 Nov 2026)

- **Level:** 2. The skeleton runs end to end.
- **Real:** Open Food Facts data, Agribalyse CO2e values, CO2e calculation.
- **Faked / stub:** recipes (5 by hand), ingredient matching (exact name only), weekly planner (by hand), interface (one simple page).
- **Riskiest question:** Can we match each recipe ingredient to the right food in Agribalyse?
- **Next milestone:** [see entry 04]

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
- ~~Which embedding model will we evaluate?~~ A multilingual sentence-transformers model with FAISS search. [ADD exact model name]
- How will we divide responsibilities across the team? *(See milestones and owners in entry 04.)*

## Next Steps

- [x] Set up the GitHub repository and task board.
- [x] Curate the first recipes. (5 recipes; target 20–30)
- [x] Implement the initial calculations.
- [x] Test the end-to-end pipeline. (Level 2 skeleton)
- [ ] Replace exact matching with RapidFuzz baseline.
- [ ] Label 100 ingredients (50 tune / 50 test).
- [ ] Expand to 20–30 recipes.
- [ ] Build and evaluate embeddings + FAISS matcher.
- [ ] Move code from notebooks to `src/` and add a smoke test in `tests/`.
