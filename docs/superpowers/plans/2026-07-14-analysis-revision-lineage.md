# Analysis Revision Lineage Implementation Plan

> **Goal:** Make every new lifecycle analysis self-identify its criteria revision
> while migrating legacy local history as explicit unknown rather than inferred
> evidence.

> **Design:** `docs/superpowers/specs/2026-07-14-analysis-revision-lineage-design.md`

## Task 1: Bind lifecycle analyses to criteria revisions

**Files:**

- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Test: `tests/schemas/test_review_state_integrity.py`
- Test: `tests/reviews/test_lifecycle.py`

### Step 1: Add failing lifecycle provenance tests

Add a skipped-analysis sequence:

1. Start with revision-1 analysis.
2. Confirm revision 2 without analyzing it.
3. Confirm and attach revision-3 analysis.
4. Revise again to revision 4.

Assert history is self-describing as revisions `[1, 3]` and the pending active
revision is 4. Also add rejections for:

- an active bundle whose revision does not equal the active criteria revision;
- a known historical revision equal to or above the active revision;
- duplicate or decreasing known historical revisions.

Run the new tests and verify RED because `ReviewBundle` has no revision field.

### Step 2: Add the Pydantic contract

Add `criteria_revision_number` to `ReviewBundle` as a positive integer or the
literal `"unknown"`, defaulting to `"unknown"` for standalone compatibility.

Extend `ReviewState` validation so:

- an active bundle requires a known revision equal to the active revision;
- known history revisions are lower than active, unique, and increasing;
- unknown historical values remain allowed without being converted.

### Step 3: Bind lifecycle transitions

- `new_review_state()` installs a deep-copied active bundle with revision 1.
- `attach_analysis()` installs a deep-copied active bundle with the current
  confirmed revision number, regardless of the incoming standalone marker.
- Existing revision/history/event state remains preserved.

Add mutation-isolation coverage for the revision field.

### Step 4: Run focused verification

```bash
.venv/bin/ruff check scopeproof_core/schemas/models.py scopeproof_core/reviews/lifecycle.py tests/schemas/test_review_state_integrity.py tests/reviews/test_lifecycle.py
.venv/bin/pytest tests/schemas/test_review_state_integrity.py tests/reviews/test_lifecycle.py -q
git diff --check
```

Commit the bounded change.

## Task 2: Migrate local records without inventing history

**Files:**

- Modify: `scopeproof_core/storage/json_store.py`
- Test: `tests/storage/test_json_store.py`

### Step 1: Add failing versioned-record tests

Add tests proving:

- new saves write `record_version: 2` and preserve known active/history revision
  numbers;
- a version-1 record loads with its active bundle bound to the active criteria
  revision and every historical bundle marked `"unknown"`;
- saving the migrated state writes version 2 without changing unknown history;
- unknown record versions remain rejected;
- migrated content still crosses Pydantic and deterministic-gate validation.

Run focused tests and verify RED against the current exact-version-1 loader.

### Step 2: Implement the narrow migration

Set `RECORD_VERSION = 2`. Accept record versions 1 and 2 only.

For version 1, deep-copy `payload["state"]`, inject the active revision number
into the active bundle when present, inject `"unknown"` into every historical
bundle, then validate through `ReviewState.model_validate(...)` and
`validated_review_state(...)`.

Do not infer historical integers and do not mutate the parsed source object in
place.

### Step 3: Run focused verification

```bash
.venv/bin/ruff check scopeproof_core/storage/json_store.py tests/storage/test_json_store.py
.venv/bin/pytest tests/storage/test_json_store.py -q
git diff --check
```

Commit the bounded change.

## Task 3: Expose and verify revision provenance

**Files:**

- Modify: `tests/reporting/test_lifecycle_exports.py`
- Modify: `docs/privacy-readiness.md`

### Step 1: Add export characterization coverage

Prove canonical JSON contains:

- the current active integer revision;
- known historical integer revisions for new lifecycle history;
- `"unknown"` for migrated legacy history.

The export must equal the validated state's JSON model dump and must not infer or
rewrite unknown history.

### Step 2: Document the local-record meaning

Update privacy/readiness documentation to state that new local history records
the producing criteria revision and migrated legacy history explicitly reports
unknown revision lineage when it cannot be proven.

Do not claim legacy lineage was recovered.

### Step 3: Run all local gates

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff clean; no test failures; 12 benchmark cases, zero must-have False
Ready, zero false blockers, zero mismatches; clean diff.

### Step 4: Verify distribution/runtime

Build a wheel into a temporary directory, install it in a clean virtual
environment, run `pip check`, both version CLIs, the installed benchmark, and a
fresh-HOME packaged Streamlit `/_stcore/health` probe.

### Step 5: Review and publish

Run an independent whole-branch review from the exact main base. Push a
`codex/` branch and open one protected PR only if local review is clean. Wait for
`verify` and CodeQL, merge only when green, synchronize local `main`, and verify
both workflows against the exact merged SHA. Do not create a release, issue
comment, fork, paid API call, organization, private repository, or synthetic
external evidence.
