# Requirements Draft Persistence Guard Design

## Problem

On a locally saved analyzed review, changing **Product requirements or acceptance
criteria** without pressing **Prepare criteria** leaves ScopeProof claiming that the
review matches its local save. Downloads remain available, replacement actions remain
unguarded, and the sidebar says evidence review and export are available. The visible
requirements draft is not part of the validated `ReviewState` or any export.

## Root Cause

The pending-review-input boundary covers inline criterion edits, add/split authoring
drafts, and criterion-detail drafts, but it does not compare `requirements_input` with
the authoritative `source_text` used by the active criteria revision.

## Selected Design

Treat a requirements widget value that differs from authoritative `source_text` as a
session-only pending requirements draft:

- include it in replacement protection, local-save truth, download readiness, and
  sidebar status;
- state explicitly that unprepared requirements are not saved or exported;
- expose **Discard unprepared requirements changes**, restoring the authoritative
  source text without changing the review;
- keep **Prepare criteria** usable when the requirements draft is the only pending
  state on an otherwise saved review, because that action consumes the draft;
- continue blocking unrelated replacement actions until the draft is prepared,
  discarded, or replacement is explicitly approved.

No durable model, lifecycle, evidence, gate, storage, or export format changes.

## Rejected Alternatives

1. **Treat the requirements box as unrelated scratch text** — rejected because it is
   the product-intent source for criteria and is displayed inside the current review
   workflow.
2. **Persist unprepared text in `ReviewState`** — rejected because unprepared text is
   not authoritative acceptance criteria.
3. **Clear the box to empty on discard** — rejected because discard should restore the
   last authoritative source, not remove it.

## Verification

- AppTest reproduces the false saved/exportable state.
- AppTest proves discard restores exact authoritative source text and leaves the
  validated review unchanged.
- AppTest proves preparing the draft consumes it into criteria without requiring an
  unrelated replacement approval.
- Existing pending-input, criteria preparation, replacement, persistence, and export
  tests remain green.
- Full Ruff, pytest, deterministic benchmark, diff check, and Streamlit health smoke.
