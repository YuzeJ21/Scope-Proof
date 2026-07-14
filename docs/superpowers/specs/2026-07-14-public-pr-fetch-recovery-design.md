# Public PR Fetch Recovery Design

## Reproduced gap

The first-use public-PR path rendered the safe GitHub ingestion error but did
not tell the user whether entered requirements or prepared criteria survived,
what to verify, or when the optional token is appropriate. A deterministic
Streamlit test reproduced the missing recovery guidance while confirming that
the URL, requirements text, and prepared criterion were retained.

## Decision

Keep the existing typed `GitHubIngestionError` message and append one concise
recovery contract:

- no review data was changed;
- verify that the PR is public and retry;
- use the optional token only when GitHub reports a rate limit.

The fetch remains user-triggered and read-only. Failure does not reset source,
criteria, analysis, resolution, or review state. The existing unsaved-review
replacement guard remains authoritative.

## Evidence boundary

The regression test uses a controlled network failure to validate workbench
state preservation and copy. It is product-behavior evidence only, not external
PR evidence, runtime verification of a third-party repository, or proof that a
PR meets acceptance criteria.

## Boundaries

No paid API/LLM, billing, fork, organization, private repository, token
persistence, automatic retry, untrusted code execution, gate change, or
synthetic validation is introduced.
