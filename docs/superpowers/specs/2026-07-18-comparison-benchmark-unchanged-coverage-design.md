# Comparison Benchmark Unchanged Coverage Design

## Goal

Extend ScopeProof's deliberately constructed re-review comparison benchmark so its executed corpus
contains the `unchanged` classification. Preserve the engineering-evidence boundary and all core
comparison, lifecycle, and gate semantics.

## Current gap

The bundled comparison benchmark executes one paired case and covers `relocated`, `modified`,
`added`, and `removed`, but reports `unchanged: 0`. Unit tests exercise the core `unchanged`
classifier; the packaged fixture-to-review-to-comparison path does not.

This is an engineering benchmark coverage gap only. Closing it does not constitute external use,
customer validation, correctness proof, or Stage 1 progress.

## Constraint discovered during design

Changed-file evidence is bound to the snapshot's `head_sha`. The existing previous and current
fixtures intentionally use different head SHAs, so an otherwise identical changed-file candidate
must classify as `relocated`, not `unchanged`. Adding such a candidate to the current case would
either fail to cover `unchanged` or require an implausible fixture in which changed content shares
one immutable SHA.

The benchmark must not weaken the exact-reference rule or misrepresent immutable evidence merely
to increase category coverage.

## Options considered

### 1. Add a second, unchanged-only corpus case

Add one small constructed snapshot and label file with exactly one deterministic candidate. Execute
that same immutable snapshot as both the previous and current side of a second case. Upgrade the
evaluation runner from one manifest case to a validated list of cases and aggregate their exact
counts.

This is the selected approach. It represents a legitimate re-review at the same immutable SHA,
keeps the existing changed-head case intact, and changes only evaluation infrastructure and data.

### 2. Add an unchanged-file retrieval input to the existing case

This could preserve different review head SHAs while binding one candidate to a common earlier
commit. However, the current offline review builder does not accept unchanged-file inputs. Adding
that plumbing would alter production-facing demo/retrieval interfaces solely for a benchmark and
would broaden this sprint unnecessarily.

### 3. Reuse one SHA across the existing before/after fixtures

This is the smallest data diff, but it would claim that different constructed file content belongs
to the same immutable commit. That conflicts with the evidence-integrity purpose of the benchmark
and is rejected.

### 4. Add only another core comparison unit test

This would not close the identified gap because the bundled comparison benchmark would still
report `unchanged: 0`.

## Manifest and runner design

Replace the single-case manifest fields with a validated nonempty `cases` list. Each case contains:

- `case_id`;
- previous fixture and labels paths;
- current fixture and labels paths;
- exact expected `EvidenceChangeCounts`.

The manifest retains these top-level literals:

- `evidence_boundary: deliberately constructed engineering evidence`;
- `does_not_advance_stage_1: true`.

The runner executes cases in manifest order without running fixture repository code. For each case
it builds both validated reviews through `build_review_from_paths`, compares them through the
unchanged `compare_reviews` function, and records exact mismatch messages. It then sums expected and
actual counts across cases into the existing aggregate result shape.

`executed_case_count` becomes two. `case_results` contains one entry per manifest case. Aggregate
mismatches remain prefixed by case ID, so failures stay bounded and attributable.

The manifest model rejects an empty corpus and duplicate case IDs. These are evaluation-input
integrity checks, not product verdict rules.

## Constructed cases

### Existing changed-head integrity case

Keep `rereview-evidence-integrity` and all its inputs unchanged. Its exact counts remain:

```json
{
  "unchanged": 0,
  "relocated": 1,
  "modified": 1,
  "added": 3,
  "removed": 3
}
```

### New unchanged-reference case

Add one deliberately constructed PR-shaped fixture with one changed-file line containing a unique
identifier such as `unchangedproof`. Add one confirmed criterion whose text contains that same
identifier. Reference the same fixture and label paths on both sides of the case so the generated
candidate has the same criterion, evidence type, source scope, matching rule, commit SHA, path,
line range, excerpt, and permalink.

