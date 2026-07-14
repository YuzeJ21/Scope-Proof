# Reanalysis Lineage Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve one ScopeProof review's identity, criteria revision number, historical analyses, and prior resolution events when confirmed edited criteria are analyzed again.

**Architecture:** Add one core lifecycle operation that attaches a validated static analysis to a confirmed bundleless revision and revalidates the resulting `ReviewState`. The Streamlit analysis action chooses the existing new-review constructor only for first analysis and the attachment operation for reanalysis.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- Never execute untrusted pull-request code.
- Preserve deterministic gate evaluation and the existing False Ready bias.
- Do not carry prior-revision human decisions into the active revision.
- Reject contradictory state; do not repair, normalize, or synthesize audit history.
- Keep lifecycle rules independent from Streamlit.

---

### Task 1: Core analysis attachment boundary

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/reviews/__init__.py`
- Test: `tests/reviews/test_lifecycle.py`

**Interfaces:**
- Consumes: `ReviewState` with `bundle is None` and confirmed `criteria_revision`; independently validated `ReviewBundle`.
- Produces: `attach_analysis(state: ReviewState, bundle: ReviewBundle) -> ReviewState`.

- [ ] **Step 1: Write the failing valid-path lifecycle test**

Create a revision with `revise_criteria(...)`, confirm it, construct a deterministic bundle for the edited criteria, and assert that `attach_analysis(...)` preserves the original review ID, revision number, history, and prior events while installing the edited active criteria.

- [ ] **Step 2: Run the valid-path test and verify RED**

Run:

```bash
.venv/bin/pytest tests/reviews/test_lifecycle.py::test_attach_analysis_preserves_reanalysis_lineage -q
```

Expected: collection fails because `attach_analysis` is not defined.

- [ ] **Step 3: Write failing rejection tests**

Cover an existing active bundle, unconfirmed revision, mismatched criteria,
mismatched source text, mismatched review provenance, preloaded resolutions,
preloaded final acceptance, and a valid-then-mutated bundle.

- [ ] **Step 4: Implement the minimal core operation**

Add:

```python
def attach_analysis(state: ReviewState, bundle: ReviewBundle) -> ReviewState:
    state = _validated_state(state)
    bundle = validated_review_bundle(bundle)
    if state.bundle is not None:
        raise ValueError("analysis attachment requires a pending revision without an active bundle")
    if not state.criteria_revision.confirmed:
        raise ValueError("analysis attachment requires a confirmed criteria revision")
    if bundle.resolutions:
        raise ValueError("attached analysis must not contain human resolutions")
    if bundle.review.final_acceptance:
        raise ValueError("attached analysis must not contain final acceptance")
    if bundle.criteria != state.criteria_revision.criteria:
        raise ValueError("attached analysis criteria must match the active revision")
    if bundle.source_text != state.criteria_revision.source_text:
        raise ValueError("attached analysis source must match the active revision")
    rebound_review = bundle.review.model_copy(
        update={
            "review_id": state.review.review_id,
            "created_at": state.review.created_at,
        }
    )
    if rebound_review != state.review:
        raise ValueError("attached analysis review must match the lifecycle review")
    active_bundle = bundle.model_copy(deep=True)
    active_bundle.review = state.review.model_copy(deep=True)
    return validated_review_state(state.model_copy(update={"bundle": active_bundle}))
```

Export `attach_analysis` from `scopeproof_core.reviews`.

- [ ] **Step 5: Run the focused lifecycle tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/reviews/test_lifecycle.py -q
```

Expected: all lifecycle tests pass.

### Task 2: Workbench reanalysis integration

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `attach_analysis(...)` from Task 1.
- Produces: a reanalysis button path that preserves the existing lifecycle state.

- [ ] **Step 1: Write the failing AppTest reproduction**

Analyze the demo, append final acceptance, edit `AC-01`, confirm the new criteria,
and run analysis again. Assert the original review ID, revision `2`, one historical
bundle, and the revision-1 event remain; assert the active bundle uses the edited
criterion and active final acceptance remains false.

- [ ] **Step 2: Run the AppTest and verify RED**

Run:

```bash
.venv/bin/pytest tests/apps/test_streamlit_app.py::test_reanalysis_preserves_review_lineage_and_prior_events -q
```

Expected: assertions show the current path resets the ID, revision, history, and events.

- [ ] **Step 3: Route reanalysis through the core operation**

Import `attach_analysis` and replace the unconditional constructor with:

```python
existing_state = st.session_state["review_state"]
st.session_state["review_state"] = (
    new_review_state(bundle)
    if existing_state is None
    else attach_analysis(existing_state, bundle)
)
```

- [ ] **Step 4: Run focused AppTest and lifecycle suites**

Run:

```bash
.venv/bin/pytest tests/apps/test_streamlit_app.py tests/reviews/test_lifecycle.py -q
```

Expected: all focused tests pass.

### Task 3: Persistence, export, and publication verification

**Files:**
- Modify: `tests/storage/test_json_store.py`
- Modify: `tests/reporting/test_lifecycle_exports.py`

**Interfaces:**
- Consumes: the attached `ReviewState` from Task 1.
- Produces: verified durable and exportable reanalysis lineage.

- [ ] **Step 1: Add round-trip boundary coverage**

Save and reload an attached state through `JsonReviewStore`, then render lifecycle
JSON and assert revision `2`, one historical bundle, and the stable review ID are
preserved.

Add a shared test construction pattern using the public lifecycle operations:

```python
state = new_review_state(build_demo_review())
revised = confirm_criteria(
    revise_criteria(state, state.criteria_revision.criteria, "Updated requirements")
)
incoming = build_demo_review()
incoming.review = incoming.review.model_copy(
    update={
        "repository": revised.review.repository,
        "pr_number": revised.review.pr_number,
        "base_sha": revised.review.base_sha,
        "head_sha": revised.review.head_sha,
        "check_state": revised.review.check_state,
        "criteria_confirmed": True,
        "ingestion_state": revised.review.ingestion_state,
        "ingestion_warnings": revised.review.ingestion_warnings,
        "skipped_files": revised.review.skipped_files,
        "tool_version": revised.review.tool_version,
        "ruleset_version": revised.review.ruleset_version,
    }
)
incoming.source_text = revised.criteria_revision.source_text
incoming.criteria = [item.model_copy(deep=True) for item in revised.criteria_revision.criteria]
attached = attach_analysis(revised, incoming)
```

- [ ] **Step 2: Run boundary tests**

Run:

```bash
.venv/bin/pytest tests/storage/test_json_store.py tests/reporting/test_lifecycle_exports.py -q
```

Expected: all storage and lifecycle-export tests pass.

- [ ] **Step 3: Run all local quality gates**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff clean; no test failures; 12 benchmark cases, zero must-have False
Ready, zero false blockers, zero mismatches; clean diff.

- [ ] **Step 4: Verify the built distribution and workbench health**

Build a wheel into a temporary directory, install it in a clean virtual
environment, verify `scopeproof --version`, `scopeproof-web --version`, the
installed benchmark, and `/_stcore/health == ok`.

- [ ] **Step 5: Commit and publish**

Commit the bounded implementation, push `codex/preserve-reanalysis-lineage`, open
a protected PR, wait for `verify` and CodeQL, merge only when green, synchronize
local `main`, and verify both workflows against the exact merged SHA.
