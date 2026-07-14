# Manual Verification Note Guard Design

## Context

ScopeProof's accepted public-MVP design defines `manually_verified` as a reviewer recording
external verification with both a claimed evidence level and a note. The current implementation
requires the level but does not require the note.

A current-source schema probe reproduced the integrity gap with empty, spaces-only, and
tab/newline-only notes. `ResolutionEvent` and `HumanResolution` accepted all three values, and a
minimal otherwise-satisfied review evaluated to `Ready`. A current-browser audit reproduced the
same gap in the Streamlit workbench: selecting `Manually Verified` with an empty `Reviewer note`
left `Save resolution` enabled.

The accepted baseline screenshot is saved at:

`/Users/yjian070/.codex/visualizations/2026/07/14/scopeproof-manual-verification-note-audit/01-empty-note-save-enabled.jpg`

## Problem

An append-only `manually_verified` event can currently claim external verification without saying
what the reviewer verified. Because that decision resolves the criterion, a blank record can help
produce `Ready` even though the audit history lacks the note required by the product contract.
This weakens the evidence trail and makes False Ready easier.

## Decision

Require a non-whitespace reviewer note only when the decision is `manually_verified`.

Defense in depth has two layers:

1. `ResolutionEvent` and `HumanResolution` reject a `manually_verified` decision whose `comment`
   is empty or contains only whitespace.
2. Streamlit states the prerequisite next to the conditional evidence-level control and disables
   `Save resolution` until the note contains non-whitespace text.

Valid note text is preserved exactly. ScopeProof will not silently trim or rewrite a reviewer's
evidence description.

## Alternatives Considered

### UI-only readiness guard

Rejected. It prevents the current interactive path from submitting a blank note but leaves direct
model construction, imported JSON, reopened records, and future non-UI callers able to bypass the
product contract.

### Require an evidence URL as well as a note

Rejected. The accepted MVP contract requires an evidence level and a note, while `evidence_url`
is optional. Making a URL mandatory would introduce a new evidence policy without contract
support and could exclude legitimate locally identified verification artifacts.

### Require notes for every human decision

Rejected. Existing semantics intentionally allow a note to be optional for decisions such as
`accepted`, `change_required`, and `not_in_scope`. This change is limited to the one decision whose
contract explicitly requires a note.

## Schema Behavior

Both persisted representations enforce the same invariant:

- `ResolutionEvent` rejects blank normalized comment content when
  `decision == HumanDecision.MANUALLY_VERIFIED`.
- `HumanResolution` rejects the same invalid state so standalone imported or exported bundles
  cannot bypass the event contract.
- The existing claimed-evidence-level requirement remains unchanged.
- Nonblank comments retain leading and trailing whitespace exactly.
- Other human decisions continue accepting an empty comment.

The validation message is stable and domain-specific:

`manually verified decisions require a reviewer note`

## Streamlit Behavior

When the reviewer selects `Manually Verified`:

- keep the existing external evidence-level selector;
- show `Reviewer note is required for manual verification. Describe what was verified.` directly
  before the save action;
- keep `Save resolution` disabled while the note is empty or whitespace-only;
- enable the action when the note contains non-whitespace text;
- preserve the existing success, reset, append-only history, unsaved-state, and gate recalculation
  behavior after a valid save.

For every other decision, save readiness remains based only on making an explicit selection.

## Gate And Lifecycle Boundaries

The deterministic gate table is unchanged for valid events. This correction changes which
`manually_verified` events are valid; it does not alter how a valid manual verification resolves a
criterion. Runtime evidence remains separate and cannot resolve a criterion. Final acceptance
remains a review-level event and cannot override blockers.

No migration rewrites old evidence. A repository-local read-only audit found 161 saved reviews and
zero `manually_verified` events, so the user's current review store has no incompatible record.
Any external alpha record that relied on a blank manual-verification note will be rejected rather
than silently upgraded or assigned invented context.

## Verification

Regression-first coverage will prove:

- both schema representations reject empty and whitespace-only manual-verification notes;
- both preserve valid note text exactly;
- other decision types still allow an empty note;
- the Streamlit action is disabled with an empty or whitespace-only note and shows the prerequisite;
- a valid note enables saving and preserves the existing form-reset behavior;
- no resolution event is appended while prerequisites are incomplete;
- the complete offline suite, Ruff, deterministic benchmark, and `git diff --check` pass;
- a clean-installed wheel enforces the schema invariant;
- the packaged local web app returns a healthy HTTP response;
- a same-state browser audit confirms the prerequisite and disabled action without submitting an
  invented manual-verification event.

## Out Of Scope

- Requiring evidence URLs.
- Changing evidence levels or decision meanings.
- Changing gate precedence, runtime-evidence semantics, or final acceptance.
- Editing or manufacturing existing review records.
- Executing pull-request code or presenting the demo as genuine external verification.
- Publishing a standalone release for this bounded correction.
