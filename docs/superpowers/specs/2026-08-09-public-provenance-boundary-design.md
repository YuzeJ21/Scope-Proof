# Verified Public Provenance Boundary

## Problem

ScopeProof currently treats any successful non-fixture GitHub pull-request fetch as
`live_public_github`. An optional token can make a private repository readable, so a
successful response is not evidence that the repository is public. That unsupported
label can flow into saved reviews, exports, and genuine-alpha outcomes.

## Decision

Introduce a typed `RepositoryVisibility` fact with two persisted states:

- `verified_public`: GitHub returned an unambiguous public visibility assertion for
  the repository that owns the requested pull request.
- `unverified`: no current verified-public assertion exists. This is the default for
  historical records and local/demo fixtures.

GitHub ingestion is the only adapter allowed to produce `verified_public`. It must
require a complete repository object whose `full_name` matches the requested
repository, whose `private` field is exactly `false`, and whose `visibility` field is
exactly `public`. An explicit private/internal value is rejected as private or
inaccessible. Missing, malformed, mismatched, or contradictory metadata is rejected
with a bounded visibility-unverified error. No snapshot is returned on either path.

## Data flow

`PullRequestSnapshot.repository_visibility` carries the ingestion result. Review
construction copies it to `Review.repository_visibility`. A review may be labeled
`LIVE_PUBLIC_GITHUB` only when the snapshot is `verified_public`; current CLI and web
paths fail closed otherwise. The field is included automatically in validated saved
records and JSON exports.

Historical saved reviews remain readable because missing fields validate as
`unverified`. They are not silently migrated to `verified_public`. A fresh GitHub
fetch and normal criteria reconfirmation are required to create a newly verified
review.

Genuine-alpha qualification is split into a session-only intake and a verified
qualification. `AlphaQualificationInput` validates the pre-fetch human inputs.
`AlphaQualification` adds a required `verified_public` fact obtained from the loaded
snapshot. `AlphaCaseRecord` persists that fact; legacy cases default to `unverified`
and cannot record outcomes or produce public summaries. Outcome recording requires
both the case and the matching review to be verified public.

## Security and privacy invariants

- Tokens remain HTTP-client state only and are never added to a model, exception,
  log, saved record, or export.
- Private, internal, missing, malformed, contradictory, and repository-mismatched
  visibility responses fail closed before files, commits, or checks are fetched.
- Local fixtures and the constructed demo remain usable but never become live-public
  evidence.
- All persisted and exported data remains Pydantic-validated.
- Legacy records remain inspectable while carrying an explicit `unverified` fact.
- No target-repository code is executed.

## Verification

Regression coverage spans GitHub ingestion, schema validation, CLI review, Streamlit
loading and analysis, alpha qualification and outcomes, local save/reopen, and JSON
export. Focused tests are run red before the implementation. The final branch must
also pass the full repository verification, reproducible wheel, installed-package,
workbench, browser, and GitHub check gates defined by the owner objective.
