# Candidate Evidence Context Guard Design

## Problem

`EvidenceItem` currently uses `min_length=1` for several required strings and no semantic
validator for candidate limitations. As a result, Pydantic accepts whitespace-only excerpts,
matching rules, relevance reasons, and limitations. A validated `ReviewBundle` can therefore
export a candidate-evidence entry whose reason, excerpt, and limitation are visually blank.

This is an evidence-integrity defect. ScopeProof must either cite explicit evidence or state what
is missing; a whitespace-only candidate must not survive validation as explicit evidence.

## Reproduced behavior

A controlled local probe constructed an `EvidenceItem` with `excerpt="   "`,
`matching_rule=" "`, `relevance_reason="\t"`, and `limitations=["   "]`. The model and a
containing `ReviewBundle` both validated. Markdown export then rendered a candidate link followed
by a blank reason, blank excerpt, and blank limitation.

## Decision

Add one field validator that rejects whitespace-only values for the required candidate-evidence
identity and context fields:

- `evidence_id`
- `criterion_id`
- `file_path`
- `commit_sha`
- `permalink`
- `excerpt`
- `matching_rule`
- `relevance_reason`

Add a list validator that rejects any whitespace-only member of `limitations`. Empty limitation
lists remain valid. Valid values are preserved exactly rather than stripped so evidence bytes do
not change silently during validation.

Advance the post-release development identity from `0.1.17` to `0.1.18.dev0` in the same first
post-release change, following the established release-line convention.

## Rejected alternatives

- **Filter blanks during export.** This would silently repair only one representation while JSON
  storage and future adapters retained invalid evidence.
- **Normalize by stripping.** This would mutate persisted evidence rather than reject an invalid
  record.
- **Add URL, SHA-format, or criterion-ID semantics.** Those are separate contracts and would make
  this bounded whitespace fix broader than the reproduced defect.
- **Change retrieval or gate logic.** The trusted retrieval path already emits nonblank context;
  the missing defense is at the persisted Pydantic boundary.

## Verification

Regression tests first prove every required field rejects empty, spaces-only, and tab/newline-only
values; limitation tests prove blank members are rejected while an empty list remains valid; a
preservation test proves valid surrounding whitespace is unchanged. Repository contracts prove the
new development identity. Full Ruff, pytest, deterministic benchmark, archived-wheel identity,
installed benchmark, and loopback health checks follow before protected integration.

Controlled schema and packaging results do not establish external PR runtime evidence, customer
validation, or adoption. No billing, paid API or LLM, private repository, second account,
organization, fork test, synthetic validation, or invented evidence is involved.
