# Review Status Availability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the persistent sidebar report review/export availability without claiming that human review is complete.

**Architecture:** Keep the existing `has_analysis` state derivation and sidebar rendering helper. Change only the analyzed-state label and its Streamlit AppTest contracts; no new state or core-engine behavior is introduced.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- The analyzed-state label is exactly `Available — Review evidence and export`.
- The label remains plain text because no stable deep Summary anchor is verified.
- Do not change final acceptance, criterion resolution, gates, schemas, exports, persistence, navigation, or release identity.
- Controlled demo and browser checks are product evidence only, never external PR or runtime evidence.
- Do not introduce paid APIs, LLMs, billing, forks, organizations, private repositories, synthetic validation, or untrusted-code execution.

---

### Task 1: Honest analyzed-state sidebar language

**Files:**
- Modify: `tests/apps/test_streamlit_app.py:562-569`
- Modify: `tests/apps/test_streamlit_app.py:792-798`
- Modify: `apps/web/app.py:1223-1226`
- Verify: `docs/superpowers/specs/2026-07-14-review-status-availability-design.md`

**Interfaces:**
- Consumes: existing `has_analysis: bool` and `_render_sidebar_step(text: str, anchor: str | None = None) -> None`.
- Produces: exact plain sidebar text `Available — Review evidence and export` whenever analysis exists.

- [ ] **Step 1: Change the regression contracts first**

Update `test_sidebar_reports_analysis_and_review_availability` to require the new label and explicitly reject the old completion claim:

```python
    assert "Complete — Analysis generated" in sidebar_text
    assert "Available — Review evidence and export" in sidebar_text
    assert "Complete — Review and export available" not in sidebar_text
```

Update the final analyzed-state list in
`test_sidebar_step_navigation_tracks_available_workflow_sections` so its last item is:

```python
        "Available — Review evidence and export",
```

- [ ] **Step 2: Verify RED**

Run:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pytest \
  tests/apps/test_streamlit_app.py::test_sidebar_reports_analysis_and_review_availability \
  tests/apps/test_streamlit_app.py::test_sidebar_step_navigation_tracks_available_workflow_sections -q
```

Expected: both tests fail because the current sidebar still renders
`Complete — Review and export available`.

- [ ] **Step 3: Implement the minimal label change**

Replace only the analyzed review/export label in `apps/web/app.py`:

```python
    if has_analysis:
        _render_sidebar_step("Available — Review evidence and export")
    else:
        _render_sidebar_step("Locked — Review and export")
```

- [ ] **Step 4: Verify GREEN and focused quality**

Run the two focused tests again, then:

```bash
"/Users/yjian070/Documents/New project 2/.venv/bin/ruff" check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

Expected: two tests pass, Ruff passes, and the diff is clean.

- [ ] **Step 5: Run complete product verification**

Run Ruff over the repository, complete offline pytest, the deterministic benchmark,
and a loopback Streamlit health check. Require 676 passing tests, one intentional
live skip, 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False
Ready, zero false blockers, exact health `ok`, and no traceback.

- [ ] **Step 6: Verify the rendered state**

Launch the committed branch on loopback, load the controlled demo, confirm criteria,
run analysis, and capture the sidebar alongside unresolved evidence. Require the new
`Available` label and absence of the old `Complete` label. Do not submit runtime
evidence, criterion decisions, or final acceptance.

- [ ] **Step 7: Commit and integrate**

Stage exactly the app, AppTest, design, and plan. Commit with:

```bash
git commit -m "Clarify review availability status"
```

Push `codex/review-status-availability`, open one ready protected PR, require both
`verify` checks plus CodeQL, merge only at the reviewed head SHA, synchronize local
main, and require exact-main CI and CodeQL success. Do not create a release, issue
comment, label, reviewer request, or other notification.
