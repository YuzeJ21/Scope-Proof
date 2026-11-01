# Command-line historical analysis handoff

The owner delegates selection, design, automated testing and independent agent review. The selected
outcome is headless inspection/handoff of a retained analysis when a saved review has changed,
unconfirmed criteria and no active bundle. This extends the existing workbench outcome to scripts.

## Approach

Reuse the historical selection/locked-consumer services and JSON/Markdown exporters from PR #234.
Add two explicit commands rather than overloading current `export` or building another report
policy. A single export with an implicit latest-history default would be smaller but could retarget
the operator's choice. Full CLI criteria-comparison parity is adjacent and deferred.

`scopeproof history REVIEW_ID [--storage-dir DIR]` emits one Pydantic-validated JSON metadata
catalog: record/repository/PR, whole-state fingerprint, current saved head/revision/confirmation,
active-analysis presence, and retained entries in stored order. Each entry has an explicit one-based
position, saved head, known/unknown revision, asserted confirmation, full analysis fingerprint,
recorded tool/ruleset and available producer source identity. No verdict or gate is computed or
reported by the catalog. Empty history produces an empty entries list. Input is bounded by the
existing saved-record size policy; no persistent index, extra history limit or pagination is added.

`scopeproof export-history REVIEW_ID --history-position N --expected-state-fingerprint HASH
[--format json|markdown] [--output PATH] [--storage-dir DIR]` requires a positive one-based position
and 64 lowercase hex fingerprint from the catalog. Validate the request before reading the record.
Load under the existing record lock and check filename/owner plus the expected full fingerprint;
release that non-reentrant lock before preparing the existing selection receipt. Preparation and
locked consumption recheck the exact saved state, position and full analysis identity. Hold the
consumer lock through rendering and stdout/file publication. Never fall back to another entry.

Render the complete report before emitting anything. Use the existing atomic create-with-receipt
file helper for optional output; never overwrite an existing path, including a racing/symlinked
target. Failure emits no report to stdout and creates no report file. OS-level stdout failures may
still be partial; no claim of transactional terminals is made. Requests are not authentication.

Keep historical producer context separate from installed validation identity. Preserve unknown
revisions and legacy saved-head labels; missing historical provenance blocks the full report through
the unchanged exporter. Catalog metadata is descriptive and does not certify export eligibility.
All saved review bytes, decisions, criteria confirmation and gates remain unchanged.

## Boundaries and verification

Core catalog/request models stay independent of Streamlit/GitHub UI. No migration, network fetch,
target-code execution, new dependency, generic review/security/autofix or criteria-confirmation
shortcut. Preserve frozen R-002's seven inputs/results, record v7, source 0.2.5 unreleased and public
v0.2.4. Stage 1 counts stay zero; Stage 3 stays dormant. No personal testing, qualifying reviews,
publication, deployment or outreach.

Regress empty/duplicate-head histories, pending criteria, unknown revision/producer context,
invalid requests, wrong owner, stale catalog and mutations between prepare/consume, missing
provenance, unchanged bytes, stdout/file equivalence and safe no-overwrite output. Verify installed
wheel commands outside the checkout, existing packaged-browser journeys, full suite at unrounded
95%, lint/lock, deterministic benchmarks, hosted Python/Windows checks, independent agent review,
exact-head guarded merge and resulting main. Label every constructed actor and input accurately.
