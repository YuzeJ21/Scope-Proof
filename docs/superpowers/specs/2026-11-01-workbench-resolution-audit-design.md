# Workbench resolution audit consistency

The owner requests automatic implementation, tests, independent agent review and guarded merge;
personal testing and qualifying reviews are not gates. Main starts at `cdd2438` (PR #242).

## Intent and constraints

The workbench must show the same applicable outcome and retained context as readable exports for
schema-valid mixed legacy resolution events. A review target uses its recorded final-acceptance
boolean, even when it also carries a decision. A criterion target uses its decision, even when it
also carries a final flag. Additional recorded fields stay visible as not applied to that target.
Review-level manual extras must not trigger the criterion-only legacy re-record warning.

Preserve event append order and deterministic current/superseded/prior-revision classification.
Show event ID, revision, asserted reviewer, note, URL, evidence claim and runtime link, including
explicit missing/empty values. Preserve offsets and label naive timestamps as timezone not recorded.
All event values are inert text/code. Recorded actors and times are assertions, not authentication
or runtime verification. No historical head or provenance is invented.

No schema, storage v7, lifecycle/gate, JSON/CSV, dependency or frozen R-002 change. Core stays
independent of Streamlit/GitHub. No release/deployment/outreach, Stage 3 or validation claim.

## Approaches and decision

Duplicating the corrected exporter logic in the UI is smaller today but invites another drift.
Importing a private exporter helper creates an unstable dependency. The selected implementation
extracts the existing plain label/value projection and boundary/empty text to
`scopeproof_core/reviews/resolution_history.py`, consumed by exports and the workbench. This is an
implementation choice made under the owner's explicit delegation, not a new owner design approval.
The existing combined UI status/revision and criterion-only warning appearance remain available.

## Verification

Reproduce wrong final-false display before product edits. Cover mixed targets, manual extras,
offset/naive dates, absent/empty values, append ordering and hostile strings with isolated AppTest.
Preserve exact machine exports and readable report output across the extraction. Verify actual
reopen/download behavior from an installed wheel in Chromium, using temporary records only.
Run full coverage >=95%, lint, deterministic benchmarks, clean-install/CLI and hosted Python/Windows
lanes. One fresh independent whole-branch reviewer examines substantive changes before guarded
exact-head merge, then verify resulting main. Automation is constructed engineering evidence only.
