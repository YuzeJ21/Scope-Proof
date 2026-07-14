# Pending Criterion Draft Save and Export Guard Design

## Reproduced gap

A deterministic AppTest saved an analyzed demo review, then entered one unsaved
manual-runtime-evidence value. The visible draft was not part of the validated
`ReviewState`, but the workbench still:

- claimed the current review matched the last local save;
- kept `Save local review` disabled as though nothing had changed;
- exposed all three exports even though they omitted the visible draft; and
- allowed review replacement without the existing unsaved-change confirmation.

The same omission applies to pending human-resolution inputs. This is a presentation
and workflow-integrity gap, not a persisted-schema or exporter defect: authoritative
exports correctly contain only appended validated objects.

## Decision

Treat any non-default criterion-detail input as pending unsaved work until it is
submitted through its own form or explicitly cleared.

While such a draft exists:

- include it in the existing unsaved-review replacement guard;
- do not claim that the visible review fully matches its local save;
- disable `Save local review`, because saving `ReviewState` cannot include the draft;
- disable Markdown, JSON, and CSV downloads, because they cannot include the draft;
- state plainly that the draft is not yet saved or exported; and
- expose `Clear pending criterion inputs` as a deliberate recovery action.

After a valid runtime-evidence or resolution submission, process its existing form
reset before deriving global unsaved state. The appended object then makes the
authoritative review unsaved in the normal fingerprint-based way, local Save becomes
available, and exports become available because they now include the validated event.

## Alternatives considered

1. **Guard save, export, and replacement with explicit clear recovery** — selected
   because every visible persistence path tells the same truth.
2. **Show a warning but keep downloads enabled** — rejected because a reviewer could
   still export a package that silently omits visible human input.
3. **Automatically append a draft during local Save or export** — rejected because it
   bypasses the explicit target-specific confirmation and Pydantic/lifecycle path.
4. **Persist transient form drafts in `ReviewState`** — rejected because it expands the
   durable schema and export contract without evidence that draft persistence is needed.

## Architecture and data flow

Refactor the existing presentation helper into three deterministic functions:

- detect whether runtime or resolution draft state is non-default;
- clear only runtime draft keys;
- clear only resolution draft keys.

The combined target-change clear continues using both form-specific clear helpers.
Existing successful-save reset markers are consumed before the top-level unsaved
calculation, preventing a one-render stale warning after a valid append.

No pending value is added to `ReviewState`, `RuntimeEvidence`, `ResolutionEvent`, or an
export. `append_runtime_evidence`, `append_resolution`, local storage, deterministic
gates, and final acceptance remain unchanged.

## Verification

- Prove a draft on an otherwise saved review removes the saved-match claim, triggers
  replacement protection, disables local Save and all downloads, and exposes clear
  recovery without mutating the review.
- Prove explicit Clear removes both runtime and resolution inputs and restores the
  prior saved/exportable state.
- Prove a valid runtime submission clears only its form before unsaved state is
  derived, enables authoritative local Save, and keeps exports available.
- Preserve target-change, successful-form-reset, save/reopen, resolution, export, and
  gate regressions.
- Run focused tests, Ruff, complete offline pytest, deterministic benchmark,
  `git diff --check`, and loopback Streamlit health.

## Evidence limits and boundaries

Controlled AppTests prove only local workbench state behavior. They are not genuine PR
runtime evidence, external adoption, user validation, or proof of correctness. No paid
API/LLM, billing, fork, organization, private repository, GitHub notification,
synthetic validation, untrusted-code execution, schema, gate, release, or evidence-level
semantics change.
