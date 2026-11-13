
import streamlit as st
import pandas as pd

from co2e import get_matcher, ingredient_co2e, load_recipes, recipe_co2e
from planner import ALLOWED_TAGS, DAYS, alternatives, plan_week, swap_meal, weekly_total


st.set_page_config(
    page_title="Food Sustainability Meal Planner",
    page_icon="🥗",
    layout="wide"
)


@st.cache_resource
def load_data(matcher_name):
    recipes, ingredients = load_recipes()

    matcher = get_matcher(matcher_name)
    ingredient_results = ingredient_co2e(ingredients, matcher)
    recipes_with_co2e = recipe_co2e(recipes, ingredient_results)

    return recipes_with_co2e


def calculate_known_total(plan, people):
    return weekly_total(plan, people)


def all_meals_complete(plan):
    return bool(plan["complete"].all())


def display_emissions(value):
    if pd.isna(value):
        return "Not available"
    return f"{value:.2f} kg CO₂e"


st.title("🥗 Your Weekly Meal Planner")
st.write(
    "Create a weekly meal plan that matches your diet, "
    "explore lower-carbon alternatives and understand the "
    "estimated environmental impact of your meals."
)

st.divider()

# SIDEBAR: USER PREFERENCES

st.sidebar.header("Your preferences")

diet = st.sidebar.selectbox(
    "Dietary preference",
    options=list(ALLOWED_TAGS.keys()),
    format_func=lambda x: x.capitalize()
)

goal = st.sidebar.selectbox(
    "Planning goal",
    options=["variety", "low_carbon"],
    format_func=lambda x: {
        "variety": "More variety",
        "low_carbon": "Lower carbon footprint"
    }[x]
)

people = st.sidebar.number_input(
    "Number of people",
    min_value=1,
    max_value=10,
    value=1,
    step=1
)

matcher_name = st.sidebar.selectbox(
    "Ingredient matching method",
    options=["ai", "labels", "rapidfuzz"],
    format_func=lambda x: {
        "ai": "AI matching",
        "labels": "Manually reviewed matches",
        "rapidfuzz": "RapidFuzz baseline"
    }[x]
)

st.sidebar.caption(
    "AI matching requires the additional dependencies "
    "and model configuration installed by the project team."
)

generate = st.sidebar.button(
    "Generate my weekly plan",
    type="primary",
    use_container_width=True
)


# GENERATE A NEW WEEK

if generate:
    try:
        with st.spinner("Calculating ingredient emissions and creating your plan..."):
            recipes = load_data(matcher_name)

            new_plan = plan_week(
                recipes,
                diet,
                goal=goal,
                seed=42
            )

            st.session_state["plan"] = new_plan
            st.session_state["original_plan"] = new_plan.copy()
            st.session_state["recipes"] = recipes
            st.session_state["people"] = people
            st.session_state["diet"] = diet
            st.session_state["matcher_name"] = matcher_name

    except Exception as error:
        st.error(f"Could not generate the plan: {error}")


# DISPLAY THE PLAN

