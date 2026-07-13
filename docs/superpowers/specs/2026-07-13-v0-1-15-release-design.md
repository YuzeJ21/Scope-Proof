# ScopeProof v0.1.15 Release Design

## Context

The latest public release is v0.1.14 at
`db03a8869326e0ebf080ca8bc6c0443caac36510`. Protected `main` is now at
`88d241990342f5d616f4a208c081f91579e6babb` and identifies itself as
`0.1.15.dev0`. Since v0.1.14, 24 protected merge commits have added durable review reopening,
head-change detection, version provenance, complete export identity and evidence matrices,
deterministic recovery guidance, resolution history, safer final acceptance, unsaved-review
protection, public-PR URL prevalidation, and clearer runtime-evidence and criterion-resolution
boundaries.

The source suite currently passes 235 tests with one intentional live-network skip. The latest
protected-main CI and CodeQL runs succeeded, and GitHub reports no open Dependabot, code-scanning,
or secret-scanning alerts. Issue #3 contains no external participant response, so none of these
local product checks may be described as external validation.

## Decision

Publish one consolidated v0.1.15 release after a single protected release-preparation pull request.
The preparation changes only release identity, public installation guidance, the copyable Action
source pin, and regression contracts for those surfaces. It does not change evidence retrieval,
gate semantics, persistence schemas, or user decision behavior.

The pull request uses two implementation commits after the design and plan:

1. Change the single version source from `0.1.15.dev0` to `0.1.15`, update README wheel and
   checksum commands, and update their repository contract tests.
2. Pin the copyable Action example to the full SHA of the first implementation commit. That SHA
   contains the exact v0.1.15 package tree; the second commit only updates the adoption example and
   its pin contract. This avoids a circular self-pin while keeping all release preparation in one
   protected pull request.

After the pull request merges and merged-main CI and CodeQL succeed, build the wheel from the exact
merge commit, generate its checksum, verify it in a clean environment, publish tag and release
`v0.1.15` targeting that merge commit, download the public assets again, and repeat checksum,
version, benchmark, and packaged-workbench health checks.

## Alternatives Considered

### 1. Recommended: one batched release-preparation PR and one release

This makes the accumulated user-facing improvements installable, keeps README and Action adoption
paths current, preserves protected-main review, and minimizes GitHub notification activity.

### 2. Tag current main without a preparation PR

Rejected because the package would still report `0.1.15.dev0`, README would install v0.1.14, and
the copyable Action example would remain pinned to an early public-alpha revision.

### 3. Continue accumulating unreleased changes

Rejected because the v0.1.14 wheel omits the current first-use and auditability improvements. More
unreleased UI work would increase the gap without producing stronger external evidence.

## Release Contract

- `scopeproof_core/version.py` is the only checked-in version value and contains `0.1.15`.
- README installs `scopeproof-0.1.15-py3-none-any.whl` from the v0.1.15 release and verifies the
  matching `.sha256` asset on macOS or Linux.
- The copyable Action example installs ScopeProof from one immutable 40-character commit SHA that
  contains the v0.1.15 package tree.
- The tag, GitHub release target, wheel metadata, module version, console versions, and a newly
  constructed review's `tool_version` all agree on v0.1.15.
- The release contains exactly the wheel and its checksum asset.
- Release notes identify the bundled demo and local verification as controlled product evidence,
  not runtime evidence for a pull request or external customer validation.
- No issue comment, dogfood update, reviewer request, or additional release is created.

## Verification

Before protected publication:

- Observe the version and documentation contract tests fail after expecting v0.1.15 but before the
  source and README changes.
- Observe the Action pin contract fail after expecting the new immutable source revision but before
  the example changes.
- Run focused repository and Action workflow tests, Ruff, all offline tests, the 12-case benchmark,
  and `git diff --check`.
- Build and clean-install the candidate wheel; verify distribution, module, console, and review
  versions; run the installed benchmark; start the installed workbench on an explicit loopback port;
  require exact `ok` from `/_stcore/health`; and stop without traceback.

After release publication:

- Resolve the tag and release target to the protected-main merge SHA.
- Download both public assets into a fresh directory and verify the checksum file.
- Install the downloaded wheel into a new environment and repeat version, benchmark, and health
  checks without using the source checkout on `PYTHONPATH`.

## Boundaries

No paid API, LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, license, untrusted-code execution, generic review feature,
security scanner, or auto-fix feature is introduced. Existing criteria confirmation, evidence
levels, gate precedence, runtime-evidence, resolution, and final-acceptance semantics are unchanged.
