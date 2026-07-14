# Export State Revalidation Design

## Problem

ScopeProof exporters accept already-constructed `ReviewState` and `ReviewBundle` instances. Pydantic
models are mutable and `model_copy(...)` does not rerun validators, so type annotations alone do not
prove that an object remains valid at export time.

A current-main probe changed only the top-level `ReviewState.review.head_sha`. All four exporters
accepted the contradictory object:

- JSON emitted both conflicting head SHAs in one artifact;
- Markdown, CSV, and HTML silently selected the nested bundle SHA and concealed the conflicting
  lifecycle SHA.

The schema, persistence, and lifecycle boundaries reject this contradiction, but a caller can still
export an invalid in-memory object directly. This violates the repository rule that every exported
object must be validated with Pydantic schemas.

## Intended Outcome

Every export reconstructs and validates its complete input before serialization or rendering.

- A `ReviewState` is rebuilt through `ReviewState.model_validate(...)`.
- A `ReviewBundle` is rebuilt through `ReviewBundle.model_validate(...)`.
- JSON serializes the validated reconstruction.
- Markdown, CSV, and HTML resolve their bundle and optional state only after reconstruction.

Invalid input is rejected. Exporters do not choose one conflicting identity, normalize fields, or
emit a partially valid artifact.

## Selected Design

Add one private `_validated_exportable(value)` helper in `scopeproof_core.reporting.exporters`. It
uses `model_dump(mode="python")` followed by the correct concrete Pydantic model's validation.

`export_json(...)` calls the helper before dumping. `_bundle_and_state(...)`, already shared by the
other three exporters, calls it before testing for an active bundle or returning render inputs.

This is preferred over:

- validating only the active review identity by hand, which duplicates schema rules and misses
  other mutated nested fields;
- validating only `ReviewState`, because direct `ReviewBundle` export is also public;
- repairing one side of a contradiction, which would conceal corrupted audit provenance;
- global frozen models or assignment validation, which is a broader compatibility change and still
  does not make every exported object boundary explicit.

## Compatibility and Error Behavior

- Valid state and bundle exports remain byte-for-byte equivalent.
- Bundle-less state retains the existing confirmed-analysis error after successful validation.
- Contradictory active identity retains the stable schema message `active bundle review must match
  lifecycle review`.
- Other mutated nested fields fail their existing schema validator messages.
- No export format, field, escaping rule, gate, evidence level, or final-acceptance behavior changes.

## Verification

Regression tests require JSON, Markdown, CSV, and HTML to reject both a contradictory state and an
invalid directly supplied bundle. Existing snapshot/content and escaping tests must remain green.
Repository-wide verification includes Ruff, all offline tests, the deterministic benchmark, clean
wheel installation and installed benchmark, and packaged workbench health.

## Out of Scope

- Global immutability or assignment validation.
- Persistence, lifecycle, schema, UI, GitHub workflow, gate, evidence, or report-format changes.
- Paid APIs, billing, organizations, second accounts, private repositories, forks, untrusted code
  execution, synthetic validation, comments, or a release.
