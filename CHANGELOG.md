# Changelog

This file highlights user-visible changes from the active development line. Authoritative notes,
artifacts, and checksums for published versions remain on the
[GitHub Releases page](https://github.com/YuzeJ21/Scope-Proof/releases).

It intentionally does not reconstruct historical releases from memory. Consult each Git tag and
its linked release entry for the exact published source and assets.

## Unreleased

Development version: `0.2.4.dev0`. Public install remains the immutable v0.2.3 release.

### Post-release engineering

- Added CLI lifecycle parity for criterion resolution, atomic external E3/E4 runtime-evidence
  recording, final acceptance, and changed-head comparison over validated local records.
- Enforced a strict saved-record envelope and lifecycle-output validation. Failed commands do not
  mutate saved records, and low-evidence acceptance notes share one fail-closed core policy across
  CLI and Streamlit.
- Added an installed-wheel packaged Chromium regression at 1280×720 and 390×844 with exact
  Playwright 1.62.0, isolated local storage, loopback-only networking, and console/page-error
  assertions.
- Added Python 3.13 package, CLI, deterministic-benchmark, and exact workbench-health engineering
  coverage in both a genuine local CPython 3.13 environment and protected CI.
- Added a keyboard-only installed-workbench path with visible-focus assertions and
  bounded native 200% zoom evidence on the tested macOS/Chrome configuration.
- Enforced verified-public provenance before a live GitHub source can be persisted, exported, or
  counted toward Alpha. Private, ambiguous, malformed, and legacy-unverified sources fail closed.
- Centralized comparison eligibility in the core: repository and pull-request identity, exact
  reviewed heads, ordered criterion definitions, and criteria-source provenance must remain
  compatible. CLI and Streamlit now reject stale comparison bases without carrying decisions or
  mutating saved reviews.

These changes are ScopeProof engineering evidence only and earn zero Stage 1 credit. Real
screen-reader operation, Windows desktop, Linux desktop, non-Chromium browser behavior, and WCAG
conformance remain unsupported.

## 0.2.3 — Evidence integrity and reviewer loop

### Product convergence source work

- Failed closed when GitHub omits, nulls, or empties a changed-file patch: the
  unavailable path is excluded, named as skipped, and makes ingestion partial
  instead of appearing as a complete empty diff.
- Prepared reopened reviews for a one-click current-head check, including their
  bounded unchanged-candidate paths, without carrying prior decisions forward.
- Connected every evidence-matrix card to criterion detail and added candidate
  count, rationale, missing-evidence, and recommended-action context.
- Required an attributable note when a reviewer accepts below the criterion's
  required candidate-evidence level; the note never raises that level.
- Exposed changed candidates first, collapsed exact Unchanged candidates, and
  added validated Markdown and JSON re-review comparison downloads.
- Reduced primary-page density by collapsing optional source revision and local
  storage details and limiting constructed-demo disclosure to the demo context.
- Bound every new criteria confirmation to an immutable source URI, optional
  source revision, exact requirements-text digest, ordered normalized-criteria
  digest, confirmer, and timestamp. Missing or changed provenance fails closed
  to `Needs Review` rather than inheriting prior certainty.
- Advanced local review storage to version 4. Version 1–3 records remain
  readable without invented criteria-source provenance and require explicit
  reconfirmation before analysis, export, or final acceptance can become
  eligible again.
- Carried the typed criteria-source snapshot through the workbench, CLI,
  trusted-base Action preview, alpha evidence record, JSON persistence, and
  JSON, Markdown, CSV, and HTML exports.
- Simplified the workbench and public-alpha page hierarchy, moved optional
  evidence-matrix filters into progressive disclosure, and aligned supported
  Streamlit and public-site visual tokens without hiding safety copy or
  changing deterministic gate behavior.
- Updated the copyable Action source-candidate pin to the final immutable
  v0.2.3 integrity commit `d553791cba83d9f756b2adce22bd814872b73ea2`. This source-install pin was
  independent from the then-current v0.2.1 release-package guidance and remains
  independent from the conditional v0.2.3 release-asset install path.

These changes are engineering source work only. They create zero Stage 1
credit and do not establish customer, market, accessibility, platform,
security, or target-repository runtime validation.

### Integrity repairs

- Added immutable `runtime_evidence_id`, repository, pull-request, and reviewed
  head provenance to every new E3/E4 runtime record and linked manual decision.
  Trusted boundaries require the link to resolve exactly one matching record.
- Advanced local storage to record version 3. Version 1/2 runtime records gain
  deterministic identities, but legacy manual decisions remain unlinked rather
  than receiving an invented association. Their gate becomes `Needs Review`
  with `runtime_verification_reconfirmation_required` until active-head
  verification is recorded again.
- Projected validated runtime identity and legacy-unlinked recovery through the
  workbench and JSON, Markdown, CSV, and HTML exports, retaining formula and
  safe-rendering protections.
- Added a visible skipped-check warning for complete passing observations
  without changing deterministic CI state, plus a bundle-less draft-clear path
  that preserves authoritative review state, resumes autosave, and keeps
  exports unavailable until reanalysis.
- Rejected ineligible positive final-acceptance events at the core lifecycle
  boundary and independently validate final-acceptance prerequisites before
  persistence, comparison, presentation, or export.
- Restricted `MANUALLY_VERIFIED` decisions to the atomic external-verification
  path and require matching runtime evidence for the same criterion, reviewer,
  and claimed evidence level at every trusted bundle/state boundary.
- Encoded bounded candidate paths, transmitted the immutable head SHA through
  a separate HTTP `ref` parameter, validated full lowercase commit SHAs, and
  failed closed on malformed or unanchored content responses.
- Added regressions for the reproduced False Ready paths, maliciously
  reconstructed states, persisted/exported/comparison boundaries, `?`, `#`,
  `%`, spaces, Unicode, traversal, and actual transmitted request provenance.
- Restricted same-head Action comment updates to comments attributed to the
  GitHub Actions bot, moved Pages write/OIDC permissions to the deployment
  job, and made the repository Action use the checked-in locked environment.

The PR #177 repairs remain historical public-main evidence. PR #180 merged the
newer exact-head runtime-evidence repair as product commit
`2a320df966eff30c05a2b1dce607a247201fa165`. Independently verified PR head
`ed9f9c0cf6b7cf7cc25403d6138e7a8391f55e0f` has the same tree,
`add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8`. This merge restores the Stage 0
engineering foundation; it does not publish v0.2.3, establish customer
validation, or determine whether the published v0.2.1 package is affected.

PR #181 merged documentation-only post-merge alignment as
`eaa66c5979e2a71769d58f0699537da474094d06`; CI, CodeQL, and Pages succeeded.
This is repository-tree CI only and does not establish release assets,
checksums, a tag, a GitHub Release, or Stage 1 evidence.

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
