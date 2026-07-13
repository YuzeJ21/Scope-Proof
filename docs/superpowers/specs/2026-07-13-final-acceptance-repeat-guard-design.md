# ScopeProof Final-Acceptance Repeat Guard Design

## Problem

Final acceptance is intentionally recordable even when criteria remain unresolved or the gate is
Blocked. That review-level event never resolves a criterion or overrides blocker precedence.

After a reviewer records final acceptance once, however, the Streamlit action remains enabled for
the unchanged criteria revision. A deterministic AppTest probe records one event with
`review.final_acceptance == True` while the button remains enabled; a second click appends an
identical event. Resolution history then shows a superseded/current pair even though the reviewer
did not change the acceptance state.

The root cause is presentation state. The core correctly treats the latest final-acceptance event in
the active revision as authoritative and preserves append-only history.

## Chosen Design

Keep `Record final acceptance` enabled before an acceptance event regardless of gate verdict. After
a successful append, store a one-run success notice and rerun Streamlit. On the next run, disable the
button when `review_state.review.final_acceptance` is true and show the retained success notice.

This prevents an accidental identical repeat while preserving the accepted lifecycle contract:

- a Blocked or unresolved review may still record final acceptance once;
- final acceptance still cannot override the gate;
- revising or reconfirming criteria resets `review.final_acceptance` to false and re-enables the
  action for the new review state;
- the core remains append-only and can still represent explicit future event types.

## Alternatives Considered

1. **Disable only after current-revision acceptance — chosen.** This fixes the observed repeat risk
   without adding prerequisites or changing gate semantics.
2. **Suppress duplicate events in `append_resolution`.** Rejected because core deduplication would
   silently change append-only domain behavior for every caller.
3. **Keep the action enabled and add confirmation.** Rejected because it adds friction to the first
   intentional acceptance while still permitting identical history noise.

## Components and Data Flow

- `apps/web/app.py` derives `final_acceptance_recorded` from the active `ReviewState`, controls the
  button disabled state, persists the one-run notice, and reruns after success.
- `ResolutionEvent(final_acceptance=True)` and `append_resolution` remain unchanged.
- `_final_acceptance`, event-status classification, gate evaluation, exports, and storage remain
  unchanged.

## Error and Safety Behavior

- The button is enabled before the first event even when the gate is Blocked.
- It becomes disabled only after a successful active-revision acceptance append.
- The success notice survives the rerun and the history shows one current acceptance event.
- Criteria revision continues to invalidate acceptance through the existing lifecycle service.
- No decision, evidence, runtime result, or gate outcome is inferred.
- Deliberately constructed demo and AppTest fixtures prove UI behavior only, not external adoption or
  acceptance evidence.

## Verification

- Add a RED AppTest proving the current button remains enabled after the first append.
- Require one event, a disabled action, retained success copy, unchanged Blocked gate reasons, and a
  single current history event after GREEN.
- Extend the criteria-revision regression to prove the action becomes enabled again after acceptance
  is invalidated by a revision.
- Preserve the lifecycle test that a fully resolved review becomes Ready only after final acceptance.
- Run focused tests, Ruff, the complete offline suite, deterministic benchmark, diff checks, clean-
  installed wheel benchmark/health smoke, and live-browser verification.

## Relationship to the Earlier Boundary Decision

The earlier final-acceptance design rejected disabling the action *until every criterion is
resolved*. This design does not add that prerequisite. It disables only an already-completed action
for the active criteria revision, so the original independent-event and blocker-precedence contract
remains intact.

## Out of Scope

- Requiring resolved criteria before the first final-acceptance event.
- Adding acceptance revocation, confirmation dialogs, or new event types.
- Core, gate, schema, export, or persistence changes.
- Release publication, paid services, APIs, fork testing, or external-validation claims.
