# Comparison Relationship Integrity Design

## Status and scope

This design implements the owner-approved Workstream 3 boundary on top of resulting `main`
commit `e40c65258f6b0be03f22d0b89f0c199e7367c6a6`. It centralizes whether two validated
ScopeProof review bundles are eligible for comparison. It does not change evidence retrieval,
criterion verdicts, gate policy, runtime-evidence semantics, release identity, or Product Stage 1.

ScopeProof remains an evidence assistant rather than a correctness oracle. Comparison describes
candidate and recorded-review changes only; it never proves criterion satisfaction and never
carries a prior human decision into the current review.

## Current problem

`scopeproof_core.reviews.comparison.compare_reviews` independently validates each bundle but does
not validate their relationship. The CLI adds repository, pull-request, and criterion checks in its
adapter, while Streamlit calls the core directly. The CLI also converts criteria to dictionaries,
which loses their confirmed order. Streamlit can retain a reopened bundle as a comparison base
after the reviewer confirms changed criteria or a changed criteria-source snapshot.

The result is an adapter-dependent trust boundary: two individually valid bundles can be compared
even when they describe different work or different confirmed requirements.

## Considered approaches

### A. Core relational validator called by `compare_reviews` — selected

Add one public core validator that independently validates both bundles and then validates their
relationship. `compare_reviews` always calls it. CLI removes its duplicate relationship logic, and
Streamlit handles the core error by clearing the stale base and withholding comparison exports.

This is the smallest approach that makes every current and future adapter share one fail-closed
rule. It keeps the core independent from Streamlit and GitHub UI concerns.

### B. Shared helper called explicitly by each adapter

Move the CLI checks to a helper but leave `compare_reviews` permissive. This reduces duplication,
but every new caller could still forget the helper. It does not establish the core as the trusted
boundary and therefore does not satisfy the workstream.

### C. New persisted comparison-request envelope

Create a new Pydantic request object containing both saved review identities before comparison.
This could support future hosted workflows, but it introduces a new persisted schema and migration
surface without present demand. The current work only needs deterministic validation of two
already validated bundles.

## Core eligibility contract

Add `validate_comparison_relationship(previous, current)` in
`scopeproof_core/reviews/comparison.py`. It returns independently validated copies of the two
bundles so the comparison cannot trust caller-mutated Pydantic instances.

Eligibility requires all of the following:

1. Both bundles pass `validated_review_bundle` and deterministic gate validation.
2. Both review identities name the same repository and pull-request number.
3. Each review has a nonblank exact head identity. A live-public GitHub review must use a
   lowercase 40-character Git object ID. Constructed engineering fixtures remain explicitly
   allowed to use named non-production identities.
4. Every static evidence candidate in each bundle is bound to that bundle's reviewed head SHA.
   Runtime evidence already has the equivalent Pydantic cross-object requirement.
5. The ordered lists of complete `Criterion` definitions are identical. Reordering, changing
   text, priority, type, source, source span, or required evidence level makes the pair ineligible.
6. Both bundles have confirmed criteria-source provenance.
7. Their source snapshot identities are compatible: `source_uri`, `source_revision`,
   `source_text_sha256`, and `normalized_criteria_sha256` must match exactly.

`confirmed_by` and `confirmed_at` are attestation metadata, not source-snapshot identity. They may
differ when the same authoritative snapshot is reconfirmed for a later head. Ignoring those two
fields preserves legitimate changed-head and same-head rereview while still failing closed on any
changed requirement source, revision, exact text, or normalized ordered criteria.

The validator raises deterministic `ValueError` messages for repository/PR mismatch, invalid head
identity, candidate/head mismatch, criterion mismatch, missing provenance, or incompatible source
provenance. `compare_reviews` performs no projection until this validation succeeds.

## Adapter behavior

### CLI

The CLI continues to load both saved reviews under one multi-record lock. It requires active
bundles, calls `compare_reviews`, and renders only after core eligibility succeeds. The current
adapter-specific repository/PR and criterion checks are removed. On failure, no saved record is
mutated and no output file is created or overwritten.

### Streamlit

Streamlit continues to preserve a reopened bundle long enough to support a legitimate rereview.
After the new analysis bundle exists, it calls the same core comparison function. If the core
rejects the relationship, Streamlit clears `comparison_base_bundle`, displays bounded recovery
copy, renders no comparison, and offers no comparison download. The current review remains usable
and contains no carried-forward decisions.

This timing avoids clearing every comparison base during ordinary source reload, while ensuring a
changed criterion or criteria-source snapshot cannot survive as an active comparison base.

## Benchmark and export behavior

The constructed comparison benchmark's positive previous/current pair must use one compatible
criteria-source snapshot. A focused negative benchmark regression changes the exact source text and
proves the core rejects the pair instead of producing counts.

Comparison Markdown and JSON remain Pydantic-revalidated projections of `ReviewComparison`.
Invalid bundle pairs never reach either renderer. Export regressions assert that a failed CLI
comparison creates no artifact and does not invoke a renderer.

## Test strategy

Tests are written before behavior changes and observed failing for the intended reason.

- Core: repository, PR, live head format, candidate/head binding, criterion content/order,
  missing provenance, changed source URI/revision/text, and compatible reconfirmation metadata.
- CLI/storage/export: the same core errors surface through the command, input files remain
  byte-identical, output is absent, and renderers are not called.
- Streamlit: changed criteria and changed provenance clear the stale base, show safe copy, expose no
  comparison downloads, and carry no prior decisions; compatible rereview remains available.
- Benchmark: positive corpus remains deterministic with zero mismatches; a changed source snapshot
  is rejected.
- Regression: all existing comparison classifications, lifecycle validation, exporters, repository
  contracts, deterministic benchmarks, package checks, and installed-wheel browser tests remain
  green.

## Evidence and product boundaries

- No target-repository code is executed.
- Static candidates are not runtime verification.
- Persisted and exported objects remain Pydantic-validated.
- Failed comparisons do not mutate saved state.
- Gate decisions remain deterministic and fail closed.
- Product Stage 1 remains exactly zero across all five targets.
- Workstreams 4 and 5, R-002, R-003, releases, tags, publishing, outreach, accounts, billing,
  private repositories, and correctness claims remain out of scope.
