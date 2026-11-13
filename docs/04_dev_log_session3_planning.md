# Development Log 04 — Session 3: Planning and Risk Management

**Project:** Food Sustainability  
**Session:** 3 (11 November 2026)  
**Log updated:** 13 November 2026  
**Final demonstration:** 2 December 2026

> **Evidence note:** This log reconstructs the Session 3 exercises using the team's reported project progress. It is **not** a record of unverified classroom votes, photos, external feedback or completed tests. Proposed decisions, deadlines and responsibilities require team confirmation.

## Project status and evidence

The team reports that the repository contains 25 recipes with ingredients in grams, Agribalyse data, 100 reviewed ingredient labels, a CO₂e calculator, a weekly planner that respects supported dietary constraints and avoids repeating protein sources, a meal-swap demo, a README and an automated smoke test. The Streamlit interface remains to be built. These statements are based on the team's progress update and have not been independently verified in this log.

On the fixed set of 50 test ingredients, RapidFuzz matched **7/50 (14%)** and the first AI version matched **11/50 (22%)**. The improvement is **8 percentage points**, below the team's required **10 percentage points**. The minimum passing result is therefore **12/50 (24%)**. The second AI version in notebook 05 is awaiting evaluation.

## Work 1 — Hill Chart and Dependency Wall

The hill chart represents **technical uncertainty**, not percentage of work completed. *Uphill* means we still need to discover whether or how something will work; *downhill* means the approach is understood and mainly needs execution.

| Component | Hill position | Rationale |
|---|---|---|
| AI ingredient matching | Uphill | First AI version misses the improvement threshold; notebook 05 still needs evaluation. |
| Recipe and Agribalyse data preparation | Downhill | 25 recipes and 100 reviewed labels are reported as available. |
| CO₂e calculator | Downhill | Core calculation code is reported as implemented. |
| Weekly meal planner | Downhill | Diet constraints and protein variety are reported as implemented. |
| Streamlit interface | Early downhill (proposed) | Core user flow is defined, but implementation and integration remain pending. |

**Dependency wall:** Recipe and Agribalyse data → ingredient mapping (AI or reviewed-label fallback) → CO₂e calculation; recipe data and constraints → weekly planner; planner and CO₂e outputs → meal swap and savings → Streamlit presentation.

**Main bottleneck (red dot):** AI ingredient matching and its evaluation. The operational demo can use reviewed labels if necessary, but this fallback must not be presented as successful AI performance.

**Evidence:** This is a reconstructed hill chart and dependency wall. The original classroom post-it photograph is unavailable; attach an authentic photograph if the team has one.

## Work 2 — Press Release

**Imagined publication date: 2 December 2026**

### Food Sustainability helps users plan lower-carbon weekly meals

**Problem.** People who want to eat more sustainably often lack accessible information about the environmental impact of individual meals. Comparing ingredients and building a varied weekly plan takes time.

**Solution.** Food Sustainability is designed to combine recipes with Agribalyse environmental-impact data. The system plans meals within supported dietary constraints, avoids repeating protein sources and estimates meal-related CO₂e. A user can compare a meal with an alternative and view the estimated emissions saved.

**Illustrative user quote (hypothetical, not actual user feedback):** “I want to eat more sustainably without calculating the environmental impact of every meal myself.”

### Frequently asked questions

**1. Where does the environmental data come from?**  
The project uses Agribalyse data and a curated set of 25 recipes with ingredient quantities in grams. Estimates depend on the ingredient mappings and data assumptions.

**2. How accurate is the AI?**  
On the fixed 50-ingredient test, the first AI version matched 11 items correctly, compared with 7 for RapidFuzz. The improved version has not yet been evaluated. We will report the measured result rather than claim accuracy we have not demonstrated.

**3. What is unfinished or simulated?**  
The Streamlit interface is not yet complete. The press-release user quote is hypothetical. If AI matching fails the predefined benchmark, the final demo will use reviewed ingredient mappings and disclose that choice.

**Evidence:** This is a drafted press release, not an original photographed A3 classroom poster. Attach the authentic poster photograph if available.

## Work 3 — Buy a Feature

The following is a **proposed prioritization**, not the result of the classroom token allocation. Feature prices are planning estimates; no votes or investments by other teams are claimed.

| Feature | Proposed price | Priority | Done when |
|---|---:|---|---|
| Streamlit interface | 3 tokens | Must | A user can generate and view a weekly meal plan. |
| CO₂e savings visualization | 2 tokens | Must | A user can replace a meal and view estimated CO₂e savings. |
| Improved AI ingredient matching | 3 tokens | Should | Notebook 05 is evaluated on the same 50 items and achieves at least 12/50 correct matches to pass the stated threshold. |
| Dietary preferences | 2 tokens | Should | The interface correctly exposes the constraints already supported by the planner. |
| Advanced analytics dashboard | 3 tokens | Won't for demo | Excluded from the 2 December scope. |

**Proposed 10-token scope:** Streamlit (3) + savings visualization (2) + AI evaluation/improvement (3) + dietary preferences (2) = **10 tokens**. This is an internal planning allocation, not classroom spending.

**Time-boxed spike:** Run notebook 05 on the fixed 50-item set, record exact matches and errors, and decide whether the AI meets the threshold. The team must agree on the time-box and owner.

**Cut list:** Advanced analytics dashboard; additional recipe categories beyond the current dataset; other features that do not support the critical demo path.

**Missing classroom evidence:** Feature-card photograph, other teams' token allocations and final classroom voting outcomes.

