"""Streamlit interface for the weekly meal planner.

Run from the repository root:
    pip install -r requirements.txt
    streamlit run src/app.py

Two tabs:
  - Weekly plan: 7 meals for your diet, CO2e per meal and per week, replace meals and compare.
    Default matching "AI + team check": the LLM answers (precomputed, notebook 09) are shown next
    to the team check, so you can see what the AI got right and what the team corrected.
  - Analyse your recipe: write your own recipe (EN/ES/CA) and get its CO2e. If a local Ollama model
    is running, the AI matches new ingredients live; otherwise you choose from the closest foods.
"""
import importlib.util

import pandas as pd
import streamlit as st

from co2e import (SOURCE_CONFIRMED, SOURCE_CORRECTED, SOURCE_TEAM, ai_checked_available, get_matcher,
                  ingredient_co2e, load_recipes, recipe_co2e)
from own_recipe import RecipeAnalyser, apply_swaps, parse_recipe, parse_servings, suggest_swaps
from planner import ALLOWED_TAGS, DAYS, alternatives, plan_week, swap_meal, swap_savings, weekly_total

MATCHER_LABELS = {
    "ai_checked": "AI + team check (recommended)",
    "labels": "Team-verified matches only",
    "rapidfuzz": "RapidFuzz baseline (automatic, not verified)",
    "ai": "Embedding AI (experimental, not verified)",
}
VERIFIED = {"ai_checked", "labels"}
EXAMPLE_RECIPE = """Lasaña de la abuela (4 personas)
400 g de ternera picada
12 placas de lasaña
2 cebollas
400 g tomàquet
100 g formatge parmesà
2 cucharadas de aceite de oliva
150 g quinoa"""


def ai_available() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ("faiss", "sentence_transformers"))


@st.cache_resource(show_spinner=False)
def load_data(matcher_name: str):
    """Recipes with kg CO2e per serving, and the ingredient-level matches behind them."""
    recipes, ingredients = load_recipes()
    ingredient_results = ingredient_co2e(ingredients, get_matcher(matcher_name))
    return recipe_co2e(recipes, ingredient_results), ingredient_results


@st.cache_resource(show_spinner=False)
def live_ai():
    """LLM matcher on a local Ollama model, or None when Ollama is not running."""
    from llm_matching import LLMMatcher, ollama_available
    if not ollama_available():
        return None
    return LLMMatcher(provider="ollama", verify=True, fewshot=True, threshold=0.3)


@st.cache_resource(show_spinner=False)
def recipe_analyser(use_live_ai: bool):
    return RecipeAnalyser(live_ai=live_ai() if use_live_ai else None)


def fmt_kg(value) -> str:
    return "Not available" if pd.isna(value) else f"{value:.2f} kg CO₂e"


def all_complete(plan: pd.DataFrame) -> bool:
    return bool(plan["complete"].all())


st.set_page_config(page_title="Food Sustainability Meal Planner", page_icon="🥗", layout="wide")

st.title("🥗 Your Weekly Meal Planner")
st.write(
    "Create a weekly meal plan that matches your diet, explore lower-carbon alternatives "
    "and understand the estimated carbon footprint of your meals — or analyse a recipe of your own."
)

# ---------------------------------------------------------------- SIDEBAR: PREFERENCES
st.sidebar.header("Your preferences")

diet = st.sidebar.selectbox("Dietary preference", options=list(ALLOWED_TAGS), format_func=str.capitalize)

goal = st.sidebar.selectbox(
    "Planning goal",
    options=["low_carbon", "variety"],
    format_func=lambda x: {"variety": "More variety", "low_carbon": "Lower carbon footprint"}[x],
)

people = int(st.sidebar.number_input("Number of people", min_value=1, max_value=10, value=1, step=1))

matcher_options = (["ai_checked"] if ai_checked_available() else []) + ["labels", "rapidfuzz"] \
    + (["ai"] if ai_available() else [])
matcher_name = st.sidebar.selectbox(
    "Ingredient matching method", options=matcher_options, format_func=MATCHER_LABELS.get
)
if "ai_checked" not in matcher_options:
    st.sidebar.caption("AI + team check is hidden: run notebook 09 to create data/ingredient_matches_llm.csv.")
