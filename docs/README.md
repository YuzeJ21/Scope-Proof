# ScopeProof documentation map

Use current operating documents for product decisions. Historical records are immutable evidence
snapshots: they preserve what was observed at a named commit or release and must not be read as the
current product state.

Current direction: prepare the v0.2.4 downloadable evaluation candidate, then return to bounded
maintenance of the engineering reference product. Source/package identity is `0.2.4`; v0.2.3
remains the published baseline until GitHub Releases provides v0.2.4 assets. Stage 1 is closed
at zero; Stage 3 is dormant and gated. No personal testing or qualifying reviews are required
for evaluation distribution. Begin with the roadmap's finish line before starting any new slice.

## Current operating documents

- [Product roadmap](../ROADMAP.md) — current stage decisions, boundaries, and next owner gates.
- [v0.2.4 evaluation candidate](releases/v0.2.4-evaluation-candidate.md) — conditional availability,
  changes, upgrade limits, exact-main verification and remaining publication steps.
- [v0.2.3 status and next stages](releases/v0.2.3-status-and-next-stages.md) — published-release
  boundary, current development line, feature ledger, gaps, and stage status.
- [Stage 2 productization packet](commercialization/stage2-readiness-packet.md) — authorized
  owner-led engineering scope; it does not claim customer validation.
- [Current official-source market comparison](commercialization/market-comparison-2026-07-26.md)
  — official-source capability refresh dated 2026-10-27; vendor claims and unvalidated positioning.
- [Development environment](development-environment.md) — supported and unsupported engineering
  environments.
- [Engine identity boundary](development/engine-identity.md) — captured core-source identity and
  unknown legacy identity; no claim of full environment reproducibility or signed execution.
- [Privacy readiness](privacy-readiness.md) — current local-only data and trust boundaries.

## Historical evidence records

- [2026-10-25 integration disposition](audits/2026-10-25-integrity-integration-disposition.md)
  preserves the pre-merge dependency, JUnit, and archival decisions.
- [Unreleased integrity case study](portfolio/2026-10-25/case-study.md) preserves its constructed
  demonstration and publication boundaries at the named source revision.

- `docs/audits/` contains exact-head implementation, verification, and review snapshots.
- `docs/releases/` contains published-release and post-merge evidence records. The current status
  document linked above is the exception and explicitly distinguishes live operating status from
  dated evidence.
- `docs/research/` contains constructed or historical research evidence. It does not establish
  customer validation or advance a product stage.

When documents differ, prefer the GitHub Release for publication availability, the current roadmap
for stage authority, and exact-head hosted checks for engineering results. Missing external evidence
remains missing.
