# ScopeProof v0.1.22 Release Design

## Context

The latest public release is v0.1.21 at
`7a99db62409efb1cbbf24f276305634f8dad061d`. Protected `main` is at
`6554671801d75d02daea223f09e3948162e37458` and identifies itself as
`0.1.22.dev0`.

Since v0.1.21, protected changes added Python 3.11 compatibility evidence, complete export
documentation, evidence-gated beta governance, disclosed constructed-demo onboarding material,
an evaluation-only repository use policy, packaged policy provenance, and non-duplicate feature
branch CI triggers. Exact `main` passes 723 tests with one intentional live-network skip, the
12-case deterministic benchmark, Ruff, protected CI, and CodeQL.

The latest public wheel remains a truthful v0.1.21 artifact, but it does not contain the current
evaluation-use policy bytes or the other protected v0.1.22-line improvements. This is normal
unreleased development state. The accumulated user-facing and distribution changes are now
cohesive enough for one consolidated release rather than additional incremental churn.

## Decision

Publish one consolidated v0.1.22 release through a protected release-preparation pull request.
The preparation changes only release identity, README wheel and checksum paths, the immutable
copyable Action source pin, repository contracts, and release documentation. It does not change
evidence retrieval, schemas, gates, lifecycle behavior, record versions, workflow permissions,
dependencies, or product behavior.

Use two implementation commits after the design and plan commits to avoid a circular Action pin:

1. finalize `0.1.22`, README wheel/checksum paths, and repository contracts;
2. pin the copyable Action example to the full SHA of commit 1, whose tree contains the exact
   v0.1.22 package source.

After protected merge and exact-main CI/CodeQL success, build from the merge SHA, publish one tag
and release containing exactly the wheel and checksum, then redownload and independently verify
both public assets. The published wheel must contain `scopeproof_core/USE_POLICY.md` with bytes
identical to the repository policy and expose the canonical Use Policy project URL without
declaring an open-source license.

## Alternatives considered

### Publish one consolidated v0.1.22 release — selected

Makes the protected development line available as one checksum-verifiable artifact and carries
the evaluation-use provenance into the user-installed wheel.

### Continue accumulating unreleased changes

Rejected for this cycle because the packaged policy provenance and compatibility/onboarding work
are meaningful distribution improvements, not isolated internal churn.

### Publish multiple feature-specific releases

Rejected because it would create unnecessary release and notification volume without producing
additional evidence.

## Release contract

- `scopeproof_core/version.py` contains the only checked-in version value, exactly `0.1.22`.
- README installs `scopeproof-0.1.22-py3-none-any.whl` from v0.1.22 and verifies the matching
  checksum on macOS or Linux.
- The copyable Action installs ScopeProof from one immutable 40-character commit SHA containing
  the exact v0.1.22 package tree.
- Tag, release target, wheel metadata, module version, both CLIs, web launcher, and a new review's
  `tool_version` agree on `0.1.22`.
- The installed wheel contains the exact evaluation-only use-policy bytes and its metadata has a
  `Use Policy` URL but no license expression or license file declaration.
- The installed benchmark reports 12 executed cases, 13 criteria, zero mismatches, zero false
  blockers, zero must-have False Ready outcomes, and no missing declared category.
- The release contains exactly the wheel and checksum asset.
- Release notes distinguish controlled engineering verification from external PR runtime evidence,
  customer validation, adoption, or proof of correctness.
- No issue comment, dogfood update, reviewer request, manually sent email, intermediate release,
  or fork test is created.

## Roadmap execution after publication

After release verification, evaluate every roadmap stage against live evidence:

- Stages 1 and 2 remain open unless a genuine public PR has source-owner-confirmed criteria and a
  real human outcome.
- Stages 4 through 6 remain ineligible until their documented entry evidence exists.
- Stage 7 remains excluded unless the owner separately reopens commercial scope.
- A blocked stage is recorded once and skipped; no synthetic evidence or recurring no-case monitor
  is permitted.

## Boundaries

No paid or LLM API, billing, organization, second account, private repository, fork test,
synthetic user, synthetic validation, invented evidence, open-source license, untrusted-code
execution, generic review, security scanner, or auto-fix feature is introduced. The release PR
contains no product behavior change.
