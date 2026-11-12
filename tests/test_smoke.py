"""Smoke test of the demo path. Run before every merge:
    python tests/test_smoke.py      (or: pytest tests/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e  # noqa: E402
from planner import ALLOWED_TAGS, alternatives, plan_week, swap_meal, weekly_total  # noqa: E402


def build():
    recipes, ingredients = load_recipes()
    return recipe_co2e(recipes, ingredient_co2e(ingredients, get_matcher("labels")))


def test_every_diet_gets_a_valid_week():
    rec = build()
    for diet in ALLOWED_TAGS:
        for goal in ["low_carbon", "variety"]:
            plan = plan_week(rec, diet, goal)
            assert len(plan) == 7
            assert plan["main_protein"].is_unique
            assert plan["dietary_tag"].isin(ALLOWED_TAGS[diet]).all()
            assert weekly_total(plan) > 0


def test_swap_keeps_the_rules():
    rec = build()
    plan = plan_week(rec, "omnivore", "variety")
    day = plan["day"].iloc[0]
    new_id = alternatives(plan, rec, "omnivore", day)["recipe_id"].iloc[0]
    plan = swap_meal(plan, rec, "omnivore", day, new_id)
    assert plan["main_protein"].is_unique and len(plan) == 7


if __name__ == "__main__":
    test_every_diet_gets_a_valid_week()
    test_swap_keeps_the_rules()
    print("Smoke test passed")
