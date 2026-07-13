# Resolution History Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the append-only resolution history identify the event that currently supplies each active-revision decision while preserving every historical event.

**Architecture:** Add a deterministic, order-preserving event classifier to the core review lifecycle, then consume it in the Streamlit presentation layer. The classifier owns lifecycle meaning; the UI owns human-readable labels and layout.

**Tech Stack:** Python 3.11+, Pydantic v2 models, Streamlit, pytest, Streamlit AppTest, Ruff.

## Global Constraints

- Do not change gate evaluation, evidence levels, decision replacement, or final-acceptance semantics.
- Do not delete, reorder, hide, persist, or export derived history statuses.
- Keep the core independent from Streamlit.
- Treat False Ready as more harmful than False Blocked.
- Add regression coverage before production implementation.

---

### Task 1: Classify append-only resolution events

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/reviews/__init__.py`
- Test: `tests/reviews/test_lifecycle.py`

**Interfaces:**
- Consumes: `list[ResolutionEvent]` and the active criteria revision number.
- Produces: `ResolutionEventStatus` and `resolution_event_statuses(events, active_revision_number) -> list[ResolutionEventStatus]`.

- [ ] **Step 1: Write the failing lifecycle tests**

Add tests that create two AC-01 decisions and two final-acceptance events in revision 1, then assert
the first event for each target is `SUPERSEDED` and the last is `CURRENT`. Add a revision-2 state
and assert every revision-1 event is `PRIOR_REVISION`.

- [ ] **Step 2: Verify RED**

Run:

```bash
../../.venv/bin/python -m pytest tests/reviews/test_lifecycle.py -q
```

Expected: import failure because `ResolutionEventStatus` and `resolution_event_statuses` do not yet
exist.

- [ ] **Step 3: Implement the minimal classifier**

Define `ResolutionEventStatus(StrEnum)` with `CURRENT`, `SUPERSEDED`, and `PRIOR_REVISION`. Scan the
active revision once to record the last index for each target tuple `(is_final_event,
criterion_id)`, then return one status per original event. Re-export the enum and helper from
`scopeproof_core.reviews`.

- [ ] **Step 4: Verify GREEN**

Run the focused lifecycle test file and require all tests to pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/reviews/lifecycle.py scopeproof_core/reviews/__init__.py tests/reviews/test_lifecycle.py
git commit -m "feat: classify resolution history events"
```

### Task 2: Explain current and historical events in Streamlit

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `resolution_event_statuses()` and the active `criteria_revision.number`.
- Produces: chronological history bullets with readable status, revision, target, outcome, and note.

- [ ] **Step 1: Write the failing AppTest**

Record `REJECTED_FINDING` and then `ACCEPTED` for AC-01. Assert the visible history contains the
explanation, `Superseded · revision 1 — AC-01: Rejected Finding`, and
`Current · revision 1 — AC-01: Accepted`.

- [ ] **Step 2: Verify RED**

Run the single AppTest and expect failure because the current identical raw-enum bullets do not
contain status or revision labels.

- [ ] **Step 3: Implement the minimal presentation**

Import the core classifier. Add the exact caption:

`Current events are the latest recorded inputs for the active revision. Superseded and prior-revision events remain audit history and do not independently control the gate.`

Render events in original order, use `_status_label()` for decisions, use `Recorded` or
`Not recorded` for final acceptance, and bold only the `Current · revision N` marker.

- [ ] **Step 4: Verify GREEN and focused regressions**

Run the new AppTest, the full Streamlit AppTest file, lifecycle tests, and Ruff on the changed files.

- [ ] **Step 5: Commit**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "clarify current resolution history"
```

### Task 3: Verify the release candidate

**Files:**
- Verify all changed files and generated package artifacts without committing artifacts.

**Interfaces:**
- Consumes: the complete branch.
- Produces: local, package, benchmark, and browser evidence suitable for a protected PR.

- [ ] **Step 1: Run static and regression gates**

Run `ruff check .`, the complete pytest suite, `git diff --check`, and inspect the branch diff.

- [ ] **Step 2: Run deterministic benchmark and package smoke**

Require all 12 benchmark cases, zero must-have False Ready, zero False Blocker, zero mismatches, a
clean wheel install, installed CLI benchmark, and local web health `ok`.

- [ ] **Step 3: Run live browser comparison**

Repeat the two-decision demo flow, capture the history at the same viewport, and confirm the current
and superseded labels match lifecycle truth without changing the Blocked gate reasons.

- [ ] **Step 4: Publish through protected GitHub workflow**

Push the `codex/resolution-history-clarity` branch, open one meaningful ready PR, wait for `verify`,
ScopeProof evidence review, and CodeQL, merge only when all required checks pass, then verify exact
post-merge main CI and synchronize local `main`.
