# ScopeProof Action-Evidence GitHub Identity Guard Design

## Problem

`ActionValidationRecord` is the offline Pydantic boundary for owner-supplied public GitHub Action
evidence. Its repository pattern currently uses `[^/]+/[^/]+`, and its PR/run URL patterns use the
same unrestricted non-slash segments. Those character classes admit spaces, tabs, and other values
that cannot identify a canonical public GitHub repository.

After the blank-context guard merged, a deterministic probe still validated all of these records:

- repository `" / "` with URL prefix `https://github.com/ / `;
- repository `"ac me/de mo"` with matching space-containing URLs;
- repository `" acme/demo"` with matching leading-space URLs.

The existing same-repository check accepts them because the malformed repository and malformed URLs
agree with each other. This is a shape-validation defect, not evidence that any checked-in Action
smoke record is false.

## Existing Contracts

- The command remains offline and validates shape and internal consistency only.
- The command must not claim that a syntactically valid URL exists or that a run actually occurred.
- All PR and run URLs must refer to the record's same repository.
- Fork testing remains excluded, and excluded records must not contain fork details.
- Existing marker, same-head, and idempotent-comment checks remain authoritative.

## Chosen Design

Replace the permissive repository and URL path-segment patterns with explicit public GitHub slug
character sets:

- owner: ASCII letters, digits, and hyphens;
- repository: ASCII letters, digits, dots, underscores, and hyphens;
- PR URL suffix: `/pull/<positive decimal shape>` as already modeled;
- run URL suffix: `/actions/runs/<positive decimal shape>` as already modeled.

Apply the same patterns to non-fork, rerun, and optional fork URLs. Keep the existing same-repository
validator after the field-level shape checks.

This slice deliberately does not attempt live GitHub verification or encode every GitHub account
naming rule. It closes the reproduced whitespace/control-character path while retaining a stable,
readable public-GitHub identity contract.

## Alternatives Considered

### 1. Add only a `strip()` comparison

Rejected. It would catch leading and trailing whitespace but still accept embedded whitespace such
as `ac me/de mo`.

### 2. Change `[^/]` to `[^/\s]`

Viable but not selected. It closes whitespace while continuing to admit query delimiters,
percent-encoded material, and other characters that are not repository slug characters.

### 3. Parse URLs and verify them against GitHub live

Rejected. URL parsing alone does not prove repository identity, and live verification would violate
the documented offline boundary and introduce network/authentication behavior.

## Data Flow

```text
owner-supplied JSON
        |
        v
field-level canonical GitHub identity patterns
        |
        v
existing repository/link/marker/rerun/fork consistency checks
        |
        v
validated offline record or deterministic validation error
```

No workflow, comment, lifecycle, gate, Streamlit, storage-version, export, or external network code
changes.

## Error and Safety Behavior

- Whitespace/control characters in repository owners, repository names, PR URLs, and run URLs are
  rejected before the record can be printed as validated.
- Existing canonical fixtures remain unchanged and valid.
- Cross-repository URLs, mismatched markers, changed rerun heads, changed comment counts, and fork
  detail violations remain rejected by the existing model-level validator.
- A passing record remains only locally shape-valid; it is not described as verified external truth.

## Verification

- Schema tests parameterize malformed repository identities and all PR/run URL fields.
- Valid owner/repository characters including hyphens, dots, and underscores remain accepted.
- CLI regression coverage proves a whitespace-containing repository record exits `2` and emits no
  validated JSON.
- Run Ruff, focused tests, the complete offline suite, the deterministic benchmark, package build,
  clean-install CLI valid/invalid smokes, and `git diff --check`.

## Out of Scope

- Live URL existence checks or GitHub API calls.
- Full SHA-format hardening.
- GitHub Enterprise hosts or private repositories.
- Workflow execution, issue comments, releases, fork testing, paid services, or untrusted PR-code
  execution.

## Evidence Limits

The probes and regression tests prove only deterministic local shape validation. They do not prove a
repository, pull request, Action run, customer, or runtime result exists.
