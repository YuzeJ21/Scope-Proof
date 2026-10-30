# Historical baselines from another saved review

## Outcome and approach

The owner explicitly requested this Stage 2 follow-on after PR #227 and delegated implementation,
automatic verification, independent review and checked merge without personal testing or qualifying
reviews. Core saved comparison already accepts any baseline record/history index; the current UI
only lists other active records and the current record's own history.

Choose a record, then its analysis. Eagerly loading every saved record to flatten all histories
would scale with every full saved file on each rerun. The chosen approach loads only the explicitly
selected other record. Preserve the existing top-level `saved:<id>` and current `history:<index>`
choices; a second **Baseline analysis** selector appears for another record. Its `active` option is
initially selected when an active bundle exists, preserving existing explicit-record comparison.
Historical options (`history:<index>`) show ordinal, criteria revision and immutable head. A
history-only record starts with no selected analysis. Never hide compatible history because the
foreign active bundle is absent or incompatible. Compatibility remains the existing core check.

## Identity and fail-closed behavior

The selected other record is loaded and Pydantic-validated read-only. Build its analysis options
from that saved snapshot; display its record identity and each option's revision/head. Missing,
corrupt or unsupported records provide no comparison. Do not fetch GitHub or rerun analysis.

Bind the secondary selection context to record ID plus its complete `state_fingerprint`. Parent
record changes clear its analysis choice, applied comparison and download lease. A changed selected
record invalidates pending and applied choices and requires explicit reselection: do not silently
switch to active or another historical index. History replacement/removal/reorder and selected-
reference-only changes count as record changes, even if head/revision labels remain the same.

Close the discovery-to-click race with optional kw-only
`prepare_saved_comparison(..., expected_baseline_fingerprint: Fingerprint | None = None)`.
Under its existing sorted record locks, validate the expected receipt through
`SavedComparisonSelection.baseline_fingerprint` and compare it with the actual saved fingerprint
before selecting history. A mismatch raises `SavedComparisonUnavailable`. Existing callers that
omit it retain their behavior; the new foreign-record picker always supplies the displayed
snapshot's fingerprint. No new persisted object or record migration is needed. Existing applied
selection/deferred-download fingerprint checks remain authoritative.

## Boundaries

Preserve complete saved JSON bytes, active/history bundles, criteria confirmation, compatibility,
candidate and selected-reference comparison semantics, source eligibility, decisions, scope and
gates. No automatic baseline guessing, reanalysis, decision carry-forward, new source retention,
dependencies or adapters. Keep all frozen research files/expectations/results/scores and private
candidate artifacts unchanged. New cases are constructed engineering evidence only; no human use,
customer validation, accessibility conformance, release/deployment/outreach or Stage 3 advance.

## Acceptance

Automated tests and installed-browser restart/reopen/download cover foreign history with distinct
head/revision/attribution, history-only records, incompatible active with compatible history,
incompatible selected history, missing/corrupt records, switching record/index, pending replacement
and atomic discovery races, applied/deferred invalidation on history/reference changes, literal
identity display and unchanged saved bytes/gates. Run original full 95% coverage, lint/lock/diff,
unchanged deterministic benchmarks, available Python/Windows lanes, independent whole-branch
review, exact-head guarded merge and resulting-main verification.
