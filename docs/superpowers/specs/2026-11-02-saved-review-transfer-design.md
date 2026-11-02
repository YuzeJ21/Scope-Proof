# Saved-review transfer

## Intent and constraints

A recipient can explicitly transfer a saved review into a separate local store and reopen it
with the existing workbench. Preserve the complete original record bytes, version, timestamp,
criteria confirmation, decisions, analysis history, and producer/source provenance. Import
never confirms criteria, recomputes evidence, infers acceptance, executes target code, or claims
an asserted actor is authenticated. The existing loader may conservatively migrate old gates
in memory when reopening. Original bytes remain available until an ordinary subsequent save.

## Approach

Use the existing versioned saved-record envelope as the portable file. Add explicit
`export-review REVIEW_ID --storage-dir DIR --output FILE` and
`import-review --input FILE --storage-dir DIR` controls. Existing report exports remain reports.
The implementation choice is CLI transfer followed by existing workbench reopening, which
avoids a second storage or migration contract. A new archive format would duplicate validation;
raw report import lacks the version context needed for safe historical migration.

Both boundaries validate through Pydantic and the deterministic gate using one shared decoder.
Bound regular-file reads at the existing 64 MiB maximum, preserve exact UTF-8 bytes, reject
unsupported versions, ambiguous duplicate JSON keys, unsafe IDs and paths, source-owner mismatch,
and any destination collision. Use existing record locks and atomic no-overwrite creation.
Never rename IDs, merge histories, overwrite records or automatically load downloaded content.
A typed JSON receipt records the content hash, bytes, original version and saved timestamp,
review/head identity, loaded state fingerprint and history count. It is a transfer receipt,
not authentication or renewed verification. Source records and frozen R-002 inputs stay unchanged.

## Verification and boundaries

Test current and legacy records, pending confirmation, retained histories, provenance, malformed
and oversized input, future versions, duplicates, paths, collisions and concurrent imports.
Exercise installed CLI on Windows and supported Python versions and reopen an imported record in
an installed Chromium workbench. Full suite retains the unrounded 95% floor. Independent agent
review and exact-head CI precede the authorized merge. Stage 2 continues; Stage 3 stays dormant.
No release, deployment, outreach, personal testing or qualifying reviews.
