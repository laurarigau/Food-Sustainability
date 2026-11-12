"""CO2e per ingredient, per recipe and per serving.

Formula: kg CO2e = (grams / 1000) x kg CO2e per kg (Agribalyse "Changement climatique").

Which matcher links ingredients to Agribalyse is a parameter:
  - "labels"    : the team-verified mapping in data/ingredient_labels.csv (FAKED: manual, declared)
  - "rapidfuzz" : the RapidFuzz baseline (real, but 7/50 on test)
  - later "ai"  : sentence-transformers + FAISS (same output format)
"""
import pandas as pd

from matching import DATA_DIR, RapidFuzzMatcher, load_agribalyse

# Agribalyse only has the cooked version of some foods, while recipes use dry weight.
# Multiply the recipe weight by this factor before applying the CO2e factor.
# Assumption (declare in log): dry noodles roughly x2.5 their weight when cooked.
COOKED_WEIGHT_FACTOR = {"noodles": 2.5}


class LabelMatcher:
    """Looks up the hand-verified Agribalyse code for a canonical ingredient (manual mapping)."""

    def __init__(self, agribalyse: pd.DataFrame | None = None):
        agb = agribalyse if agribalyse is not None else load_agribalyse()
        labels = pd.read_csv(DATA_DIR / "ingredient_labels.csv", dtype={"agribalyse_code": str})
        labels = labels.drop_duplicates("canonical_ingredient").set_index("canonical_ingredient")
        self.lookup = labels["agribalyse_code"].to_dict()
        self.agb = agb.set_index("agribalyse_code")

    def match(self, ingredient: str) -> dict:
        code = self.lookup.get(ingredient)
        if code is None or pd.isna(code) or code not in self.agb.index:
            return {"ingredient": ingredient, "agribalyse_code": None, "agribalyse_name": None,
                    "co2e_per_kg": None, "score": 0.0, "uncertain": True}
        row = self.agb.loc[code]
        return {"ingredient": ingredient, "agribalyse_code": code, "agribalyse_name": row["agribalyse_name"],
                "co2e_per_kg": float(row["co2e_per_kg"]), "score": 100.0, "uncertain": False}


def get_matcher(name: str = "labels"):
    if name == "labels":
        return LabelMatcher()
    if name == "rapidfuzz":
        return RapidFuzzMatcher()
    if name == "ai":
        from ai_matching import EmbeddingMatcher
        return EmbeddingMatcher()
    raise ValueError(f"Unknown matcher: {name}")


def load_recipes():
    recipes = pd.read_csv(DATA_DIR / "recipes.csv")
    ingredients = pd.read_csv(DATA_DIR / "recipe_ingredients.csv")
    return recipes, ingredients


def ingredient_co2e(ingredients: pd.DataFrame, matcher) -> pd.DataFrame:
    """Add the Agribalyse match and kg CO2e to every recipe ingredient row."""
    cache = {name: matcher.match(name) for name in ingredients["ingredient_clean"].unique()}
    df = ingredients.copy()
    df["agribalyse_name"] = df["ingredient_clean"].map(lambda n: cache[n]["agribalyse_name"])
    df["co2e_per_kg"] = df["ingredient_clean"].map(lambda n: cache[n]["co2e_per_kg"])
    df["uncertain"] = df["ingredient_clean"].map(lambda n: cache[n]["uncertain"])
    factor = df["ingredient_clean"].map(COOKED_WEIGHT_FACTOR).fillna(1.0)
    df["kg_co2e"] = df["quantity_g"] * factor / 1000 * df["co2e_per_kg"]
    return df


def recipe_co2e(recipes: pd.DataFrame, ing_co2e: pd.DataFrame) -> pd.DataFrame:
    """kg CO2e per recipe and per serving. Uncertain ingredients are excluded and listed."""
    agg = ing_co2e.groupby("recipe_id").agg(
        kg_co2e_recipe=("kg_co2e", "sum"),
        uncertain_ingredients=("ingredient_clean",
                               lambda s: ", ".join(s[ing_co2e.loc[s.index, "uncertain"]])),
    ).reset_index()
    out = recipes.merge(agg, on="recipe_id", how="left")
    out["kg_co2e_serving"] = out["kg_co2e_recipe"] / out["servings"]
    out["complete"] = out["uncertain_ingredients"] == ""
    return out
