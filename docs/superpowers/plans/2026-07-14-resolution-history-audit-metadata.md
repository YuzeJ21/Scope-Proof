# Resolution History Audit Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display each persisted resolution event's reviewer, UTC timestamp, and applicable claimed evidence level in the Streamlit resolution history.

**Architecture:** Keep the change in the Streamlit presentation layer. Read already validated `ResolutionEvent` fields and add one compact metadata caption below the existing chronological event summary; do not change lifecycle classification, event persistence, exports, or deterministic gates.

**Tech Stack:** Python 3.12, Pydantic 2, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Keep the existing event summary, chronological order, current/superseded/prior-revision status, and final-acceptance wording unchanged.
- Show reviewer and Pydantic JSON UTC timestamp for every event.
- Show claimed evidence level only when `claimed_evidence_level` is not `None`.
- Do not change schemas, events, lifecycle, persistence, exports, gates, final acceptance, workflows, dependencies, release state, or external evidence.
- Fixtures and browser captures prove UI behavior only; never present them as runtime verification, external adoption, or acceptance evidence.

---

### Task 1: Render complete resolution-event audit metadata

**Files:**
- Modify: `apps/web/app.py:1296-1336`
- Modify: `tests/apps/test_streamlit_app.py:2058-2090`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `ResolutionEvent.reviewer: str`, `ResolutionEvent.timestamp: datetime`, and `ResolutionEvent.claimed_evidence_level: EvidenceLevel | None`.
- Produces: one `st.caption` per rendered event containing reviewer, `Recorded at (UTC)`, and an optional claimed-level segment.

- [ ] **Step 1: Write failing AppTests**

Add `datetime`, `UTC`, `append_resolution`, and `ResolutionEvent` imports if not already present. Construct fixed validated events through the current analyzed demo state and lifecycle operation so the active bundle stays consistent:

```python
def test_resolution_history_shows_reviewer_timestamp_and_claimed_level() -> None:
    app = analyzed_demo(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    review_state = append_resolution(
        review_state,
        ResolutionEvent(
            event_id="manual-audit-event",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="Controlled verification note",
            reviewer="Controlled reviewer",
            claimed_evidence_level=EvidenceLevel.E3,
            timestamp=datetime(2026, 7, 14, 19, 45, tzinfo=UTC),
            criteria_revision_number=1,
        ),
    )
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle
    app = app.run()

    assert (
        "Reviewer: Controlled reviewer · Recorded at (UTC): 2026-07-14T19:45:00Z · "
        "Claimed evidence level: E3"
    ) in [item.value for item in app.caption]


def test_resolution_history_omits_claimed_level_for_non_manual_decision() -> None:
    app = analyzed_demo(new_app())
    review_state = app.session_state["review_state"].model_copy(deep=True)
    review_state = append_resolution(
        review_state,
        ResolutionEvent(
            event_id="accepted-audit-event",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Controlled acceptance note",
            reviewer="Controlled reviewer",
            timestamp=datetime(2026, 7, 14, 19, 50, tzinfo=UTC),
            criteria_revision_number=1,
        ),
    )
    app.session_state["review_state"] = review_state
    app.session_state["bundle"] = review_state.bundle
    app = app.run()

    captions = [item.value for item in app.caption]
    assert "Reviewer: Controlled reviewer · Recorded at (UTC): 2026-07-14T19:50:00Z" in captions
    assert not any("Claimed evidence level" in item for item in captions)
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
PYTHONPATH="$PWD" "/Users/yjian070/Documents/New project 2/.venv/bin/pytest" -q \
  tests/apps/test_streamlit_app.py -k 'resolution_history_shows_reviewer or resolution_history_omits_claimed'
```

Expected: both tests fail because no event metadata caption exists.

- [ ] **Step 3: Implement the minimal metadata caption**

Inside the existing `for event, event_status in zip(...)` loop, immediately after the event summary:

```python
recorded_at = event.model_dump(mode="json")["timestamp"]
metadata = f"Reviewer: {event.reviewer} · Recorded at (UTC): {recorded_at}"
if event.claimed_evidence_level is not None:
    metadata += f" · Claimed evidence level: {event.claimed_evidence_level.value}"
st.caption(metadata)
```

- [ ] **Step 4: Run focused and adjacent tests to confirm GREEN**

Run:

```bash
PYTHONPATH="$PWD" "/Users/yjian070/Documents/New project 2/.venv/bin/ruff" check \
  apps/web/app.py tests/apps/test_streamlit_app.py
PYTHONPATH="$PWD" "/Users/yjian070/Documents/New project 2/.venv/bin/pytest" -q \
  tests/apps/test_streamlit_app.py -k 'resolution_history or final_acceptance'
```

Expected: Ruff and all selected tests pass.

- [ ] **Step 5: Run complete verification**

Run:

```bash
PYTHONPATH="$PWD" "/Users/yjian070/Documents/New project 2/.venv/bin/pytest" -q
PYTHONPATH="$PWD" "/Users/yjian070/Documents/New project 2/.venv/bin/python" \
  -m scopeproof_core.evals.runner
"/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pip check
git diff --check
```

Expected: zero failures, 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False Ready, zero false blockers, no broken requirements, and a clean diff check.

- [ ] **Step 6: Run loopback and browser verification**

Start the worktree app on an unused loopback port, require `/_stcore/health` to return exactly `ok`, and use the in-app browser to reproduce the same controlled manual-verification state. Capture and inspect the updated history. Require reviewer, UTC timestamp, and E3 to be visible; require the final-acceptance boundary copy and gate verdict to remain unchanged. Check browser warning/error logs.

- [ ] **Step 7: Commit the implementation**

Run:

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py \
  docs/superpowers/specs/2026-07-14-resolution-history-audit-metadata-design.md \
  docs/superpowers/plans/2026-07-14-resolution-history-audit-metadata.md
git diff --cached --check
git commit -m "Show resolution history audit metadata"
```

Expected: one intentional implementation commit after the already committed design.

### Task 2: Publish and reconcile the protected change

**Files:**
- No additional source files.

**Interfaces:**
- Consumes: verified branch head SHA and GitHub branch protection requiring `verify`.
- Produces: green protected PR, exact squash merge, verified merged main, and a clean synchronized checkout.

- [ ] **Step 1: Push and open one ready PR**

Push `codex/resolution-history-audit-metadata`. Create a ready PR summarizing the reproduced omission, display-only correction, and verification evidence. Do not add comments, labels, reviewers, reactions, or a release.

- [ ] **Step 2: Require protected checks and merge exact head**

Wait for required `verify` and CodeQL checks. Fix only genuine failures. Squash-merge only when all required checks pass and GitHub still reports the reviewed head SHA.

- [ ] **Step 3: Verify merged main and clean the branch**

Fast-forward local `main` to the exact merge SHA. Require that SHA's own CI, deterministic benchmark, installed-wheel smoke, and CodeQL run to pass. Confirm open Dependabot and CodeQL alerts remain zero and `origin/main...HEAD` is `0 0`. Remove only this owned worktree and branch.

- [ ] **Step 4: Rotate the persistent goal**

Reconcile issue #3, open PRs, release, Action pins, dependencies, docs, and product behavior. Do not mark the goal complete or blocked. Select the next evidence-backed improvement or perform the lightweight external waiting check while keeping the goal active.
