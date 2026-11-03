# Workbench saved-review handoff

## Outcome and approach

A sender and recipient can complete saved-review handoff from the local workbench, without
terminal commands. The completed CLI transfer in PR #249 supplies the storage contract. This
slice adds an explicit saved-record download and upload inspection/import in Resume a saved
review. It does not add another record format or change review authority.

Alternatives considered: leave recipients on CLI (does not remove the identified workflow
barrier); automatically import/open an uploaded report (would bypass selection and replacement
boundaries); explicit preview and import followed by existing reopening (selected implementation
judgment under the owner's instruction to proceed without routine design questions).

## Core and UI contract

Reuse the existing strict transfer decoder, recorded-facts guard, 64 MiB cap, original IDs,
legacy migrations and atomic no-overwrite creation. Expose byte-based inspection/import and a
locked saved-record snapshot service so the UI never uses temporary untrusted paths. Preview
is Pydantic validated and shows repository/PR/head, original version/time and producer identity,
input origin, criteria revision/confirmation, active-analysis/history counts and content hash.
Preview and transfer authenticate no actors and supply no renewed evidence.

For download, explicitly prepare the selected saved record, bind the download to its exact bytes,
and revalidate the record under its existing lock at click time. Revoke old callbacks when the
selection changes or pending review inputs appear. Clearly label complete saved records separately
from analysis reports. No unsaved edits are included.

For import, choose one JSON file, explicitly inspect it, then explicitly confirm/import that
exact byte snapshot. Replacing/clearing the upload clears preview and consent. Recheck bytes and
validation before atomic creation; collisions fail without overwrite or renaming. Import never
hydrates or replaces the open review. Refresh the saved inventory and use the existing explicit
Reopen local review action with its unsaved-work guard.

The upload widget and local transport use 68 MB/MiB headroom to admit a full 64 MiB record;
the core enforces 64 MiB before decoding. The JUnit widget retains its 2 MB allowance and 1 MiB
parser limit. UI errors are fixed recovery text. Record content renders as inert text.

## Verification and boundaries

Core tests cover preview fidelity, strict byte/hash binding, legacy facts and collision safety.
App tests cover explicit controls, stale downloads, upload replacement, malformed/oversized data,
collisions, failure recovery and preserving open drafts. A real installed-wheel browser journey
downloads a record, imports it into a fresh store, inspects history after explicit reopen and
checks original bytes and pending confirmation. Test actual transport at the 64 MiB boundary.
Run full 95% suite, lint, benchmarks, compatibility checks and independent automated review.
Frozen R-002 remains unchanged. No source execution, qualifying human evidence, publication,
deployment, accounts or new adapters. Stage 3 stays dormant.
