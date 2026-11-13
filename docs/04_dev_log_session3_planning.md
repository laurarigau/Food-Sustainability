### Session 3: Planning to Demo Day — 11 November 2026

**Objective:** Identify bottlenecks and dependencies, define the scope for 2 December, assess risks, and establish milestones and team working rules.

**Documentation note (updated 13 November):** This log combines the confirmed implementation progress reported by us with proposed planning decisions. The original classroom photos, token allocations, red-team feedback, and external smoke-test observations were not available when this update was written. Proposed items are explicitly labelled and should not be interpreted as activities or results verified in class.

---

#### Work 1: Hill chart and dependency wall

The following is a **current status assessment**, not a reconstruction of the physical hill chart created in class.

| Component | Current position | Dependencies / status |
|---|---|---|
| Data (Open Food Facts + Agribalyse) | Downhill | Agribalyse data and 100 reviewed ingredient labels are available; the exact integration with OFF should be checked in the repository. |
| Recipes | Downhill | 25 recipes with ingredient quantities in grams are available in `data/`. |
| Ingredient matching (AI) | Uphill | The first AI version scores 11/50 against 7/50 for RapidFuzz; a second version still needs evaluation. |
| CO2e calculation | Downhill | Implemented in `src/`; depends on the ingredient-to-impact mapping. |
| Weekly planner | Downhill | Implemented in `src/`; respects dietary constraints and avoids repeating protein sources, according to the current team update. |
| Interface (Streamlit) | Uphill | Not yet implemented; needs stable outputs from the existing planner and CO2e code. |

**Main bottleneck:** Ingredient matching remains the main *quality and evaluation* uncertainty. However, it no longer blocks the existing demo because the team can use its manually reviewed labels. Streamlit integration is the remaining user-facing delivery dependency.

**Mitigation (proposal):** Keep the verified-label mapping as a clearly disclosed fallback, use a stable output schema between matching, footprint calculation and the planner, and develop the interface independently of the second AI experiment.

**Original hill-chart photo:** Not available; attach if recovered. No classroom positions are claimed here.

#### Work 2: Press release (draft for 2 December)

**Headline:** Households can plan a week of meals that fits their dietary preferences and understand the estimated carbon footprint of each meal.

**Problem:** It is difficult for people to compare the environmental impact of everyday meals. Ingredient-level footprint data is not straightforward to interpret or combine into a practical weekly plan.

**Solution:** Food Sustainability uses a curated collection of 25 recipes, ingredient quantities in grams and Agribalyse impact data to estimate meal-level CO2e. The existing Python planner creates a weekly menu under dietary and protein-variety constraints. A working demo can replace a meal and show the change in estimated emissions. A Streamlit interface is planned for the final presentation.

**Illustrative user quote (not collected from an actual user):** “I want to understand which meal swaps could reduce my weekly food footprint without having to calculate everything myself.”

**FAQs**

1. **Where does the data come from?** The project uses Agribalyse impact data, 25 curated recipes with gram quantities, and 100 reviewed ingredient labels. Open Food Facts is part of the original project data context; the exact data flow should be verified before the presentation.
2. **How accurate is the AI?** On the team's 50-item evaluation set, RapidFuzz matched 7/50 correctly (14%) and the first AI version matched 11/50 (22%), an improvement of 8 percentage points. This is below the team's 10-point improvement threshold. The second AI version has not yet been evaluated, so no additional accuracy is claimed.
3. **What is manual or simplified?** Recipes and reviewed ingredient labels are curated manually. The weekly planner uses explicit rules rather than an AI recommender. The demo can use the reviewed labels when AI matching does not meet the agreed threshold. This limitation will be disclosed.

**Original A3 press-release photo:** Not available; attach if recovered. This text is a revised draft, not a transcription of the in-class poster.

#### Work 3: Buy a feature — proposed final scope

**Important:** The table below is a **proposed MoSCoW prioritisation**, not the outcome of the in-class token exercise. Token prices and votes are unknown.

| Feature | Proposed priority | Definition of done | Classroom tokens |
|---|---|---|---|
| Weekly menu generation | Must | A seven-day plan is generated from available recipes and respects the implemented dietary and protein-variety rules. | Not recorded |
| Meal and weekly CO2e estimates | Must | The demo calculates and displays estimates from ingredient quantities and mapped Agribalyse values. | Not recorded |
| Meal swap and emissions comparison | Must | Replacing one meal displays the estimated change in CO2e. | Not recorded |
| Streamlit interface | Must | A user can run the main demo path without editing Python source code. | Not recorded |
| Second AI matcher evaluation | Should | Results are reported on the same fixed 50-item test set and compared with RapidFuzz. | Not recorded |
| Confidence / unmatched-ingredient disclosure | Should | Unsupported or uncertain mappings are explicitly identified rather than silently treated as verified. | Not recorded |
| Grocery list | Won't for demo | Deferred beyond 2 December. | Not recorded |
| Price optimisation | Won't for demo | Deferred beyond 2 December. | Not recorded |
| Embedding-based recipe recommendation | Won't for demo | Deferred beyond 2 December; the existing rule-based planner remains. | Not recorded |

**Proposed cut list:** Grocery-list generation, price optimisation and embedding-based recipe recommendation. The aim is to protect the end-to-end demo from scope growth.

**Proposed spike:** Evaluate the second AI ingredient matcher in notebook 05 on the existing 50-item test set by 24 November. **Success criterion:** at least 12/50 correct, equivalent to a gain of at least 10 percentage points over RapidFuzz's 7/50. **If unsuccessful:** keep the reviewed-label fallback for the demo and document the unsuccessful experiment.