if matcher_name not in VERIFIED:
    st.sidebar.warning(
        "Automatic matching makes mistakes (see the evaluation in the dev logs). "
        "Use it to compare methods, not to trust the CO₂e numbers."
    )

generate = st.sidebar.button("Generate my weekly plan", type="primary", width="stretch")

tab_plan, tab_recipe = st.tabs(["📅 Weekly plan", "🔍 Analyse your recipe"])

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
        tab_plan.error(f"Could not generate the plan: {error}")


def render_ai_summary(ingredient_results: pd.DataFrame) -> None:
    """What the AI did for the recipe ingredients (AI + team check only)."""
    ing = ingredient_results.drop_duplicates("ingredient_clean")
    counts = ing["source"].value_counts()
    confirmed, corrected, unsure = (int(counts.get(s, 0)) for s in (SOURCE_CONFIRMED, SOURCE_CORRECTED, SOURCE_TEAM))
    with st.expander(f"🤖 What did the AI do? It matched {confirmed} of {len(ing)} ingredients exactly "
                     f"as the team; the team corrected {corrected} and checked {unsure} where the AI was not sure."):
        st.write(
            "An LLM (Qwen 2.5 14B + a verification step, notebook 08/09) proposed an Agribalyse food for each "
            "ingredient. The team checked every proposal: the CO₂e uses the team-checked food, so the numbers "
            "are reliable, and you can see where the AI was right."
        )
        table = ing[["ingredient_clean", "source", "ai_suggestion", "agribalyse_name"]].rename(columns={
            "ingredient_clean": "Ingredient", "source": "Result", "ai_suggestion": "AI proposed",
            "agribalyse_name": "Food used for CO₂e"}).sort_values("Result")
        st.dataframe(table.fillna("—"), hide_index=True, width="stretch")


