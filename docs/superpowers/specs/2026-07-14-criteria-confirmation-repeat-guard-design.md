# Criteria Confirmation Repeat Guard Design

## Reproduced gap

A current-main AppTest probe loaded the controlled demo, confirmed revision 1,
and generated analysis. With no visible criterion edit:

- `Confirm criteria` remained enabled;
- clicking it advanced the criteria revision from 1 to 2;
- the active analysis bundle changed from present to absent;
- `Run deterministic analysis` became enabled again.

The lifecycle correctly treats an explicit revision as invalidating prior
analysis. The UI incorrectly offers that destructive transition when the
reviewer has made no change to confirm.

## Decision

Disable `Confirm criteria` when either:

- any visible criterion text is blank; or
- the visible criterion set is already confirmed and has no pending edit.

Keep the control visible. Re-enable it immediately when a valid text, priority,
evidence-level, order, add, split, or remove edit makes the visible set differ
from the authoritative confirmed criteria.

## Alternatives considered

1. **Disable while unchanged** — selected because it preserves the visible
   confirmation boundary while preventing a false, destructive action.
2. **Hide after confirmation** — rejected because the user loses the stable
   location of the action that returns after an edit.
3. **Treat repeated confirmation as a no-op in the lifecycle** — rejected
   because the lifecycle should continue honoring every explicit revision; the
   defect is that the UI offers confirmation without a revision.

## Architecture and data flow

Use the already-derived `criteria_edits_pending` Boolean and the authoritative
`st.session_state["criteria_confirmed"]` flag in the existing button's
`disabled` expression. Do not change the click handler, lifecycle services,
revision model, bundle invalidation, gate evaluation, or persistence.

## Verification

- Add an AppTest that requires confirmation to be disabled after analysis with
  no edits and proves revision 1 plus its bundle remain unchanged.
- In the same test, edit one criterion and require confirmation to re-enable;
  existing pending-edit tests continue proving reconfirmation invalidates stale
  analysis correctly.
- Run focused tests, Ruff, the complete offline suite, deterministic benchmark,
  `git diff --check`, and loopback Streamlit health.

## Evidence limits and boundaries

The controlled probe and AppTests prove only local workbench state behavior.
They are not external PR evidence, third-party runtime verification, user
adoption evidence, or proof of correctness. No acceptance, evidence, gate,
schema, export, storage, release, paid API/LLM, billing, fork, organization,
private repository, synthetic validation, notification, or untrusted-code
behavior changes.
