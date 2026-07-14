# ScopeProof v0.1.18 Release Design

## Context

The latest public release is v0.1.17 at
`f62590bc2ad8c22cb2d9a57d3b245d85bbde9da1`. Protected `main` is now at
`457df03f8a44429339f41db38c5911fdbe239577` and identifies itself as
`0.1.18.dev0`.

Since v0.1.17, 29 protected pull requests have formed one coherent trust and
local-control batch. The changes validate persisted and exported objects at
lifecycle boundaries, bind evidence and resolution history to the correct
review and criteria revision, preserve ingestion limitations, make runtime
evidence prerequisites explicit, harden rendered references, require Action
review opt-in, enforce deterministic gate inputs, and add confirmed
single-record local review deletion with public guidance.

Exact `main` passes Ruff, 658 tests with one intentional live-network skip,
and the 12-case/13-criterion deterministic benchmark with zero mismatches,
must-have False Ready, false blockers, evidence-link errors, or unexecuted
categories. Protected-main CI and CodeQL pass, and GitHub reports no open
Dependabot or code-scanning alerts. Issue #3 still contains only owner-authored
responses, so this release cannot be described as external validation.

## Decision

Publish one consolidated v0.1.18 release after one protected release-preparation
pull request. The public v0.1.17 wheel lacks the current evidence-integrity,
lineage, deterministic-gate, rendering, and local-deletion behavior. The batch
is large and cohesive enough to justify one meaningful release rather than
more notification-producing incremental releases.

The preparation changes only release identity, README installation guidance,
the immutable copyable Action source pin, and regression contracts. It does not
change evidence retrieval, schemas, gates, lifecycle behavior, record versions,
workflow permissions, dependencies, or final acceptance.

Two implementation commits avoid a circular Action pin:

1. finalize `0.1.18`, README wheel paths, and repository contracts;
2. pin the copyable Action example to the full SHA of commit 1, which contains
   the exact v0.1.18 package tree.

After protected merge and exact-main CI/CodeQL success, build from the merge
SHA, publish one tag and release with exactly the wheel and checksum, redownload
both assets, and independently repeat checksum, identity, dependency, benchmark,
and packaged-workbench health verification.

## Alternatives considered

### Consolidated v0.1.18 release — selected

Makes the verified batch installable and refreshes the immutable Action source
in one necessary release.

### Continue accumulating unreleased changes

Rejected because v0.1.17 is already 29 protected merges and more than 300 tests
behind current `main`; further delay widens the supported-installation gap.

### Tag current main without preparation

Rejected because the package reports `0.1.18.dev0`, README installs v0.1.17,
and the copyable Action remains pinned to the v0.1.17 package tree.

## Release contract

- `scopeproof_core/version.py` contains the only checked-in version value,
  exactly `0.1.18`.
- README installs `scopeproof-0.1.18-py3-none-any.whl` from v0.1.18 and verifies
  the matching checksum on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit
  SHA containing the exact v0.1.18 package tree.
- Tag, release target, wheel metadata, module version, both CLIs, web launcher,
  and a new review's `tool_version` agree on `0.1.18`.
- The release contains exactly the wheel and checksum asset.
- Release notes distinguish controlled product verification from PR runtime
  evidence, customer validation, or proof of correctness.
- No issue comment, dogfood update, reviewer request, email, intermediate
  release, or fork test is created.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository,
fork test, synthetic user, synthetic validation, license, untrusted-code
execution, generic review, security scanner, or auto-fix feature is introduced.
No product behavior changes in the preparation PR.
