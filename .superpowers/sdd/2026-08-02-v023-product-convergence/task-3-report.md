# Task 3 report — provenance lifecycle and v4 local records

## Implemented

- Made `new_review_state` require a validated bundle provenance snapshot and copy it into
  the initial criteria revision, including the snapshot's confirmation timestamp.
- Made criteria revision clear active review/revision provenance and confirmation time while
  retaining the superseded bundle, including its provenance, in append-only analysis history.
- Changed `confirm_criteria` to require a `CriteriaSourceProvenance`, revalidate it against the
  pending revision's exact source text and ordered criteria before mutation, and copy it into
  both the lifecycle review and active revision.
- Made `attach_analysis` require exact provenance equality across the lifecycle review,
  pending revision, and incoming bundle before review-identity rebinding.
- Made final-acceptance eligibility fail closed when active provenance is absent or unequal.
- Advanced local review records from version 3 to version 4 while retaining read support for
  versions 1 through 4.
- Made every v1-v3 load run one full active/history gate recomputation after the existing
  lineage, runtime-evidence, and CI migrations. No migration creates criteria provenance.
- Preserved legacy source text, ordered criteria, candidate evidence, runtime evidence facts,
  resolution events, reviewer attribution, and positive/negative final-acceptance facts.
  Historical positive final-acceptance events remain valid without provenance; only the gate
  interpretation becomes fail-closed.
- Updated directly affected lifecycle-report test helpers for the required confirmation
  signature. No report fields or export guards were implemented in this task.
- Corrected one stale comparison Ready fixture to provide a real validated source snapshot;
  the gate was not weakened.

## TDD record

1. Baseline reproduction: `uv run pytest -q tests/reviews/test_lifecycle.py` produced the
   disclosed **10 failed / 58 passed**. The stale provenance retained by `revise_criteria`
   contradicted the revised source/criteria before reanalysis.
2. RED lifecycle contract: after adding the required snapshot/clearing/equality/final-acceptance
   regressions and updating successful calls to the new API, the lifecycle file produced
   **20 failed / 53 passed**. Failures were the missing required argument and the four absent
   lifecycle guards.
3. GREEN lifecycle: the lifecycle file passed **73 tests**.
4. RED persistence contract: the focused v4 and v1-v3 migration selection produced
   **5 failed / 2 passed**. New saves still wrote v3 and v3 legacy gates were not recomputed.
5. GREEN persistence: the same selection passed **7 tests**; the complete storage file passed
   **67 tests** after aligning the prior v1 stale-gate test with the new full-recompute rule.
6. Broader affected run initially exposed one stale comparison fixture expecting `Ready`
   without provenance. Supplying validated fixture provenance restored the intended assertion.

## Fresh verification

- `uv run pytest -q tests/reviews/test_lifecycle.py tests/storage/test_json_store.py \
  tests/schemas/test_review_state_integrity.py tests/reporting/test_lifecycle_exports.py` —
  **209 passed**.
- `uv run pytest -q tests/reviews tests/storage tests/schemas \
  tests/gates/test_validation.py tests/reporting/test_lifecycle_exports.py` — **535 passed**.
- `uv run ruff check scopeproof_core/reviews/lifecycle.py \
  scopeproof_core/storage/json_store.py tests/reviews/test_lifecycle.py \
  tests/reviews/test_comparison.py tests/storage/test_json_store.py \
  tests/schemas/test_review_state_integrity.py \
  tests/reporting/test_lifecycle_exports.py` — **passed**.
- `git diff --check` — **passed**.

## Deferred downstream integration

- `apps/web/app.py` still uses the pre-provenance confirmation call. Task 6 must build the
  owner-confirmed snapshot from the new criteria-source inputs and pass it explicitly.
- CLI and trusted-base Action construction still require Task 4 propagation before their new
  review path can satisfy `new_review_state`.
- Export fields/guards and alpha-record propagation remain Task 5 scope.
- These are planned downstream slices, not evidence that this intermediate Task 3 commit is a
  complete product-convergence branch.
