# Inspect saved criteria revision changes

## Intent and delegated design

The owner delegated the next bounded automatic product improvement after PR #234, with no
personal testing or qualifying reviews. Live main is `9f7a0b86316063e1fa001d9179d1c67920c42d22`;
all post-merge checks pass and the workspace is clean. Independent gap inspection selected
requirements change inspection: revising criteria archives analysis and clears the active bundle,
while evidence comparison correctly refuses changed criteria or provenance.

Add a separate read-only criteria comparison. CLI parity would extend access to an existing
outcome; final-acceptance comparison would add narrower context. Neither explains changed
requirements. Reusing `ReviewComparison` would weaken its compatibility contract, so leave it
untouched. The owner has delegated routine design choices and execution; no further approval
or participant program is needed.

## Contract

Compare one explicitly selected history position in one opened saved record with that record's
current saved criteria revision, including an unconfirmed revision with no active analysis.
Never include unsaved input drafts, compare evidence, infer semantic matching, carry decisions
forward, confirm criteria, mutate storage or run analysis. IDs identify recorded keys only;
the same ID can be reused and does not prove continuity. Different IDs remain separate even
when their text matches. Positions are one-based recorded positions, not rankings.

`scopeproof_core/reviews/criteria_comparison.py` provides:

- `CriteriaSnapshot`: frozen, extra-forbid Pydantic view with exact saved head, positive or unknown
  revision, explicit confirmation, full source text, complete ordered `Criterion` records and
  optional recorded provenance. Require explicit fields, unique criterion IDs, and matching
  provenance digests when present. No generated historical timestamps or inferred provenance.
- `CriteriaComparisonSelection`: nested `HistoricalAnalysisSelection` plus previous/current
  criteria-snapshot SHA-256 fingerprints. Full owner/state/history/analysis fingerprints remain
  binding. Fingerprints are consistency checks, not authenticated provenance.
- `CriteriaRevisionComparison`: fixed report kind/version/boundary, selection, previous/current
  snapshots and installed validation tool/ruleset/core-source identity. Revalidate snapshots,
  hashes and known revision order. Computed per-ID rows expose complete previous/current records,
  positions and changed fields, with only-previous/only-current/fields-changed/identical labels.
  Separate exact source-text, provenance-record and criterion-order distinctions remain visible.
  Missing provenance is explicitly unavailable, not an empty confirmed source.
- `prepare_criteria_comparison(store, state, history_index)` and
  `locked_criteria_comparison(store, selection)` validate the complete saved state, filename owner,
  exact history position and both snapshots under the existing record lock. Yield detached data
  while retaining the lock through consumers. Changed/deleted/reordered/retargeted records fail
  closed without fallback. Core imports no UI.

`scopeproof_core/reporting/criteria_comparison.py` revalidates before JSON/Markdown export.
Reports contain criteria snapshots only: no gate, evidence, runtime or decision projections.
Missing historical provenance may be reported as unknown because this is a requirements-only
view, not an acceptance report; existing historical/full-report export policy stays unchanged.
Markdown uses existing safe text/code rendering, with complete criterion and provenance fields,
full source text and clearly labeled confirmation. Exact heads are saved context, not fresh
source verification. No external source is fetched. Current validation identity stays separate
from requirement authorship, asserted confirmation and historical analysis producer identity.

## Workbench

Within the existing historical inspector, add explicit **Compare with saved current criteria**.
It is available only after explicit historical selection and uses its exact saved record.
The previous historical-only report stays independent. Show a separate requirements-only warning,
previous/current revision and confirmation, full before/after details and JSON/Markdown downloads.
Use existing inert Markdown adapter and scoped responsive preview style. Legacy full-report
provenance restrictions must not prevent this limited criteria view.

Changing historical selection, reopening/resetting, unsaved model state or record changes clears
the criteria selection and invalidates old callbacks. New criteria callbacks bind selection and
lease generation, locked reload and post-render lease validation. Unsaved text widget drafts
never enter reports; saved pending criteria remain explicitly unconfirmed. No acceptance controls.

## Verification and finish

Test added/removed IDs, complete field edits, reused IDs, identical text with different IDs,
order-only/source-only/provenance-only changes, no changes, empty current set, unconfirmed current
revision, unknown historical revision/provenance, malformed/tampered snapshots and stale/deleted
records. Assert saved bytes and current state are unchanged. Test stale callbacks before/after
render and reopen reset. Extend the existing installed history-only journey to download both
requirements formats, check exact content and inert text, and capture desktop/phone/CSS-200%
geometry. Browser automation is not accessibility conformance or independent use.

Run the full suite with the existing unrounded 95% floor, lint/lock checks, both deterministic
benchmarks, clean installed-wheel verification, packaged browser and available Python/Windows CI.
Obtain independent agent review, resolve supported findings, require exact-head hosted CI and
CodeQL, guarded merge and resulting-main verification. Preserve seven frozen R-002 files,
record v7, current evidence-comparison/confirmation/gate semantics and public v0.2.4.
Source stays 0.2.5 unreleased; Stage 1 closed at zero, Stage 2 owner-led, Stage 3 dormant.
No release, deployment, outreach, qualifying reviews, accounts/billing or standing queue.