Its exact counts are:

```json
{
  "unchanged": 1,
  "relocated": 0,
  "modified": 0,
  "added": 0,
  "removed": 0
}
```

The aggregate expected result is therefore:

```json
{
  "unchanged": 1,
  "relocated": 1,
  "modified": 1,
  "added": 3,
  "removed": 3
}
```

## Scope

Expected implementation changes are limited to:

- `scopeproof_core/evals/comparison_runner.py` for validated multi-case iteration and aggregation;
- `evals/comparisons/rereview_evidence_integrity.json` for the case-list manifest;
- new `evals/comparisons/unchanged_pr.json` and `unchanged_labels.json` inputs;
- `tests/evals/test_comparison_runner.py` for red/green corpus, aggregation, mismatch, and manifest
  validation coverage;
- `tests/test_repository_contracts.py` for the exact packaged corpus and all-five-kind coverage
  contract.

No README, CLI interface, version, or release change is required because the command and public
evidence-boundary wording remain accurate.

## Explicit non-goals

Do not modify:

- `scopeproof_core/reviews/comparison.py` or any classification identity/signature rule;
- `scopeproof_core/demo.py`, retrieval behavior, acceptance-criterion verdict rules, or schemas for
  product reviews and evidence;
- lifecycle, exports, UI, or any readiness gate;
- Stage 1 state or any external-validation, participant, or market-evidence record.

Do not add paid APIs, LLM calls, repository-code execution, generic review, security scanning,
automatic fixes, outreach, or synthetic claims of validation.

## Test-driven implementation

1. Update focused tests to require two executed cases, the exact aggregate five-kind count map, and
   an `unchanged-reference` case with exactly one unchanged candidate. Preserve all evidence-boundary
   assertions.
2. Add tests rejecting an empty `cases` list and duplicate case IDs. Update the bounded mismatch
   test to mutate one named case. Run the focused suite and record the expected RED state.
3. Add a repository contract requiring the packaged corpus files and a positive aggregate expected
   count for every `EvidenceChangeKind`. Run it and record RED.
4. Implement the Pydantic manifest models, ordered case execution, and deterministic count summing.
5. Add the constructed unchanged fixture and labels, then migrate the manifest to two cases.
6. Run the focused suite and `scopeproof comparison-benchmark`. Require two executed cases, zero
   mismatches, the exact aggregate counts above, and `does_not_advance_stage_1: true`.
7. Run repository contracts, Ruff, and the complete test suite.

The command output is runtime engineering evidence for checked-in constructed fixtures only. It is
not evidence about an external repository, user workflow, customer demand, or product correctness.

## Failure handling

- If the unchanged-only case produces any kind other than exactly one `unchanged`, treat it as a
  fixture or runner defect; do not weaken the classifier or adjust expected counts to accept it.
- If the existing case's counts change, treat it as a regression; do not absorb the change into the
  manifest.
- Missing files, invalid manifests, empty corpora, and duplicate case IDs fail before comparison.
- Count mismatches preserve the existing nonzero CLI exit behavior.
- Preserve `/Users/yjian070/Documents/New project 2/.coverage 2` and the unrelated existing
  re-review worktree file byte-for-byte.

## Acceptance criteria

- The bundled constructed benchmark executes exactly two cases.
- The unchanged-reference case reports exactly one `unchanged` and zero other changes.
- Aggregate counts are exactly `unchanged: 1`, `relocated: 1`, `modified: 1`, `added: 3`, and
  `removed: 3`.
- The existing changed-head case's fixtures and exact counts remain unchanged.
- The benchmark reports zero mismatches.
- The engineering-evidence boundary and `does_not_advance_stage_1: true` remain present in validated
  output.
- No core classifier, product review schema, retrieval behavior, gate, lifecycle, UI, or export
  behavior changes.
- Focused tests, repository contracts, Ruff, and the full suite pass.
