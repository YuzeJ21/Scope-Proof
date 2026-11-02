# Typed criteria handoff and product direction — 2026-11-02

Baseline: main `5b9860bce7f4d9349692e02b9bb8e492cad2e135` (PR #247). Its CI and CodeQL were green;
both checkouts were clean and no PR was open at this goal's start. Public v0.2.4 is unchanged;
source remains unreleased 0.2.5 and saved record writer remains version 9.

## Outcome and rationale

An operator can prepare a source-bound normalized criteria document, inspect/edit it, explicitly
confirm it, and pass the same complete intent to CLI validation and review. The previous public
CLI path constructed only sequential IDs and text, so existing custom criteria confirmations
correctly failed their complete-field digest check. The new path preserves supported fields
rather than weakening that check or silently reconstructing E1 defaults.

The [design](../superpowers/specs/2026-11-02-typed-criteria-handoff-design.md) selects one small
input contract over full saved-review transfer. The [implementation plan](../superpowers/plans/2026-11-02-typed-criteria-handoff.md)
includes adversarial confirmation and write-boundary checks. New constructed cases/results are
separate from frozen R-002. No retrieval or gate rule changes.

## Behavior and limits

- `prepare-criteria` emits a Pydantic-validated **unconfirmed** draft, with complete Criterion
  defaults and exact UTF-8 source hash. It grants no actor, evidence, decision or acceptance.
- Optional `--criteria` on preparation, confirmation validation and `review` uses one bounded
  regular-file reader and pure-core source-bound document. Nonempty unique IDs and unknown-field
  rejection apply; the maximum is 1 MiB. Invalid typed input never falls back to text parsing.
- Confirmation binds original source bytes and the complete ordered normalized criteria. Explicit
  normalized edits are permitted, as in the workbench; semantic source mapping is not inferred.
  IDs, source spans and origins remain asserted metadata. No identity authentication is added.
- Validation precedes network/fixture ingestion and report/store writes. Both draft and existing
  confirmation creation use atomic no-overwrite output. Review/export use existing validation.
- Existing text-only callers retain their digests. GitHub Action and alpha remain text-only;
  the typed option does not import a saved review, rerun it or carry decisions forward.

## Product assessment and next stages

The [official-source market refresh](../commercialization/market-comparison-2026-11-02.md) finds
substantial requirement-alignment and traceability overlap. The strongest current hypothesis is
explaining and revisiting a review decision, not unique acceptance detection. Local deterministic
records and explicit evidence boundaries are implemented strengths; public-only access,
evaluation-only licensing, setup work, conservative matching and asserted identities are limits.

Finish this bounded Stage 2 outcome with engineering evidence, then consider safe portable review
transfer under a separate design. A downloadable update needs publication authorization and fresh
version-bound evidence. Stage 1 remains closed with all counts zero; Stage 3 is dormant pending
genuine independent use and separate authorization. No personal testing, qualifying-review
request, outreach, deployment, release, beta, accessibility-conformance or customer claim follows.

## Verification record

The external packet at
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-02-typed-criteria-handoff`
retains raw commands/results, genuine RED/GREEN tests, independent agent review and dispositions,
package identities, frozen-input checks, exact-head CI and resulting-main integration evidence.
The local evidence is constructed automation, not genuine practitioner use. Final counts and
commit/run identities belong to that version-bound packet and PR, not a moving-head claim here.
