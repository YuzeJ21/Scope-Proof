# ScopeProof documentation map

Use current operating documents for product decisions. Historical records are immutable evidence
snapshots: they preserve what was observed at a named commit or release and must not be read as the
current product state.

## Current operating documents

- [Product roadmap](../ROADMAP.md) — current stage decisions, boundaries, and next owner gates.
- [v0.2.3 status and next stages](releases/v0.2.3-status-and-next-stages.md) — published-release
  boundary, current development line, feature ledger, gaps, and stage status.
- [Stage 2 productization packet](commercialization/stage2-readiness-packet.md) — authorized
  owner-led engineering scope; it does not claim customer validation.
- [Current official-source market comparison](commercialization/market-comparison-2026-07-26.md)
  — dated competitive research and positioning hypotheses.
- [Development environment](development-environment.md) — supported and unsupported engineering
  environments.
- [Privacy readiness](privacy-readiness.md) — current local-only data and trust boundaries.

## Historical evidence records

- `docs/audits/` contains exact-head implementation, verification, and review snapshots.
- `docs/releases/` contains published-release and post-merge evidence records. The current status
  document linked above is the exception and explicitly distinguishes live operating status from
  dated evidence.
- `docs/research/` contains constructed or historical research evidence. It does not establish
  customer validation or advance a product stage.

When documents differ, prefer the GitHub Release for publication availability, the current roadmap
for stage authority, and exact-head hosted checks for engineering results. Missing external evidence
remains missing.
