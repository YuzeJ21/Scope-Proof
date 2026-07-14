# Active Review-State Integrity Design

## Problem

`ReviewState` persists two representations of the active review: `review` at the lifecycle-state
level and `bundle.review` inside the active analyzed bundle. Lifecycle services construct and update
them together, but the Pydantic model does not require them to agree.

A deterministic current-main probe changed the top-level review ID, repository, and head SHA while
leaving the active bundle unchanged. `ReviewState.model_validate(...)` accepted the object.
`JsonReviewStore.save(...)` then named the file from the top-level review ID, while
`export_markdown(state)` reported the bundle's different review ID, repository, and head SHA. One
validated persisted object can therefore disagree about which review and commit it represents.

This is an active-state integrity defect, not a storage-path or exporter-rendering defect. Storage
and exporters each consume a documented part of `ReviewState`; the authoritative Pydantic boundary
must reject contradictory active identity before either consumer runs.

## Intended Outcome

When `ReviewState.bundle` is present, require `ReviewState.review` to equal
`ReviewState.bundle.review` as complete validated `Review` objects.

Full equality covers review ID, repository, pull request, base and head SHAs, check and ingestion
states, criteria confirmation, limitations, final acceptance, creation time, tool version, and
ruleset version. This prevents future review fields from silently bypassing the integrity rule.

When `bundle` is `None`, no comparison is required. That state is valid while criteria are revised
or confirmed before a replacement analysis. `analysis_history` remains historical and may contain
older criteria, gate, acceptance, or commit provenance; it is deliberately excluded from active
identity equality.

## Approaches Considered

### 1. Compare only review ID, repository, PR number, and head SHA

This addresses the reproduced example but leaves other active provenance able to diverge, including
base SHA, ingestion completeness, criteria confirmation, final acceptance, and version identity.
Every future `Review` field would require another hand-maintained list update.

### 2. Require complete active `Review` equality — selected

This expresses the lifecycle invariant directly, automatically covers every validated review field,
and preserves the intentional distinction between the active bundle and historical bundles.

### 3. Automatically copy one review over the other during validation

Normalization would make the object internally consistent but conceal which side was corrupted. It
could silently rewrite storage identity, provenance, or gate inputs. ScopeProof should reject
contradictory audit state and require the caller to reconstruct it through lifecycle services.

## Architecture and Data Flow

Add one `model_validator(mode="after")` to `ReviewState` in
`scopeproof_core/schemas/models.py`:

1. If no active bundle exists, return the state unchanged.
2. If `bundle.review != review`, raise a stable `ValueError` stating that the active bundle review
   must match the lifecycle review.
3. Otherwise return the state unchanged.

`new_review_state`, `_recalculate`, `append_resolution`, and `append_runtime_evidence` already keep
the two objects aligned. `revise_criteria` intentionally removes the active bundle before changing
the lifecycle review. No service or adapter change is required.

## Error and Compatibility Behavior

- Saved JSON with contradictory active review identity fails during `ReviewState` validation before
  it can be reopened, exported, or resaved.
- Valid current records and historical records whose active reviews agree continue to load.
- Bundle-less pending-revision states remain valid.
- Historical analysis bundles may retain older review facts.
- The validator rejects contradictory input; it does not infer, normalize, or overwrite identity.
- No raw Pydantic output is added to the Streamlit UI; its existing load error boundary remains the
  user-facing recovery path.

## Regression Coverage

Add focused tests proving:

- each differing active `Review` field causes `ReviewState` validation to fail;
- a valid state with an active bundle round-trips unchanged;
- a bundle-less revised or confirmed state remains valid;
- `JsonReviewStore.load(...)` rejects a saved record whose top-level and bundle review identities
  differ;
- valid lifecycle resolution, runtime-evidence, save/reopen, and export paths remain green.

Verification includes focused schema, lifecycle, storage, and reporting tests, Ruff, the complete
offline suite, the 12-case deterministic benchmark, `git diff --check`, a clean wheel build and
external installation smoke, and the installed local workbench health endpoint. These checks prove
controlled object integrity, not external runtime evidence, adoption, or final acceptance.

## Out of Scope

- Requiring historical `analysis_history` reviews to equal the active review.
- Changing review fields, record versions, storage filenames, lifecycle services, exporters, UI
  copy, evidence, findings, resolutions, runtime evidence, final acceptance, or gates.
- Auto-repairing contradictory saved records or adding migrations without real affected records.
- Paid APIs, LLMs, billing, organizations, accounts, private repositories, forks, untrusted PR-code
  execution, synthetic validation, comments, or a release.
