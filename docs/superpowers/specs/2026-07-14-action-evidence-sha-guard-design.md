# ScopeProof Action-Evidence SHA Guard Design

## Problem

`ActionValidationRecord` stores the base requirements commit, the non-fork PR head commit, and the
same-head rerun commit. These identifiers anchor the requirements confirmation, comment marker, and
idempotency comparison. Current `main` requires only `min_length=1`, so arbitrary strings such as
`"x"`, `"not-a-sha"`, forty `g` characters, and 39- or 41-character hex strings all validate when
the marker and rerun value repeat the same arbitrary text.

This is an evidence-shape defect. The same-head comparison proves only equality; it does not prove
that either value has the shape of a GitHub commit ID.

## Authoritative Current Evidence

- Live GitHub PR #71 returned 40-character lowercase hexadecimal base, head, and merge commit IDs.
- Local `git rev-parse HEAD` returned the same 40-character lowercase hexadecimal shape.
- The checked-in public Action smoke record uses the exact 40-character head SHA
  `098fe7b83b3bb04adc924930e36a5ac727aa145b` in its comment marker.
- The external-validation runbook instructs the owner to copy the exact base/head SHA and marker,
  not an abbreviation.
- Only `tests/schemas/test_action_validation_record.py` and `tests/cli/test_cli.py` use shorthand
  identifiers such as `base123` and `head123`; they are controlled fixtures, not compatibility
  evidence from a user record.

## Chosen Design

Require `requirements_base_sha`, `non_fork_head_sha`, and `rerun_head_sha` to match exactly forty
lowercase hexadecimal characters:

```text
^[0-9a-f]{40}$
```

Migrate the two controlled Action-validation fixtures to deterministic 40-character lowercase
values. Keep all model-level behavior unchanged:

- the comment marker must exactly reference `non_fork_head_sha`;
- the rerun head must equal the non-fork head;
- the rerun comment count must equal the first-run count;
- all links must reference the same canonical public GitHub repository;
- `fork_status: excluded` must not include fork details.

The CLI inherits the stricter contract through its existing
`ActionValidationRecord.model_validate_json` call.

## Alternatives Considered

### 1. Accept either 40- or 64-character lowercase hexadecimal identifiers

Rejected for this public GitHub.com alpha. No current repository, live GitHub response, checked-in
smoke record, or documented workflow input provides a 64-character commit ID. Accepting an
unobserved shape would weaken the evidence boundary without a present compatibility requirement.

### 2. Accept abbreviated hexadecimal SHAs

Rejected. Abbreviations are context-dependent and can become ambiguous as a repository grows. The
runbook already requires copying the exact GitHub value.

### 3. Keep nonblank strings and rely on same-head equality

Rejected. Equality between two arbitrary strings does not establish commit-identifier shape and is
the reproduced defect.

## Components and Data Flow

```text
owner-supplied Action evidence JSON
        |
        v
Pydantic 40-char lowercase SHA field patterns
        |
        v
existing exact marker and same-head checks
        |
        v
validated offline record or deterministic schema error
```

No Streamlit, GitHub workflow, publishing, lifecycle, findings, gate, runtime-evidence,
final-acceptance, export, or storage-version code changes.

## Error and Safety Behavior

- Empty, whitespace-only, abbreviated, overlong, non-hexadecimal, and uppercase identifiers are
  rejected before a record can be printed as validated.
- A correctly shaped but nonexistent SHA may still pass local shape validation. The CLI remains
  explicitly offline and must not claim URL or commit existence.
- Changed but correctly shaped rerun heads still reach and fail the existing `same head SHA` check.
- Correctly shaped but mismatched markers still reach and fail the existing marker check.
- No identifier is trimmed, lowercased, expanded, or otherwise rewritten.

## Verification

- Parameterized schema tests cover every SHA field and invalid shape category.
- Existing marker and changed-head tests use alternative valid 40-character identifiers so they
  continue proving model-level semantics rather than failing early on field shape.
- CLI coverage proves an invalid commit identifier exits `2` and emits no validated JSON.
- A canonical record remains accepted and value-preserving.
- Run Ruff, focused tests, the complete offline suite, the deterministic benchmark, package build,
  clean-install valid/invalid CLI smokes, installed benchmark, and `git diff --check`.

## Out of Scope

- Contacting GitHub or proving a correctly shaped SHA exists.
- SHA-256 Git repository support without evidence from the supported GitHub.com surface.
- Changing Action workflow execution, comments, releases, branch protection, fork policy, paid
  services, or untrusted PR-code execution.

## Evidence Limits

This slice proves deterministic local shape validation only. It does not create or verify a public
PR, GitHub Action run, runtime result, customer, or product adoption event.
