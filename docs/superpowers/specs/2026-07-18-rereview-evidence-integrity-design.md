# Re-review Evidence Integrity Design

## Summary

ScopeProof currently compares evidence across two validated review bundles by generated evidence
ID. Generated IDs are positional within a criterion, so the same ID can refer to a different
commit, file, line, excerpt, or candidate after a pull-request head changes. That can make a
material evidence change look unchanged in the re-review summary.

This engineering-research sprint replaces ID-only comparison with a conservative deterministic
evidence-delta classifier. It reports unchanged, relocated, modified, added, and removed
candidates; exposes the result in the local workbench; and exports a separately validated
comparison report. All fixtures and results remain deliberately constructed engineering evidence.
They do not advance public-alpha Stage 1 or establish correctness, adoption, customers, or market
validation.

## Product boundary

ScopeProof remains an evidence assistant, not a correctness oracle.

- Every comparison fact cites the previous candidate, current candidate, or both.
- A candidate classified as unchanged is not proof that its criterion is satisfied.
- Relocated, modified, added, and removed candidates require review on the current head.
- Re-analysis continues to clear final acceptance and require current-revision human decisions.
- The application never executes pull-request code.
- Matching remains deterministic, reproducible, local, and independent of Streamlit.
- No LLM, paid API, billing, private repository, account, integration, generic code review,
  security scanner, or automatic fix is added.

## Problem statement

`compare_reviews()` currently computes added and removed evidence from `EvidenceItem.evidence_id`.
The retrieval engine generates IDs such as `EV-AC-01-01` from criterion ID and candidate rank.
After a head change, a newly ranked candidate can reuse that ID even when its immutable reference
and content changed. Conversely, a semantically identical candidate can receive a different ID
when its rank changes.

The comparison must use inspectable evidence identity rather than treating positional IDs as
stable semantic identity. When correspondence is uncertain, ScopeProof must show a removal and an
addition instead of inventing a relationship.

## Selected approach

Enhance the comparison layer without changing the persisted `EvidenceItem` schema.

`scopeproof_core.reviews.comparison` receives two already validated `ReviewBundle` values, derives
comparison-only Pydantic records, and performs one-to-one deterministic matching. Streamlit and
exporters consume the resulting model; they do not reimplement matching.

This approach preserves compatibility with existing review JSON, avoids a storage migration, and
keeps comparison logic in the core engine. Persisted evidence fingerprints and lifecycle-stored
comparison state are excluded because they add migration and duplicate-state risk without being
needed for the current defect.

## Comparison model

### EvidenceChangeKind

The string enum contains exactly:

- `unchanged`
- `relocated`
- `modified`
- `added`
- `removed`

### EvidenceReference

A comparison-safe projection of one validated `EvidenceItem`:

- `evidence_id`
- `criterion_id`
- `commit_sha`
- `file_path`
- `line_start`
- `line_end`
- `excerpt`
- `context_excerpt`
- `permalink`
- `evidence_type`
- `evidence_level`
- `source_scope`
- `matching_rule`
- `relevance_reason`

Required strings remain nonblank through the existing `EvidenceItem` validation and construction
from a revalidated bundle. The projection is immutable comparison data and contains no credentials
or adapter state.

### EvidenceChange

Each change contains:

- `criterion_id`
- `kind`
- `previous: EvidenceReference | None`
- `current: EvidenceReference | None`
- `reason`

Model validation enforces:

- `unchanged`, `relocated`, and `modified` contain both references;
- `added` contains only `current`;
- `removed` contains only `previous`;
- every present reference uses the top-level `criterion_id`;
- `reason` is nonblank.

### ReviewComparison

The existing head, finding-status, resolution, gate, and ruleset fields remain. Evidence output is
upgraded to:

- `evidence_changes: list[EvidenceChange]`
- deterministic per-kind counts derived from the change list

The existing `added_evidence_ids` and `removed_evidence_ids` properties remain available as
derived compatibility views. They are not stored as a second source of truth.

