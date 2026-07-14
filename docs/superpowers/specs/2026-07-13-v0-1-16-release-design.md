# ScopeProof v0.1.16 Release Design

## Context

The latest public release is v0.1.15 at
`257c01b025609a919b727f5061e8bd6824b95807`. Protected `main` is now at
`577a7b9e4a978b7a9acca3a5835a410b4c27d75d` and identifies itself as
`0.1.16.dev0`. Since v0.1.15, six protected pull requests have improved the local review workflow:

- PR #59 explains required and observed evidence levels at their points of use.
- PR #60 renders gate reasons as product language while preserving deterministic reason codes.
- PR #61 removes duplicate criteria-confirmation feedback.
- PR #62 reduces the evidence matrix to its scan-oriented fields and moves deep context into the
  selected criterion detail.
- PR #63 makes review reopening a collapsed secondary path and strengthens the first-use hierarchy.
- PR #64 distinguishes unconfirmed visible criterion edits from the last confirmed analysis,
  prevents rerunning analysis across that mismatch, and requires confirmation before a fresh run.

The source suite passes 243 tests with one intentional live-network skip. Protected-main CI and
CodeQL succeeded at the current main SHA. GitHub reports no open Dependabot, code-scanning, or
secret-scanning alerts. Issue #3 still contains only owner-authored responses, so this release must
not be described as external validation.

## Decision

Publish one consolidated v0.1.16 release after a single protected release-preparation pull
request. The accumulated changes materially affect the installed Streamlit workbench's first-use
clarity and its criteria-confirmation trust boundary, so leaving them only on the development line
would keep the verified public wheel behind current product behavior.

The preparation changes only release identity, public installation guidance, the immutable
copyable Action source pin, and regression contracts for those surfaces. It does not change
evidence retrieval, schemas, gates, persistence, runtime-evidence, resolution, or final-acceptance
behavior.

The pull request uses two implementation commits after this design and its plan:

1. Change the single version source from `0.1.16.dev0` to `0.1.16`, update README wheel and
   checksum commands, and update their repository contracts.
2. Pin the copyable Action example to the full SHA of the first implementation commit. That SHA
   contains the exact v0.1.16 package tree; the second commit changes only the adoption example
   and its pin contract, avoiding a circular self-pin.

After protected merge and successful merged-main CI and CodeQL, build the wheel from the exact
merge commit, generate and verify its checksum, publish tag and release `v0.1.16`, download both
public assets into a fresh directory, and repeat checksum, identity, benchmark, dependency, and
packaged-workbench health verification outside the checkout.

## Alternatives Considered

### 1. Recommended: one batched preparation PR and one v0.1.16 release

This makes six coherent first-use and trust improvements installable, preserves protected-main
review, keeps README and the copyable Action current, and minimizes notification-generating
activity to one necessary PR and one meaningful release.

### 2. Tag current main without a preparation PR

Rejected because the package would report `0.1.16.dev0`, README would still install v0.1.15, and
the copyable Action would continue installing the v0.1.15 release tree.

### 3. Continue accumulating unreleased changes

Rejected because the public wheel currently lacks the pending-criteria safety boundary and the
coherent first-use hierarchy changes. Waiting would increase the gap between protected main and
the supported installation path without producing external evidence.

## Release Contract

- `scopeproof_core/version.py` remains the only checked-in version value and contains `0.1.16`.
- README installs `scopeproof-0.1.16-py3-none-any.whl` from the v0.1.16 release and verifies the
  matching `.sha256` asset on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing
  the exact v0.1.16 package tree.
- The tag, GitHub release target, wheel metadata, module version, console versions, and a new
  review's `tool_version` all agree on `0.1.16`.
- The release contains exactly the wheel and its checksum asset.
- Release notes identify the local demo, automated tests, benchmark, and health smoke as
  controlled product verification, not runtime evidence for a pull request or external customer
  validation.
- No issue comment, dogfood update, reviewer request, intermediate release, or fork test is
  created.

## Verification

Before protected publication:

- Change the repository contracts first and observe focused failures before changing version and
  README values.
- Change the Action pin contract first and observe its focused failure before updating the example.
- Run focused contracts, Ruff, all offline tests, the deterministic benchmark, and diff checks.
- Build exactly one candidate wheel and clean-install it outside the checkout.
- Require `pip check`; distribution, module, CLI, web launcher, and new-review versions all equal
  `0.1.16`; the installed benchmark executes 12 cases and 13 criteria with zero mismatches, zero
  must-have False Ready, and zero false blockers.
- Start the installed workbench on explicit loopback, require exact `ok` from
  `/_stcore/health`, stop cleanly, and reject a traceback in its log.
- After pushing the branch, clean-install the exact public full-SHA Action pin and repeat identity
  and benchmark checks.

After publication:

- Require the tag and release target to resolve to the protected-main merge SHA.
- Redownload exactly two public assets, verify the checksum, and compare the public wheel digest
  with the prepublication digest.
- Clean-install the public wheel in another fresh environment and repeat dependency, identity,
  benchmark, and workbench health checks outside the checkout.

## Boundaries

No paid API, LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, license, untrusted-code execution, generic review feature,
security scanner, or auto-fix feature is introduced. Existing criteria confirmation, evidence
levels, gate precedence, runtime-evidence, resolution, final-acceptance, Pydantic validation, and
core/UI separation remain unchanged.
