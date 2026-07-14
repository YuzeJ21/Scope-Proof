# ScopeProof Action-Evidence Context Guard Design

## Problem

`scopeproof validate-action-evidence` validates an owner-supplied public GitHub Action record
without contacting GitHub. The record is intentionally evidence-shaped rather than proof that the
URLs are real, but every required value still needs meaningful content before ScopeProof echoes the
object as validated.

Current `main` uses `Field(min_length=1)` for `requirements_base_sha`, `non_fork_head_sha`,
`rerun_head_sha`, and `validated_by`, plus `Field(min_length=1)` for the `limitations` list itself.
Pydantic therefore accepts strings containing only whitespace and a non-empty limitations list whose
only item is whitespace. A deterministic source probe successfully validated a record whose three
SHAs, validator identity, and sole limitation contained only spaces.

This is a persisted-object validation defect. It does not prove any current checked-in Action smoke
record is false, and the command still does not independently verify GitHub URLs.

## Existing Contracts

- The record represents owner-supplied public technical-smoke evidence.
- The validator checks local shape and same-head/idempotency consistency only; it does not contact
  GitHub or prove submitted URLs are genuine.
- A rerun must use the same head SHA and preserve the marker-matched comment count.
- `fork_status: excluded` is the permanent single-account public-alpha path and must not accept fork
  run details.
- The record must preserve user-supplied valid text rather than silently inventing or replacing it.
- No change may execute pull-request code, require billing, or create external validation activity.

## Chosen Design

Add focused validators to `ActionValidationRecord`:

1. `requirements_base_sha`, `non_fork_head_sha`, `rerun_head_sha`, and `validated_by` must each
   contain at least one non-whitespace character.
2. Every entry in `limitations` must contain at least one non-whitespace character. The existing
   list-level minimum still requires at least one limitation.
3. Valid values are returned unchanged. This slice rejects content-free evidence but does not
   normalize, trim, or claim to verify it.

Keep the existing model-level consistency checks unchanged. The CLI automatically inherits the
stronger schema because it already calls `ActionValidationRecord.model_validate_json` before
printing a record.

## Alternatives Considered

### 1. Enable global string stripping

Rejected. It would silently rewrite every string in the evidence object, including URLs and comment
markers, and would broaden the change beyond the demonstrated defect.

### 2. Require full 40-character hexadecimal Git SHAs

Deferred. That may be a useful shape-hardening decision, but current contract tests intentionally use
short deterministic identifiers. It is a separate compatibility decision and is not needed to reject
content-free evidence.

### 3. Validate the URLs live against GitHub

Rejected. The command is explicitly offline and cannot independently establish external truth. Live
verification would introduce network, authentication, rate-limit, and trust-boundary changes.

## Components and Data Flow

```text
owner-supplied JSON
        |
        v
ActionValidationRecord.model_validate_json
        |
        +-- required scalar content checks
        +-- per-limitation content checks
        +-- existing repository/link/marker/rerun/fork consistency checks
        |
        v
validated JSON echoed by the CLI
```

No Streamlit, lifecycle, gate, evidence-retrieval, export, storage-version, or GitHub Action workflow
code changes.

## Error and Safety Behavior

- A whitespace-only required scalar produces a stable Pydantic validation error and the CLI exits
  through its existing argparse error path.
- A limitations list containing any whitespace-only entry is rejected rather than silently dropping
  or rewriting the entry.
- A valid record remains byte-for-byte unchanged at the field-value level after validation.
- Existing same-repository, marker, same-head, comment-count, and fork-exclusion checks still run.
- Validation remains a local shape check and must not be described as proof of external truth.

## Verification

- Parameterized schema tests cover each required scalar with spaces, tabs, and newlines.
- Parameterized schema tests reject whitespace-only limitation entries.
- Preservation tests prove surrounding whitespace on otherwise nonblank human text is not silently
  rewritten by this slice.
- CLI regression coverage proves an invalid JSON record exits nonzero and does not emit validated
  output.
- Existing valid-record, rerun, repository-link, marker, and fork-exclusion tests remain green.
- Run Ruff, focused tests, the complete offline suite, the deterministic benchmark, package build and
  clean-install CLI smoke, and `git diff --check`.

## Out of Scope

- Contacting GitHub or proving URLs and runs exist.
- Changing SHA format compatibility, GitHub slug patterns, or record versioning.
- Changing Action execution, comments, workflows, branch protection, findings, gates, runtime
  evidence, final acceptance, or exports.
- Creating a new external Action run, issue comment, release, or other notification-producing event.

## Evidence Limits

The source probe and regression tests establish deterministic local validation behavior only. They
do not create or prove a real external Action run, public-PR outcome, runtime result, customer use, or
product adoption.
