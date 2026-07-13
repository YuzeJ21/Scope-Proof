# ScopeProof Fresh-Session Review Reopen Design

## Problem

ScopeProof advertises durable local reviews that can be reopened by review ID. The current
Streamlit controls for reopening are rendered only inside the post-analysis branch. A fresh app
session has no bundle, so it exposes neither the review-ID field nor the reopen button. A
deterministic temporary-storage reproduction saved a valid review successfully, started a fresh
AppTest session, and found both reopen controls absent.

The current handler also does not clear `st.session_state["snapshot"]` or synchronize the
`requirements_input` widget. If the control were merely moved, reopening over a different loaded
PR could leave an unrelated snapshot eligible for re-analysis with the reopened criteria. A saved
`ReviewState` contains the validated analysis, evidence, history, and source text, but it does not
contain the original `PullRequestSnapshot`. Reopening must therefore restore reviewable state
without pretending the original source is loaded for a new analysis.

## Chosen Design

Place a compact `Reopen saved review` section at the start of the workflow, before the public-PR
and requirements widgets are instantiated. This makes reopening available in a fresh session and
allows the handler to synchronize widget-backed session keys safely in the same run.

On a successful load, hydrate the validated saved state into:

- `review_state`
- `bundle`
- `criteria`
- `criteria_confirmed`
- `source_text`
- `requirements_input`

Explicitly set `snapshot` to `None` and `resolutions` to an empty list. The reopened bundle and
append-only lifecycle history remain immediately viewable and exportable. Deterministic analysis
remains disabled until the operator deliberately loads the public PR or demo again and reconfirms
criteria. The sidebar distinguishes this state as `Next — Reload source to rerun analysis` while
still reporting the saved analysis and review/export steps as complete.

Remove the duplicate reopen controls from the post-analysis summary section. Saving remains next
to the active review because it requires an analyzed `ReviewState`.

## Error Recovery

- A missing review ID displays `No saved review was found for that review ID.`
- An unsupported record version displays a concise version-compatibility message.
- Other I/O or validation failures display a stable record-integrity message without raw paths,
  tracebacks, or Pydantic internals.
- Failed loads do not mutate any existing session state.

`JsonReviewStore` remains the authoritative path and Pydantic validation boundary. The UI does not
accept arbitrary paths, follow symlinks, or bypass record validation.

## Alternatives Considered

1. Persist the entire PR snapshot in every local review. This would permit immediate reruns, but
   stores more repository content and risks silently analyzing stale source.
2. Add a separate saved-review landing mode. This creates unnecessary navigation and state
   complexity for one local identifier field.
3. Move only the existing controls. This fixes discoverability but leaves widget desynchronization
   and cross-review snapshot contamination possible.

## Components and Data Flow

```text
Review ID
   ↓
JsonReviewStore.load (path restrictions + Pydantic validation)
   ↓
Hydrate saved ReviewState and source text
   ↓
Clear unpersisted PR snapshot
   ↓
View/export saved bundle now; reload source before re-analysis
```

No core schema or lifecycle change is required. `apps/web/app.py` owns session hydration and
first-use messaging; `JsonReviewStore` continues to own validated persistence.

## Verification

- Add an AppTest using temporary HOME storage that saves a deterministic demo review, starts a
  fresh app session, and proves the reopen controls are available before analysis.
- Prove a successful fresh-session reopen restores review identity, source text, criteria,
  confirmation, bundle, history, visible evidence, and export controls.
- Prove `requirements_input` matches the persisted source text.
- Prove reopening over a loaded snapshot clears that snapshot and disables re-analysis.
- Prove a missing review ID produces concise guidance and leaves the previous session state intact.
- Preserve storage traversal/symlink/version tests and export equivalence tests.
- Run focused AppTests, storage/reporting tests, Ruff, the complete offline test suite, the 12-case
  deterministic benchmark, `git diff --check`, and a real local Streamlit fresh-session reopen
  using temporary storage.

## Out of Scope

- Persisting or reconstructing PR snapshots.
- Automatically refetching GitHub data or detecting a new head during reopen.
- Changing evidence, findings, resolution history, final acceptance, gates, or exports.
- Adding a saved-review browser, deletion controls, cloud storage, telemetry, or paid services.
