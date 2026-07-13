# Fresh-Session Review Reopen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make validated local reviews reopenable from a fresh Streamlit session without reusing an unrelated PR snapshot.

**Architecture:** Move reopen controls before source and requirement widgets, then hydrate saved ReviewState through one presentation-layer helper. The saved bundle becomes immediately viewable/exportable, while the unpersisted PullRequestSnapshot is cleared so a deliberate source reload is required before re-analysis.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- `JsonReviewStore.load` remains the only review-record loading and validation boundary.
- Reopening must never reconstruct or reuse a `PullRequestSnapshot`.
- Saved evidence, findings, resolutions, final acceptance, gates, and exports remain unchanged.
- Re-analysis remains disabled until a public PR or demo is deliberately loaded and criteria are reconfirmed.
- Failed loads must not mutate session state or display raw paths, tracebacks, or Pydantic internals.
- No core schema, lifecycle, GitHub ingestion, or storage-format change is allowed.

---

### Task 1: Expose safe reopen controls before analysis

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `JsonReviewStore.load(review_id: str) -> ReviewState` and `UnsupportedRecordVersion`.
- Produces: `_hydrate_reopened_review(state: ReviewState) -> None`, synchronized Streamlit session keys, and source-reload guidance.

- [ ] **Step 1: Write failing fresh-session and stale-snapshot AppTests**

Add `import pytest` to `tests/apps/test_streamlit_app.py`, then add:

```python
def saved_demo_review(app: AppTest) -> tuple[AppTest, str]:
    app = analyzed_demo(app)
    review_id = app.session_state["review_state"].review.review_id
    app = app.button(key="save_review").click().run()
    return app, review_id


def test_saved_review_can_be_reopened_from_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    assert fresh.text_input(key="reopen_review_id").value == ""
    fresh = fresh.text_input(key="reopen_review_id").set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()

    reopened = fresh.session_state["review_state"]
    assert reopened == saved_state
    assert fresh.session_state["bundle"] == saved_state.bundle
    assert fresh.session_state["criteria"] == saved_state.criteria_revision.criteria
    assert fresh.session_state["criteria_confirmed"] is True
    assert fresh.session_state["source_text"] == saved_state.criteria_revision.source_text
    assert (
        fresh.text_area(key="requirements_input").value
        == saved_state.criteria_revision.source_text
    )
    assert fresh.session_state["snapshot"] is None
    assert fresh.button(key="run_analysis").disabled is True
    assert len(fresh.download_button) == 3


def test_reopening_clears_an_unrelated_loaded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())

    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    app = app.text_input(key="reopen_review_id").set_value(review_id).run()
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["snapshot"] is None
    assert app.button(key="run_analysis").disabled is True
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Reload source to rerun analysis" in sidebar_text


def test_missing_saved_review_has_safe_recovery_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()
    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()
    app = app.button(key="reopen_review").click().run()

    assert [item.value for item in app.error] == [
        "No saved review was found for that review ID."
    ]
    assert app.session_state["review_state"] is None
    assert app.session_state["bundle"] is None
```

- [ ] **Step 2: Run the new tests and verify the current nesting fails**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_saved_review_can_be_reopened_from_a_fresh_session \
  tests/apps/test_streamlit_app.py::test_reopening_clears_an_unrelated_loaded_snapshot \
  tests/apps/test_streamlit_app.py::test_missing_saved_review_has_safe_recovery_copy -q
```

Expected: FAIL because a fresh app does not expose `reopen_review_id` or `reopen_review`.

- [ ] **Step 3: Add the presentation-layer hydration helper**

Import `UnsupportedRecordVersion` beside `JsonReviewStore`, then add after `_prepare_from_text`:

```python
def _hydrate_reopened_review(state: ReviewState) -> None:
    """Restore persisted review state without claiming its source snapshot is loaded."""
    st.session_state["snapshot"] = None
    st.session_state["criteria"] = state.criteria_revision.criteria
    st.session_state["criteria_confirmed"] = state.review.criteria_confirmed
    st.session_state["bundle"] = state.bundle
    st.session_state["source_text"] = state.criteria_revision.source_text
    st.session_state["requirements_input"] = state.criteria_revision.source_text
    st.session_state["resolutions"] = []
    st.session_state["review_state"] = state
```

- [ ] **Step 4: Move and categorize reopen handling before source widgets**

Immediately after the introductory caption and before `st.header("1 · Start Review")`, add:

```python
storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
st.markdown("### Reopen saved review")
reopen_id = st.text_input("Review ID", key="reopen_review_id")
if st.button("Reopen local review", key="reopen_review", disabled=not reopen_id.strip()):
    try:
        reopened_state = review_store.load(reopen_id.strip())
    except FileNotFoundError:
        st.error("No saved review was found for that review ID.")
    except UnsupportedRecordVersion:
        st.error("This saved review requires a different ScopeProof record version.")
    except (OSError, ValueError):
        st.error("The saved review could not be opened. Verify its ID and record integrity.")
    else:
        _hydrate_reopened_review(reopened_state)
        st.success("Review reopened from validated local storage.")
```

Keep the existing storage-directory caption under the source preparation controls, but remove its
duplicate assignment. In Summary & Export, change save to `review_store.save(review_state)` and
delete the old `reopen_review_id` input, button, and exception block.

- [ ] **Step 5: Make the sidebar distinguish a reopened bundle from a loaded source**

Replace the first sidebar status expression with:

```python
    st.markdown(
        "Complete — Source loaded"
        if has_source
        else (
            "Next — Reload source to rerun analysis"
            if has_analysis
            else "Next — Load a public PR or demo"
        )
    )
```

- [ ] **Step 6: Run focused AppTest, storage, and reporting regressions**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py tests/storage tests/reporting -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: all selected tests and Ruff pass. Existing durable-reopen and exporter tests remain green.

- [ ] **Step 7: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: reopen saved reviews from fresh sessions"
```

### Task 2: Verify the complete product and rendered fresh-session path

**Files:**
- Verify only: repository-wide source, test suite, benchmark fixtures, and installed Streamlit app.

**Interfaces:**
- Consumes: committed fresh-session reopen implementation.
- Produces: deterministic regression evidence and local runtime evidence for the real rendered workflow.

- [ ] **Step 1: Run repository-wide gates**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; 185 or more tests pass with only the intentional live GitHub test skipped;
all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false
blockers; diff check is clean.

- [ ] **Step 2: Start Streamlit with temporary HOME storage**

Run:

```bash
temp_home=$(mktemp -d /tmp/scopeproof-reopen-runtime.XXXXXX)
HOME="$temp_home" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python \
  -m streamlit run apps/web/app.py --server.headless true \
  --server.address 127.0.0.1 --server.port 8514
```

Expected: `http://127.0.0.1:8514/_stcore/health` returns `ok`.

- [ ] **Step 3: Inspect the rendered fresh-session workflow**

Use the deterministic demo to create and save one temporary local review. Open a fresh local app
session, enter that review ID, and reopen it. Confirm the saved criteria, evidence matrix, verdict,
history, and exports render; source status requests an explicit reload; deterministic analysis is
disabled. Do not record runtime evidence, a human resolution, or final acceptance.

- [ ] **Step 4: Remove temporary runtime storage and confirm branch hygiene**

Stop Streamlit, remove only the `temp_home` directory created in Step 2, then run:

```bash
git status --short --branch
git log --oneline --decorate -3
```

Expected: clean `codex/fresh-review-reopen` with only the design, plan, and implementation commits
ahead of main.
