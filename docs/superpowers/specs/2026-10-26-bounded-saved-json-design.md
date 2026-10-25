# Bounded saved JSON reads

**Stage:** Owner-led Stage 2 productization. **Status:** Owner-directed implementation.

## Intent and boundary

Loading an app-owned review, genuine alpha case, or owner rehearsal currently reads the complete JSON file before Pydantic validation. A corrupted or replaced local file can therefore consume unbounded memory. Limit each persisted JSON record to 64 MiB of UTF-8 bytes on every supported storage backend. Reject an oversized file before parsing, and reject an oversized validated record before publishing or replacing its contents. The limit applies to the outer saved record, including its version envelope. An oversized record is a clear local-storage error; it does not silently become an empty review or a changed gate verdict.

Keep existing symlink, regular-file, path-identity, locking, atomic-write, migration, and Pydantic validation behavior. The read path may inspect file metadata for an early rejection, but must still read at most 64 MiB plus one byte from the opened file so a concurrent growth or incorrect size report cannot bypass the cap. Decode only UTF-8. Write the exact measured UTF-8 bytes so Windows newline translation cannot make an accepted record unreadable. A file at exactly the limit is allowed. No target-repository code is run, and no evidence or gate semantics change.

## Approaches

- **Chosen:** Put one bounded UTF-8 reader in `atomic_files.py`, use it for descriptor and portable reads, and apply the same constant at all three saved-record writers. This keeps the byte rule consistent while preserving each store's existing identity and transaction flow.
- Put independent caps in each store. This would duplicate the cross-platform checks and risks different behavior after one path changes.
- Cap only at Pydantic validation. That occurs after an unbounded read and therefore does not close the resource gap.

## Verification

Automated tests cover exact-limit and over-limit reads on descriptor and portable paths, review, alpha-case, and rehearsal loads, and rejection before saves or updates replace or create a file. Run focused storage tests, lint, the deterministic benchmark, and the full protected-suite equivalent. This is engineering evidence only, not customer or runtime validation.
