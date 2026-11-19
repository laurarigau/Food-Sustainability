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


def test_llm_matcher_format_without_api():
    """LLM matcher with a fake LLM (no API key needed): same output format, NONE -> uncertain."""
    import json
    from llm_matching import LLMMatcher

    def fake(system, user):
        if "Return ONLY a JSON object:\n{\"english\"" in system:
            return json.dumps({"english": "hake, raw", "synonyms": [], "french": "merlu, cru"})
        code = "26044" if "26044 |" in user else "NONE"
        return json.dumps({"code": code, "confidence": "high", "reason": "same food"})

    m = LLMMatcher(complete=fake, cache=False)
    r = m.match("merluza")
    assert r["agribalyse_code"] == "26044" and not r["uncertain"] and r["co2e_per_kg"] > 0
    assert set(r) >= {"ingredient", "agribalyse_code", "agribalyse_name", "co2e_per_kg", "score", "uncertain"}
    none = LLMMatcher(complete=lambda s, u: '{"code": "NONE"}', cache=False).match("xampinyons")
    assert none["uncertain"] and none["co2e_per_kg"] is None

    # verify step: a "no" turns a confident pick into "uncertain" (no CO2e number)
    def fake_no(system, user):
        return '{"same_food": "no"}' if "same_food" in system else fake(system, user)
    v = LLMMatcher(complete=fake_no, cache=False, verify=True).match("merluza")
    assert v["uncertain"] and v["co2e_per_kg"] is None and v["rejected_by_verify"]


if __name__ == "__main__":
    test_every_diet_gets_a_valid_week()
    test_swap_keeps_the_rules()
    test_swap_savings_only_counts_changed_meals()
    test_streamlit_app_runs()
    test_llm_matcher_format_without_api()
    print("Smoke test passed")
