# Platform-Safe Alpha Storage Design

## Status and scope

This design implements the owner-approved storage-integrity phase from verified `main` commit
`9426e8714ffd2c3742bb074ae26fc788f1049c63`. It is limited to local alpha-case storage,
owner-rehearsal storage, CLI report publication, and a hosted Windows compatibility lane. It does
not change evidence interpretation, execute target-repository code, advance Product Stage 1, or
begin browser-lifecycle expansion.

## Current problem

The rehearsal store dereferences `os.O_DIRECTORY` and `os.O_NOFOLLOW` at import time, so importing
the CLI is not portable to Windows. The alpha-case store uses check-then-replace writes without an
exclusive claim, allowing concurrent writers to overwrite one another. CLI report destinations
also check for existence before a later ordinary write, creating a no-overwrite time-of-check to
time-of-use race.

## Selected architecture

Add a small core filesystem utility that validates existing path components without following
symbolic-link or Windows reparse-point targets, writes a private same-directory temporary file,
flushes it, and publishes it with exclusive create semantics. An existing target always fails
closed. Temporary files are removed on success and ordinary failure.

Updates acquire an exclusive same-directory claim before rereading and validating the current
record. The claim spans validation and atomic replacement, so only one process can commit an
outcome from an unresolved case. A competing process fails without mutation. A stale claim left by
process termination is intentionally fail-closed rather than guessed safe; recovery requires an
owner-observed local cleanup, never silent takeover.

When all required capabilities are available, the shared primitives keep the opened POSIX
directory descriptor through create, claim, and replacement so an ancestor swap cannot redirect a
mutation. Capability detection uses `getattr`/`hasattr` and never dereferences missing constants
during import. Other platforms use the portable validated-path backend and revalidate the same
directory identity immediately before mutation. Both backends validate every loaded or saved
object with Pydantic.

The rehearsal and alpha-case stores use these shared primitives while retaining the rehearsal
store's descriptor-relative POSIX read/list implementation. CLI reports use the exclusive
publication primitive at the final write boundary, so a destination created after the initial
check is never overwritten.

## Path and mutation contract

- Existing ancestors and storage roots must be real directories, never symlinks or reparse points.
- Existing records must be regular files, never symlinks or reparse points.
- Create-only writes publish at most once; an existing target raises `FileExistsError`.
- Alpha updates preserve qualification fields, accept exactly one outcome, and serialize competing
  writers through a per-record exclusive claim.
- Interrupted or failed writes preserve the prior committed bytes and clean ordinary temporary
  artifacts.
- Malformed JSON, schema-invalid data, or an ID that disagrees with the requested filename fails
  closed.
- Platform capability absence selects the conservative portable backend or raises a user-safe
  storage error; it never weakens validation silently.

## Hosted Windows evidence

Add a Windows-hosted CI job that installs the package, imports CLI and both alpha stores, runs the
focused storage/CLI regressions, validates package dependencies and versions, and runs installed
deterministic benchmarks. The existing Linux lanes continue to cover the complete suite, coverage,
wheel, health, and packaged browser regression. Passing Windows CI is package/CLI/storage evidence,
not proof of every Windows desktop workflow or accessibility conformance.

## Test strategy

Regressions are written before implementation and cover missing POSIX constants at import,
create/create and update/update process races, interrupted writes, target and ancestor symlinks,
malformed/schema-invalid records, filename/payload ID disagreement, report destination races,
artifact cleanup, POSIX behavior preservation, and workflow structure. Final verification includes
Ruff, the complete suite at 95% or higher coverage, repository contracts, deterministic and
comparison benchmarks, two byte-identical wheels, clean installation, version equality, CLI and
web health, packaged Chromium, Python 3.11/3.13, hosted Windows, final audit, and independent review.

## Evidence and product boundaries

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Criteria confirmation remains mandatory and target-repository code is never executed.
- Persisted and exported objects remain Pydantic-validated.
- Gate behavior remains deterministic and fail closed; False Ready is more harmful than False
  Blocked.
- Reviewer identity remains asserted, not authenticated; the Action remains opt-in and
  informational.
- Product Stage 1 remains exactly 0/5, 0/3, 0/3, 0/3, and 0/2.
- Releases, tags, publishing, outreach, R-002/R-003 changes, and later product phases remain out of
  scope.