## Work 4 — What Went Wrong? / Failure Lessons

The planning exercise emphasizes failure modes that can undermine an otherwise promising demo: late integration, undocumented assumptions, unreliable deployment steps and insufficient end-to-end testing.

**Application to our project:** Working scripts in isolation do not prove that a new user can reproduce the complete flow. We should integrate early, keep the README executable, test from a clean environment and retain a simple terminal demo as a backup.

**Evidence note:** We do not have the team's original classroom discussion notes, so these are proposed project-specific lessons rather than a transcript of the exercise.

## Work 5 — Pre-mortem

**Scenario:** It is 2 December and the demonstration has failed. What most likely caused the failure?

| Risk | Likelihood (proposed) | Impact (proposed) | Mitigation / fallback |
|---|---|---|---|
| AI ingredient matching misses benchmark | High | High | Evaluate notebook 05 promptly; use reviewed mappings in demo if needed, and disclose limitations. |
| Streamlit integration fails | Medium | High | Test the end-to-end flow early; retain `python src/run_demo.py` as backup. |
| Wrong ingredient mappings distort CO₂e estimates | Medium | High | Restrict demo to reviewed mappings and document limitations. |

### Decision rule for the highest risk

**Metric:** Correct matches out of the **same 50 test ingredients**.  
**Baseline:** RapidFuzz 7/50.  
**Passing threshold:** AI ≥12/50 (at least +10 percentage points).  
**Proposed decision date:** 20 November 2026; team confirmation required.

- **Continue:** AI reaches at least 12/50; document the evaluation and integrate the supported AI use case.
- **Revise:** Performance improves but misses the target; inspect errors and consider a narrower, explicitly labeled AI experiment.
- **Stop for final demo:** The threshold is not reached by the agreed cutoff; use reviewed mappings for the operational demo and report the AI experiment honestly.

**Evidence:** Original red-team feedback and classroom likelihood/impact voting are unavailable. This is a reconstructed assessment.

## Work 6 — Milestones and Team Rules

### Proposed milestones

| Date | Milestone | Done when | Owner |
|---|---|---|---|
| 16 Nov | AI evaluation | Notebook 05 runs on the fixed test set and results are logged. | To assign |
| 20 Nov | Streamlit MVP | Users can generate and view a weekly plan. | To assign |
| 24 Nov | End-to-end integration | Meal swap and CO₂e savings work through Streamlit. | To assign |
| 26 Nov | External smoke test | Another team attempts to run the demo using only the README; blockers are logged. | To assign |
| 29 Nov | Code freeze | No new features; only critical fixes. | Whole team |
| 1 Dec | Rehearsal | Full demo and terminal backup are tested. | Whole team |
| 2 Dec | Final demonstration | Demo runs and repository/logs are up to date. | Whole team |

These dates and assignments are **proposals**, not confirmed commitments.

### Proposed team rules

1. **Branches:** One short-lived branch per task; aim to merge within 1–2 days.
2. **Review:** At least one teammate reviews each pull request.
3. **Integration:** Merge small changes regularly; aim to update `main` at least twice a week.
4. **Testing:** Run the critical-path smoke test before merging changes that affect the demo.
5. **Scope:** After code freeze, accept only fixes essential to a reliable demonstration.

**Critical path:** Recipe data → ingredient mapping → CO₂e calculation and weekly planning → meal swap → savings display.

## Work 7 — Smoke Test Swap

**Objective:** Confirm that a person outside the team can clone and run the project from the README alone.

### Instructions for the external team

1. Clone the repository.
2. Follow the README's environment setup instructions.
3. Install dependencies: `pip install -r requirements.txt`.
4. Run the terminal demo: `python src/run_demo.py`.
5. Verify that the demo produces a meal replacement and estimated CO₂e savings.
6. Record blockers, unclear instructions and the exact error messages, without receiving verbal guidance.

### Evidence and results

| Check | Current status |
|---|---|
| README instructions | Reported as present; not independently verified here |
| Terminal demo | Reported as implemented; not independently verified here |
| Automated test in `tests/` | Reported as present; not equivalent to external validation |
| Another team's independent run | **Not verified / pending** |
| Actual blockers and fixes | **Not available; do not invent** |

### Potential fix list (not observed failures)

| Potential blocker | Action | Owner |
|---|---|---|
| Missing package | Update dependency list | To assign |
| Unclear setup step | Clarify README | To assign |
| Relative file-path failure | Test from repository root and fix paths | To assign |
| Demo exception | Reproduce, fix and rerun | To assign |

**Definition of done:** An external tester can complete the critical demo path using only repository instructions; actual blockers and their resolutions are documented.

## Final scope and disclosure checklist

- [ ] Run notebook 05 and report its exact result on the fixed 50-item benchmark.
- [ ] Confirm final AI-versus-reviewed-mapping decision.
- [ ] Implement and integrate Streamlit or document the terminal-only fallback.
- [ ] Assign milestone owners and confirm dates.
- [ ] Obtain actual external smoke-test feedback and log fixes.
- [ ] Attach original classroom photographs only if available; otherwise retain reconstruction labels.
- [ ] Ensure each team member contributes and repository history reflects actual work.
- [ ] Prepare one final slide summarizing demo, AI evidence, risks and scope decisions.
- [ ] Rehearse the complete demo before 2 December.

**Integrity statement:** Proposed feature prices, risk ratings, dates, team rules and example language are clearly marked as proposals. No classroom vote, external test, photo, AI result or completed integration has been fabricated.
