
# Development Log — Weekly Meal Planner

## Initial Project Decisions

**Objective:** Build a meal planning tool that helps households choose practical weekly menus with a lower estimated food footprint.

**Initial scope:**
- A curated recipe dataset.
- Preference-based recipe matching.
- Estimated emissions calculations.
- A seven-day menu.

## Initial Assumptions

- A small recipe dataset is sufficient to demonstrate the end-to-end workflow.
- Ingredient names and quantities can be mapped to compatible environmental impact factors.
- Embeddings may improve recipe matching compared with a keyword-based baseline.

## Main Technical Risk

Ingredient quantities and environmental impact factors may not be sufficiently consistent to produce reliable estimates.

## Planned First Milestone

Build a working pipeline using a small dataset before expanding the recipe collection or developing the interface.

## Open Questions

- Which impact-factor source and system boundary will we use?
- How will we handle missing ingredient data?
- Which embedding model will we evaluate?
- How will we divide responsibilities across the team?

## Next Steps

- [ ] Set up the GitHub repository and task board.
- [ ] Curate the first recipes.
- [ ] Implement the initial calculations.
- [ ] Test the end-to-end pipeline.
