"""Streamlit interface for the weekly meal planner.

Run from the repository root:
    pip install -r requirements.txt
    streamlit run src/app.py

The AI matcher is optional: it only appears in the menu when requirements-ai.txt is installed.
"""
import importlib.util

import pandas as pd
import streamlit as st

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e
from planner import ALLOWED_TAGS, DAYS, alternatives, plan_week, swap_meal, swap_savings, weekly_total

MATCHER_LABELS = {
    "labels": "Team-verified matches (recommended)",
    "rapidfuzz": "RapidFuzz baseline (automatic, not verified)",
    "ai": "AI matching (experimental, not verified)",
}


def ai_available() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("faiss", "sentence_transformers"))


@st.cache_resource(show_spinner=False)
def load_data(matcher_name: str):
    """Recipes with kg CO2e per serving, and the ingredient-level matches behind them."""
    recipes, ingredients = load_recipes()
    ingredient_results = ingredient_co2e(ingredients, get_matcher(matcher_name))
    return recipe_co2e(recipes, ingredient_results), ingredient_results


def fmt_kg(value) -> str:
    return "Not available" if pd.isna(value) else f"{value:.2f} kg CO₂e"


def all_complete(plan: pd.DataFrame) -> bool:
    return bool(plan["complete"].all())


st.set_page_config(page_title="Food Sustainability Meal Planner", page_icon="🥗", layout="wide")

st.title("🥗 Your Weekly Meal Planner")
st.write(
    "Create a weekly meal plan that matches your diet, explore lower-carbon alternatives "
    "and understand the estimated carbon footprint of your meals."
)
st.divider()

# ---------------------------------------------------------------- SIDEBAR: PREFERENCES
st.sidebar.header("Your preferences")

diet = st.sidebar.selectbox("Dietary preference", options=list(ALLOWED_TAGS), format_func=str.capitalize)

goal = st.sidebar.selectbox(
    "Planning goal",
    options=["low_carbon", "variety"],
    format_func=lambda x: {"variety": "More variety", "low_carbon": "Lower carbon footprint"}[x],
)

people = int(st.sidebar.number_input("Number of people", min_value=1, max_value=10, value=1, step=1))

matcher_options = ["labels", "rapidfuzz"] + (["ai"] if ai_available() else [])
matcher_name = st.sidebar.selectbox(
    "Ingredient matching method", options=matcher_options, format_func=MATCHER_LABELS.get
)
if "ai" not in matcher_options:
    st.sidebar.caption("AI matching is hidden: install `requirements-ai.txt` to enable it.")
if matcher_name != "labels":
    st.sidebar.warning(
        "Automatic matching makes mistakes (see the evaluation in the dev logs). "
        "Use it to compare methods, not to trust the CO₂e numbers."
    )

generate = st.sidebar.button("Generate my weekly plan", type="primary", width="stretch")

# ---------------------------------------------------------------- GENERATE A NEW WEEK
if generate:
    try:
        with st.spinner("Calculating ingredient emissions and creating your plan..."):
            recipes, ingredient_results = load_data(matcher_name)
            new_plan = plan_week(recipes, diet, goal=goal, seed=42)
        st.session_state.update(
            plan=new_plan,
            original_plan=new_plan.copy(),
            recipes=recipes,
            ingredient_results=ingredient_results,
            diet=diet,
            matcher_name=matcher_name,
        )
    except Exception as error:  # show the reason in the page instead of crashing
        st.error(f"Could not generate the plan: {error}")

if "plan" not in st.session_state:
    st.info("Choose your preferences in the sidebar and click **Generate my weekly plan** to get started.")
    st.stop()

plan = st.session_state["plan"]
original_plan = st.session_state["original_plan"]
recipes = st.session_state["recipes"]
ingredient_results = st.session_state["ingredient_results"]
plan_diet = st.session_state["diet"]
plan_matcher = st.session_state["matcher_name"]
verified = plan_matcher == "labels"

if (diet, matcher_name) != (plan_diet, plan_matcher):
    st.info("You changed the diet or matching method. Click **Generate my weekly plan** to apply it.")

# ---------------------------------------------------------------- WEEKLY SUMMARY
st.subheader("Your 7-day meal plan")
st.caption(f"Diet: {plan_diet.capitalize()} | Matching: {MATCHER_LABELS[plan_matcher]} | People: {people}")

current_total = weekly_total(plan, people)
saved, comparable = swap_savings(original_plan, plan, people)

