# Changelog

This file highlights user-visible changes from the active development line. Authoritative notes,
artifacts, and checksums for published versions remain on the
[GitHub Releases page](https://github.com/YuzeJ21/Scope-Proof/releases).

It intentionally does not reconstruct historical releases from memory. Consult each Git tag and
its linked release entry for the exact published source and assets.

## Unreleased

Candidate version: 0.2.3 (merged to `main` via PR #174; not published).

### Known release blockers

- The post-merge audit reproduced core final-acceptance and
  manual-verification bypasses that can produce a schema-valid `Ready` state
  without all current decisions or paired runtime evidence.
- Unencoded candidate-path metacharacters can prevent the GitHub `ref`
  parameter from being transmitted while the retrieved record still claims
  the requested SHA; exact-head candidate retrieval therefore needs a
  request-level repair.

These findings were reproduced against current `main`. v0.2.3 is not
release-ready; both defects require regression coverage and full current-head
verification before any publication decision. The audit did not determine
whether the published v0.2.1 package is affected.

### Changed

- Updated the transitive GitPython lock from 3.1.52 to 3.1.57 after GitHub reported five
  high-severity advisories. GitPython remains an indirect Streamlit dependency; no direct runtime
  dependency or target-repository execution path was added.
- Fixed the advanced Action publisher so same-head reruns find an existing ScopeProof marker beyond
  the first 100 issue comments instead of creating a duplicate audit comment.
- Added deterministic per-criterion retrieval diagnostics across stored reviews, the workbench,
  CLI-created reviews, the constructed demo, and JSON, Markdown, CSV, and HTML exports. Diagnostics
  explain the search path but remain explicitly non-evidentiary.
- Added a frozen-result R-002 miss taxonomy: 14 threshold rejections and one unsupported evidence
  form, with no retuning or rescoring of the completed benchmark.
- Added evidence-delta guidance that requires revisiting prior decisions after relevant re-review
  changes, plus a compact candidate-strength summary, unresolved-criteria queue, and visible
  keyboard-focus treatment.
- Completed the
  [R-002 SWE-bench Verified static engineering benchmark](docs/research/r002-swebench-verified/summary.md):
  20 historical public PRs across 12 repositories, frozen research labels, two byte-identical
  offline runs, zero unexpected Ready outcomes, and no target-code execution.
- Added the self-contained public-alpha participant quickstart install path from PR #172, pinned
  to the verified public v0.2.1 wheel. Participant setup and benchmark success are engineering
  evidence only; they did not publish v0.2.2 and do not advance Stage 1.
- Restored the safe first-use hierarchy so the deliberately constructed demo entry appears before
  public-PR-only inputs and remains visible in the initial desktop viewport.
- Expanded the deliberately constructed comparison benchmark from one changed-head case to two
  paired cases, adding exact Unchanged coverage while preserving all core classification rules.
- Corrected observed-CI aggregation for empty legacy status aggregates, surfaced relevant static
  eval definitions as E2 test intent, and recorded the hash-bound R-001 Microsoft public-PR
  engineering comparison.
- Renamed the R-001 acceptance-criteria record so GitHub cannot misclassify research prose as a
  Python dependency manifest.

### Boundaries

- R-002 measures static engineering behavior against benchmark-owner research labels. It is not
  customer precision, correctness, runtime verification, acceptance, or Stage 1 evidence.
- The added case and its runtime result remain engineering evidence only. They do not advance
  Stage 1 or constitute correctness, customer, market, participant, or external-use evidence.
- R-001 records public engineering research only: no Microsoft code was executed, skipped eval
  checks are not runtime proof, and its `blocked` result carries zero Stage 1 credit.

## 0.2.1 — Re-review evidence integrity

### Added

- Deterministic re-review evidence classification for Unchanged, Relocated, Modified, Added, and
  Removed candidates, with conservative ambiguity fallback.
- Two-sided JSON, Markdown, and Streamlit comparison output anchored to previous and current
  immutable evidence references.
- A checked-in comparison benchmark and `scopeproof comparison-benchmark` command.
- Evidence-gated commercial-discovery and inbound design-partner documentation.

### Changed

- Public-alpha intake is inbound-only through the public GitHub issue form; stale direct-message
  and follow-up instructions were removed.

### Boundaries

- The comparison corpus is deliberately constructed engineering evidence. It does not advance Stage 1,
  prove correctness, establish external use, or constitute customer or market validation.
- No paid API, LLM, billing, private repository, account, fork test, email, direct message,
  automated outreach, scraping, synthetic validation, generic review, security scanner, or
  automatic fix capability was added.

## 0.2.0 — Reviewer-first product reset

### Changed

- Reframed the primary product as acceptance coverage for PR reviewers, using Strong candidate,
  Weak candidate, No candidate, Analysis incomplete, Reviewer verified, and Rejected language.
- Human-readable review status is now Action required, Review incomplete, Accepted with
  exceptions, or Review complete; persisted enums remain backward compatible.
- Standard review is the default. Participant qualification and outcomes appear only in an
  optional Alpha feedback session.
- Visible GitHub checks are labelled Observed CI state; neutral and skipped checks no longer count
  as passing.

### Added

- Bounded neighboring context for evidence candidates without changing immutable matched lines.
- Atomic external verification that records runtime evidence and its attributable decision
  together.
- Deterministic final-acceptance prerequisites for complete ingestion, passing observed CI, and
  current accepted decisions across all criteria.
- Explicit bounded unchanged-file candidate paths and immutable re-review comparison.
- Inline local alpha-case creation, one-outcome collection, and separate report and quote consent.

### Boundaries

- This release does not claim genuine participant validation or beta readiness. The truthful state
  remains `waiting_for_inbound_public_alpha_submission` until the roadmap's external gates are met.
- No paid LLM API, private repository, billing, account, fork testing, untrusted-code execution,
  generic review, security scan, or automatic fix capability was added.

## Published releases

See [all ScopeProof releases](https://github.com/YuzeJ21/Scope-Proof/releases) for versioned notes,
wheel assets, and checksum files. A changelog entry alone is not release or verification evidence.
