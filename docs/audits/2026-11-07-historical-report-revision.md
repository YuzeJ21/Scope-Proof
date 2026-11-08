# Selected retained-analysis CSV/HTML revision labels — 2026-11-07

Baseline: PR #272 main `069af259ac17b6c555d10b10f36e7211b068aac4`, with green resulting-main
CI [42428549217](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42428549217).
Source stays unpublished `0.2.7.dev0`; public v0.2.6 is unchanged.

## Reproduction and cause

The immutable public-v0.2.6 pending corpus contains an unconfirmed current revision 3, no active
analysis, and retained analyses at revisions 1 and 2. Explicitly selecting the revision-2 bundle
and exporting it through the core CSV/HTML APIs shows revision 1. JSON already retains revision 2.
A supported legacy bundle with revision `unknown` also incorrectly shows revision 1 in CSV/HTML.

Both exporters revalidate the input through the existing Pydantic and deterministic gate boundary.
Their display expressions then use the full state's criteria revision when available but a literal
1 for a bare bundle. The validated bundle already supplies its positive integer revision or the
literal `unknown`; the fallback discards that fact. No state or saved-file mutation causes the error.

## Bounded repair and retained boundaries

The CSV `criteria_revision` column and HTML criteria-revision metadata use
`bundle.criteria_revision_number` when no complete state is supplied. The full-state branch is
retained; its existing validator requires the active bundle's known revision to match the state.
No new helper, schema, record format, policy rule or version declaration is required.

Bare-bundle reports remain analysis-only: they cannot establish the owning pending review's
current status, complete decision-event history or current-head verification. An explicit retained
Ready result remains the selected historical result, not acceptance of a pending revision.
Pending current-state JSON, Markdown, CSV and HTML exports remain blocked by existing validation.
Unknown revision stays unknown; it is not inferred from timestamps, list position or current state.

The dedicated historical-analysis UI/CLI paths continue to offer their existing JSON and Markdown
reports. This repair adds no historical CSV/HTML download control and changes no Markdown/JSON
report behavior. Producer identity, confirmation/provenance, evidence and audit contents remain
recorded facts. No target-repository code is executed in the application server.

## Automated evidence and limits

Regression coverage exercises the native retained revision-2 case alongside its pending revision 3,
legacy unknown, first revision 1, active full-state revision 2, analysis-only boundaries, pending
denial, input immutability and producer preservation. The native fixtures and generation/provenance
hashes are retained unchanged. Existing malformed/provenance, historical-selection, rendering and
native preservation regressions remain required.

Merge requires independent agent engineering review and exact-head CI: lint, full suite with the
unrounded 95% coverage floor, deterministic benchmarks, supported Python/Windows checks and
installed CLI/browser journeys. Resulting-main checks are verified separately. Exact heads,
commands, final results and review dispositions are retained with the PR and external artifacts.

These are constructed automated engineering checks, not genuine independent use, qualifying
reviews, target-runtime proof, accessibility conformance or beta validation. Frozen R-002 and
older audits are unchanged. Stage 2 remains owner-led and Stage 3 remains dormant pending genuine
independent-use evidence and separate authorization. No new release, deployment or outreach occurs.
