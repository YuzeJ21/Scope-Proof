# Inspect and hand off one saved historical analysis

## Intent and delegated choice

After PR #233 the owner delegated one high-value automatic product improvement, with no personal
testing or qualifying reviews. Live main `80870aff7affed5c5a97c026daf3507bebcd53b6` and all three
post-merge workflows are green; both checkouts are clean and no PR is open. Independent gap
inspection confirms that saved history is intact in whole-state JSON, but UI history access is a
comparison workflow requiring a compatible saved active analysis. A pending revised record with
no active bundle, or different criteria, cannot inspect and hand off a retained analysis by itself.

Select a separate read-only historical inspector on the opened saved record. Reusing comparison
would weaken its compatibility contract; replacing the active bundle would corrupt review authority.
A separate criteria-change comparison is useful but solves a different question. This selected
slice adds historical JSON/Markdown only, without a new standalone viewer for arbitrary files,
CSV/HTML history formats, new adapters, criteria matching or event-history replay.

## Core and report contract

New `scopeproof_core/reviews/historical_analysis.py` exposes:

- `HistoricalAnalysisSelection`: frozen, extra-forbid, revalidated Pydantic receipt with local
  `review_id`, `state_fingerprint`, strict nonnegative `history_index` and `analysis_fingerprint`.
- `prepare_historical_analysis(store, state, history_index)`: validate open state and index, load
  under the existing record lock, require filename/owner identity and exact full-state fingerprint,
  select that retained position only, and return the receipt. No active bundle, compatible current
  criteria or current criteria confirmation is required for reading an already validated history.
- `locked_historical_analysis(store, selection)`: revalidate the receipt, reload under the same
  lock and compare full-state/analysis fingerprints and owner before yielding a detached
  `HistoricalAnalysisReport`. Keep the lock held through the consumer. Changed/deleted/corrupt,
  reordered/replaced histories and mismatched files fail without fallback.
- `HistoricalAnalysisReport`: explicit `report_kind='scopeproof_historical_analysis'`,
  `schema_version=1`, fixed historical boundary, receipt, full `analysis: ReviewBundle`, and current
  validation tool/ruleset/core-source identity. Validate the analysis with existing deterministic
  bundle rules, receipt ownership and fingerprint; preserve its producer tool/ruleset/source
  identity, exact head and `criteria_revision_number`, including `unknown`. Hashes are consistency
  checks, not authentication. No generated report timestamps or inferred source metadata.

`analysis_fingerprint` is SHA-256 over the existing validated bundle's deterministic model JSON,
including full recorded data. A reparsed or mutated report must reproduce it; missing/defaulted
timestamps cannot quietly become recorded history. The saved-state fingerprint separately binds
the complete owner and history position. No object is persisted and record version 7 is unchanged.

New `scopeproof_core/reporting/historical_analysis.py` provides
`export_historical_json(report)` and `export_historical_markdown(report)`. Both fully revalidate the
report, current validation identity and original bundle export eligibility. Missing criteria-source
provenance remains an export blocker under the existing policy; do not fabricate it or synthesize
a `ReviewState`. JSON carries the typed historical envelope. Markdown leads with historical-only
identity/boundary, known or unknown revision, owner/state/analysis hashes and validation identity,
then reuses the existing safe complete bundle report. Rename its normal title/status label to
historical details and historical status (installed policy). The wrapper supplies the revision
that standalone Markdown currently omits; standalone CSV/HTML revision defaults are not reused.

Loading a historical record may conservatively revalidate/migrate its gate under installed policy.
The report states that policy context and never claims to restore an unverified original gate or
current-head authority. Existing findings, missing evidence, citations, latest criterion decisions,
runtime records, file-scope decisions and selected-reference audit remain the snapshot's records.
Full owning resolution-event history is not reconstructed from current events.

## Workbench and freshness

New `apps/web/historical_analysis.py` renders an **Inspect retained analysis** expander before the
active-analysis conditional in Decision Progress. It consumes the current opened state, store and
an explicit `current_is_saved` equality check. It may operate with a saved pending criteria revision
or changed criteria/source observations, because output is explicitly historical; existing current
analysis/export/final-acceptance controls remain unchanged. Unsaved model changes or unavailable
storage disable selection. Draft current inputs never become part of the historical report.

Use a neutral history selector with no default: `History N · criteria revision X · head SHA`.
Show recorded owner identity and the historical boundary before selection. Clicking
**Inspect selected historical analysis** prepares a receipt and applies it to a volatile session
lease. Each rerun revalidates the saved snapshot before displaying it. Do not auto-apply a new
history when a record changes. Selection changes, reopen/reset, changed owner/fingerprint, storage
loss or failed validation clear the selection and invalidate old download callbacks.

The panel shows the historical head/revision/producer/validation identities, then a read-only full
Markdown report when exportable. For legacy missing provenance, show identity and the precise
unavailable-report limitation; no report downloads or fabricated provenance. No editable decision,
source reload, acceptance or save controls are added. Safe existing Markdown escaping/reference
rendering is reused. Head/hash widgets wrap at narrow widths; unsafe text stays inert.

New `deferred_historical_export` and `HistoricalAnalysisExportLease` in the existing deferred-export
module bind click-time output to both the original receipt and lease generation, reload and hold
the record lock through rendering, and recheck the lease afterward. No stale prefetched bytes.

## Automated finish line and boundaries

Construct history-only and incompatible-current cases, multiple/unknown revisions, real lifecycle
retained decisions/references/runtime facts, missing provenance, no history, filename mismatch,
invalid receipt types/indexes, changed/removed/reordered history, runtime-only/reference-only owner
mutations, export field/fingerprint tampering, no inferred defaults and no artifact access/execution.
Assert saved JSON bytes, current state/criteria/decisions/gates and frozen benchmark files unchanged.

Core/report/AppTest and installed-wheel restart/reopen/inspect/download checks must cover both
formats, history-only access, current draft separation, stale callbacks and safe text. Capture the
actual historical section at desktop, phone and 200% CSS zoom with dimensions; no accessibility or
native-zoom claim. Extend an existing constructed journey where practical and label counts accurately.
Run full existing 95% coverage, lint/lock/contracts, deterministic benchmarks, clean install/package,
available Python/Windows CI, independent whole-branch review/fixes, guarded exact-head merge and
separate resulting-main verification.

Do not alter seven frozen R-002 inputs/results, historical labels/scores, current gate or comparison
semantics, source execution boundaries, private candidate artifacts or public v0.2.4. Source stays
unreleased 0.2.5, Stage 1 closed at zero, Stage 2 owner-led and Stage 3 dormant. No personal testing,
qualifying reviews, release, deployment, outreach, accounts/billing or standing next queue follows.