col1, col2, col3 = st.columns(3)
col1.metric("Meals planned", len(plan))
col2.metric("Weekly CO₂e" if all_complete(plan) else "Known weekly CO₂e", f"{current_total:.2f} kg")
if comparable:
    # Negative = lower footprint than the original plan (shown in green)
    col3.metric("Change vs original plan", f"{-saved:+.2f} kg CO₂e",
                delta=f"{-saved:+.2f} kg", delta_color="inverse")
else:
    col3.metric("Change vs original plan", "Not calculated")

if not all_complete(plan):
    st.warning(
        "Some ingredients have no confident match, so the weekly figure only includes the matched "
        "ingredients. It is a partial estimate, not the complete footprint."
    )
if not verified:
    st.warning(
        "These numbers come from automatic matching, which is not verified by the team. "
        "Open a meal to see which Agribalyse food was used for each ingredient."
    )
st.divider()

# ---------------------------------------------------------------- DAILY MEALS
for _, meal in plan.iterrows():
    with st.expander(f"{meal['day']} — {meal['recipe_name']} · {fmt_kg(meal['kg_co2e_serving'])}"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Dietary category**  \n{str(meal['dietary_tag']).capitalize()}")
        c2.write(f"**Main protein**  \n{str(meal['main_protein']).capitalize()}")
        c3.write(f"**Estimated emissions per serving**  \n{fmt_kg(meal['kg_co2e_serving'])}")

        if not meal["complete"]:
            st.warning(f"Incomplete estimate. No confident match for: {meal['uncertain_ingredients']}")
        elif verified:
            st.success("All ingredients matched with team-verified Agribalyse foods.")
        else:
            st.info("All ingredients matched automatically (not verified). Check the table below.")

        rows = ingredient_results[ingredient_results["recipe_id"] == meal["recipe_id"]]
        table = pd.DataFrame({
            "Ingredient": rows["ingredient_clean"],
            "Grams (recipe)": rows["quantity_g"],
            "Agribalyse food used": rows["agribalyse_name"].where(~rows["uncertain"], "— uncertain —"),
            "kg CO₂e (recipe)": rows["kg_co2e"].round(3),
        })
        st.dataframe(table, hide_index=True, width="stretch")
        st.caption(f"Recipe for {int(meal['servings'])} servings; the meal estimate is per serving.")

st.divider()

# ---------------------------------------------------------------- REPLACE A MEAL
st.subheader("🔄 Replace a meal")
st.write(
    "Alternatives respect your diet and do not repeat a main protein. Only recipes with a "
    "complete estimate are offered, so the comparison is meaningful."
)

selected_day = st.selectbox("Which day would you like to change?", options=DAYS)
current_meal = plan[plan["day"] == selected_day].iloc[0]
options = alternatives(plan, recipes, plan_diet, selected_day)
options = options[options["complete"]]

st.write(f"Current meal: **{current_meal['recipe_name']}** ({fmt_kg(current_meal['kg_co2e_serving'])})")

if options.empty:
    st.info("No alternative with a complete estimate is available for this day. Try another day.")
else:
    labels = {
        f"{o['recipe_name']} — {o['kg_co2e_serving']:.2f} kg CO₂e "
        f"({o['kg_co2e_serving'] - current_meal['kg_co2e_serving']:+.2f})": o["recipe_id"]
        for _, o in options.iterrows()
    }
    choice = st.selectbox("Choose an alternative meal (lowest CO₂e first)", options=list(labels))
    if st.button("Replace meal", type="primary"):
        st.session_state["plan"] = swap_meal(plan, recipes, plan_diet, selected_day, labels[choice])
        st.rerun()

if st.button("Reset to the original plan"):
    st.session_state["plan"] = original_plan.copy()
    st.rerun()

st.divider()

# ---------------------------------------------------------------- IMPACT OF THE CHANGES
st.subheader("Impact of your changes")
changed_days = (plan.set_index("day")["recipe_id"] != original_plan.set_index("day")["recipe_id"]).sum()

if changed_days == 0:
    st.info("You have not replaced any meal yet.")
elif not comparable:
    st.warning("Saving not calculated: a replaced meal has an incomplete estimate.")
elif saved > 0:
    st.success(
        f"Your {changed_days} change(s) reduce the estimated footprint by **{saved:.2f} kg CO₂e** "
        f"per week for {people} person(s)."
    )
elif saved < 0:
    st.info(f"Your {changed_days} change(s) increase the estimated footprint by {abs(saved):.2f} kg CO₂e.")
else:
    st.info("Your changes do not alter the weekly estimate.")

st.caption(
    "Estimates use Agribalyse 3.2 (kg CO₂e per kg of food) and one meal per day. "
    "A lower estimate is not proof of a real reduction in emissions."
)