def render_plan() -> None:
    if "plan" not in st.session_state:
        st.info("Choose your preferences in the sidebar and click **Generate my weekly plan** to get started.")
        return

    plan = st.session_state["plan"]
    original_plan = st.session_state["original_plan"]
    recipes = st.session_state["recipes"]
    ingredient_results = st.session_state["ingredient_results"]
    plan_diet = st.session_state["diet"]
    plan_matcher = st.session_state["matcher_name"]
    verified = plan_matcher in VERIFIED
    show_sources = ingredient_results["source"].notna().any()

    if (diet, matcher_name) != (plan_diet, plan_matcher):
        st.info("You changed the diet or matching method. Click **Generate my weekly plan** to apply it.")

    # ------------------------------------------------------------ WEEKLY SUMMARY
    st.subheader("Your 7-day meal plan")
    st.caption(f"Diet: {plan_diet.capitalize()} | Matching: {MATCHER_LABELS[plan_matcher]} | People: {people}")

    current_total = weekly_total(plan, people)
    saved, comparable = swap_savings(original_plan, plan, people)

    col1, col2, col3 = st.columns(3)
    col1.metric("Meals planned", len(plan))
    col2.metric("Weekly CO₂e" if all_complete(plan) else "Known weekly CO₂e", f"{current_total:.2f} kg")
    if comparable and abs(saved) < 0.005:
        col3.metric("Change vs original plan", "No change yet")
    elif comparable:
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
    if show_sources:
        render_ai_summary(ingredient_results)
    st.divider()

    # ------------------------------------------------------------ DAILY MEALS
    for _, meal in plan.iterrows():
        with st.expander(f"{meal['day']} — {meal['recipe_name']} · {fmt_kg(meal['kg_co2e_serving'])}"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Dietary category**  \n{str(meal['dietary_tag']).capitalize()}")
            c2.write(f"**Main protein**  \n{str(meal['main_protein']).capitalize()}")
            c3.write(f"**Estimated emissions per serving**  \n{fmt_kg(meal['kg_co2e_serving'])}")

            if not meal["complete"]:
                st.warning(f"Incomplete estimate. No confident match for: {meal['uncertain_ingredients']}")
            elif verified:
                st.success("All ingredients matched with team-checked Agribalyse foods.")
            else:
                st.info("All ingredients matched automatically (not verified). Check the table below.")

            rows = ingredient_results[ingredient_results["recipe_id"] == meal["recipe_id"]]
            table = pd.DataFrame({
                "Ingredient": rows["ingredient_clean"],
                "Grams (recipe)": rows["quantity_g"],
                "Agribalyse food used": rows["agribalyse_name"].where(~rows["uncertain"], "— uncertain —"),
                "kg CO₂e (recipe)": rows["kg_co2e"].round(3),
            })
            if show_sources:
                table["Source"] = rows["source"].values
            st.dataframe(table, hide_index=True, width="stretch")
            st.caption(f"Recipe for {int(meal['servings'])} servings; the meal estimate is per serving.")

    st.divider()

    # ------------------------------------------------------------ REPLACE A MEAL
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

    # ------------------------------------------------------------ IMPACT OF THE CHANGES
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


def render_own_recipe() -> None:
    st.subheader("Analyse your own recipe")
    st.write(
        "Write one ingredient per line, in English, Spanish or Catalan (for example `300 g merluza`, "
        "`1 kg patates`, `2 huevos` or `2 cucharadas de aceite`). We estimate its carbon footprint, "
        "compare it with the meals of the planner and show what to change to reduce it."
    )
    ai = live_ai()
    if ai is not None:
        st.caption(f"🤖 Live AI: **on** (local model `{ai.model_name}` via Ollama). New ingredients are matched "
                   "by the AI; if it is not sure, you choose.")
    else:
        st.caption("🤖 Live AI: **off**. Ingredients the team already checked are recognised automatically; "
                   "for new ones you choose from the closest Agribalyse foods. To turn the AI on, install "
                   "[Ollama](https://ollama.com) and run `ollama pull qwen2.5:7b`.")

    c1, c2 = st.columns([3, 1])
    name = c1.text_input("Recipe name", value="My recipe")
    text = st.text_area("Ingredients", value=EXAMPLE_RECIPE, height=200)
    servings = int(c2.number_input("Servings", min_value=1, max_value=20,
                                   value=parse_servings(text) or 2, step=1))

    parsed, errors = parse_recipe(text)
    if errors:
        st.warning("These lines were skipped (write a quantity first, e.g. `5 g sal`): " + "; ".join(errors))
    if parsed["estimated"].any():
        st.caption("Estimated weights (pieces or spoons; write grams to be exact): " + ", ".join(
            f"{r.ingredient} ≈ {r.quantity_g:.0f} g" for r in parsed[parsed["estimated"]].itertuples()))
    if parsed.empty:
        st.info("Add at least one ingredient with its weight.")
        return

    analyser = recipe_analyser(ai is not None)
    resolved = st.session_state.setdefault("resolved_cache", {})
    todo = [i for i in parsed["ingredient"].unique() if i not in resolved]
    if todo:
        with st.spinner(f"Matching {len(todo)} ingredient(s)..."):
            for ing in todo:
                resolved[ing] = analyser.resolve(ing)

    # Human in the loop: the user chooses the food for the ingredients nobody matched
    choices = {}
    missing = [i for i in parsed["ingredient"].unique() if resolved[i]["agribalyse_code"] is None]
    if missing:
        st.markdown("**Help us with these ingredients** — choose the closest food, or leave it out. "
                    "Your choice is remembered, so next time it is automatic:")
        for ing in missing:
            cands = analyser.candidates(ing, first=resolved[ing].get("candidate_codes"))
            opts = [None] + [c for c, _ in cands]
            names = dict(cands)
            choices[ing] = st.selectbox(
                f"“{ing}”", options=opts, key=f"pick_{ing}",
                format_func=lambda c: "— leave it out —" if c is None else names[c],
            )
            if choices[ing] and analyser.remembered.get(ing) != choices[ing]:
                analyser.remember(ing, choices[ing])
        st.caption("Tip: if the list does not fit, write the ingredient in English (e.g. `mushroom`).")

    result = analyser.co2e(parsed, choices, resolved)
    known = result["kg_co2e"].notna()
    total = float(result.loc[known, "kg_co2e"].sum())
    per_serving = total / servings

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total CO₂e" if known.all() else "Known CO₂e", f"{total:.2f} kg")
    m2.metric("Per serving", f"{per_serving:.2f} kg")
    recipes, _ = load_data("labels")
    complete = recipes[recipes["complete"]]
    median = float(complete["kg_co2e_serving"].median())
    if known.all():
        m3.metric("vs typical planner meal", f"{per_serving - median:+.2f} kg",
                  delta=f"{(per_serving / median - 1) * 100:+.0f}%", delta_color="inverse")
    else:                                              # a partial total would look lower than it is
        m3.metric("vs typical planner meal", "—", help="Not compared: some ingredients are left out.")
        st.warning("Some ingredients are left out, so this is a partial estimate and we do not compare it "
                   "with the planner: " + ", ".join(result.loc[~known, "ingredient"]))

    table = pd.DataFrame({
        "Ingredient": result["ingredient"],
        "Grams": result["quantity_g"],
        "Agribalyse food used": result["agribalyse_name"].fillna("— left out —"),
        "How it was matched": result["source"].fillna("—"),
        "kg CO₂e": result["kg_co2e"].round(3),
    })
    st.dataframe(table, hide_index=True, width="stretch")

    if known.any() and total > 0:
        top = result.loc[known].sort_values("kg_co2e", ascending=False).iloc[0]
        share = top["kg_co2e"] / total * 100
        of = "the footprint" if known.all() else "the known footprint"
        st.markdown(f"**Biggest contributor:** {top['ingredient']} ({share:.0f}% of {of} of {name}).")
        st.bar_chart(result.loc[known].set_index("ingredient")["kg_co2e"], horizontal=True,
                     x_label="kg CO₂e", y_label="")
        lowest = complete.sort_values("kg_co2e_serving").iloc[0]
        st.caption(f"For reference: the lowest-carbon meal in the planner is **{lowest['recipe_name']}** "
                   f"({lowest['kg_co2e_serving']:.2f} kg CO₂e per serving); the typical one is {median:.2f} kg.")
        render_swaps(result, total, servings, analyser.agb, complete=bool(known.all()))


def render_swaps(result: pd.DataFrame, total: float, servings: int, agb: pd.DataFrame,
                 complete: bool = True) -> None:
    """Lower-carbon swaps for the biggest emitters; tick them to see the new footprint."""
    st.markdown("#### 🌱 How to reduce it")
    swaps = suggest_swaps(result, agb)
    if not swaps:
        if complete:
            st.info("No high-impact ingredient (meat, fish, cheese, butter): this recipe is already low-carbon.")
        else:                                          # the missing ingredient could be the big emitter
            st.info("No high-impact ingredient among the ones we could match. Some ingredients are left out, "
                    "so we cannot say this recipe is low-carbon: choose a food for them above.")
        return
    chosen, used = [], set()
    for k, s in enumerate(swaps):
        text = (f"Use **half the {s['ingredient']}** ({s['quantity_g']:.0f} g → {s['quantity_g'] / 2:.0f} g)"
                if s["swap_to"] == "half" else
                f"Swap **{s['ingredient']}** ({s['quantity_g']:.0f} g) for **{s['swap_to']}**")
        label = f"{text}: −{s['kg_saved']:.2f} kg CO₂e (−{s['pct_of_recipe']:.0%} of the recipe)"
        if st.checkbox(label, key=f"swap_{k}_{s['ingredient']}_{s['swap_to']}",
                       disabled=s["ingredient"] in used):
            chosen.append(s)
            used.add(s["ingredient"])                  # one swap per ingredient
    if chosen:
        new_total = float(apply_swaps(result, chosen, agb)["kg_co2e"].sum())
        st.success(f"With these changes: **{new_total / servings:.2f} kg CO₂e per serving** instead of "
                   f"{total / servings:.2f} (−{(1 - new_total / total):.0%}).")
    st.caption("Swaps keep the same weight (a simplification, not a nutrition rule). "
               "Your choices of food are saved in data/user_confirmations.csv and never used to score the AI.")


with tab_plan:
    render_plan()
with tab_recipe:
    render_own_recipe()
