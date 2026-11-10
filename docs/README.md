# ScopeProof documentation map

Use current operating documents for product decisions. Historical records are immutable evidence
snapshots: they preserve what was observed at a named commit or release and must not be read as the
current product state.

Current direction: align current entry points and the separately authorized website publication
with the completed, publicly verified v0.2.7 release from `e099679ed63309716a7ce4726557ef794bfd5c80`.
PR #276 completed the no-install constructed HTML repository download; its actual public
v0.2.6 exporter provenance, unchanged input and offline checks remain intact. PR #277 completed
the bounded saved-history event-scan repair at main `944c791`; see the
[measurement and limits](audits/2026-11-08-history-event-validation.md).
PR #275's website alignment and separately authorized Pages publication remain complete at
`388b7dae276253ac015efd852cd510bc3999f9fd` as historical evidence. The later v0.2.7 site alignment
has its own owner-authorized publication through the manual Pages workflow.
PR #272 completed native-v0.2.6 compatibility; PR #273 completed CSV/HTML revision labels;
PR #274 completed the bounded browser-test synchronization repair at main
`37799a04942e2926bf9c73882a9e0f4e1e44698f`, with green resulting-main CI. Natural baseline runs
and controlled signal-loss evidence remain distinct; the exact natural Streamlit transition
remains unproven. See the [roadmap](../ROADMAP.md),
[observer assessment](audits/2026-11-07-browser-observer-reopen.md) and
[evaluation-page assessment](audits/2026-11-08-evaluation-page-alignment.md).
Current development source/package is **0.2.8.dev0**, unpublished. The
[v0.2.7 Release record](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.7) identifies the
published default evaluation download, final source, wheel, source archive, checksum manifest
and completed public-download verification. Earlier verified **v0.2.6** remains at
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`
with its [Release record](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6).
The private `0.2.7.dev0` candidate remains historical and unpublished; it does not establish final
availability or artifact identity. Released bytes retain their own source commit. Stage 1 is closed
at zero; Stage 3 is dormant and gated. No personal testing or qualifying reviews are required
for evaluation distribution. Begin with the roadmap's finish line before starting any new slice.

## Current operating documents

- [Start here: evaluation guide](evaluation-guide.md) — published/source/candidate capability map,
  one constructed workflow, exact-baseline engineering evidence and remaining limits.
- [No-install constructed HTML report](examples/offline-handoff/README.md) — download before setup,
  expected Action required, simulation boundaries, provenance and regeneration.
- [November 2 product and market assessment](commercialization/product-direction-2026-11-02.md) —
  official-source overlap, adoption constraints, and priorities before publication.
- [Product roadmap](../ROADMAP.md) — current stage decisions, boundaries, and next owner gates.
- [Evaluation-page assessment](audits/2026-11-08-evaluation-page-alignment.md) — current-release routing,
  saved-decision positioning and the earlier source-only preview scope. The later authorized
  [Pages publication](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42494611672) is complete.
- [v0.2.7 published evaluation release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.7) —
  fixed source, three public assets and completed public-download verification.
- [Historical-analysis revision-label assessment](audits/2026-11-07-historical-report-revision.md) —
  completed PR #273 CSV/HTML display correction and retained current-state export guards.
- [Browser-observer assessment](audits/2026-11-07-browser-observer-reopen.md) — captured timeout,
  bounded natural runs, controlled signal-loss replay and the test-only synchronization boundary.
- [Native v0.2.6 compatibility assessment](audits/2026-11-07-native-v026-compatibility.md) —
  completed PR #272 provenance-bound constructed histories and permanent regression boundary.
- [v0.2.5 public verification](releases/v0.2.5-public-verification.md) — release source, assets,
  fresh installs and workbench handoff checks.
- [v0.2.4 public verification](releases/v0.2.4-public-verification.md) — earlier published source/tag/assets,
  automatic public-download checks, upgrade limits and evidence boundaries.
- [Earlier status and next stages](releases/v0.2.3-status-and-next-stages.md) — feature ledger
  and stage decisions before v0.2.5 publication.
- [Stage 2 productization packet](commercialization/stage2-readiness-packet.md) — authorized
  owner-led engineering scope; it does not claim customer validation.
- [Development environment](development-environment.md) — supported and unsupported engineering
  environments.
- [Engine identity boundary](development/engine-identity.md) — captured core-source identity and
  unknown legacy identity; no claim of full environment reproducibility or signed execution.
- [Privacy readiness](privacy-readiness.md) — current local-only data and trust boundaries.

## Historical evidence records

- [PR #221 private v0.2.5 candidate](releases/v0.2.5-evaluation-candidate.md) — original source,
  record-v5 scope and preparation guidance; not the later source tree despite the same version.
- [Earlier market comparison](commercialization/market-comparison-2026-07-26.md) — refreshed
  2026-10-27, retained as historical research rather than the current product decision.
- [PR #247 market comparison](commercialization/market-comparison-2026-11-02.md) — original
  typed-criteria and transfer recommendations, now implemented on source.

- [Workbench saved-review handoff](audits/2026-11-02-workbench-review-handoff.md) — explicit recipient inspection/import and saved-record downloads, preserving open work and original provenance.

- [Saved-review transfer](audits/2026-11-02-saved-review-transfer.md) — bounded complete-record transfer, provenance preservation and installed reopening on unreleased source.

- [Dependency declaration alignment](audits/2026-10-29-dependency-baseline-alignment.md) records
  the unreleased source correction, unchanged lock versions and isolated exact-floor verification.
- [Dependency-floor and JUnit upload assessment](audits/2026-10-29-runtime-dependency-floor.md)
  records exact installed combinations, partial older-UI evidence, and the reproduced byte-boundary
  defect plus unreleased-source repair. Published v0.2.4 remains unchanged.
- [Covered-suite performance maintenance](audits/2026-10-29-verification-performance.md) records
  the controlled timing/accounting comparison, CI-only scope and unchanged verification gates.
- [v0.2.4 evaluation preparation](releases/v0.2.4-evaluation-candidate.md) preserves the candidate
  plan and version-bound upgrade guidance; its publication status is superseded by the record above.
- [Native v0.2.3 → v0.2.4 upgrade rehearsal](research/2026-10-29-v023-v024-upgrade.md) preserves
  one constructed old-writer/new-reader result and its native fixture; missing scope remains
  Needs review, and no independent-use evidence is claimed.
- [2026-10-25 integration disposition](audits/2026-10-25-integrity-integration-disposition.md)
  preserves the pre-merge dependency, JUnit, and archival decisions.
- [Unreleased integrity case study](portfolio/2026-10-25/case-study.md) preserves its constructed
  demonstration and publication boundaries at the named source revision.

- `docs/audits/` contains exact-head implementation, verification, and review snapshots.
- `docs/releases/` contains published-release records and dated engineering ledgers.
- `docs/research/` contains constructed or historical research evidence. It does not establish
  customer validation or advance a product stage.

When documents differ, prefer the GitHub Release for publication availability, the current roadmap
for stage authority, and exact-head hosted checks for engineering results. Missing external evidence
remains missing.
