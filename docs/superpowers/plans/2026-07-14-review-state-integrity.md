# Active Review-State Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent one validated `ReviewState` from carrying contradictory active lifecycle and bundle review provenance.

**Architecture:** Add one Pydantic after-validator to `ReviewState`. When an active bundle exists, its complete nested `Review` must equal the top-level lifecycle `Review`; bundle-less pending-revision states and historical analysis bundles retain their existing semantics. Storage, exporters, lifecycle operations, and UI remain consumers of the validated state.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, Ruff, existing lifecycle and local JSON store.

## Global Constraints

- No paid API, LLM, billing, organization, second account, private repository, or fork testing.
- Never execute untrusted PR code or invent evidence, requirements, findings, runtime results, users, or validation.
- Preserve deterministic gates, False Ready safety, evidence levels, final acceptance, and local-first behavior.
- Keep the core engine independent from Streamlit and GitHub UI layers.
- Reject contradictory state; do not normalize or auto-repair it.
- Do not compare historical analysis bundles to the active review.
- Do not publish a release for this schema-only integrity slice.

---

### Task 1: Reproduce active review divergence

**Files:**
- Create: `tests/schemas/test_review_state_integrity.py`

**Interfaces:**
- Consumes: `ReviewState.model_validate(payload)` and real lifecycle-created state.
- Produces: focused regressions for active-review equality and valid bundle-less pending state.

- [ ] **Step 1: Add failing active-divergence tests**

Create `tests/schemas/test_review_state_integrity.py` with:

```python
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import ReviewState


ACTIVE_REVIEW_OVERRIDES = [
    {"review_id": "different-review"},
    {"repository": "acme/different"},
    {"pr_number": 999},
    {"base_sha": "different-base"},
    {"head_sha": "different-head"},
    {"check_state": "failing"},
    {"criteria_confirmed": False},
    {"ingestion_state": "partial", "ingestion_warnings": ["Different warning"]},
    {"ingestion_state": "partial", "skipped_files": ["src/different.py"]},
    {"final_acceptance": True},
    {"created_at": datetime(2020, 1, 1, tzinfo=UTC)},
    {"tool_version": "0.0.0-history"},
    {"ruleset_version": "0.0.0-history"},
]


@pytest.mark.parametrize("review_overrides", ACTIVE_REVIEW_OVERRIDES)
def test_review_state_rejects_divergent_active_bundle_review(review_overrides) -> None:
    payload = new_review_state(build_demo_review()).model_dump(mode="python")
    payload["review"].update(review_overrides)

    with pytest.raises(
        ValidationError, match="active bundle review must match lifecycle review"
    ):
        ReviewState.model_validate(payload)


def test_review_state_accepts_matching_active_bundle_review() -> None:
    state = new_review_state(build_demo_review())

    reopened = ReviewState.model_validate_json(state.model_dump_json())

    assert reopened == state


def test_review_state_accepts_bundleless_pending_revision() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        state.criteria_revision.source_text,
    )

    reopened = ReviewState.model_validate_json(revised.model_dump_json())

    assert reopened.bundle is None
    assert reopened.analysis_history == [state.bundle]
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas/test_review_state_integrity.py -q
```

Expected: 13 divergent cases fail because current `ReviewState` accepts them; the two valid-state cases pass.

### Task 2: Enforce complete active-review equality

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Test: `tests/schemas/test_review_state_integrity.py`

**Interfaces:**
- Consumes: `ReviewState.review` and optional `ReviewState.bundle.review`.
- Produces: `ReviewState.validate_active_review_identity() -> ReviewState` as a Pydantic after-validator.

- [ ] **Step 1: Add the minimal validator**

Add this method to `ReviewState`:

```python
@model_validator(mode="after")
def validate_active_review_identity(self) -> ReviewState:
    if self.bundle is not None and self.bundle.review != self.review:
        raise ValueError("active bundle review must match lifecycle review")
    return self
```

- [ ] **Step 2: Run focused tests and verify GREEN**

Run the Task 1 command.

Expected: all 15 tests pass with no warnings.

- [ ] **Step 3: Run lifecycle and reporting regressions**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/reviews tests/reporting -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  scopeproof_core/schemas/models.py tests/schemas/test_review_state_integrity.py
```

Expected: all tests and Ruff pass. Existing resolution, runtime-evidence, final-acceptance, and export paths remain unchanged.

### Task 3: Prove corrupted local records cannot reopen

**Files:**
- Modify: `tests/storage/test_json_store.py`

**Interfaces:**
- Consumes: version-one local JSON records loaded through `JsonReviewStore.load(review_id)`.
- Produces: a regression proving contradictory active review identity is rejected by nested Pydantic validation.

- [ ] **Step 1: Add the storage regression**

Add to `tests/storage/test_json_store.py`:

```python
def test_load_rejects_mismatched_active_bundle_review(tmp_path: Path) -> None:
    store = JsonReviewStore(tmp_path)
    path = store.save(review_state())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["review"]["head_sha"] = "different-head"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError, match="active bundle review must match lifecycle review"
    ):
        store.load("review-1")
```

- [ ] **Step 2: Run schema, storage, lifecycle, and reporting tests**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/schemas tests/storage tests/reviews tests/reporting -q
```

Expected: all tests pass, including valid save/reopen and historical bundle behavior.

### Task 4: Verify, package, and commit

**Files:**
- Verify all changed files.

**Interfaces:**
- Consumes: completed active-state integrity changes.
- Produces: reviewed commits ready for protected publication.

- [ ] **Step 1: Run repository-wide checks**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; all tests pass; benchmark executes 12 cases with zero mismatches, zero must-have False Ready, and zero false blockers; diff is clean.

- [ ] **Step 2: Build and verify a clean external wheel installation**

Build the branch wheel under `/tmp/scopeproof-review-state-wheel`, install it into a fresh
`/tmp/scopeproof-review-state-venv`, require `pip check`, exact `scopeproof 0.1.18.dev0`, and the
installed 12-case benchmark with the same zero-error metrics.

- [ ] **Step 3: Verify the installed workbench health endpoint**

Run the installed `scopeproof-web` on `127.0.0.1:8515`, poll `/_stcore/health` until it returns
exactly `ok`, then stop it. Do not submit review, evidence, resolution, or acceptance data.

- [ ] **Step 4: Review and commit**

Run:

```bash
git diff --check
git add scopeproof_core/schemas/models.py \
  tests/schemas/test_review_state_integrity.py \
  tests/storage/test_json_store.py \
  docs/superpowers/specs/2026-07-14-review-state-integrity-design.md \
  docs/superpowers/plans/2026-07-14-review-state-integrity.md
git commit -m "fix: validate active review state identity"
```

Expected: one intentional commit containing only the bounded schema guard, regressions, and its design records.
