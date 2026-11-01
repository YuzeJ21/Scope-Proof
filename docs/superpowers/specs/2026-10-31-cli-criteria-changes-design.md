# Headless saved requirements-change handoff

Baseline main: `06b8333aca2f7692436c2748fad3f500272e6a82` (PR #237), clean with post-merge
CI/CodeQL/base-advance successful. The owner delegates routine design and automatic execution,
including independent agent review and guarded merge, without personal testing/qualifying reviews.

## Selected outcome and approach

A recipient of a saved pending revision can list/export retained history through the CLI, but
cannot hand off the old-versus-current requirements explanation without the workbench. Historical
export omits the new pending criteria; evidence comparison correctly refuses changed criteria or
no-active records. Expose the already implemented requirements-only report from PR #235.

Add `scopeproof export-criteria-changes REVIEW_ID --history-position N
--expected-state-fingerprint HASH [--format json|markdown] [--output PATH] [--storage-dir DIR]`.
Reuse `history` for discovery, `HistoricalExportRequest` for strict positive one-based position and
64 lowercase hex fingerprint, and the existing criteria selection/locked-consumer/export services.
This request describes a historical-position-bound report export; no new request schema or alias
is needed. Default JSON, stdout without `--output`, atomic no-overwrite optional files.

The selected design is a thin explicit command alongside the existing historical handoff. Extending
ordinary `compare` would blur evidence-compatibility and requirements-only policies. Full CLI
requirements editing/reanalysis or two-record historical evidence comparison is a larger outcome
and deferred. Review-level acceptance comparison is a real intentional omission but requires new
context semantics; it is not needed to expose this existing saved-requirements report.

## Integrity contract

Validate request before reading. Under the existing store lock, require filename/owner identity
and expected whole-state fingerprint; release before preparing the receipt, because locks are
non-reentrant. `prepare_criteria_comparison` rechecks the saved state and binds historical position,
analysis and both criteria snapshots. `locked_criteria_comparison` rechecks those facts and holds
the lock through complete rendering and stdout/file publication. No default or fallback selection.
Use the existing atomic create-with-receipt helper. Validation failure emits no report; existing,
racing and symlink output targets remain intact. Terminal I/O failures are not transactional.

Reports retain complete previous/current ordered criteria, exact JSON source whitespace, recorded
heads, known/unknown revisions, asserted confirmation and available provenance. Same IDs are keys,
not semantic continuity. Saved pending criteria remain unconfirmed. Missing provenance is unknown
in this requirements-only report; unchanged full historical acceptance-report policy still blocks
that report. No evidence equivalence, verdict, decision carry-forward, criteria confirmation,
record mutation, migration, source/artifact fetch, target-code execution or authentication claim.

Core remains independent of Streamlit/GitHub UI. Preserve record v7, all seven frozen R-002
inputs/results, source 0.2.5 unreleased and public v0.2.4. Stage 1 counts remain zero and Stage 3
dormant. No new dependency, adapter, account, billing, generic review/security/autofix, release,
deployment, outreach, participant contact or standing feature queue.

## Verification and finish

Regress pending/no-active records; duplicate heads/unknown revision; missing provenance without
relaxing acceptance exports; exact whitespace and complete fields; strict mandatory selection;
owner mismatch; state mutation before preparation and consumption; immutable saved bytes; full
render before output; safe existing/racing/symlink targets and lock through publication. Run a
trusted constructed installed-wheel catalog-to-report-to-stale-refusal journey outside checkout.
Automated actors are constructed, not practitioners. Run full unrounded 95% coverage, lint/lock,
both deterministic benchmarks, clean install, existing seventeen browser checks, Python/Windows
CI, independent agent review, exact-head guarded merge and resulting-main verification.
