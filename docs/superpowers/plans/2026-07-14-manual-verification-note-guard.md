# Manual Verification Note Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require an explicit nonblank reviewer note before a manual-verification decision can be persisted or used to resolve a criterion.

**Architecture:** Enforce the invariant in both Pydantic representations that can enter persisted or exported review state, then mirror the same prerequisite in Streamlit so users receive a clear disabled state before submission. Preserve the existing lifecycle and deterministic gate behavior for every valid event.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest, Ruff, hatchling wheel packaging.

## Global Constraints

- A reviewer note is required only when `decision == HumanDecision.MANUALLY_VERIFIED`.
- Empty and whitespace-only notes are invalid; valid note text is preserved exactly.
- `ResolutionEvent` and `HumanResolution` must enforce the same invariant.
- Other human decisions continue allowing an empty note.
- Valid manual verification still requires a claimed evidence level and still resolves the criterion through the existing gate table.
- Runtime evidence, final acceptance, evidence levels, gate precedence, exports, storage format, and event append-only semantics remain unchanged.
- Never execute pull-request code or present the deliberately constructed demo as genuine external verification.
- Do not require an evidence URL, add dependencies, publish a release, or create notification-only GitHub activity.

---

### Task 1: Pydantic manual-verification invariant

**Files:**
- Create: `tests/schemas/test_manual_verification.py`
- Modify: `scopeproof_core/schemas/models.py:345-392`

**Interfaces:**
- Consumes: `HumanDecision.MANUALLY_VERIFIED`, `EvidenceLevel.E4`, `HumanResolution`, and `ResolutionEvent`.
- Produces: identical `manually verified decisions require a reviewer note` validation behavior in both persisted representations.

- [ ] **Step 1: Write the failing schema tests**

Create `tests/schemas/test_manual_verification.py`:

```python
import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
)


def manual_resolution(comment: str) -> HumanResolution:
    return HumanResolution(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment=comment,
        claimed_evidence_level=EvidenceLevel.E4,
    )


def manual_event(comment: str) -> ResolutionEvent:
    return ResolutionEvent(
        criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED,
        comment=comment,
        claimed_evidence_level=EvidenceLevel.E4,
    )


@pytest.mark.parametrize("factory", [manual_resolution, manual_event])
@pytest.mark.parametrize("comment", ["", "   ", "\t\n"])
def test_manual_verification_rejects_blank_reviewer_note(factory, comment: str) -> None:
    with pytest.raises(
        ValidationError,
        match="manually verified decisions require a reviewer note",
    ):
        factory(comment)


@pytest.mark.parametrize("factory", [manual_resolution, manual_event])
def test_manual_verification_preserves_nonblank_reviewer_note(factory) -> None:
    value = factory("  Verified in staging  ")

    assert value.comment == "  Verified in staging  "


@pytest.mark.parametrize("model", [HumanResolution, ResolutionEvent])
def test_other_human_decisions_keep_optional_reviewer_note(model) -> None:
    value = model(
        criterion_id="AC-01",
        decision=HumanDecision.ACCEPTED,
    )

    assert value.comment == ""
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/schemas/test_manual_verification.py -q
```

Expected: six blank-note cases fail because neither model raises; valid-note and other-decision cases pass.

- [ ] **Step 3: Implement the minimal schema checks**

In `HumanResolution.manual_verification_needs_level`, retain the level check and add:

```python
if self.decision is HumanDecision.MANUALLY_VERIFIED and not self.comment.strip():
    raise ValueError("manually verified decisions require a reviewer note")
```

In `ResolutionEvent.validate_event_kind`, immediately after the existing manual level check, add the same conditional:

```python
if self.decision is HumanDecision.MANUALLY_VERIFIED and not self.comment.strip():
    raise ValueError("manually verified decisions require a reviewer note")
```

- [ ] **Step 4: Run focused schema and lifecycle tests and verify GREEN**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/schemas/test_manual_verification.py tests/reviews/test_lifecycle.py \
  tests/gates/test_evaluator.py -q
'/Users/yjian070/Documents/New project 2/.venv/bin/ruff' check \
  scopeproof_core/schemas/models.py tests/schemas/test_manual_verification.py
```

Expected: all tests pass and Ruff prints `All checks passed!`.

- [ ] **Step 5: Commit the schema invariant**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_manual_verification.py
git commit -m "fix: require manual verification notes"
```

### Task 2: Recoverable Streamlit prerequisite state

**Files:**
- Modify: `apps/web/app.py:753-767`
- Modify: `tests/apps/test_streamlit_app.py:730-750`

**Interfaces:**
- Consumes: `decision: HumanDecision | None` and `resolution_note: str` from the existing Streamlit controls.
- Produces: `manual_verification_ready: bool`, stable prerequisite copy, and a disabled save action until the conditional note is valid.

- [ ] **Step 1: Write the failing Streamlit readiness regression**

Add before `test_successful_manual_verification_clears_conditional_evidence_level`:

