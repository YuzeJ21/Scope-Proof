# Review Identity Guard Design

## Problem

`PullRequestSnapshot` and `Review` are authoritative Pydantic boundaries for public-PR identity and
persisted review provenance. Current `main` accepts whitespace-only base and head SHAs because
`Field(min_length=1)` counts whitespace as content. Its repository pattern also accepts whitespace
segments, so `" / "` passes validation.

A deterministic probe changed the demo bundle payload to repository `" / "`, base SHA `"   "`, and
head SHA `"\t"`. `ReviewBundle.model_validate(...)` accepted the payload, and the Markdown exporter
rendered all three values as review identity. This permits a persisted or imported object to claim
an unusable repository and blank commit provenance even though every export treats those fields as
audit identity.

This is a schema-boundary defect. The normal GitHub client supplies concrete values, but direct
model callers, saved JSON, and imported bundles must not rely on one ingestion adapter for identity
integrity.

## Intended Outcome

Reject invalid public-PR identity at both model boundaries:

- `PullRequestSnapshot.repository` and `Review.repository` must use the existing canonical GitHub
  owner/repository shape already enforced by `ActionValidationRecord`:
  `^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$`.
- `base_sha` and `head_sha` in both models must contain at least one non-whitespace character.
- Valid values remain unchanged; validators reject invalid input but do not trim or normalize it.
- Deliberately constructed fixtures and historical local reviews may keep readable non-40-character
  commit identifiers such as `base123` and `head-demo-002`.

`ReviewBundle` continues to rely on the nested `Review` model, so saved and imported bundles inherit
the same protection without exporter-specific checks.

## Approaches Considered

### 1. Validate only `Review`

This protects persisted and exported bundles, but lets malformed identity survive the retrieval
boundary until the review is constructed. It leaves two different definitions of acceptable PR
identity.

### 2. Validate `PullRequestSnapshot` and `Review` consistently — selected

This rejects malformed identity at ingestion and again at persistence/export. It follows the
existing defense-in-depth pattern, changes only Pydantic contracts, and requires no adapter or
exporter branching.

### 3. Require canonical 40-character hexadecimal Git SHAs

This is appropriate for live GitHub data but would invalidate the project's deliberately
constructed fixtures and historical local reviews that intentionally use readable identifiers.
Changing those artifacts would add migration and benchmark churn without improving the verified
blank-provenance defect.

## Architecture and Data Flow

Only `scopeproof_core/schemas/models.py` changes in production:

1. A shared repository pattern constant prevents drift between Action, snapshot, and review
   contracts.
2. `PullRequestSnapshot` and `Review` apply the same nonblank validator to `base_sha` and
   `head_sha`.
3. Existing callers continue constructing the same models and receive ordinary Pydantic validation
   errors for invalid identity.
4. Storage and JSON, Markdown, CSV, and HTML exporters remain unchanged because they consume only
   validated models.

No Streamlit or GitHub UI logic is introduced into the core engine.

## Error and Compatibility Behavior

- Whitespace-only SHAs fail with stable product-independent schema text stating that review
  identity must contain non-whitespace text.
- Repositories with blank segments, extra slashes, spaces, or unsupported GitHub characters fail
  the canonical pattern.
- Valid repository and SHA text is preserved exactly.
- Historical bundles with valid owner/repository identity and nonblank readable SHA tokens continue
  to reopen.
- No network call, PR code execution, paid service, telemetry, or external write is added.

## Regression Coverage

Add focused schema tests that prove:

- `PullRequestSnapshot` and `Review` reject whitespace-only base or head SHA values;
- both models reject whitespace repository segments;
- both models preserve valid repository and nonblank SHA values exactly;
- a `ReviewBundle` payload with malformed nested review identity is rejected before any exporter can
  consume it;
- the existing historical review round trip, demo fixture, storage tests, and all export formats
  remain valid.

Verification includes focused schema and reporting tests, Ruff, the complete offline pytest suite,
the deterministic 12-case benchmark, `git diff --check`, a clean wheel build and external
installation smoke, plus the local workbench health endpoint. This schema-only change does not
claim runtime evidence, external adoption, or reviewer acceptance.

## Out of Scope

- Requiring 40-character hexadecimal SHAs for deliberately constructed or historical data.
- Changing review IDs, versions, warnings, skipped-file paths, evidence, findings, runtime evidence,
  resolutions, final acceptance, gates, storage format, or exports.
- Adding generic security scanning, code review, auto-fix behavior, paid APIs, billing, forks,
  organizations, accounts, private repositories, or synthetic validation.
- Publishing a release solely for this schema hardening slice.
