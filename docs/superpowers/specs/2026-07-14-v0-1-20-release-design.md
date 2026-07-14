# ScopeProof v0.1.20 Release Design

## Context

The latest public release is v0.1.19 at
`b6d09df88d37f7b2bb4b80e202331bc72f500d09`. Protected `main` is at
`02d633808c8ef0234f5932baa9f94ac064bb0029` and identifies itself as
`0.1.20.dev0`.

Since v0.1.19, 12 protected pull requests have formed one coherent operator-trust batch:

- the installed workbench explains public-PR fetch recovery and review availability;
- unchanged criteria cannot be reconfirmed accidentally;
- criterion-specific, criteria-edit, criteria-authoring, and requirements drafts cannot be
  mistaken for persisted or exported review state;
- runtime evidence records show their complete persisted context and UTC timestamp; and
- resolution history shows attribution metadata while new human events record an explicit,
  non-blank reviewer identity.

Exact `main` passes Ruff, 703 tests with one intentional live-network skip, and the
12-case/13-criterion deterministic benchmark with zero mismatches, must-have False Ready, false
blockers, evidence-link errors, or unexecuted categories. Its protected CI and CodeQL runs pass.
GitHub reports zero open Dependabot, code-scanning, and secret-scanning alerts. Issue #3 still has
only owner-authored responses, so this release is not external validation.

## Decision

Publish one consolidated v0.1.20 release through one protected release-preparation pull request.
The v0.1.19 wheel lacks the current draft-persistence guards, complete audit records, and
attributable decision workflow. The 12-PR batch materially improves the installed public-alpha
workbench and is large enough to justify one release without incremental churn.

The preparation changes only release identity, README release-install guidance, the immutable
copyable Action source pin, repository contracts, and the release design/plan. It does not change
evidence retrieval, schemas, gates, lifecycle behavior, record versions, workflow permissions,
dependencies, or product behavior.

Use two implementation commits to avoid a circular Action pin:

1. finalize `0.1.20`, README wheel/checksum paths, and repository contracts;
2. pin the copyable Action example to the full SHA of commit 1, whose tree contains the exact
   v0.1.20 package source.

After protected merge and exact-main CI/CodeQL success, build from the merge SHA, publish one tag
and release containing exactly the wheel and checksum, then redownload and independently verify
both public assets.

## Alternatives considered

### Consolidated v0.1.20 release — selected

Makes the complete verified operator-trust batch installable and refreshes the immutable Action
source in one meaningful release.

### Continue accumulating unreleased changes

Rejected because the public wheel is already 12 protected product and reliability PRs behind
`main`; waiting further widens the supported-installation gap.

### Tag current `main` without preparation

Rejected because the package reports `0.1.20.dev0`, README still installs v0.1.19, and the
copyable Action remains pinned to the v0.1.19 package tree.

## Release contract

- `scopeproof_core/version.py` contains the only checked-in version value, exactly `0.1.20`.
- README installs `scopeproof-0.1.20-py3-none-any.whl` from v0.1.20 and verifies the matching
  checksum on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing
  the exact v0.1.20 package tree.
- Tag, release target, wheel metadata, module version, both CLIs, web launcher, and a new review's
  `tool_version` agree on `0.1.20`.
- The release contains exactly the wheel and checksum asset.
- Release notes describe controlled local verification without calling it external PR runtime
  evidence, customer validation, or proof of correctness.
- No issue comment, dogfood update, reviewer request, manually sent email, intermediate release,
  or fork test is created.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, license, untrusted-code execution, generic review, security
scanner, or auto-fix feature is introduced. The release-preparation PR contains no product
behavior change.
