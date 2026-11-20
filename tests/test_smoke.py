"""Smoke test of the demo path. Run before every merge:
    python tests/test_smoke.py      (or: pytest tests/)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e  # noqa: E402
from planner import (ALLOWED_TAGS, alternatives, plan_week, proteins_are_unique,  # noqa: E402
                     swap_meal, swap_savings, weekly_total)

SRC = Path(__file__).resolve().parent.parent / "src"
DATA = SRC.parent / "data"


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
    assert at.sidebar.selectbox[2].value in ("ai_checked", "labels")   # a verified method is the default
    at.sidebar.button[0].click().run()
    assert not at.exception and not at.error
    at.selectbox[0].set_value("Thursday").run()
    at.button[0].click().run()                          # "Replace meal"
    assert not at.exception and not at.error


def test_own_recipe():
    """'Analyse your recipe': parsing, team-confirmed ES/CA names, user choice for a new food."""
    from own_recipe import RecipeAnalyser, parse_recipe, SOURCE_KNOWN, SOURCE_USER

    parsed, errors = parse_recipe("300 g merluza\n1 kg de patates\n150g quinoa\nsal al gusto")
    assert list(parsed["quantity_g"]) == [300, 1000, 150] and errors == ["sal al gusto"]
    a = RecipeAnalyser()
    res = a.co2e(parsed)
    assert res.loc[0, "source"] == SOURCE_KNOWN and res.loc[0, "kg_co2e"] > 0      # merluza -> hake
    assert pd.isna(res.loc[2, "kg_co2e"])                                         # quinoa: user must choose
    code = a.candidates("quinoa")[0][0]
    res = a.co2e(parsed, {"quinoa": code})
    assert res.loc[2, "source"] == SOURCE_USER and res.loc[2, "kg_co2e"] > 0


def _fake_ai_matches(path):
    """AI answers for the recipe ingredients: all = team label, except one wrong and one unsure."""
    labels = pd.read_csv(DATA / "ingredient_labels.csv", dtype={"agribalyse_code": str})
    lab = labels.drop_duplicates("canonical_ingredient").set_index("canonical_ingredient")["agribalyse_code"]
    names = sorted(pd.read_csv(DATA / "recipe_ingredients.csv")["ingredient_clean"].unique())
    df = pd.DataFrame({"model": "fake", "ingredient": names, "agribalyse_code": [lab[n] for n in names]})
    df["uncertain"] = df["agribalyse_code"].isna()
    df.loc[df.ingredient == "lamb", "agribalyse_code"] = lab["beef"]               # AI wrong -> team corrects
    df.loc[df.ingredient == "tuna", "uncertain"] = True                            # AI not sure -> team
    df.to_csv(path, index=False)


def test_ai_checked_matcher():
    import tempfile
    from co2e import (CheckedAIMatcher, LabelMatcher, SOURCE_CONFIRMED, SOURCE_CORRECTED, SOURCE_TEAM,
                      SOURCE_NONE)
    path = Path(tempfile.mkdtemp()) / "ai.csv"
    _fake_ai_matches(path)
    m, team = CheckedAIMatcher(ai_file=path), LabelMatcher()
    assert m.match("egg")["source"] == SOURCE_CONFIRMED
    lamb = m.match("lamb")
    assert lamb["source"] == SOURCE_CORRECTED and lamb["agribalyse_code"] == team.match("lamb")["agribalyse_code"]
    assert m.match("tuna")["source"] == SOURCE_TEAM
    assert m.match("mushroom")["source"] == SOURCE_NONE and m.match("mushroom")["uncertain"]


def test_app_with_ai_checked_and_own_recipe():
    """The app with 'AI + team check' (fake AI file) and the 'Analyse your recipe' tab."""
    try:
        from streamlit.testing.v1 import AppTest
    except ImportError:
        print("streamlit not installed: app test skipped")
        return
    import os, tempfile
    path = Path(tempfile.mkdtemp()) / "ai.csv"
    _fake_ai_matches(path)
    os.environ["AI_MATCHES_FILE"] = str(path)
    try:
        import importlib, co2e
        importlib.reload(co2e)
        at = AppTest.from_file(str(SRC / "app.py"), default_timeout=60).run()
        assert at.sidebar.selectbox[2].value == "ai_checked"
        at.sidebar.button[0].click().run()
        assert not at.exception and not at.error
        assert any("What did the AI do" in e.label for e in at.expander)
        assert any(m.label == "Per serving" for m in at.metric)           # own recipe tab computed
    finally:
        del os.environ["AI_MATCHES_FILE"]


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
    test_own_recipe()
    test_ai_checked_matcher()
    test_app_with_ai_checked_and_own_recipe()
    test_llm_matcher_format_without_api()
    print("Smoke test passed")
