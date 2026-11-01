# Headless retained-analysis handoff

Baseline: PR #236 main `8320146ce53c4f1023f10d8d113328bf4e491526`, verified clean with
post-merge CI/code analysis successful. A read-only independent gap assessment identified an actual
workflow gap: the workbench could export retained history after criteria changes, while the CLI
could only export current state. The selected outcome is explicit historical handoff for scripts.

## Supported behavior

- `history REVIEW_ID` emits a Pydantic metadata catalog for one saved record, with saved order,
  explicit one-based positions, current saved context, full state/analysis fingerprints and recorded
  producer identity. Empty history stays empty; duplicate heads remain distinct positions.
- `export-history` requires an explicit position and expected whole-state fingerprint. The existing
  historical selection/consumer services revalidate owner, full state and full analysis. Store locks
  are sequential, never nested; consumption retains the lock through rendering and publication.
- JSON/Markdown use the existing historical-only exporters. Missing historical provenance blocks
  full export before output. Unknown revisions and producer source identity remain unknown; saved
  legacy heads are context rather than verified commit identities. No readiness verdict is added.
- Optional files use atomic no-overwrite creation, including racing/symlink targets. Complete
  rendering precedes stdout or file output; terminals are not claimed to be transactional on I/O
  failure. Saved records, current criteria confirmation, findings, decisions and gates stay intact.

## Verification and limits

Regression coverage addresses pending/no-active records, metadata-only/empty/duplicate-head catalogs,
strict required requests, stale catalog/prepare/consume races, owner mismatches, missing provenance,
lock-bound publication, immutable saved bytes and no-overwrite output. A trusted constructed recipe
is copied outside the checkout and run against an installed wheel for catalog/JSON/Markdown/stale
refusal. This is automatic engineering evidence, never independent use or authenticated review.

The execution packet records commands, RED/GREEN runs, full unrounded 95% coverage, lint/lock,
deterministic benchmarks, installed package/browser checks, independent agent review and exact-head
and resulting-main CI. Packet location:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-10-31-cli-historical-analysis`.
Final hosted identities/results are recorded there and in the PR after verification; this document
does not turn pending execution into a completed result.

Frozen R-002 inputs/results and persisted record v7 are preserved. Source remains unreleased
0.2.5; public v0.2.4 is unchanged. Stage 1 external counts stay zero, Stage 2 remains owner-led and
Stage 3 dormant. No release, deployment, outreach, target-code execution, personal testing or
qualifying review is part of this task. Criteria-comparison CLI parity and other capabilities are
deferred options requiring a fresh need/selection, not a standing queue. The genuine Stage 3 gate
still requires independent-use evidence and separate authorization.
