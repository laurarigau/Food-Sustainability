"""CO2e per ingredient, per recipe and per serving.

Formula: kg CO2e = (grams / 1000) x kg CO2e per kg (Agribalyse "Changement climatique").

Which matcher links ingredients to Agribalyse is a parameter:
  - "ai_checked": AI proposes, the team checks (default when data/ingredient_matches_llm.csv exists).
                  The LLM answers are precomputed (notebook 09). Where the AI agrees with the team
                  label it is "confirmed"; where it disagrees or is not sure, the team label is used
                  and the row says so. Same numbers as "labels", but you see what the AI did.
  - "labels"    : the team-verified mapping in data/ingredient_labels.csv (manual, declared)
  - "rapidfuzz" : the RapidFuzz baseline (real, but 7/50 on test)
  - "ai"        : sentence-transformers + FAISS (same output format)
  - "llm"       : retrieve candidates + an LLM chooses live (llm_matching.py, needs a GPU/API/Ollama)
"""
import os
from pathlib import Path

import pandas as pd

from matching import DATA_DIR, RapidFuzzMatcher, load_agribalyse

# Agribalyse only has the cooked version of some foods, while recipes use dry weight.
# Multiply the recipe weight by this factor before applying the CO2e factor.
# Assumption (declare in log): dry noodles roughly x2.5 their weight when cooked.
COOKED_WEIGHT_FACTOR = {"noodles": 2.5}

AI_MATCHES_FILE = Path(os.environ.get("AI_MATCHES_FILE", DATA_DIR / "ingredient_matches_llm.csv"))

# Where the number of each ingredient comes from (shown in the app)
SOURCE_CONFIRMED = "AI ✓ confirmed by team"
SOURCE_CORRECTED = "Team corrected the AI"
SOURCE_TEAM = "Team (AI not sure)"
SOURCE_AI_ONLY = "AI only (not checked)"
SOURCE_NONE = "No equivalent in Agribalyse"


class LabelMatcher:
    """Looks up the hand-verified Agribalyse code for a canonical ingredient (manual mapping)."""

    def __init__(self, agribalyse: pd.DataFrame | None = None):
        agb = agribalyse if agribalyse is not None else load_agribalyse()
        labels = pd.read_csv(DATA_DIR / "ingredient_labels.csv", dtype={"agribalyse_code": str})
        labels = labels.drop_duplicates("canonical_ingredient").set_index("canonical_ingredient")
        self.lookup = labels["agribalyse_code"].to_dict()   # NaN = team said "NO MATCH"
        self.agb = agb.set_index("agribalyse_code")

    def match(self, ingredient: str) -> dict:
        code = self.lookup.get(ingredient)
        if code is None or pd.isna(code) or code not in self.agb.index:
            return {"ingredient": ingredient, "agribalyse_code": None, "agribalyse_name": None,
                    "co2e_per_kg": None, "score": 0.0, "uncertain": True}
        row = self.agb.loc[code]
        return {"ingredient": ingredient, "agribalyse_code": code, "agribalyse_name": row["agribalyse_name"],
                "co2e_per_kg": float(row["co2e_per_kg"]), "score": 100.0, "uncertain": False}


class CheckedAIMatcher:
    """AI proposes (precomputed LLM answers), the team confirms or corrects (team labels)."""

    def __init__(self, agribalyse: pd.DataFrame | None = None, ai_file=AI_MATCHES_FILE):
        agb = agribalyse if agribalyse is not None else load_agribalyse()
        self.team = LabelMatcher(agb)
        self.agb = agb.set_index("agribalyse_code")
        ai = pd.read_csv(ai_file, dtype={"agribalyse_code": str})
        self.ai = ai.set_index("ingredient").to_dict("index")
        self.model = str(ai["model"].iloc[0]) if "model" in ai and len(ai) else "LLM"

    def _ai_code(self, ingredient: str):
        row = self.ai.get(ingredient)
        if row is None or bool(row["uncertain"]) or pd.isna(row["agribalyse_code"]):
            return None
        return row["agribalyse_code"] if row["agribalyse_code"] in self.agb.index else None

    def match(self, ingredient: str) -> dict:
        ai_code = self._ai_code(ingredient)
        ai_name = self.agb.at[ai_code, "agribalyse_name"] if ai_code else None
        team = self.team.match(ingredient)
        has_label = ingredient in self.team.lookup

        if team["agribalyse_code"]:                       # the team has a verified food
            if ai_code == team["agribalyse_code"]:
                source = SOURCE_CONFIRMED
            elif ai_code is None:
                source = SOURCE_TEAM
            else:
                source = SOURCE_CORRECTED
            return {**team, "source": source, "ai_suggestion": ai_name}
        if has_label:                                     # the team checked: no equivalent food
            return {**team, "source": SOURCE_NONE, "ai_suggestion": ai_name}
        if ai_code:                                       # new ingredient, nobody checked it yet
            return {"ingredient": ingredient, "agribalyse_code": ai_code, "agribalyse_name": ai_name,
                    "co2e_per_kg": float(self.agb.at[ai_code, "co2e_per_kg"]), "score": 1.0,
                    "uncertain": False, "source": SOURCE_AI_ONLY, "ai_suggestion": ai_name}
        return {**team, "source": SOURCE_NONE, "ai_suggestion": None}


def ai_checked_available() -> bool:
    return AI_MATCHES_FILE.exists()


def get_matcher(name: str = "labels"):
    if name == "ai_checked":
        return CheckedAIMatcher()
    if name == "labels":
        return LabelMatcher()
    if name == "rapidfuzz":
        return RapidFuzzMatcher()
    if name == "ai":
        from ai_matching import EmbeddingMatcher
        return EmbeddingMatcher()
    if name == "llm":
        from llm_matching import LLMMatcher
        return LLMMatcher()
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
    df["source"] = df["ingredient_clean"].map(lambda n: cache[n].get("source"))
    df["ai_suggestion"] = df["ingredient_clean"].map(lambda n: cache[n].get("ai_suggestion"))
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
