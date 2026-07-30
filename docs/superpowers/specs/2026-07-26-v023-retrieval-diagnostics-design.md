# ScopeProof v0.2.3 Retrieval Diagnostics Design

## Status

Approved direction from the 2026-07-25 product-flow audit. This specification narrows
the first v0.2.3 Evidence Quality Sprint slice to explainable retrieval diagnostics.

## Problem

ScopeProof currently returns deterministic candidate evidence, but a criterion with no
candidate only receives a generic statement that no candidate was found. A reviewer
cannot inspect:

- which normalized criterion terms were searched;
- which changed or bounded unchanged paths were searched;
- how many inspectable lines were considered;
- whether exact-identifier requirements, overlap rules, or relevance thresholds removed
  every possible line.

That ambiguity makes a conservative `No candidate` result harder to trust. It also makes
retrieval defects difficult to convert into focused regression cases.

## Goals

1. Produce one deterministic, validated retrieval diagnostic for every analyzed criterion.
2. Explain the searched terms, paths, evidence types, line counts, candidate count, and
   primary outcome without exposing a correctness claim.
3. Persist diagnostics in new reviews and render them in the web flow and exports.
4. Preserve old saved reviews that do not contain diagnostics.
5. Keep every gate threshold, evidence level, and Ready/Blocked decision unchanged.
6. Preserve the completed R-002 scored artifacts and frozen metrics byte-for-byte.

## Non-goals

- Changing tokenization, stemming, scoring, ranking, thresholds, or candidate limits.
- Retuning the engine against the completed R-002 cohort.
- Adding semantic, embedding, LLM, code-execution, security, or generic review behavior.
- Treating search diagnostics as implementation, test, runtime, or correctness evidence.
- Claiming Stage 1, customer, or market validation.

## Considered approaches

### A. Validated diagnostic result beside candidate evidence — selected

The retrieval engine returns a validated result containing the existing evidence list and
one diagnostic per criterion. Existing `retrieve_evidence()` remains as a compatibility
wrapper. Product entry points use the richer result and persist diagnostics in the review
bundle.

This keeps diagnostics separate from evidence, exposes them to every product surface, and
prevents gate logic from accidentally treating diagnostic metadata as proof.

### B. Add diagnostic prose to `Finding.missing_evidence` — rejected

This is smaller, but it mixes two different concepts: evidence the reviewer still needs and
metadata about how ScopeProof searched. The result would also be difficult to validate or
analyze deterministically.

### C. Log diagnostics only during benchmarks — rejected

This would help engineering research but would not help the user understand a live review,
persisted review, or export.

## Data model

Add the following validated models to `scopeproof_core.schemas.models`:

### `RetrievalOutcome`

An enum with these exact values:

- `candidates_found`
- `no_searchable_terms`
- `no_inspectable_lines`
- `exact_identifier_not_found`
- `no_term_overlap`
- `below_relevance_threshold`

### `CriterionRetrievalDiagnostic`

The model forbids extra fields and contains:

- `criterion_id: str`
- `outcome: RetrievalOutcome`
- `searched_terms: list[str]`
- `exact_identifiers: list[str]`
- `searched_paths: list[str]`
- `searched_evidence_types: list[EvidenceType]`
- `changed_file_count: int`
- `unchanged_candidate_file_count: int`
- `inspectable_line_count: int`
- `exact_identifier_match_line_count: int`
- `term_overlap_line_count: int`
- `below_threshold_line_count: int`
- `accepted_candidate_count: int`

All lists are deduplicated and deterministically sorted. All counts are non-negative.
The accepted candidate count describes the final selected candidates, not all provisional
matches.

### `EvidenceRetrievalResult`

The model forbids extra fields and contains:

- `evidence: list[EvidenceItem]`
- `diagnostics: list[CriterionRetrievalDiagnostic]`

### `ReviewBundle.retrieval_diagnostics`

