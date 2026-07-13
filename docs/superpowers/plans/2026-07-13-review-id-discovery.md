# Review-ID Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the active local review UUID persistently visible and copyable before and after save/reopen.

**Architecture:** Render the existing validated `review_state.review.review_id` in Summary & Export using Streamlit's native code block. Reuse that same value in the save confirmation without changing storage, lifecycle, or export behavior.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- The ID must come only from `ReviewState.review.review_id`.
- Do not expose a filesystem path, token, PR content, or new persisted field.
- Do not change saving, reopening, lifecycle history, evidence, gates, or exports.
- Use Streamlit's native code-block copy affordance; do not add clipboard JavaScript.

---

### Task 1: Display and confirm the current review ID

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `review_state.review.review_id: str`.
- Produces: a `Current review ID` caption, one native code block containing the UUID, and a save success message containing the same UUID.

- [ ] **Step 1: Write failing AppTests for visibility and save confirmation**

Add before the existing durable save/reopen test:

```python
def test_current_review_id_is_copyable_and_used_in_save_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    review_id = app.session_state["review_state"].review.review_id

    assert review_id in [item.value for item in app.code]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Current review ID" in caption_text
    assert "Save this review before using the ID in a future session" in caption_text

    app = app.button(key="save_review").click().run()
    assert f"Review {review_id} saved locally." in [item.value for item in app.success]
```

Extend `test_saved_review_can_be_reopened_from_a_fresh_session` after reopen with:

```python
    assert review_id in [item.value for item in fresh.code]
```

- [ ] **Step 2: Run the tests and confirm review-ID presentation is absent**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_current_review_id_is_copyable_and_used_in_save_confirmation \
  tests/apps/test_streamlit_app.py::test_saved_review_can_be_reopened_from_a_fresh_session -q
```

Expected: FAIL because the UUID is not rendered and the save message is generic.

- [ ] **Step 3: Render the ID and include it in the save message**

In Summary & Export, immediately after `st.header("5 · Summary & Export")`, add:

```python
    if review_state is not None:
        st.caption(
            "Current review ID — save this review before using the ID in a future session."
        )
        st.code(review_state.review.review_id, language=None)
```

Change the save success call to:

```python
        st.success(f"Review {review_state.review.review_id} saved locally.")
```

- [ ] **Step 4: Run focused AppTests and Ruff**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

Expected: all AppTests pass; Ruff and diff checks pass.

- [ ] **Step 5: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: expose saved review IDs"
```

### Task 2: Verify complete and rendered behavior

**Files:**
- Verify only: repository-wide source, tests, benchmark fixtures, and Streamlit app.

**Interfaces:**
- Consumes: committed review-ID presentation.
- Produces: full deterministic verification and rendered local evidence that the UUID remains visible across save and fresh-session reopen.

- [ ] **Step 1: Run repository-wide gates**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: 186 or more tests pass with only the intentional live test skipped; all 12 benchmark
cases execute with zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 2: Run the real Streamlit workflow with temporary HOME storage**

Run:

```bash
temp_home=$(mktemp -d /tmp/scopeproof-review-id-runtime.XXXXXX)
HOME="$temp_home" /Users/yjian070/Documents/New\ project\ 2/.venv/bin/python \
  -m streamlit run apps/web/app.py --server.headless true \
  --server.address 127.0.0.1 --server.port 8515
```

Confirm `http://127.0.0.1:8515/_stcore/health` returns `ok`. Load the deterministic demo, confirm
criteria, run analysis, and verify the current review ID appears in a native code block. Save the
review and verify the same ID appears in the success message. Open a fresh tab/session, reopen the
review, and verify the same ID remains visible while analysis stays disabled. Do not record runtime
evidence, a resolution, or final acceptance.

- [ ] **Step 3: Clean temporary state and confirm branch hygiene**

Stop Streamlit, remove only the temporary HOME created in Step 2, and confirm a clean
`codex/review-id-discovery` branch with the design, plan, and implementation commits ahead of main.

Run:

```bash
git status --short --branch
git log --oneline --decorate -4
```
