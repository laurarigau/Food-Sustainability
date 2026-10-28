### Data Cleaning — 28 October 2026

**Objective:** Prepare a clean subset of Open Food Facts data for the Weekly Meal Planner prototype.

**Work completed:**
- Selected seven relevant columns from the original dataset.
- Checked product identifiers for duplicates.
- Extracted product names and ingredient descriptions from multilingual data structures.
- Removed records without usable product names or ingredient descriptions.
- Standardized category and allergen tags.
- Converted supported quantity and serving-size formats into grams.
- Identified unusual serving-size values for manual review.

**Results:**
- Initial sample: 1,000 products.
- Products retained: 880.
- Products with missing category tags: 457.
- Products without recorded allergen tags: 324.
- Quantities converted into grams: 423.
- Serving sizes converted into grams: 755 before final validation.

**Limitations:** Missing allergen tags do not guarantee allergen absence. Product quantities and serving sizes are not equivalent to ingredient quantities in recipes.

**Next step:** Build a curated recipe dataset containing ingredients, quantities, serving sizes and dietary information.
