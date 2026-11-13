"""Smoke test of the demo path. Run before every merge:
    python tests/test_smoke.py      (or: pytest tests/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e  # noqa: E402
from planner import (ALLOWED_TAGS, alternatives, plan_week, proteins_are_unique,  # noqa: E402
                     swap_meal, swap_savings, weekly_total)

SRC = Path(__file__).resolve().parent.parent / "src"


def build():
    recipes, ingredients = load_recipes()
    return recipe_co2e(recipes, ingredient_co2e(ingredients, get_matcher("labels")))


def test_every_diet_gets_a_valid_week():
    rec = build()
    for diet in ALLOWED_TAGS:
        for goal in ["low_carbon", "variety"]:
            plan = plan_week(rec, diet, goal)
            assert len(plan) == 7
            assert proteins_are_unique(plan)
            assert plan["dietary_tag"].isin(ALLOWED_TAGS[diet]).all()
            assert weekly_total(plan) > 0


def test_swap_keeps_the_rules():
    rec = build()
    plan = plan_week(rec, "omnivore", "variety")
    day = plan["day"].iloc[0]
    new_id = alternatives(plan, rec, "omnivore", day)["recipe_id"].iloc[0]
    plan = swap_meal(plan, rec, "omnivore", day, new_id)
    assert proteins_are_unique(plan) and len(plan) == 7


def test_swap_savings_only_counts_changed_meals():
    rec = build()
    plan = plan_week(rec, "omnivore", "variety")
    assert swap_savings(plan, plan) == (0.0, True)
    worst = plan.loc[plan["kg_co2e_serving"].idxmax()]
    options = alternatives(plan, rec, "omnivore", worst["day"])
    best = options[options["complete"]].iloc[0]
    new = swap_meal(plan, rec, "omnivore", worst["day"], best["recipe_id"])
    saved, comparable = swap_savings(plan, new, people=2)
    assert comparable
    assert abs(saved - 2 * (worst["kg_co2e_serving"] - best["kg_co2e_serving"])) < 1e-9


def test_streamlit_app_runs():
    """Generate a plan and replace a meal through the real Streamlit page (needs streamlit)."""
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("streamlit not installed: app test skipped")
        return
    at = AppTest.from_file(str(SRC / "app.py"), default_timeout=60).run()
    assert at.sidebar.selectbox[2].value == "labels"   # verified matches are the default
    at.sidebar.button[0].click().run()
    assert not at.exception and not at.error
    at.selectbox[0].set_value("Thursday").run()
    at.button[0].click().run()                          # "Replace meal"
    assert not at.exception and not at.error


if __name__ == "__main__":
    test_every_diet_gets_a_valid_week()
    test_swap_keeps_the_rules()
    test_swap_savings_only_counts_changed_meals()
    test_streamlit_app_runs()
    print("Smoke test passed")
