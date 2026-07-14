# Pending Criteria Persistence Guard Design

## Reproduced gap and root cause

A current-main AppTest saved an analyzed review and then changed the visible text of
`AC-01` without confirming the edit. The criteria section correctly warned that the
edit was pending and continued showing evidence from the last confirmed revision, but
the workbench still:

- claimed the current review matched its last local save;
- exposed Markdown, JSON, and CSV downloads containing the old confirmed criterion;
- allowed review replacement without unsaved-work confirmation; and
- kept the sidebar label `Available — Review evidence and export`.

The root cause is state timing. `criteria_edits_pending` is derived inside the criteria
editor after the source/reopen replacement guard has already rendered. Summary and
download readiness then use only persisted-review fingerprints and criterion-detail
draft state, not the visible unconfirmed criteria widgets.

## Decision

Derive one presentation-only pending-criteria Boolean from the current authoritative
criteria and their text, priority, and required-evidence widget values. The helper must
work both before and after the criteria editor renders by using each authoritative
value as the default when a widget key does not yet exist.

While criteria edits are pending:

- include them in the existing unsaved-review replacement guard;
- state that the visible edits are not saved or exported;
- disable `Save local review` and all three downloads;
- retain the existing requirement to confirm edits before analysis;
- show `Pending — Resolve inputs before export` in the sidebar; and
- expose `Discard unconfirmed criteria edits` as an explicit recovery action.

Discard restores only current criteria widget values from the last confirmed
authoritative criteria. It does not revise criteria, invalidate analysis, append an
event, modify the review, or change its saved fingerprint. Confirm continues using the
existing validated `revise_criteria` and `confirm_criteria` lifecycle path.

## Alternatives considered

1. **Shared early detector plus confirm/discard recovery** — selected because source,
   save, export, and sidebar state all receive the same truth without changing durable
   objects.
2. **Move the source and replacement controls below the criteria editor** — rejected
   because those controls intentionally define the first-use flow and are consumed by
   earlier source actions.
3. **Set a sticky pending flag from widget callbacks** — rejected because reverting all
   fields to their confirmed values would remain falsely pending without another full
   comparison.
4. **Auto-confirm edits during local Save or export** — rejected because it bypasses the
   explicit reviewer-confirmation boundary and would invalidate analysis implicitly.

## Architecture and data flow

Only `apps/web/app.py` presentation state changes:

- `_criteria_draft_pending(criteria: list[Criterion]) -> bool` compares current widget
  state with the authoritative list;
- `_clear_criteria_draft(criteria: list[Criterion]) -> None` restores widget values;
- a pending reset marker lets the post-widget discard button apply changes safely at
  the beginning of the next Streamlit rerun;
- one combined pending-input Boolean gates replacement, summary truth, local Save, and
  downloads; and
- the existing later `criteria_edits_pending` variable reuses the same helper.

`Criterion`, `CriteriaRevision`, `ReviewState`, Pydantic validation, lifecycle services,
analysis, findings, gates, final acceptance, storage formats, and exporter contents
remain unchanged.

## Verification

- Add an AppTest proving an edit on an otherwise saved review triggers replacement
  protection, removes the saved-match claim, disables local Save and downloads, and
  updates the sidebar without mutating the authoritative review.
- Add an AppTest proving Discard restores text, priority, and evidence level, removes
  pending guidance, and restores the prior saved/exportable state.
- Add an AppTest proving Confirm still creates a new revision, invalidates stale
  analysis, and clears pending persistence guards.
- Preserve blank-edit recovery, unchanged-confirmation guard, pending-edit analysis
  lock, criterion-detail draft guards, save/reopen, and export tests.
- Run focused tests, Ruff, complete offline pytest, the deterministic benchmark,
  `git diff --check`, and loopback Streamlit health.

## Evidence limits and boundaries

The controlled demo and AppTests prove only local workbench state behavior. They are
not external PR evidence, genuine runtime verification, user adoption, or proof of
correctness. No paid API/LLM, billing, fork, organization, private repository, GitHub
notification, release, synthetic validation, untrusted-code execution, schema, gate,
or evidence-level semantics change.
