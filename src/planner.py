"""Rule-based weekly planner.

Rules:
  1. Respect the diet: a user can eat recipes of their diet and of any stricter diet.
  2. Do not repeat the main protein during the week. Recipes without a main protein
     (main_protein == "none", e.g. Tomato Pasta) can appear more than once per week.
  3. Goal "low_carbon": prefer the recipes with the lowest kg CO2e per serving.
     Recipes with a complete estimate come first: an incomplete estimate looks lower
     only because some ingredients are missing.
     Goal "variety": random choice (fixed seed for reproducible demos).
"""
import random

import pandas as pd

NO_PROTEIN = "none"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

ALLOWED_TAGS = {
    "vegan": ["vegan"],
    "vegetarian": ["vegan", "vegetarian"],
    "pescatarian": ["vegan", "vegetarian", "pescatarian"],
    "omnivore": ["vegan", "vegetarian", "pescatarian", "omnivore"],
}


def allowed_recipes(recipes: pd.DataFrame, diet: str) -> pd.DataFrame:
    if diet not in ALLOWED_TAGS:
        raise ValueError(f"Unknown diet '{diet}'. Choose from {list(ALLOWED_TAGS)}")
    return recipes[recipes["dietary_tag"].isin(ALLOWED_TAGS[diet])]


def plan_week(recipes: pd.DataFrame, diet: str, goal: str = "low_carbon", seed: int = 42) -> pd.DataFrame:
    pool = allowed_recipes(recipes, diet)
    if goal == "low_carbon":
        pool = pool.assign(_incomplete=~pool["complete"]).sort_values(["_incomplete", "kg_co2e_serving"])
        pool = pool.drop(columns="_incomplete")
    elif goal == "variety":
        pool = pool.sample(frac=1, random_state=seed)
    else:
        raise ValueError("goal must be 'low_carbon' or 'variety'")

    chosen, used_proteins = [], set()
    for _, r in pool.iterrows():
        protein = r["main_protein"]
        if protein == NO_PROTEIN or protein not in used_proteins:
            chosen.append(r)
            if protein != NO_PROTEIN:
                used_proteins.add(protein)
        if len(chosen) == 7:
            break
    if len(chosen) < 7:
        raise RuntimeError(f"Not enough recipes with different main proteins for diet '{diet}'")

    plan = pd.DataFrame(chosen).reset_index(drop=True)
    plan.insert(0, "day", DAYS)
    return plan


def alternatives(plan: pd.DataFrame, recipes: pd.DataFrame, diet: str, day: str) -> pd.DataFrame:
    """Recipes that could replace the meal of `day` without breaking the rules, lowest CO2e first."""
    others = plan[plan["day"] != day]
    pool = allowed_recipes(recipes, diet)
    pool = pool[~pool["recipe_id"].isin(plan["recipe_id"])]
    taken = set(others["main_protein"]) - {NO_PROTEIN}
    pool = pool[~pool["main_protein"].isin(taken)]
    return pool.sort_values("kg_co2e_serving")


def swap_meal(plan: pd.DataFrame, recipes: pd.DataFrame, diet: str, day: str, new_recipe_id: str) -> pd.DataFrame:
    options = alternatives(plan, recipes, diet, day)
    if new_recipe_id not in set(options["recipe_id"]):
        raise ValueError(f"{new_recipe_id} cannot replace {day}: wrong diet or repeated main protein")
    new_row = options[options["recipe_id"] == new_recipe_id].iloc[0]
    plan = plan.copy()
    idx = plan.index[plan["day"] == day][0]
    for col in new_row.index:
        plan.at[idx, col] = new_row[col]
    return plan


def weekly_total(plan: pd.DataFrame, people: int = 1) -> float:
    return float(plan["kg_co2e_serving"].sum() * people)


def proteins_are_unique(plan: pd.DataFrame) -> bool:
    """True when no main protein is repeated (recipes without a main protein are ignored)."""
    proteins = plan.loc[plan["main_protein"] != NO_PROTEIN, "main_protein"]
    return bool(proteins.is_unique)


def swap_savings(original: pd.DataFrame, current: pd.DataFrame, people: int = 1) -> tuple[float, bool]:
    """CO2e saved by the meals the user changed: (kg saved, comparable).

    Only the changed days are compared, so meals that stayed the same cancel out even if
    their own estimate is incomplete. The result is "comparable" only when every changed
    meal (old and new) has a complete estimate (no uncertain ingredients).
    """
    old = original.set_index("day")
    new = current.set_index("day")
    changed = [d for d in new.index if new.at[d, "recipe_id"] != old.at[d, "recipe_id"]]
    if not changed:
        return 0.0, True
    comparable = bool(old.loc[changed, "complete"].all() and new.loc[changed, "complete"].all())
    saved = float((old.loc[changed, "kg_co2e_serving"].sum() - new.loc[changed, "kg_co2e_serving"].sum()) * people)
    return saved, comparable
