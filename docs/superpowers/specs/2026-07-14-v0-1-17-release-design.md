# ScopeProof v0.1.17 Release Design

## Context

The latest public release is v0.1.16 at `e6f2ad46c7cf56f7ce2886d20d6b2a8aa7f30c22`. Protected `main` is now at `900f026c4ef31cf0e14e6d422afafa80b02fea01` and identifies itself as `0.1.17.dev0`.

Since v0.1.16, 13 protected pull requests have formed one coherent hardening batch:

- clearer prepared-criteria handoff;
- Pydantic rejection of blank acceptance criteria, runtime context, manual-verification notes, and runtime limitations;
- GitHub Action evidence validation for nonblank context, canonical GitHub identity, commit SHAs, event head SHA, and event repository identity;
- discoverable saved local reviews;
- rejection of a symlinked or otherwise non-directory local review-store root.

The current source suite passes 353 tests with one intentional live-network skip. The 12-case/13-criterion deterministic benchmark has zero mismatches, zero must-have False Ready, and zero false blockers. Protected main CI and CodeQL succeeded at the current SHA, and GitHub reports no open Dependabot or code-scanning alerts. Issue #3 still contains only owner-authored responses, so the release cannot be described as external validation.

## Decision

Publish one consolidated v0.1.17 release after one protected release-preparation pull request. The batch materially affects installed first-use behavior, saved-review recovery, persistence safety, and the copyable Action's offline evidence contract. Leaving it only on the development line would keep the supported public wheel and Action source pin behind verified product behavior.

The preparation changes only release identity, README installation guidance, the immutable copyable Action source pin, and regression contracts for those surfaces. It does not change evidence retrieval, schemas beyond already-merged v0.1.17 work, gates, lifecycle, record versions, final acceptance, workflow permissions, or dependencies.

The pull request uses two implementation commits after this design and plan:

1. Change the single version source from `0.1.17.dev0` to `0.1.17`, update README wheel/checksum commands, and update repository contracts.
2. Pin the copyable Action example to the full SHA of the first implementation commit. That SHA contains the exact v0.1.17 package tree; the second commit changes only the adoption example and its pin contract, avoiding a circular self-reference.

After protected merge and exact merged-main CI/CodeQL success, build from the merge SHA, publish one tag and release with exactly the wheel and checksum, redownload both public assets, and independently repeat checksum, identity, dependency, benchmark, and packaged-workbench health verification.

## Alternatives considered

### 1. One consolidated v0.1.17 release — selected

This makes the coherent hardening batch installable, refreshes the immutable Action source, and limits notification activity to one necessary PR and one meaningful release.

### 2. Tag current main without preparation

Rejected because the package reports `0.1.17.dev0`, README installs v0.1.16, and the copyable Action remains pinned to the v0.1.16 package tree.

### 3. Continue accumulating unreleased changes

Rejected because the public wheel currently lacks saved-review discovery and the reviewed storage and Action-evidence safeguards. More accumulation would widen the supported-installation gap without producing external adoption evidence.

## Release contract

- `scopeproof_core/version.py` is the only checked-in version value and contains `0.1.17`.
- README installs `scopeproof-0.1.17-py3-none-any.whl` from v0.1.17 and verifies the matching `.sha256` asset on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing the exact v0.1.17 package tree.
- Tag, release target, wheel metadata, module version, console versions, and a new review's `tool_version` all agree on `0.1.17`.
- The release contains exactly the wheel and checksum asset.
- Release notes distinguish controlled product verification from runtime evidence for a PR, external customer validation, or proof of correctness.
- No issue comment, dogfood update, reviewer request, intermediate release, or fork test is created.

## Verification

Before protected publication:

- Change repository and Action contracts first and observe focused failures.
- Run Ruff, all offline tests, the deterministic benchmark, and diff checks.
- Build one candidate wheel from an archive of the branch, install it outside the checkout, and require `pip check` plus exact distribution/module/CLI/web/new-review identity.
- Run the installed benchmark and exact loopback `ok` health smoke with clean shutdown.
- After pushing, clean-install the public full-SHA Action pin and repeat identity and benchmark checks.

After publication:

- Require tag and release target to resolve to the protected-main merge SHA.
- Redownload exactly two assets, verify the checksum and prepublication digest match, install the public wheel into a fresh environment, and repeat dependency, identity, benchmark, and workbench health checks outside the checkout.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository, fork test, synthetic user, synthetic validation, license, untrusted-code execution, generic review, security scanner, or auto-fix feature is introduced. No product behavior beyond release identity and public adoption pins changes in the preparation PR.