if "plan" in st.session_state:

    plan = st.session_state["plan"]
    original_plan = st.session_state["original_plan"]
    recipes = st.session_state["recipes"]

    # Keep the displayed total consistent with the generated plan.
    people = st.session_state["people"]

    st.subheader("Your 7-day meal plan")

    st.caption(
        f"Diet: {st.session_state['diet'].capitalize()} | "
        f"Matching method: {st.session_state['matcher_name']} | "
        f"People: {people}"
    )

    # WEEKLY SUMMARY

    current_total = calculate_known_total(plan, people)
    original_total = calculate_known_total(original_plan, people)

    col1, col2, col3 = st.columns(3)

    col1.metric("Meals planned", len(plan))

    if all_meals_complete(plan):
        col2.metric(
            "Weekly CO₂e",
            f"{current_total:.2f} kg"
        )
    else:
        col2.metric(
            "Known weekly CO₂e",
            f"{current_total:.2f} kg"
        )

    if all_meals_complete(plan) and all_meals_complete(original_plan):
        difference = original_total - current_total

        col3.metric(
            "Change from original plan",
            f"{difference:.2f} kg",
            delta=f"{difference:.2f} kg saved" if difference >= 0
            else f"{abs(difference):.2f} kg more",
            delta_color="normal"
        )
    else:
        col3.metric("Carbon savings", "Not calculated")

    if not all_meals_complete(plan):
        st.warning(
            "Some ingredient matches are uncertain. The displayed "
            "weekly figure only includes ingredients with a successful "
            "match, so it is a partial estimate, not the complete "
            "footprint of the meals. Carbon savings are not calculated "
            "for incomplete plans."
        )

    st.divider()

    # DAILY MEALS

    for index, meal in plan.iterrows():

        with st.expander(
            f"{meal['day']} — {meal['recipe_name']}",
            expanded=True
        ):

            col1, col2, col3 = st.columns(3)

            col1.write("**Dietary category**")
            col1.write(str(meal["dietary_tag"]).capitalize())

            col2.write("**Main protein**")
            col2.write(str(meal["main_protein"]).capitalize())

            col3.write("**Estimated emissions**")
            col3.write(display_emissions(meal["kg_co2e_serving"]))

            if meal["complete"]:
                st.success("All ingredient matches are available.")
            else:
                st.warning(
                    "This estimate is incomplete. The following "
                    "ingredients could not be matched confidently: "
                    + str(meal["uncertain_ingredients"])
                )

    st.divider()

    # REPLACE A MEAL

    st.subheader("🔄 Replace a meal")
    st.write(
        "Choose a day to explore alternative recipes. "
        "Alternatives shown here have complete ingredient matches "
        "and respect your dietary preference and protein variety."
    )

    selected_day = st.selectbox(
        "Which day would you like to change?",
        options=DAYS
    )

    available_options = alternatives(
        plan,
        recipes,
        st.session_state["diet"],
        selected_day
    )

    # Only offer complete alternatives so the comparison is meaningful.
    available_options = available_options[
        available_options["complete"] == True
    ]

    if len(available_options) == 0:

        st.info(
            "There are no fully matched alternative recipes available "
            "for this day. Try another day or check the ingredient data."
        )

    else:

        current_meal = plan[plan["day"] == selected_day].iloc[0]

        st.write(
            f"Current meal: **{current_meal['recipe_name']}** "
            f"({display_emissions(current_meal['kg_co2e_serving'])})"
        )

        recipe_choices = {}
        choice_labels = []

        for _, option in available_options.iterrows():
            label = (
                f"{option['recipe_name']} — "
                f"{option['kg_co2e_serving']:.2f} kg CO₂e"
            )
            recipe_choices[label] = option["recipe_id"]
            choice_labels.append(label)

        selected_recipe_label = st.selectbox(
            "Choose an alternative meal",
            options=choice_labels
        )

        if st.button("Replace meal", type="primary"):

            before_swap = calculate_known_total(plan, people)

            new_recipe_id = recipe_choices[selected_recipe_label]

            updated_plan = swap_meal(
                plan,
                recipes,
                st.session_state["diet"],
                selected_day,
                new_recipe_id
            )

            st.session_state["plan"] = updated_plan

            st.success(
                f"Your {selected_day} meal has been replaced!"
            )

            st.rerun()

    st.divider()

    # FINAL WEEKLY SUMMARY

    st.subheader("Your updated weekly impact")

    plan = st.session_state["plan"]

    if all_meals_complete(plan):

        updated_total = weekly_total(plan, people)

        st.metric(
            "Complete weekly estimate",
            f"{updated_total:.2f} kg CO₂e"
        )

        if all_meals_complete(original_plan):
            saved = original_total - updated_total

            if saved > 0:
                st.success(
                    f"Your changes reduced the estimated footprint "
                    f"by {saved:.2f} kg CO₂e."
                )
            elif saved < 0:
                st.info(
                    f"Your changes increased the estimated footprint "
                    f"by {abs(saved):.2f} kg CO₂e."
                )
            else:
                st.info("Your changes did not alter the weekly estimate.")

    else:
        known_total = weekly_total(plan, people)

        st.warning(
            f"Known emissions: {known_total:.2f} kg CO₂e. "
            "This is incomplete because some ingredients remain unmatched."
        )

else:

    st.info(
        "Choose your preferences in the sidebar and click "
        "'Generate my weekly plan' to get started."
    )



