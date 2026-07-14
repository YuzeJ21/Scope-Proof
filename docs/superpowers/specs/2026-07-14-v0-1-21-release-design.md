# ScopeProof v0.1.21 Release Design

## Context

The latest public release is v0.1.20 at
`bfed3ece3769b444e4b290e9bf9b9d370b3a9e0d`. Protected `main` is at
`5b0b9537cd09154cb92abe5d4736337b65bd92ec` and identifies itself as
`0.1.21.dev0`.

Since v0.1.20, protected PR #138 added one bounded operator command:
`scopeproof list`. It lists locally persisted review IDs in sorted order, returns an empty result
successfully, and skips corrupt or non-review entries without executing repository code. Exact
`main` passes Ruff, 710 tests with one intentional live-network skip, and protected CI and CodeQL.

The public README now documents `scopeproof list`, but its verified installation path still
installs v0.1.20. A fresh isolated installation of that public wheel reports `0.1.20` and rejects
`scopeproof list` as an invalid command. That is a reproducible release-contract mismatch, not an
external user report or runtime validation.

The same-day local workbench audit found no remaining runtime-evidence or final-acceptance defect:
required fields gate saving, missing-field guidance is explicit, fallback errors are stable, and
final acceptance remains a separate human action that cannot override a Blocked gate. Those
controlled observations do not justify product changes and are not customer evidence.

## Decision

Publish one focused v0.1.21 release through a protected release-preparation pull request. The
release makes the already merged, documented `scopeproof list` command available through the
verified public wheel and restores agreement between documentation and installed behavior.

The preparation changes only release identity, README wheel/checksum paths, the immutable
copyable Action source pin, repository contracts, and this release documentation. It does not
change evidence retrieval, schemas, gates, lifecycle behavior, record versions, workflow
permissions, dependencies, or product behavior.

Use two implementation commits after the design and plan commits to avoid a circular Action pin:

1. finalize `0.1.21`, README wheel/checksum paths, and repository contracts;
2. pin the copyable Action example to the full SHA of commit 1, whose tree contains the exact
   v0.1.21 package source.

After protected merge and exact-main CI/CodeQL success, build from the merge SHA, publish one tag
and release containing exactly the wheel and checksum, then redownload and independently verify
both public assets, including the installed `scopeproof list` command.

## Alternatives considered

### Publish v0.1.21 — selected

Makes the verified list command installable and restores the public installation contract with
one small, auditable release.

### Remove or hide the list documentation

Rejected because the command is merged, tested, safe, and useful. Hiding supported behavior would
make the documentation less complete without improving product safety.

### Continue calling the command source-only

Rejected because the README's primary path promises a verified public wheel and then documents
the command without a version caveat. Leaving the mismatch in place creates avoidable operator
confusion.

## Release contract

- `scopeproof_core/version.py` contains the only checked-in version value, exactly `0.1.21`.
- README installs `scopeproof-0.1.21-py3-none-any.whl` from v0.1.21 and verifies the matching
  checksum on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing
  the exact v0.1.21 package tree.
- Tag, release target, wheel metadata, module version, both CLIs, web launcher, and a new review's
  `tool_version` agree on `0.1.21`.
- A fresh installed wheel supports `scopeproof list` for empty, sorted, and corrupt-entry cases.
- The release contains exactly the wheel and checksum asset.
- Release notes describe controlled local verification without calling it external PR runtime
  evidence, customer validation, or proof of correctness.
- No issue comment, dogfood update, reviewer request, manually sent email, intermediate release,
  or fork test is created.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, invented evidence, license, untrusted-code execution,
generic review, security scanner, or auto-fix feature is introduced. The release-preparation PR
contains no product behavior change.
