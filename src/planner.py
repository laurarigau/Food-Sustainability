"""Rule-based weekly planner.

Rules:
  1. Respect the diet: a user can eat recipes of their diet and of any stricter diet.
  2. Do not repeat the main protein during the week.
  3. Goal "low_carbon": prefer the recipes with the lowest kg CO2e per serving.
     Goal "variety": random choice (fixed seed for reproducible demos).
"""
import random

import pandas as pd

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
        pool = pool.sort_values("kg_co2e_serving")
    elif goal == "variety":
        pool = pool.sample(frac=1, random_state=seed)
    else:
        raise ValueError("goal must be 'low_carbon' or 'variety'")

    chosen, used_proteins = [], set()
    for _, r in pool.iterrows():
        if r["main_protein"] not in used_proteins:
            chosen.append(r)
            used_proteins.add(r["main_protein"])
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
    pool = pool[~pool["main_protein"].isin(others["main_protein"])]
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
