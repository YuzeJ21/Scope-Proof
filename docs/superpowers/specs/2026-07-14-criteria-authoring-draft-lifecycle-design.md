# Criteria Authoring Draft Lifecycle Design

## Problem

On a locally saved analyzed review, entering text in either **Add criterion** or
**Split criterion into one behavior per line** leaves the interface claiming that
the current review matches its local save. Exports stay available, review replacement
does not require confirmation, and the sidebar says review and export are available.
Those unsubmitted inputs are not part of the validated `ReviewState` or any export.

Successful add and split operations also leave their submitted text in the widgets.
The still-populated action can be submitted again, making a completed operation look
like an outstanding draft and making accidental duplicate edits easier.

## Root Cause

`has_pending_review_input` covers inline criterion edits and criterion-detail forms,
but not the two criterion-authoring inputs. `_apply_criteria_update` reruns after a
successful operation without arranging a safe next-run reset for the widget that was
consumed.

## Selected Design

Treat non-empty add and split text as session-only criterion-authoring drafts:

- include them in the existing pending-review-input boundary used by replacement,
  local-save truth, downloads, and sidebar status;
- show exact copy that the drafts are not saved or exported;
- expose a deliberate clear action that changes only these presentation inputs;
- clear the consumed input after a successful add or split via a next-run reset marker;
- keep the relevant add or split submit action usable when its own draft is the only
  pending state on an otherwise saved review;
- continue blocking destructive or unrelated replacement actions until the draft is
  submitted, cleared, or the user explicitly approves replacement.

The helper remains in the Streamlit layer. No schema, lifecycle, evidence, gate,
storage, or export format changes.

## Rejected Alternatives

1. **Leave authoring text outside persistence truth** — rejected because the screen
   would continue to imply that all visible review inputs are saved and exportable.
2. **Clear all authoring inputs on any criteria operation** — rejected because an
   unrelated operation could silently discard another unfinished draft.
3. **Persist authoring drafts in `ReviewState`** — rejected because drafts are not
   confirmed acceptance criteria and would broaden the durable schema without an
   evidence-integrity benefit.

## Verification

- AppTest reproduces the false saved/exportable state for add and split drafts.
- AppTest proves explicit clear restores the saved/exportable state without changing
  the validated review.
- AppTest proves successful add and split operations clear only the consumed input and
  cannot be repeated accidentally from stale widget text.
- Existing criteria confirmation, replacement, save/export, and error-recovery tests
  remain green.
- Full Ruff, pytest, deterministic benchmark, diff check, and Streamlit health smoke.