## Deterministic matching algorithm

Evidence is partitioned by `criterion_id`. Candidates from different criteria can never match.
Within each criterion, previous and current candidates are sorted by a stable tuple of evidence
type, source scope, file path, line range, normalized excerpt, commit SHA, permalink, and evidence
ID. Each candidate can participate in at most one pair.

Normalization for comparison only converts CRLF/CR to LF, trims leading and trailing whitespace on
each line, and joins the normalized lines with LF. It does not case-fold, stem, remove punctuation,
or rewrite repository text.

Matching runs in this fixed order:

1. **Unchanged:** pair an exact full reference match, including commit SHA, path, line range,
   normalized excerpt, evidence type, source scope, matching rule, and permalink.
2. **Relocated:** pair only when normalized excerpt, evidence type, source scope, and matching rule
   are identical and that signature identifies exactly one unmatched candidate on each side. SHA,
   path, line range, permalink, or positional evidence ID may differ.
3. **Modified:** pair only when criterion ID, file path, evidence type, source scope, and matching
   rule identify exactly one unmatched candidate on each side while the normalized excerpts differ.
4. **Removed and added:** every remaining previous candidate becomes `removed`; every remaining
   current candidate becomes `added`.

No token similarity, fuzzy matching, edit-distance threshold, LLM judgment, or arbitrary first
match is allowed. If either side has multiple candidates for a proposed signature, that stage does
not pair them. The conservative fallback is separate removed and added records.

The output order is criterion ID, kind order (`modified`, `relocated`, `added`, `removed`,
`unchanged`), current-or-previous path, line range, and evidence ID. Input list order cannot change
the result.

## Classification reasons

Reasons are deterministic, bounded product copy:

- `unchanged`: `Candidate reference is unchanged between the two reviews.`
- `relocated`: identify which of commit, path, or line range changed and state that the current
  candidate requires review.
- `modified`: state that the candidate excerpt changed at the same deterministic file identity and
  requires review.
- `added`: state that the candidate appears only in the current review.
- `removed`: state that the candidate appears only in the previous review.

Reasons describe observable comparison facts only. They never use `passed`, `verified`, `correct`,
or equivalent correctness language.

## Lifecycle behavior

The sprint does not change lifecycle event semantics. Existing re-analysis behavior already:

- preserves the previous bundle in analysis history;
- clears final acceptance;
- retains append-only prior events for audit;
- excludes prior-revision decisions from the active gate;
- requires new current-revision decisions before final acceptance can become available.

Evidence changes therefore improve explanation and auditability without introducing a second
invalidation mechanism.

## Workbench experience

The re-review section displays:

1. previous and current head SHA;
2. a compact count for each evidence change kind;
3. changed items before unchanged items;
4. criterion ID and classification;
5. previous reference when present;
6. current reference when present;
7. the deterministic reason;
8. a reminder that candidate comparison does not prove criterion satisfaction.

Reference labels contain file and line information, while the full immutable permalink remains
available. Modified, relocated, added, and removed entries state that the current evidence must be
reviewed before recording a new decision. Unchanged entries state only that the candidate reference
did not change.

The Streamlit layer renders `ReviewComparison`; it does not calculate fingerprints, pair
candidates, or infer change kinds.

## Comparison exports

Comparison export is separate from the existing single-review export contract.

New functions in `scopeproof_core.reporting.exporters` accept and revalidate `ReviewComparison`:

- `export_comparison_json(comparison) -> str`
- `export_comparison_markdown(comparison) -> str`

JSON is sorted, indented, UTF-8-safe, and newline-terminated. Markdown includes head SHAs, gate and
ruleset changes, evidence counts, evidence changes, finding-status changes, decision changes, and
the evidence-assistant limitation. Repository-controlled strings use the existing inert escaping
and code-rendering helpers.

The export never labels a comparison as external validation. Constructed benchmark artifacts and
documentation explicitly say `deliberately constructed engineering evidence` and
`does not advance Stage 1`.

