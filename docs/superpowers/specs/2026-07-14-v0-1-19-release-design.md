# ScopeProof v0.1.19 Release Design

## Context

The latest public release is v0.1.18 at
`c52e87340d33bab49c776635e2dd3a328b9074b2`. Protected `main` is now at
`424e4bca975c130e5e7584ed479cf4556b5c3568` and identifies itself as
`0.1.19.dev0`.

Since v0.1.18, 12 protected pull requests have formed one coherent first-use and recovery batch.
The changes add a confirmed-analysis cue, loaded-source identity, persistent step navigation,
safe local-save and storage-unavailable guidance, and atomic recovery boundaries for runtime
evidence, final acceptance, criterion resolution, analysis, criteria confirmation, and all four
criteria edit operations.

Exact `main` passes Ruff, 675 tests with one intentional live-network skip, and the
12-case/13-criterion deterministic benchmark with zero mismatches, must-have False Ready, false
blockers, evidence-link errors, or unexecuted categories. Protected-main CI and CodeQL pass.
GitHub reports no open Dependabot alerts and no open code-scanning alerts. Issue #3 still contains
only owner-authored responses, so this release cannot be described as external validation.

## Decision

Publish one consolidated v0.1.19 release after one protected release-preparation pull request. The
public v0.1.18 wheel lacks the current first-use navigation and expected-error recovery behavior.
The 12-PR batch is cohesive and materially improves the installed workbench, so one release is
justified without creating incremental release churn.

The preparation changes only release identity, README installation guidance, the immutable
copyable Action source pin, and regression contracts. It does not change evidence retrieval,
schemas, gates, lifecycle behavior, record versions, workflow permissions, dependencies, or final
acceptance.

Two implementation commits avoid a circular Action pin:

1. finalize `0.1.19`, README wheel paths, and repository contracts;
2. pin the copyable Action example to the full SHA of commit 1, which contains the exact v0.1.19
   package tree.

After protected merge and exact-main CI/CodeQL success, build from the merge SHA, publish one tag
and release with exactly the wheel and checksum, redownload both assets, and independently repeat
checksum, identity, dependency, benchmark, and packaged-workbench health verification.

## Alternatives considered

### Consolidated v0.1.19 release — selected

Makes the verified first-use and recovery batch installable and refreshes the immutable Action
source in one necessary release.

### Continue accumulating unreleased changes

Rejected because v0.1.18 is already 12 protected product/reliability PRs behind current `main`;
further delay widens the supported-installation gap.

### Tag current main without preparation

Rejected because the package reports `0.1.19.dev0`, README installs v0.1.18, and the copyable
Action remains pinned to the v0.1.18 package tree.

## Release contract

- `scopeproof_core/version.py` contains the only checked-in version value, exactly `0.1.19`.
- README installs `scopeproof-0.1.19-py3-none-any.whl` from v0.1.19 and verifies the matching
  checksum on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing
  the exact v0.1.19 package tree.
- Tag, release target, wheel metadata, module version, both CLIs, web launcher, and a new review's
  `tool_version` agree on `0.1.19`.
- The release contains exactly the wheel and checksum asset.
- Release notes distinguish controlled product verification from PR runtime evidence, customer
  validation, or proof of correctness.
- No issue comment, dogfood update, reviewer request, email, intermediate release, or fork test is
  created.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, license, untrusted-code execution, generic review, security
scanner, or auto-fix feature is introduced. No product behavior changes in the preparation PR.
