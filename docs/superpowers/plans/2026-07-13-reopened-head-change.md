# Reopened Review Head-Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report deterministic head-SHA continuity when a saved review is reopened and the same pull request is reloaded, while preventing old evidence from being reused.

**Architecture:** Keep comparison logic in `JsonReviewStore.detect_head_change`. Add only transient Streamlit session state to mark a reopened review and display the comparison result before the old analysis is invalidated.

**Tech Stack:** Python 3.11+, Streamlit session state, Pydantic-validated domain models, pytest, Streamlit AppTest.

## Global Constraints

- Every criterion verdict must cite explicit evidence or state what evidence is missing.
- Implementation evidence must never be presented as test or runtime verification.
- Users must confirm normalized acceptance criteria before analysis.
- Never execute untrusted repository code in the application server.
- Keep gate decisions deterministic and reproducible.
- Treat False Ready as more harmful than False Blocked.
- No billing, paid API, LLM API, fork testing, synthetic validation, or invented evidence.
- The saved review record is never mutated by source reload.

---

### Task 1: Prove changed-head invalidation in the Streamlit flow

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `saved_demo_review(app: AppTest) -> tuple[AppTest, str]`, `load_demo_snapshot() -> PullRequestSnapshot`
- Produces: regression tests for changed-head and same-head reload behavior

- [ ] **Step 1: Write the failing changed-head test**

Add `from unittest.mock import patch` and use `model_copy(update={"head_sha": ...})` to construct a validated same-PR snapshot. Reopen the saved review in a fresh AppTest session, patch `scopeproof_core.demo.load_demo_snapshot`, reload the demo, and assert:

```python
assert old_head in warning_text
assert changed_head in warning_text
assert "saved evidence remains anchored" in warning_text
assert fresh.session_state["review_state"] is None
assert fresh.session_state["bundle"] is None
assert fresh.session_state["criteria_confirmed"] is False
assert fresh.button(key="run_analysis").disabled is True
```

- [ ] **Step 2: Run the test and verify the missing UI integration**

Run: `python -m pytest tests/apps/test_streamlit_app.py::test_reopened_review_reports_changed_head_before_invalidating_analysis -q`

Expected: FAIL because no warning reports the saved and current SHA.

- [ ] **Step 3: Write the failing same-head test**

Reopen and reload the unmodified demo snapshot, then assert an informational notice contains the unchanged SHA and that analysis remains invalidated until criteria are confirmed again.

- [ ] **Step 4: Run both focused tests**

Run: `python -m pytest tests/apps/test_streamlit_app.py -k 'reopened_review_reports' -q`

Expected: both tests FAIL because the comparison result is not rendered.

- [ ] **Step 5: Commit the red tests**

```bash
git add tests/apps/test_streamlit_app.py
git commit -m "test: cover reopened review head changes"
```

### Task 2: Compare source identity before analysis reset

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `JsonReviewStore.detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange`
- Produces: `_record_reopened_source_reload(snapshot: PullRequestSnapshot) -> None`; session keys `reopened_review_id` and `source_reload_notice`

- [ ] **Step 1: Add transient state and the comparison helper**

Import `PullRequestSnapshot`, add both transient keys to `_STATE_DEFAULTS`, and implement a helper with this contract:

```python
def _record_reopened_source_reload(snapshot: PullRequestSnapshot) -> None:
    state: ReviewState | None = st.session_state["review_state"]
    reopened_id: str | None = st.session_state["reopened_review_id"]
    st.session_state["source_reload_notice"] = None
    if (
        state is not None
        and reopened_id == state.review.review_id
        and state.review.repository == snapshot.repository
        and state.review.pr_number == snapshot.pr_number
    ):
        st.session_state["source_reload_notice"] = JsonReviewStore.detect_head_change(
            state, snapshot
        )
```

- [ ] **Step 2: Manage the reopened-review lifecycle**

Set `reopened_review_id` and clear `source_reload_notice` in `_hydrate_reopened_review`. Clear `reopened_review_id` in `_reset_analysis`, but leave the notice intact so it survives the reset that follows comparison. Clear the notice after a successful new analysis.

- [ ] **Step 3: Compare before replacing either source**

Load each snapshot into a local variable, call `_record_reopened_source_reload(snapshot)`, then assign it to session state and call `_reset_analysis`. Apply the same order to the demo and public-GitHub loaders.

- [ ] **Step 4: Render deterministic continuity copy**

Below the source controls, render:

```python
if notice is not None and notice.changed:
    st.warning(
        f"PR head changed from {notice.saved_head_sha} to {notice.current_head_sha}. "
        "Prior saved evidence remains anchored to the old head. Reconfirm criteria "
        "and run a new review; do not reuse old evidence."
    )
elif notice is not None:
    st.info(
        f"PR source reloaded at the same head SHA: {notice.current_head_sha}. "
        "Reconfirm criteria and run a new review before relying on current results."
    )
```

- [ ] **Step 5: Run the focused tests**

Run: `python -m pytest tests/apps/test_streamlit_app.py -k 'reopened_review_reports' -q`

Expected: PASS.

- [ ] **Step 6: Run the Streamlit and storage regression suites**

Run: `python -m pytest tests/apps/test_streamlit_app.py tests/storage/test_json_store.py -q`

Expected: PASS.

- [ ] **Step 7: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: report reopened review head changes"
```

### Task 3: Verify product truth and publish the protected change

**Files:**
- Verify: `README.md`
- Verify: `docs/superpowers/specs/2026-07-13-reopened-head-change-design.md`
- Verify: `docs/superpowers/plans/2026-07-13-reopened-head-change.md`

**Interfaces:**
- Consumes: completed tests and Streamlit UI
- Produces: evidence-backed protected pull request with no release

- [ ] **Step 1: Run static and full regression gates**

Run: `python -m ruff check .`

Expected: PASS.

Run: `python -m pytest -q`

Expected: all tests pass, with only the intentional live-network skip if still configured.

- [ ] **Step 2: Run benchmark and repository hygiene gates**

Run the repository's documented benchmark command and confirm `12/12`, zero mismatches, zero must-have False Ready, and zero false blockers. Then run `git diff --check` and confirm no whitespace errors.

- [ ] **Step 3: Perform a real Streamlit same-head browser check**

Start Streamlit with a temporary `HOME`, save and reopen the demo review, reload the same demo source, and verify the same-head informational notice is visible, criteria confirmation is reset, and analysis remains locked. Do not describe this as changed-head runtime evidence.

- [ ] **Step 4: Review branch scope and commit any documentation correction**

Confirm the README claim is now supported, no license was added, and no unrelated files changed. If verification reveals wording drift, correct only the affected sentence and commit it.

- [ ] **Step 5: Push once and open one protected pull request**

Push `codex/reopened-head-change`, open one ready pull request, and wait for required `verify` and CodeQL checks. Do not create comments, issues, releases, labels, or notification-only updates.

- [ ] **Step 6: Merge only after every required check is green**

Merge through protected `main`, verify the main SHA and post-merge CI/CodeQL status, then delete the remote feature branch. Do not publish a release for this bounded fix.
