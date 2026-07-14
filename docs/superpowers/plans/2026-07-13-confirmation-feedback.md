# Criteria-Confirmation Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show exactly one durable success message after criteria confirmation without changing the
confirmation or analysis-lock contracts.

**Architecture:** Add one Streamlit AppTest contract around the existing confirmation interaction,
then remove the redundant transient `st.success` call from the handler. Preserve the persistent
confirmation banner, sidebar milestone, next-action copy, and enabled analysis action.

**Tech Stack:** Python 3.11+, Streamlit AppTest, Pydantic 2, pytest, Ruff, Hatchling.

## Global Constraints

- The only production change is removal of `Criteria confirmed. Analysis can now begin.` from the
  `confirm_criteria` handler.
- `Criteria confirmed by the reviewer.` remains the sole success message.
- Sidebar milestones and analysis-button state remain unchanged.
- Criteria, review lifecycle, evidence, gates, persistence, exports, runtime evidence, resolutions,
  and final acceptance remain unchanged.
- Version remains exactly `0.1.16.dev0`; README continues to reference public v0.1.15.
- No paid API, billing, external service, fork test, issue comment, release, or untrusted-code
  execution.

---

### Task 1: Remove duplicate confirmation feedback

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `load_demo(AppTest) -> AppTest`, Streamlit button key `confirm_criteria`, button key
  `run_analysis`, `app.success`, and `app.sidebar.markdown`.
- Produces: one durable confirmation success message with unchanged confirmation state and next
  action.

- [ ] **Step 1: Write the failing regression**

Add immediately after `test_sidebar_reports_confirmation_and_next_action_in_same_run`:

```python
def test_criteria_confirmation_shows_one_durable_success_message() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    assert [item.value for item in app.success] == [
        "Criteria confirmed by the reviewer."
    ]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert app.button(key="run_analysis").disabled is False
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_criteria_confirmation_shows_one_durable_success_message -q
```

Expected: one assertion failure because `app.success` contains both confirmation messages.

- [ ] **Step 3: Remove the redundant transient banner**

In `apps/web/app.py`, keep:

```python
        st.session_state["bundle"] = None if state is None else state.bundle
```

and delete only:

```python
        st.success("Criteria confirmed. Analysis can now begin.")
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the Step 2 command.

Expected: `1 passed` with no errors.

- [ ] **Step 5: Run adjacent Streamlit regressions**

Run:

```bash
../../.venv/bin/python -m pytest tests/apps/test_streamlit_app.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit the bounded implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "remove duplicate criteria confirmation feedback"
```

### Task 2: Verify the packaged confirmation state

**Files:**
- Verify: all branch changes
- Build transiently under: `/tmp/scopeproof-confirmation-feedback-*`
- Save screenshots under:
  `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-confirmation-feedback-audit`

**Interfaces:**
- Consumes: Task 1 implementation.
- Produces: source, wheel, runtime, and before/after visual evidence.

- [ ] **Step 1: Run source gates**

Run Ruff, full pytest, `python -m scopeproof_core.evals.runner`, and
`git diff origin/main...HEAD --check`. Require zero failures, zero benchmark mismatches, zero
must-have False Ready, and zero false blockers.

- [ ] **Step 2: Build and verify one clean development wheel**

Build exactly `scopeproof-0.1.16.dev0-py3-none-any.whl`, install it with declared dependencies in a
fresh venv, and from `/tmp` require distribution version, module version, both console versions,
and a new Review's tool version to equal `0.1.16.dev0`. Run the installed benchmark and `pip check`.

- [ ] **Step 3: Run packaged health**

Start the installed workbench on an unused loopback port with a fresh temporary `HOME` and require
the exact body `ok` from `/_stcore/health`.

- [ ] **Step 4: Exercise and capture the post-confirmation state**

In the in-app browser, load the deliberately constructed demo and confirm criteria. From a fresh
DOM snapshot require exactly one success message, sidebar completion plus next-action copy, and an
enabled analysis button. Do not run analysis, record evidence, resolve criteria, or accept review.
Save `02-single-confirmation.png` and inspect the saved file.

- [ ] **Step 5: Compare before and after together**

Place `01-duplicate-confirmation-accepted.png` and `02-single-confirmation.png` into one comparison
image at the same 1280×720 viewport. Require one banner, stable controls and hierarchy, no clipping,
and no browser console errors.

- [ ] **Step 6: Stop runtime and review scope**

Stop the packaged server without a traceback. Require a clean worktree and a diff limited to the
design, plan, one removed success call, and regression coverage.

### Task 3: Integrate through protected main

**Files:**
- Publish branch: `codex/confirmation-feedback`

**Interfaces:**
- Consumes: fully verified branch.
- Produces: protected-main single-message confirmation feedback.

- [ ] **Step 1: Push and open one ready pull request**

Describe the captured duplicate state, bounded removal, preserved confirmation contract, and fresh
verification. State that browser/AppTest evidence is controlled product evidence. Do not add an
issue comment, reviewer request, or release.

- [ ] **Step 2: Merge only after all checks pass**

Require both verify jobs, CodeQL language jobs and aggregate, and the informational ScopeProof job
to pass with a clean merge state.

- [ ] **Step 3: Verify merged main and clean up**

Require merged-main CI and CodeQL success, fast-forward local main, confirm clean
`HEAD == origin/main`, remove the owned worktree and merged branch, and verify v0.1.15 remains the
latest release with no issue #3 comment or new security alert.
