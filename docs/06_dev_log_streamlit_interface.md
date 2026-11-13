# Streamlit Interface and User Experience — 13 November 2026

> **Update (entry 07):** when run from a clean environment, the app failed on the first click (AI was the default method and `streamlit` was not in `requirements.txt`). Both are fixed, the savings logic was improved and the app is now covered by the smoke test. See [entry 07](07_dev_log_ai_rev2_and_review_fixes.md).

## Objective

Build a user-facing interface for the weekly meal planner, connecting the existing recipe database, ingredient-matching system, CO₂e calculations and rule-based weekly planner. The goal is to make the project accessible to a household user without requiring them to run Python scripts manually.

## Work completed

- Developed an initial Streamlit interface in `src/app.py`.
- Connected the interface to the existing backend functions in `src/co2e.py` and `src/planner.py`, avoiding duplication of the core calculation and planning logic.
- Added user controls for:
  - Dietary preference: vegan, vegetarian, pescatarian or omnivore.
  - Planning objective: variety or lower carbon footprint.
  - Number of people.
  - Ingredient-matching method: manually reviewed labels, RapidFuzz or AI.
- Designed the weekly plan display to show seven meals, including recipe name, dietary category, main protein and estimated CO₂e per serving.
- Integrated the existing meal replacement functionality, allowing users to select a day and choose an alternative recipe.
- Added weekly emissions summaries and a comparison between the original and updated plans.
- Added warnings for uncertain ingredient matches so that incomplete carbon estimates are not presented as fully reliable.
- Added Streamlit to the project's dependencies.

## Interface and technical approach

The interface uses Streamlit and reuses the existing project architecture:

1. The user selects their preferences.
2. The application loads the recipes and calculates ingredient-level emissions using the selected matcher.
3. The existing `plan_week()` function generates a seven-day menu respecting dietary restrictions and the no-repeated-main-protein rule.
4. The application displays the meals and their estimated carbon footprints.
5. The user can select a day and replace its meal using `alternatives()` and `swap_meal()`.
6. The application recalculates the weekly total and displays the difference from the original plan.

The interface uses Streamlit session state to preserve the weekly plan when the application reruns after user interactions.

## Handling uncertainty

A key design decision was to make the limitations of ingredient matching visible to the user.

The existing CO₂e calculation excludes ingredients that cannot be confidently matched to Agribalyse. Therefore, the resulting recipe estimate can be incomplete.

The interface distinguishes between complete and incomplete estimates:

- Complete: all ingredients have a successful match.
- Incomplete: one or more ingredients remain uncertain, meaning the displayed emissions represent only the known portion.

Carbon savings are only presented as a complete comparison when both plans contain complete estimates.

## Challenges and limitations

- The AI matching method requires additional dependencies and a stable model configuration.
- Ingredient matching accuracy remains limited, so carbon estimates must be interpreted carefully.
- Some ingredients may not have a suitable equivalent in Agribalyse.
- The interface still needs end-to-end testing to verify that all backend functions work correctly through Streamlit.
- The application currently represents one planned meal per day rather than a complete breakfast, lunch and dinner menu.

## Validation still required

- Run the Streamlit application and verify that it launches correctly.
- Generate weekly plans for different dietary preferences.
- Verify that the planner respects dietary restrictions and avoids repeated main proteins.
- Replace meals and check that the weekly emissions total updates correctly.
- Test cases where no valid alternative is available.
- Verify that uncertain ingredient matches trigger the appropriate warnings.
- Compare five recipe-level CO₂e estimates against manually verified ingredient matches.
- Test the interface with the final AI model and configuration once integrated.

## Next steps

- Complete end-to-end testing of the Streamlit application.
- Validate the carbon estimates against manually reviewed results.
- Improve the visual presentation and usability of the interface.
- Document any bugs, assumptions and limitations identified during testing.
- Run the final smoke test and update the README.
- Upload the final implementation and evidence to GitHub.

## Evidence

- `src/app.py`
- `src/planner.py`
- `src/co2e.py`
- `requirements.txt`