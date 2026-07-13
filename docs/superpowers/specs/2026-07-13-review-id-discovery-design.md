# ScopeProof Review-ID Discovery Design

## Problem

The workbench now supports reopening a validated local review from a fresh session, but a rendered
save/reopen audit found that the active review UUID is never shown. `Save local review` displays
only a generic success message, while `Reopen saved review` requires the exact UUID. The audit had
to inspect the temporary storage filename to continue, which a normal first-use workflow should
not require.

## Chosen Design

In `Summary & Export`, show `Current review ID` whenever an analyzed `ReviewState` exists. Render the
exact validated UUID with `st.code(..., language=None)` so Streamlit supplies a standard copy
affordance without adding clipboard JavaScript. Add a caption stating that the operator should save
the review before using the ID in a future session.

After a successful save, include the same UUID in the confirmation: `Review <id> saved locally.`
The ID remains visible after reruns because it comes from the validated active ReviewState rather
than transient UI state.

## Alternatives Considered

1. Add a saved-review browser. This requires directory listing, selection, deletion policy, and
   more privacy/error states than the proven gap warrants.
2. Show only the storage filename or directory. This forces filesystem navigation and exposes an
   implementation detail instead of the identifier the reopen form accepts.
3. Put the UUID only in the success toast. The message is transient and harder to recover after any
   rerun, so it is not a durable copy path.

## Safety and Data Flow

- The displayed value comes only from `review_state.review.review_id`, which is already validated
  by Pydantic and used by `JsonReviewStore` as the record identifier.
- No path, token, PR content, evidence, or new persisted field is exposed.
- Saving, reopening, evidence, findings, lifecycle history, final acceptance, gates, and exports do
  not change.
- No custom clipboard script, telemetry, API, or paid service is added.

## Verification

- Add AppTest coverage proving the exact active review ID is visible in a code block before save.
- Prove the save confirmation includes the same ID.
- Prove a fresh-session reopened review displays the same ID.
- Preserve save/reopen, temporary-storage, and export regression coverage.
- Run focused AppTests, Ruff, the full offline suite, the 12-case benchmark, `git diff --check`, and
  a real local Streamlit save/fresh-reopen inspection with temporary storage.

## Out of Scope

- Listing, searching, deleting, renaming, or syncing saved reviews.
- Changing the UUID format, storage filename, or record schema.
- Adding browser clipboard APIs or custom frontend components.
