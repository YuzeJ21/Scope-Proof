# Historical report revision labels Implementation Plan

> **For agentic workers:** Use the existing isolated checkout. Root implements the exporter fix;
> independent workers own tests and current documentation, followed by fresh whole-change review.

**Goal:** CSV/HTML exports of a selected retained bundle identify its recorded criteria revision.

**Architecture:** Keep the shared Pydantic/deterministic export validation boundary. For a full
state use its active revision; for a bare bundle use its own validated positive integer or
literal `unknown`. Do not construct a current lifecycle state to render history.

**Tech Stack:** Python, Pydantic, pytest, existing core CSV/HTML exporters and hosted CI.

**Spec:** User request and the [bounded assessment](../../audits/2026-11-07-historical-report-revision.md).

## Constraints and review focus

- Source remains unpublished `0.2.7.dev0`; public v0.2.6 and recorded producer identities stay intact.
- Missing legacy revision must remain `unknown`; first revision 1 remains valid.
- A retained revision 2 must not become its owning pending revision 3 or a fabricated revision 1.
- Pending current-state exports remain denied; bare-bundle reports retain analysis-only boundaries.
- Invalid/missing provenance remains rejected; persisted native records and frozen R-002 stay intact.
- Dedicated historical JSON/Markdown, UI/CLI controls, schemas and gate policy are unchanged.

## One bounded repair

- [ ] Add failing tests in `tests/reporting/test_historical_revision_labels.py` for native
  retained revision 2, unknown and revision 1, full-state revision 2, pending denial and immutability.
- [ ] Observe revision-label assertion failures before production edits.
- [ ] In `scopeproof_core/reporting/exporters.py`, replace the bare-bundle fallback in CSV/HTML
  with `bundle.criteria_revision_number`; preserve the full-state branch.
- [ ] Run new and related native/reporting tests, lint and repository contracts; fix supported findings.
- [ ] Update current roadmap/changelog to close PR #272 and describe only this report repair.
- [ ] Independently review, run all required exact-head CI, merge, verify resulting main and
  synchronize clean checkouts. Retain exact commands/results in PR checks and local artifacts.

No personal testing, qualifying reviews, new release, deployment or outreach is required or performed.