```python
@pytest.mark.parametrize("note", ["", "   ", "\t\n"])
def test_manual_verification_requires_nonblank_reviewer_note(note: str) -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.MANUALLY_VERIFIED
    ).run()
    app = app.text_area(key="resolution_note").set_value(note).run()

    assert app.button(key="save_resolution").disabled is True
    assert len(app.session_state["review_state"].resolution_events) == 0
    assert (
        "Reviewer note is required for manual verification. Describe what was verified."
    ) in [item.value for item in app.caption]
```

Update the successful manual-verification test to set a real note before saving and assert it is
preserved in the appended event:

```python
app = app.text_area(key="resolution_note").set_value(
    "Verified the export in staging."
).run()
assert app.button(key="save_resolution").disabled is False
app = app.button(key="save_resolution").click().run()

assert app.session_state["review_state"].resolution_events[0].comment == (
    "Verified the export in staging."
)
```

- [ ] **Step 2: Run the readiness tests and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py -q \
  -k 'manual_verification_requires_nonblank_reviewer_note or successful_manual_verification'
```

Expected: the three invalid-note cases fail because `Save resolution` is enabled and the caption is missing; the updated success case errors or fails because the schema now rejects its previously blank note.

- [ ] **Step 3: Implement the Streamlit prerequisite**

After the conditional manual-level selector, derive readiness and render the stable prerequisite:

```python
manual_verification_ready = (
    decision is not HumanDecision.MANUALLY_VERIFIED or bool(resolution_note.strip())
)
if not manual_verification_ready:
    st.caption(
        "Reviewer note is required for manual verification. Describe what was verified."
    )
```

Change the button readiness to:

```python
disabled=decision is None or not manual_verification_ready,
```

- [ ] **Step 4: Run focused Streamlit, schema, and lifecycle tests and verify GREEN**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py tests/schemas/test_manual_verification.py \
  tests/reviews/test_lifecycle.py -q
'/Users/yjian070/Documents/New project 2/.venv/bin/ruff' check \
  apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
```

Expected: all tests pass, Ruff is clean, and `git diff --check` emits no output.

- [ ] **Step 5: Commit the recoverable UI state**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: guard manual verification submission"
```

### Task 3: Complete verification and protected publication

**Files:**
- Verify only; no planned source edits.

**Interfaces:**
- Consumes: the branch tree containing the design, schema guard, UI readiness guard, and regressions.
- Produces: source, benchmark, wheel, HTTP, browser, and protected-GitHub evidence for the exact branch.

- [ ] **Step 1: Run the complete local gates**

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/ruff' check .
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.evals.runner
git diff --check
git status --short --branch
```

Expected: Ruff passes; all offline tests pass with one documented skip; 12 benchmark cases and 13 criteria execute with zero mismatches, zero must-have False Ready, and zero false blockers; the worktree is clean after committed changes.

- [ ] **Step 2: Build and verify a clean wheel**

Build with `pip wheel --no-deps` into a new `/tmp/scopeproof-manual-note-*` directory. Install it in a clean virtual environment, run `pip check`, and run a source-independent probe that proves both models reject empty, spaces-only, and tab/newline-only notes while preserving `"  Verified in staging  "` exactly. Record the wheel SHA-256.

Expected: package version remains `0.1.17.dev0`, every invalid note is rejected, valid evidence text is unchanged, and `pip check` reports no broken requirements.

- [ ] **Step 3: Run packaged HTTP smoke and browser audit**

Start the clean-installed `scopeproof-web` on an unused loopback port and require `/_stcore/health` to return exactly `ok`. In the current in-app Browser, open the packaged app, load the deliberately constructed demo, confirm criteria, run deterministic analysis, select `Manually Verified`, and leave the reviewer note empty. Do not save the resolution, runtime evidence, or final acceptance.

Require:

- the prerequisite caption is visible;
- `Save resolution` is disabled;
- no resolution event is appended;
- the final-acceptance boundary and blocked demo verdict remain unchanged;
- browser error/warning diagnostics are empty.

Save and inspect the accepted same-state screenshot beside the baseline audit image. Compare the two at the same viewport and document the resolved readiness gap plus screenshot-only accessibility limits.

- [ ] **Step 4: Publish and merge through protected GitHub**

Push `codex/manual-verification-note-guard`. Create a ready pull request with the reproduced blank-note-to-Ready evidence, regression-first proof, unchanged gate semantics for valid events, clean-wheel and browser evidence, and permanent no-cost/no-fork boundaries. Do not comment on issue #3 or publish a release.

Wait for every PR `verify`, ScopeProof evidence review, CodeQL language job, and aggregate CodeQL result. Fix only genuine failures. Merge with squash and expected head SHA only when all checks are green.

- [ ] **Step 5: Verify protected main and clean local state**

Wait for post-merge main CI and CodeQL success. Fast-forward local `main`, confirm `HEAD == origin/main`, remove the owned worktree, prune it, delete the owned local branch after confirming its tree matches merged `main`, and verify:

- no open PR remains;
- all open Dependabot, code-scanning, and secret-scanning alert counts are zero;
- every Action reference remains pinned to a full SHA;
- issue #3 still has no genuine external response unless live state changed;
- latest release remains v0.1.16 because this correction does not justify standalone release churn;
- root `git status --short --branch` is clean.

Immediately rotate the persistent goal into the next evidence-backed finite loop.
