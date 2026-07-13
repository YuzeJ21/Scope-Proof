# Local Save Freshness Design

## Problem

ScopeProof tells a reviewer when a review is saved, but it does not retain that
status across Streamlit reruns. More importantly, after a saved review changes,
the workbench does not say that the persisted copy is now stale. A reviewer can
therefore leave the page believing that later resolutions or runtime evidence
were saved when only an earlier state exists on disk.

## Product boundary

This slice reports only whether the current in-memory `ReviewState` exactly
matches the state last saved or reopened in this browser session. It does not
claim that a file still exists, that another process has not changed it, or that
the review was synchronized anywhere outside local storage.

## Design

Store a deterministic fingerprint of the last locally persisted
`ReviewState` in Streamlit session state. Compute the fingerprint from the
Pydantic-validated model's canonical JSON representation.

When a review is first analyzed and has never been saved in the current
session:

- label it `Unsaved changes`;
- keep `Save local review` enabled.

After a successful save:

- retain a `Review saved locally` notice across the required rerun;
- record the current fingerprint;
- label the state `Saved locally — current review matches the last local save`;
- disable the save action while the state remains identical.

After any operation changes the `ReviewState`, including a resolution, runtime
evidence, final acceptance, or criteria revision:

- the current fingerprint no longer matches;
- label it `Unsaved changes`;
- re-enable the save action.

After reopening a validated local review:

- initialize the saved fingerprint from the reopened state;
- label it as matching the local save;
- keep the save action disabled until the review changes.

Starting a different source or resetting analysis clears the saved fingerprint
so a new review can never inherit a saved label from the old review.

## Rejected alternatives

### Keep the transient success message only

This does not reveal that later changes are unsaved.

### Read the disk file on every Streamlit rerun

Continuous file reads add failure modes and imply stronger external freshness
than the UI needs. The indicator is intentionally scoped to this session's last
successful save or validated reopen.

### Add persistence metadata to `ReviewState`

Save freshness is UI session state, not review evidence. Adding it to the core
schema would mix presentation concerns into the deterministic engine and alter
the durable record contract.

## Trust and evidence language

The UI must say `matches the last local save`, not `secure`, `synced`, or
`backed up`. The fingerprint is an equality check for session UX only; it is not
test, runtime, or external validation evidence.

## Verification

- AppTest: a newly analyzed review is unsaved and save is enabled.
- AppTest: save reruns, retains feedback, labels the current state saved, and
  disables duplicate save.
- AppTest: appending a human resolution makes the saved review unsaved again
  and re-enables save.
- AppTest: reopening a validated record starts in the saved state.
- Full tests, Ruff, deterministic benchmark, clean-installed wheel benchmark,
  HTTP health smoke, and live browser verification.
