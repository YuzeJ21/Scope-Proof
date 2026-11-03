# Safe saved-review transfer — 2026-11-02

The selected Stage 2 outcome lets a recipient transfer and reopen a complete saved review.
`export-review` and `import-review` use the existing versioned envelope. They retain original
bytes, saved time/version, identity, criteria confirmation, decisions, historical analyses,
selected references and test-import audit data. A typed receipt describes the copied content.
The existing workbench reopens imported records; no new UI state or acceptance rule is added.

The core validates through the shared Pydantic/migration/deterministic-gate boundary before
writing. Reads are bounded at 64 MiB and require safe regular-file paths. Duplicate keys,
unknown versions, missing recorded identities/audit timestamps, unsafe review IDs and export filename/owner mismatch fail closed. Atomic
creation plus existing per-record mutation locks prevents overwrite, including concurrent
imports and corrupt destination collisions. No implicit merge or ID renaming occurs.

Legacy files keep their original bytes. The established loader may derive a more conservative
gate in memory; a normal later save still uses the current writer. Original producer identities
and recorded actors are retained claims, not authenticated identities. Content hashes establish
byte identity only. Neither imported acceptance nor historical observations become renewed
runtime verification. No source is executed and no network request is needed for transfer.

Constructed coverage includes current and historical-only reviews with pending criteria,
original producer and actor fields, native v4 migration, imported JUnit data, malformed/future/
duplicate/oversized input, path and owner rejection, collisions, concurrency and write failures.
The installed CLI journey verifies bytes and history on supported platforms; an installed
Chromium journey imports into a fresh workbench home, reopens history, compares saved criteria
and checks current acceptance controls stay unavailable. Automation is not qualifying use.

The implementation/review/command evidence is retained outside the source tree in
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-02-saved-review-transfer`.
Final counts and exact-head CI/merge identities belong to that version-bound packet and PR.
Frozen R-002 input/results are untouched. Public release remains v0.2.4; this is unreleased
0.2.5 source. Stage 2 continues and Stage 3 remains dormant pending genuine independent-use
evidence and separate authorization. No personal testing, qualifying review, publication,
deployment or outreach is required or performed.

Independent automated review reproduced missing constructor-default provenance: incomplete
records could acquire fresh UUIDs or timestamps on each load. Transfer now requires those
facts to have been explicitly recorded, before migration serialization can hide their absence.
Omission regressions reproduce the defect and verify rejection without creating a destination.
Existing deterministic legacy migrations and unknown producer-version handling remain intact.
The review also clarified README placement so transfer receipts cannot be confused with review
command verdict output. These are engineering findings and fixes, not qualifying human review.
