# Final-Acceptance Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Streamlit workbench distinguish review-level final acceptance from criterion-level resolution without changing lifecycle or gate behavior.

**Architecture:** Add a semantic heading and static boundary guidance in the existing Streamlit presentation layer immediately before the existing final-acceptance button. Keep the button, append-only event, lifecycle service, Pydantic schemas, and deterministic gate unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- Final acceptance remains an independently recordable append-only review event.
- Final acceptance must not resolve criteria or override deterministic gate precedence.
- No criterion decision, evidence, runtime observation, or acceptance is inferred.
- Core lifecycle, schemas, exporters, and gate evaluation remain unchanged.
- Never execute PR code or represent the demo as external validation.

---

### Task 1: Clarify the final-acceptance boundary

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: existing Streamlit `record_final_acceptance` button and `append_resolution(ReviewState, ResolutionEvent) -> ReviewState` lifecycle path.
- Produces: a `Final review acceptance` heading and exact boundary guidance while retaining the existing button key and event behavior.

- [ ] **Step 1: Write the failing AppTest**

Add `GateVerdict` to the schema imports and add this regression after
`test_final_acceptance_control_is_visible_only_after_analysis`:

```python
def test_final_acceptance_is_labeled_as_review_level_without_overriding_gate() -> None:
    app = analyzed_demo(new_app())
    state_before = app.session_state["review_state"]
    gate_before = state_before.bundle.gate

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Final review acceptance" in markdown_text
    assert "records a review-level acceptance event" in caption_text
    assert "does not resolve individual criteria or override the deterministic gate" in caption_text
    assert "Review every criterion and its evidence before recording" in caption_text

    app = app.button(key="record_final_acceptance").click().run()
    state_after = app.session_state["review_state"]

    assert state_after.review.final_acceptance is True
    assert state_after.bundle.gate.verdict is GateVerdict.BLOCKED
    assert state_after.bundle.gate.blocking_criteria == gate_before.blocking_criteria
    assert state_after.bundle.gate.unresolved_criteria == gate_before.unresolved_criteria
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_final_acceptance_is_labeled_as_review_level_without_overriding_gate -q
```

Expected: FAIL because the heading and boundary copy are absent; the existing gate behavior remains available for the later assertions.

- [ ] **Step 3: Add the minimal presentation boundary**

Immediately before the existing `record_final_acceptance` button in `apps/web/app.py`, add:

```python
    st.markdown("### Final review acceptance")
    st.caption(
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    )
```

Do not change the button declaration or its event handler.

- [ ] **Step 4: Run focused GREEN and lint**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_final_acceptance_control_is_visible_only_after_analysis \
  tests/apps/test_streamlit_app.py::test_final_acceptance_is_labeled_as_review_level_without_overriding_gate \
  tests/apps/test_streamlit_app.py::test_human_decision_and_final_acceptance_append_history \
  tests/reviews/test_lifecycle.py::test_final_acceptance_event_allows_ready_after_criterion_resolution \
  tests/gates/test_evaluator.py::test_ready_requires_final_acceptance -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: five tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "clarify review final acceptance"
```

### Task 2: Verify and publish the bounded improvement

**Files:**
- Verify: all repository source, tests, benchmark fixtures, package contents, and the Streamlit flow.

**Interfaces:**
- Consumes: committed Task 1 presentation change.
- Produces: protected-main merge evidence with no release.

- [ ] **Step 1: Run broad local verification**

Run Ruff, the complete pytest suite, `scopeproof benchmark`, and `git diff --check origin/main...HEAD`.
Require all tests to pass apart from the intentional live skip; require all 12 benchmark cases,
zero must-have False Ready, zero False Blocker, and zero mismatches.

- [ ] **Step 2: Verify the installed wheel and live UI**

Build a wheel, install it with dependencies in a fresh temporary virtual environment, confirm both
console scripts report `0.1.15.dev0`, run the installed benchmark, and require exact `ok` from the
installed Streamlit health endpoint. In the browser, repeat the deliberately constructed demo flow,
capture the unresolved final-acceptance boundary, and confirm the new heading and guidance are
visible while the verdict remains `Blocked`. Do not record runtime evidence or final acceptance.

- [ ] **Step 3: Publish through protected main**

Review `origin/main...HEAD`, push `codex/final-acceptance-boundary`, open one ready pull request, wait
for required `verify`, ScopeProof evidence review, and CodeQL checks, and merge only when all pass.
Confirm exact post-merge `main` CI and CodeQL success, synchronize local main, and remove the owned
worktree and branch. Do not publish a release for this presentation-only change.
