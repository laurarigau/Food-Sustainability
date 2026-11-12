"""Demo path, end to end: diet -> 7-day menu -> CO2e per meal and per week -> swap one meal.

Usage:
    python src/run_demo.py
    python src/run_demo.py --diet vegetarian --goal variety --people 2
    python src/run_demo.py --matcher rapidfuzz      # see how wrong matches change the numbers
    python src/run_demo.py --matcher ai             # AI matcher (needs requirements-ai.txt)
"""
import argparse

import pandas as pd

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e
from planner import ALLOWED_TAGS, alternatives, plan_week, swap_meal, weekly_total


def show(plan: pd.DataFrame, people: int) -> None:
    cols = ["day", "recipe_name", "dietary_tag", "main_protein", "kg_co2e_serving"]
    view = plan[cols].copy()
    view["kg_co2e_serving"] = view["kg_co2e_serving"].round(2)
    view["note"] = plan["uncertain_ingredients"].apply(lambda s: f"uncertain: {s}" if s else "")
    print(view.to_string(index=False))
    print(f"\nWeekly total: {weekly_total(plan, people):.2f} kg CO2e ({people} person(s), 1 meal per day)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diet", default="omnivore", choices=list(ALLOWED_TAGS))
    ap.add_argument("--goal", default="variety", choices=["low_carbon", "variety"])
    ap.add_argument("--people", type=int, default=1)
    ap.add_argument("--matcher", default="labels", choices=["labels", "rapidfuzz", "ai"])
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    recipes, ingredients = load_recipes()
    ing = ingredient_co2e(ingredients, get_matcher(args.matcher))
    rec = recipe_co2e(recipes, ing)

    print(f"=== Weekly plan | diet: {args.diet} | goal: {args.goal} | matcher: {args.matcher} ===\n")
    plan = plan_week(rec, args.diet, args.goal, args.seed)
    show(plan, args.people)

    # Swap the highest-CO2e meal for its lowest-CO2e alternative
    worst = plan.loc[plan["kg_co2e_serving"].idxmax()]
    options = alternatives(plan, rec, args.diet, worst["day"])
    if len(options):
        best = options.iloc[0]
        print(f"\n=== Swap {worst['day']}: {worst['recipe_name']} ({worst['kg_co2e_serving']:.2f}) "
              f"-> {best['recipe_name']} ({best['kg_co2e_serving']:.2f}) ===\n")
        before = weekly_total(plan, args.people)
        plan = swap_meal(plan, rec, args.diet, worst["day"], best["recipe_id"])
        show(plan, args.people)
        after = weekly_total(plan, args.people)
        print(f"Saved: {before - after:.2f} kg CO2e ({(before - after) / before:.0%})")


if __name__ == "__main__":
    main()