## Deterministic benchmark research case

Add one paired before/after constructed case representing the original defect:

- the previous and current reviews reuse the same positional evidence ID;
- the current head SHA changes;
- one candidate is relocated without excerpt change;
- one candidate is modified at the same file identity;
- one previous candidate is removed;
- one current candidate is added;
- an intentionally ambiguous pair falls back to removed plus added;
- the expected result contains zero unclassified candidates and exact per-kind counts.

The comparison case is executed by a focused deterministic comparison-benchmark function and is
reported separately from the existing 12-case acceptance-coverage benchmark. The existing
benchmark output and release-blocking metrics retain their current meanings. Comparison benchmark
failure returns a nonzero exit in its dedicated test/command path but is not represented as real
participant evidence.

## Error handling and fail-closed behavior

- Both review bundles are revalidated before comparison.
- Invalid comparison models fail with Pydantic validation errors before rendering or export.
- Duplicate or ambiguous match signatures are not resolved by list position.
- An unmatched candidate is never discarded; it appears as added or removed.
- Export failures do not mutate the review or comparison.
- The UI reports a bounded comparison error and preserves both saved reviews without exposing local
  paths, raw model payloads, or credentials.

## Test strategy

Test-first implementation covers:

- exact unchanged references;
- SHA-only, line-only, path-only, and combined relocation;
- modified excerpts at a unique same-file identity;
- added and removed candidates;
- identical positional evidence IDs that point to different references;
- ambiguous duplicate signatures falling back to removed plus added;
- one-to-one pairing and deterministic ordering under permuted input;
- Pydantic previous/current and criterion invariants;
- compatibility views for added and removed evidence IDs;
- JSON schema shape and deterministic serialization;
- Markdown escaping, immutable references, limitation copy, and forbidden correctness claims;
- Streamlit rendering of counts, old/current locations, reasons, and review-again guidance;
- the paired constructed comparison benchmark;
- the existing acceptance benchmark, Ruff, full test suite with at least 95 percent coverage,
  package build, clean installed-wheel smoke, and diff checks.

## Engineering-research maturity sequence

After this sprint, further engineering research remains ordered as follows:

1. evidence integrity: stale references, ambiguous pairing, deterministic deltas, and False Ready
   regression cases;
2. criteria quality: deterministic compound, duplicate, vague, and independently-judgeable
   warnings without automatic rewriting;
3. explanation quality: stable missing-evidence reason codes and next actions that preserve the
   implementation/test/runtime boundary;
4. report maturity: review and comparison lineage in validated JSON, Markdown, and HTML;
5. usability: keyboard navigation, accessible labels, responsive layout, empty states, recovery,
   and the ten-minute first workflow;
6. constructed benchmark depth, always reported separately from participant evidence;
7. genuine public alpha, which remains the only path to Stage 1 progress;
8. limited beta and commercial decisions only after the roadmap's external evidence gates pass.

Local Pro, private-repository ingestion, commercial licensing, billing, hosted source processing,
accounts, integrations, and enterprise capabilities remain deferred.

## Success criteria

The sprint is complete when:

- evidence changes no longer depend on positional evidence ID identity;
- all five classifications are deterministic, inspectable, and Pydantic-validated;
- ambiguous correspondence fails closed to removed plus added;
- re-review UI and standalone comparison exports expose both sides and the limitation boundary;
- the constructed paired benchmark reproduces and prevents the original hidden-change defect;
- existing review files and single-review exports remain compatible;
- complete verification passes;
- no claim of correctness, adoption, customer validation, or Stage 1 progress is introduced.

## Non-goals

- semantic code understanding or LLM matching;
- executing repository tests or code;
- automatic acceptance or resolution carry-forward;
- changing the deterministic gate based on comparison classification;
- persisting fingerprints or comparison state in existing review files;
- generic code review, security scanning, automatic fixes, or requirements invention;
- releases, billing, accounts, private repositories, integrations, or external outreach;
- treating constructed cases as participant or commercial evidence.
