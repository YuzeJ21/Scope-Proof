# Unsaved Review Replacement Guard Design

## Problem

ScopeProof now identifies when the current validated review differs from its
last local save. However, `Reopen local review`, `Load deliberately constructed
demo`, `Fetch public PR`, `Prepare criteria`, and criterion-set reset actions can
still replace that unsaved state immediately. A reviewer can lose recorded
decisions or runtime evidence with one navigation or reset action.

## Product boundary

The guard protects only replacement operations inside the current Streamlit
session. It does not implement autosave, browser-close protection, cloud sync,
or recovery of changes that were already discarded.

## Design

Derive `has_unsaved_review` from the same validated `ReviewState` fingerprint
used by the local-save freshness indicator.

When the current review is unsaved:

- show a warning above the reopen/start controls stating that replacing the
  current review will discard unsaved changes;
- show an unchecked `Allow replacing the unsaved current review` checkbox;
- disable `Reopen local review`, `Load deliberately constructed demo`,
  `Fetch public PR`, `Prepare criteria`, and criterion add, split, remove, or
  reorder actions until the reviewer explicitly checks it;
- retain ordinary in-review actions such as criterion confirmation,
  resolutions, runtime evidence, final acceptance, exports, and local save.

When no analyzed review exists, or the current review matches its last local
save, replacement controls behave exactly as before and the checkbox is absent.

After a permitted replacement action, reset the approval so it cannot silently
authorize a later replacement.

## Why one shared approval

These actions have the same consequence: they reset the current in-memory
review instead of creating a lifecycle revision. One visible approval keeps the
decision explicit without placing separate confirmation controls across the
page.

## Rejected alternatives

### Automatically save before replacement

Autosave would change the user's persistence decision and could overwrite a
local record they intentionally left unchanged.

### Disable replacement until save, with no discard path

This would force persistence even when the reviewer intentionally wants to
discard a draft.

### Modal confirmation

The project supports a broad Streamlit version range. An inline deterministic
approval is simpler to test, remains visible, and follows existing form-gating
patterns.

## Trust language

The warning says `discard unsaved changes`; it does not claim recovery,
backup, synchronization, or file integrity. The approval is UI session state
and never enters review evidence, exports, or deterministic gate decisions.

## Verification

- AppTest: a new unsaved review disables every replacement action and shows the
  warning and checkbox.
- AppTest: approving replacement enables the actions.
- AppTest: loading the demo after approval replaces the prior review and resets
  approval.
- AppTest: a locally saved or reopened review does not require approval.
- Full tests, Ruff, deterministic benchmark, clean-installed wheel benchmark,
  packaged HTTP health, and live browser verification.
