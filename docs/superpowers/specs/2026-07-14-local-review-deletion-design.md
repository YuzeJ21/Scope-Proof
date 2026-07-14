# Local Review Deletion Design

## Problem

ScopeProof is local-first and persists review records only when a user saves
them, but the product can only list, reopen, overwrite, and export those records.
The privacy guidance tells users to delete JSON files or the whole directory by
hand. There is no validated product action for removing one saved record.

This leaves a practical local-data control gap: a user who can create a review
inside ScopeProof should be able to delete that exact app-owned record without
manually navigating hidden filesystem paths.

## Outcome

Add one validated deletion boundary to `JsonReviewStore`, expose it through the
CLI and Streamlit workbench, and document the behavior.

Deletion removes only the selected saved JSON record. It never deletes the
review directory, exported reports, source repositories, GitHub data, or an
open in-memory review.

## Approaches considered

### Keep filesystem-only guidance

This avoids code, but leaves the product without a usable deletion control and
continues to place hidden-path knowledge on the user.

### Add a Streamlit-only unlink

This improves the workbench but duplicates path and safety logic in the UI and
leaves CLI users with no supported operation.

### Add one store operation reused by CLI and Streamlit — selected

This keeps filesystem ownership in the existing storage layer, gives both
surfaces the same behavior, and makes path safety independently testable.

## Storage contract

Add `JsonReviewStore.delete(review_id: str) -> None`.

The operation:

1. validates the ID with the existing simple-record identifier rule;
2. validates that the store root is a regular directory and not a symlink;
3. resolves only an existing regular, non-symlink `<review_id>.json` entry via
   the existing safe lookup;
4. unlinks that exact directory entry;
5. raises `FileNotFoundError` when no safe exact record exists.

It does not parse or repair the record before deletion. A corrupt but safely
named regular record can still be deleted. Symlink records, traversal IDs,
directories, and files outside the configured root are never deletion targets.

The operation returns no deleted content and does not claim secure erasure from
storage media or backups.

## CLI flow

Add:

```text
scopeproof delete REVIEW_ID [--storage-dir PATH]
```

On success, print deterministic JSON containing the deleted review ID and the
configured storage directory. Existing top-level error handling converts a
missing or invalid record into a nonzero, user-readable CLI error.

The CLI does not add a force flag, wildcard, bulk delete, directory delete, or
interactive prompt. Supplying the exact review ID is the explicit operator
action.

## Streamlit flow

Extend the existing `Reopen saved review` expander so deletion uses the same
selected saved review ID:

- show a checkbox labeled `Permanently delete the selected local review` only
  after a saved review is selected;
- show `Delete saved review` disabled until the checkbox is selected;
- call `JsonReviewStore.delete(...)` only from the enabled action;
- after success, clear the deleted selection and confirmation on the next
  rerun, refresh the saved-ID list, and show a success notice;
- render fixed recovery copy for a missing/raced record or unavailable store,
  never a raw exception;
- do not require unsaved-review replacement approval because deletion does not
  replace or discard the active in-memory state.

If the deleted record is also open in the current session, keep the complete
`ReviewState` in memory, clear its saved fingerprint, and explain that the open
review remains available as unsaved work. The user may save it again later.

If another record is open, deleting the selected saved record leaves that
active review untouched.

## Session state

Use explicit session-only state for:

- deletion confirmation;
- a post-action reset pending flag, applied before constructing the selectbox;
- a one-rerun success or recovery notice.

This follows the workbench's existing reset-after-rerun pattern and avoids
mutating a widget key after the widget has been instantiated.

## Privacy documentation

Update `docs/privacy-readiness.md` to state that one saved review can be deleted
through the CLI or workbench. Keep these limits explicit:

- ScopeProof has no hosted copy;
- exported files remain user-owned and are not removed;
- deletion removes the app-owned local record, not storage backups or secure
  media remnants;
- deleting an open saved record keeps the in-memory review until the session
  ends or the user replaces it.

## Verification

Storage regressions prove:

- exact regular records are deleted;
- traversal IDs, symlink roots, symlink records, directories, and missing
  records are not deleted;
- no neighboring record is changed.

CLI regressions prove exact success JSON, removal, custom storage support, and
safe failure for missing/invalid IDs.

Streamlit AppTest proves confirmation is required, the selected record is
removed, other records remain discoverable, reset/notice behavior is stable,
and deleting the current saved record preserves it in memory as unsaved work.

Complete verification includes Ruff, all offline tests, deterministic benchmark,
`git diff --check`, a clean wheel install, installed CLI deletion in a temporary
store, and a fresh-HOME workbench health/interaction smoke. No real user review
or external evidence is deleted during testing.

## Non-goals

- Bulk deletion or deleting the entire review directory.
- Secure erasure guarantees, backup deletion, or exported-report deletion.
- Hosted retention controls, private repositories, accounts, or billing.
- Changing review schemas, evidence, findings, gates, final acceptance,
  lifecycle history, or record versions.
- Executing repository code, adding generic cleanup, or auto-deleting records.
- Creating a release, issue comment, fork test, paid API call, or synthetic
  external validation.