**Original buy-a-feature cards and votes:** Not available. Do not report invented prices, token totals or classroom decisions.

#### Work 4: What went wrong? — learning from the case studies

Session 3 discussed two examples of integration and release failures: Healthcare.gov (2013), where separately developed parts were integrated too late, and Knight Capital (2012), where a release inconsistency activated old code. The relevant lesson for this project is to test the complete demo path and review changes before the final presentation. These are class examples, not incidents that occurred in Food Sustainability.

#### Work 5: Pre-mortem — proposed risk assessment

The following risks are a **new team planning proposal**, not a record of the missing red-team post-its. Likelihood and impact are qualitative estimates.

| Risk | Likelihood | Impact | Fallback | Proposed decision rule |
|---|---|---|---|---|
| AI ingredient matching fails to reach the agreed improvement threshold | High | Medium | Use the 100 reviewed labels for the supported demo ingredients and disclose the limitation. | If notebook 05 scores below 12/50 on the fixed test set by 24 Nov, stop further matcher development for the demo and use the reviewed-label path. |
| Streamlit integration is incomplete or unstable | Medium | High | Run the existing `python src/run_demo.py` command-line demonstration. | If the full interface flow is not working by the 27 Nov code freeze, use the tested CLI demo for the presentation. |
| Missing or incorrect ingredient mappings lead to misleading CO2e outputs | Medium | High | Restrict the demonstration to checked recipes/ingredients and label estimates as such. | Before code freeze, manually verify the ingredient mappings and outputs used in the final demonstration; remove or flag any unverified cases. |

**Red team / classroom likelihood-impact grid:** Not available. The table above should be reviewed by the team before being treated as an agreed risk register.

#### Work 6: Milestones and team rules

**Proposed milestones (dates and owners require team confirmation):**

| Date | Milestone | Done when | Owner |
|---|---|---|---|
| 13 Nov | Existing working skeleton and data checkpoint | The 25 recipes, 100 reviewed labels, CO2e code, weekly planner, demo script and smoke-test script are present in the repository, as reported by the team. | Team — existing work |
| 18 Nov | Documentation and local reproducibility | `docs/04` is updated; a teammate installs dependencies and runs the CLI demo using the README. | To assign |
| 24 Nov | AI decision | Notebook 05 is evaluated on the same fixed 50 examples; the score, comparison and keep/stop decision are logged. | To assign |
| 27 Nov | Code freeze | Streamlit demo path works end to end, or the documented CLI fallback is selected; only bug fixes follow. | To assign |
| 29 Nov | Rehearsal | Someone outside the development team attempts the demo from the README; blockers and fixes are logged. | To assign |
| 2 Dec | Demo day | Present the working main loop, state which components are manual or rule-based, and explain the AI benchmark decision. | Whole team |

**Proposed team rules (not yet confirmed as classroom selections):**

| Area | Proposed rule |
|---|---|
| Branches | One short branch per task, merged within 1–2 days. |
| Review | Another team member reviews each pull request before merging. |
| Integration | Integrate into `main` at least twice a week. |
| Testing | Run the critical-path smoke test before every merge. |

#### Work 7: Smoke test swap

**Internal smoke-test status:** The team reports that a smoke test exists in `tests/`, and that the README contains setup and execution instructions. This does **not** establish that the test has passed on another machine or that another team has completed the classroom swap.

**External team that tested the repository:** Not recorded.

**External test outcome:** Not recorded. Do not mark as passed or failed without evidence.

| Check / potential blocker | Next action | Owner | Due |
|---|---|---|---|
| Install dependencies from `requirements.txt` | Have another person perform a clean installation and record the result. | To assign | Before 29 Nov |
| Run `python src/run_demo.py` | Verify the weekly menu, meal replacement and CO2e comparison without developer assistance. | To assign | Before 29 Nov |
| Run the test script in `tests/` | Record the exact command, pass/fail status and any errors. | To assign | Before 27 Nov |
| Run the Streamlit demo | Test the same critical path once the interface is implemented. | To assign | Before 29 Nov |

**Classroom smoke-test feedback / fix list:** Not available. Replace this note only if the original evidence is recovered or a new external test is actually performed.

---

#### Decisions and rationale

- **Fixed deadline, variable scope:** Prioritise a reliable end-to-end demonstration for 2 December rather than adding untested features.
- **Preserve a working fallback:** The reviewed-label mapping supports the existing demo even if AI matching does not meet the success threshold.
- **Evaluate AI transparently:** The first version improves accuracy from 14% to 22% on 50 test items, but misses the agreed 10-percentage-point improvement threshold. Evaluate the second version before deciding whether to integrate it.
- **Separate matching from planning:** Ingredient matching is the experimental AI component; menu generation uses explicit rules. Avoid presenting rule-based logic as AI.
- **Document uncertainty:** Report the evaluation set, limitations, manual curation, and any unsupported mappings rather than claiming broader accuracy or coverage.

#### Next steps

1. Execute notebook 05 in Colab, record the second AI version's score on the fixed test set and apply the agreed decision rule.
2. Validate that the README and existing CLI demo work in a clean environment.
3. Build the smallest Streamlit interface around the already working planner, footprint calculation and meal-swap comparison.
4. Confirm owners and dates, complete an independent smoke test, and record the actual outcome.
5. Rehearse the final demo and prepare one slide explaining the system, benchmark, risks and fallback.

**Evidence currently available:** Repository files and the team's reported implementation status; benchmark results of 7/50 for RapidFuzz and 11/50 for AI version 1. **Evidence not available:** Original hill-chart and A3 photographs, buy-a-feature token records, red-team post-its, and external smoke-test feedback.
