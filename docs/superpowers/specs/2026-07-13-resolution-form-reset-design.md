# Resolution Form Reset Design

## Problem

After ScopeProof successfully appends a human criterion resolution, Streamlit keeps the submitted
decision and reviewer note in their keyed widgets. The **Save resolution** button therefore remains
enabled. A second unchanged click appends an identical audit event, making the first event appear
superseded even though the reviewer did not express a new decision.

## Evidence

- The successful-save branch updates the review state and bundle but does not clear the
  `resolution_decision`, `resolution_note`, or conditional `manual_evidence_level` widget state.
- A live deliberately constructed demo retained `Accepted` and `Evidence reviewed` after the first
  save while leaving **Save resolution** active.
- Clicking the unchanged button again produced two revision-1 AC-01 events: the first was labelled
  `Superseded` and the identical second event `Current`.
- The deterministic gate remained Blocked, so this is an audit-history and interaction-integrity
  defect rather than evidence of a gate-calculation defect.

## Approaches Considered

1. **Clear the form after a successful append (selected).** Set a short-lived reset marker and
   success notice, rerun, then clear the keyed widgets before they are instantiated. This makes a
   second resolution an explicit new action without changing core semantics.
2. **Disable only exact duplicate submissions.** This prevents the observed duplicate but leaves a
   completed action looking editable and requires comparison rules for optional fields.
3. **Reject duplicate events in the core.** This would incorrectly change append-only domain
   semantics because two separately reviewed, identical decisions can still be legitimate events.

## Design

The Streamlit layer owns the reset because widget state is a presentation concern. Immediately
after a successful `append_resolution()` call, the app stores two ephemeral session values:

- a marker requesting the resolution widgets be reset on the next run; and
- the existing success message as a one-run flash notice.

The app then reruns. Before rendering the resolution widgets, it consumes the reset marker and
clears the decision, reviewer note, and conditional manual-evidence-level keys. It also consumes and
renders the success notice. The result is an empty decision, empty note, disabled save button, one
visible success confirmation, and an unchanged append-only history containing exactly one event.

## Boundaries

- No gate, evidence, decision-replacement, or history-classification semantics change.
- No persisted or exported schema changes.
- No event is deleted or rewritten.
- Failed validation or failed append attempts do not clear the reviewer's input.
- The core remains independent from Streamlit.
- The UI does not claim the overall review is Ready after a criterion resolution.

## Verification

- A Streamlit AppTest must fail on the existing retained controls, then pass by asserting one event,
  cleared widgets, a disabled save button, and a preserved success notice after a successful save.
- Existing resolution, manually-verified evidence-level, history, and gate tests must remain green.
- Full Ruff, offline pytest, deterministic benchmark, installed-wheel smoke, and a live browser
  comparison are required before publication.
