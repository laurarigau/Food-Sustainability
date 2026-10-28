
# Weekly Meal Planner 

## 1. Project Overview
The Weekly Meal Planner is a proposed AI-assisted tool designed to help households create practical weekly menus with a lower estimated food-related carbon footprint.
The system combines recipe data, ingredient information and environmental impact factors to recommend meals based on user preferences and compare their estimated emissions.

## 2. Problem Statement
Planning meals with a lower environmental impact can require researching recipes, checking ingredients and comparing environmental information across different sources. This information is not always available in one place or presented in a consistent format.
Our project aims to simplify this process by bringing recipe matching and estimated food-footprint information together in one tool.

## 3. User Value
Users can:
- Discover recipes that match their dietary preferences and food preferences.
- Compare estimated carbon footprints across meal options.
- Generate a proposed seven-day menu.
- Replace individual meals and compare changes in the estimated weekly footprint.
- Understand where estimates rely on incomplete data or category averages.

## 4. Proposed Features
- **Recipe dataset:** A curated collection of recipes, ingredients, quantities, serving sizes and dietary tags.
- **Data processing:** Cleaning ingredient names, standardising quantities and mapping ingredients to compatible environmental impact factors.
- **AI-powered recipe matching:** Using pretrained text embeddings to retrieve and rank recipes based on user preferences.
- **Dietary constraints:** Applying deterministic checks to exclude recipes that violate supported dietary requirements.
- **Carbon-footprint estimation:** Calculating estimated kg CO₂e per serving when compatible data is available.
- **Weekly menu output:** Displaying a seven-day menu, meal-level estimates and the estimated total footprint.
- **Data transparency:** Flagging missing values, assumptions and estimates based on category averages.

## 5. Data Sources
### Open Food Facts
[Open Food Facts](https://world.openfoodfacts.org/) is a proposed source of product and ingredient information. Its suitability for the recipe dataset will depend on data coverage, access conditions and licensing.

### Recipe Dataset
A small, curated recipe dataset will provide the initial recipes, ingredient quantities, serving sizes and dietary tags.

### Environmental Impact Factors
A compatible source of food-related environmental impact factors will be selected and reviewed. The project will document the source, units, system boundaries, coverage and licence before using the factors for comparisons.

**Important:** Environmental estimates will only be treated as evidence-based once their underlying data and calculation method have been validated.

## 6. Proposed Technology
- **Programming language:** Python
- **Data storage:** CSV files for the initial prototype
- **Data processing:** Ingredient cleaning, quantity standardisation and category mapping
- **AI component:** Pretrained text embeddings for recipe retrieval and ranking
- **Interface:** A simple user interface to be selected during development
- **Evaluation:** Comparison of embedding-based retrieval with a keyword-based baseline
The technology choices may be refined as implementation progresses.

## 7. Initial Prototype Scope
The first end-to-end prototype will use approximately 20–30 curated recipes, subject to data availability.
The prototype will aim to:
1. Accept user preferences.
2. Retrieve and rank suitable recipes.
3. Apply hard dietary constraints.
4. Calculate estimated emissions where sufficient data is available.
5. Display a proposed seven-day menu.
6. Allow users to replace meals and compare estimated totals.
Automatic shopping, price optimisation and personalised medical nutrition advice are outside the initial scope.

## 8. Evaluation Plan
The system will be evaluated using a small, manually reviewed set of preference queries and relevant recipes.
Planned evaluation activities include:
- Comparing embedding-based retrieval with a keyword-based baseline.
- Measuring precision at 5 (P@5).
- Testing dietary constraints separately.
- Manually reviewing ingredient mappings and footprint calculations.
- Reporting recipe and ingredient data coverage, including missing estimates.
A lower estimated footprint will not, by itself, be interpreted as proof of actual behavioural or environmental impact.

## 9. Repository Structure
```text
weekly-meal-planner/
├── README.md
├── data/
│   ├── README.md
│   ├── recipes.csv
│   └── impact_factors.csv
├── src/
│   ├── README.md
│   ├── data_processing.py
│   ├── recipe_matching.py
│   ├── emissions.py
│   └── main.py
├── tests/
│   └── README.md
├── docs/
│   ├── README.md
│   ├── system_sketch.png
│   └── development_log.md
├── requirements.txt
└── .gitignore
```
This is the intended structure. Files will be added as the corresponding components are developed and validated.

## 10. Current Status
The project concept, initial scope, proposed architecture and development plan are being defined.
The immediate priorities are to establish the repository structure, curate an initial recipe dataset, select a suitable environmental impact-factor source and build a small working prototype.
Implementation status and outstanding limitations will be updated as the project develops.

## 11. Main Technical Risk
The main technical challenge is mapping ingredient names and recipe quantities to sufficiently consistent environmental impact factors.
If reliable coverage is insufficient, the project will restrict the supported recipe set, flag missing data and clearly communicate the limitations of its estimates.

## 12. Team and Contributions
Team members and responsibilities will be documented as tasks are assigned.
Contributions will be tracked through the project board and repository history.