Add a default-empty list. Historical saved records therefore remain valid. When the list is
non-empty, bundle validation requires:

- unique diagnostic criterion IDs;
- every diagnostic references a bundle criterion;
- exactly one diagnostic for every bundle criterion;
- each diagnostic's `accepted_candidate_count` equals the number of evidence items for that
  criterion.

Diagnostics remain optional only for backward compatibility.

## Retrieval behavior

Add `retrieve_evidence_with_diagnostics(snapshot, criteria, unchanged_files=None)`.

The function preserves the existing candidate algorithm exactly while collecting counters
from the same iteration:

1. Normalize criterion terms and exact identifiers.
2. Build the same changed-file and bounded unchanged-file inputs.
3. Record deterministic searched paths and classified evidence types.
4. Count inspectable non-removed, line-anchored lines.
5. Count lines containing an exact identifier when exact identifiers are required.
6. Count lines with any normalized criterion-term overlap.
7. Count overlapping lines rejected by the existing test-specific or global relevance
   thresholds.
8. Select candidates using the existing diversity and eight-candidate limit.
9. Produce the evidence items exactly as today.
10. Produce one diagnostic with the following outcome precedence:

   - selected candidates exist → `candidates_found`;
   - no normalized terms → `no_searchable_terms`;
   - no inspectable lines → `no_inspectable_lines`;
   - exact identifiers exist and no line contains one → `exact_identifier_not_found`;
   - no line overlaps any criterion term → `no_term_overlap`;
   - otherwise → `below_relevance_threshold`.

`retrieve_evidence()` becomes a compatibility wrapper returning
`retrieve_evidence_with_diagnostics(...).evidence`.

## Product behavior

The web app, CLI, and constructed demo use the richer retrieval result and persist its
diagnostics in `ReviewBundle`.

### Criterion detail

Show a `How ScopeProof searched` section after the evidence status:

- outcome label;
- searched term list;
- searched path count and expandable sorted path list;
- searched evidence types;
- inspectable-line count;
- candidate count;
- one conservative explanation derived from the outcome.

The section must state: `Search diagnostics explain retrieval; they are not evidence that the
criterion is satisfied or missing from the repository.`

### Exports

- JSON receives the validated `retrieval_diagnostics` field through the bundle schema.
- Markdown and HTML add a retrieval-diagnostic subsection to each criterion when a diagnostic
  exists.
- CSV adds one `retrieval_diagnostic` column containing deterministic JSON.
- Historical bundles render `Retrieval diagnostics were not recorded for this review` rather
  than inventing a search history.

## Error handling and evidence boundaries

- Blank terms and paths are rejected by schema validation.
- No diagnostic is inferred while reopening a historical review.
- Partial ingestion is shown beside the diagnostic so users do not mistake searched scope for
  complete-repository coverage.
- Search diagnostics never create evidence IDs, change evidence levels, satisfy a criterion,
  or enter gate evaluation.
- Untrusted repository code remains unexecuted.

## Testing

Use test-driven development.

1. Schema tests cover valid diagnostics, non-negative counts, unique criterion references,
   complete diagnostic coverage, and evidence-count agreement.
2. Retrieval tests prove every outcome and deterministic list ordering.
3. Regression tests prove existing evidence items and gate decisions are unchanged.
4. Product-path tests prove web/CLI/demo bundles persist diagnostics.
5. Export tests cover diagnostics and the historical-review fallback.
6. The completed R-002 canonical result and summary must not change.
7. Run focused tests, Ruff, the full suite, and package verification before completion.

## Success criteria

- Every new product-path review contains exactly one validated diagnostic per criterion.
- A no-candidate criterion explains its deterministic search scope and primary filtering
  outcome.
- Existing candidate IDs, references, levels, scores, and gate verdicts remain unchanged.
- Historical bundles load without fabricated diagnostics.
- R-002 completed artifacts remain unchanged.
- No paid API, external notification, release, push, or Stage 1 claim is introduced.
