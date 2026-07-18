# Changelog

This file highlights user-visible changes from the active development line. Authoritative notes,
artifacts, and checksums for published versions remain on the
[GitHub Releases page](https://github.com/YuzeJ21/Scope-Proof/releases).

It intentionally does not reconstruct historical releases from memory. Consult each Git tag and
its linked release entry for the exact published source and assets.

## Unreleased

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
  remains `waiting_for_external_participant_evidence` until the roadmap's external gates are met.
- No paid LLM API, private repository, billing, account, fork testing, untrusted-code execution,
  generic review, security scan, or automatic fix capability was added.

## Published releases

See [all ScopeProof releases](https://github.com/YuzeJ21/Scope-Proof/releases) for versioned notes,
wheel assets, and checksum files. A changelog entry alone is not release or verification evidence.
