# Final-Acceptance Repeat Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent an unchanged criteria revision from recording the same final acceptance twice while preserving first-event independence from gate state.

**Architecture:** Derive a presentation-only recorded flag from `ReviewState.review.final_acceptance`, disable the existing button only when that flag is true, and preserve success copy through a rerun. Core resolution events, lifecycle recalculation, and gate behavior remain unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- The first final-acceptance event remains available even when the review is Blocked or unresolved.
- Final acceptance never resolves criteria or overrides the deterministic gate.
- Criteria revision invalidation re-enables the action through the existing false reset.
- Resolution events remain append-only; no core deduplication is added.
- Test fixtures are UI regressions, not external acceptance evidence.
- Do not publish a release for this unreleased workbench reliability change.

---

### Task 1: Specify the post-acceptance interaction contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `analyzed_demo(AppTest) -> AppTest`, `record_final_acceptance`, criteria widgets, and `confirm_criteria`.
- Produces: post-acceptance repeat-prevention and revision-reset assertions.

- [ ] **Step 1: Add a failing repeat-prevention regression**

Extend `test_final_acceptance_is_labeled_as_review_level_without_overriding_gate()` after its existing gate assertions:

```python
    assert len(state_after.resolution_events) == 1
    assert app.button(key="record_final_acceptance").disabled is True
    assert "Final acceptance appended to the local review history." in [
        item.value for item in app.success
    ]
    history = [item.value for item in app.markdown if "Final acceptance:" in item.value]
    assert history == [
        "- **Current · revision 1** — Final acceptance: Recorded — "
        "Reviewer recorded final acceptance"
    ]
```

- [ ] **Step 2: Verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_final_acceptance_is_labeled_as_review_level_without_overriding_gate -q
```

Expected: FAIL because the button remains enabled after acceptance.

- [ ] **Step 3: Add revision-reset coverage after GREEN**

Add:

```python
def test_criteria_revision_reenables_final_acceptance_after_invalidation() -> None:
    app = analyzed_demo(new_app())
    app = app.button(key="record_final_acceptance").click().run()
    assert app.button(key="record_final_acceptance").disabled is True

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "User can export the research list as a downloadable CSV"
    ).run()

    assert app.session_state["review_state"].review.final_acceptance is False
    assert app.session_state["review_state"].bundle is None
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert app.button(key="record_final_acceptance").disabled is False
```

### Task 2: Disable only the already-completed action

**Files:**
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `review_state.review.final_acceptance: bool` and `append_resolution`.
- Produces: `final_acceptance_recorded: bool` and `final_acceptance_save_notice: str | None` presentation state.

- [ ] **Step 1: Consume retained notice and derive disabled state**

Before the final-acceptance heading, add:

```python
    final_acceptance_save_notice = st.session_state.pop(
        "final_acceptance_save_notice", None
    )
    final_acceptance_recorded = bool(
        review_state is not None and review_state.review.final_acceptance
    )
```

- [ ] **Step 2: Disable only after acceptance and show the retained notice**

Change the button and notice rendering to:

```python
    if st.button(
        "Record final acceptance",
        key="record_final_acceptance",
        disabled=final_acceptance_recorded,
    ):
```

After the button block, render:

```python
    if final_acceptance_save_notice is not None:
        st.success(final_acceptance_save_notice)
```

- [ ] **Step 3: Store success and rerun after append**

Replace the existing `st.success` after the append with:

```python
            st.session_state["final_acceptance_save_notice"] = (
                "Final acceptance appended to the local review history."
            )
            st.rerun()
```

- [ ] **Step 4: Verify GREEN and add the revision-reset test**

Run the focused test from Task 1, add the exact-key revision test, and run both. Expected: both pass.

- [ ] **Step 5: Run focused regression and static gates**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py tests/reviews/test_lifecycle.py tests/gates -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

Expected: all selected tests and Ruff pass with no diff errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: prevent repeated final acceptance"
```

### Task 3: Verify and integrate

**Files:**
- Verify only: full repository, package, browser artifact folder, and GitHub state.

**Interfaces:**
- Consumes: committed Tasks 1-2.
- Produces: full verification and protected-main evidence.

- [ ] **Step 1: Run Ruff, full pytest, deterministic benchmark, and diff checks**

Expected: at least 227 tests pass with one intentional skip; benchmark has 12 executed cases, zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 2: Build and clean-install the development wheel**

Run installed version, benchmark, and loopback workbench health checks from a fresh `/tmp` environment. Do not publish the wheel.

- [ ] **Step 3: Verify the live browser states**

Use the deliberately constructed demo. Before acceptance, confirm the action is enabled and the gate is Blocked. After one transient demo acceptance, confirm the action is disabled, success remains visible, history has one current event, and the gate remains Blocked. Do not save the demo review or present it as external evidence.

- [ ] **Step 4: Publish and merge one protected PR**

Push the branch, open one ready PR without reviewers or comments, wait for all CI/ScopeProof/CodeQL checks, merge only when green, verify merged-main CI/CodeQL, synchronize local main, remove the worktree, prune the branch, and continue the goal loop.
