# Runtime-Evidence Form Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the manual runtime-evidence form after a successful append so an accidental second click cannot duplicate the submitted record.

**Architecture:** Reuse the workbench's presentation-only pending-reset pattern. A successful append stores a reset marker and one-run success notice, reruns Streamlit, clears the runtime widget keys before rendering, and lets the existing readiness rule disable Save; Pydantic, lifecycle, gate, and final-acceptance code remain unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- Runtime evidence remains human supplied, append-only, and restricted to E3 or E4.
- Runtime evidence must not change static findings or deterministic gate truth.
- Only a successful append clears the form; failed validation preserves user input.
- Final acceptance, resolution events, gate evaluation, exports, and persisted schemas remain unchanged.
- Never execute PR code or represent test fixtures as genuine external runtime evidence.
- Do not publish a release for this unreleased workbench reliability improvement.

---

### Task 1: Specify the successful-save reset contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `analyzed_demo(AppTest) -> AppTest`, runtime-evidence widget keys, and `save_runtime_evidence`.
- Produces: `test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat()`.

- [ ] **Step 1: Add the failing regression**

Add this test after the existing complete-record runtime-evidence test:

```python
def test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/reset"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.text_area(key="runtime_limitations").set_value("Fixture limitation").run()
    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()

    app = app.button(key="save_runtime_evidence").click().run()

    assert len(app.session_state["review_state"].bundle.runtime_evidence) == 1
    assert app.text_input(key="runtime_artifact_reference").value == ""
    assert app.text_area(key="runtime_scenario").value == ""
    assert app.text_input(key="runtime_environment").value == ""
    assert app.text_input(key="runtime_result").value == ""
    assert app.text_input(key="runtime_reviewer").value == ""
    assert app.text_area(key="runtime_limitations").value == ""
    assert app.selectbox(key="runtime_evidence_level").value is EvidenceLevel.E3
    assert app.button(key="save_runtime_evidence").disabled is True
    assert "Manual runtime evidence appended without changing static findings." in [
        item.value for item in app.success
    ]
```

- [ ] **Step 2: Run the regression and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat -q
```

Expected: FAIL because `runtime_artifact_reference` remains populated after the successful append.

- [ ] **Step 3: Retain the RED output as execution evidence**

Do not commit a red branch. Implement Task 2, then commit the test and production change together.

### Task 2: Reset runtime-evidence presentation state after success

**Files:**
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `append_runtime_evidence(ReviewState, RuntimeEvidence) -> ReviewState` and the runtime-evidence widget keys.
- Produces: `runtime_evidence_form_reset_pending: bool` and `runtime_evidence_save_notice: str` session keys.

- [ ] **Step 1: Clear widget state before rendering after a successful-save marker**

Immediately before `st.markdown("### Manual runtime evidence")`, add:

```python
    if st.session_state.pop("runtime_evidence_form_reset_pending", False):
        st.session_state["runtime_artifact_reference"] = ""
        st.session_state["runtime_scenario"] = ""
        st.session_state["runtime_environment"] = ""
        st.session_state["runtime_result"] = ""
        st.session_state["runtime_reviewer"] = ""
        st.session_state["runtime_limitations"] = ""
        st.session_state["runtime_evidence_level"] = EvidenceLevel.E3
    runtime_evidence_save_notice = st.session_state.pop(
        "runtime_evidence_save_notice", None
    )
```

- [ ] **Step 2: Render the retained success notice after the prerequisite caption**

```python
    if runtime_evidence_save_notice is not None:
        st.success(runtime_evidence_save_notice)
```

- [ ] **Step 3: Mark success and rerun instead of rendering an ephemeral message**

Replace the existing success call after `append_runtime_evidence` with:

```python
                st.session_state["runtime_evidence_form_reset_pending"] = True
                st.session_state["runtime_evidence_save_notice"] = (
                    "Manual runtime evidence appended without changing static findings."
                )
                st.rerun()
```

Leave the `except ValueError` path unchanged.

- [ ] **Step 4: Run the regression and verify GREEN**

Run the Task 1 command. Expected: `1 passed`.

- [ ] **Step 5: Run focused regressions**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py \
  tests/reviews/test_lifecycle.py \
  tests/schemas/test_runtime_evidence.py -q
```

Expected: all selected tests pass, including prerequisite readiness, unchanged static findings, lifecycle, and final-acceptance behavior.

- [ ] **Step 6: Run focused static checks and commit**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: clear runtime evidence form after save"
```

Expected: Ruff passes, diff check has no output, and one implementation commit is created.

### Task 3: Verify the complete product and protected integration

**Files:**
- Verify only: repository source, package, workflows, and local browser artifacts.

**Interfaces:**
- Consumes: committed Task 2 behavior.
- Produces: offline regression evidence, installed-wheel evidence, live-browser evidence, and protected-main GitHub evidence.

- [ ] **Step 1: Run repository-wide verification**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; at least 226 tests pass with only the intentional live GitHub test skipped; all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 2: Build and clean-install the wheel**

Build from the branch, install it with dependencies into a fresh `/tmp` virtual environment, run `scopeproof benchmark`, start `scopeproof-web` on an unused loopback port, and confirm `/_stcore/health` returns `ok`. Do not publish or attach the wheel.

- [ ] **Step 3: Inspect the live UI without inventing runtime evidence**

Start the branch workbench on an unused loopback port. Use the deliberately constructed demo only to reach the post-analysis screen. Confirm the empty form is disabled and the final-acceptance boundary is unchanged. Do not submit invented runtime evidence. Use AppTest evidence for the successful-save transition and capture the empty post-reset state from the real branch UI.

- [ ] **Step 4: Push one focused protected PR**

Push `codex/runtime-evidence-form-reset`, open one ready PR with verification evidence, and add no reviewers, comments, issue updates, or release activity.

- [ ] **Step 5: Merge only after all checks pass and synchronize main**

Wait for required `verify`, ScopeProof, and CodeQL checks. If they pass, merge normally, verify merged-main CI and CodeQL at the exact merge SHA, fast-forward local `main`, remove the worktree, prune the branch, and confirm a clean checkout.

