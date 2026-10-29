# v0.2.4 Evaluation Release Preparation Implementation Plan

> **For agentic workers:** Use the execution and independent-review workflow in this session.

**Goal:** Merge a phase-safe v0.2.4 release-preparation PR and verify private candidate assets from
the resulting exact main commit, without publication or personal testing.

**Architecture:** Keep published v0.2.3 identity separate from the v0.2.4 candidate. Align current
surfaces and existing repository contracts; preserve immutable historical evidence. Build the
candidate after the protected merge, with a private version-bound evidence packet.

**Tech Stack:** Python, Pydantic, pytest, Ruff, uv/Hatch, Markdown, static HTML, GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-29-v024-evaluation-release-design.md`

## Global Constraints

- No publication, tags, asset uploads, deployment, outreach or progress comments.
- No personal testing or qualifying reviews; no invented independent-use evidence.
- Preserve frozen research, historical hashes, evidence rules, criteria confirmation and decisions.
- Main changes use a reviewed PR with exact-head hosted checks; no direct main push.
- GitHub Releases is the availability authority; candidate assets are private until authorized.

## Review Focus

- Before publication, install links must be conditional and the site CTA must resolve.
- Historical v0.2.3 observations must retain their original versions, hashes and meaning.
- Pre-v5 loading must be described as conservative reassessment, never invented acceptance.
- Candidate source, final archives and recorded checks must have explicit identities.
- Distribution readiness must not be described as Stage 3, human validation or conformance.

### Task 1: Align candidate identity and release documentation

Files: `scopeproof_core/version.py`, `uv.lock`, `tests/test_repository_contracts.py`, `README.md`,
`CHANGELOG.md`, `ROADMAP.md`, `SECURITY.md`, `site/index.html`, `docs/README.md`,
`docs/development-environment.md`, `docs/releases/v0.2.3-status-and-next-stages.md`,
`docs/alpha/participant-quickstart.md`, `docs/commercialization/design-partner-sprint.md`,
and new `docs/releases/v0.2.4-evaluation-candidate.md`.

- [ ] Verify clean isolated baseline and existing contracts.
- [ ] Promote source to `0.2.4`; update existing contracts for conditional candidate installation,
  source identity, current ledger v5, and preserved historical publication facts.
- [ ] Align active guidance and release notes with the spec, retaining dated snapshots.
- [ ] Refresh only the package version in the lock; run contracts, locked checks and lint.
- [ ] Run full suite with 95% coverage and both deterministic benchmarks.
- [ ] Independent whole-branch review; fix supported findings and rerun affected checks.
- [ ] Commit/push the preparation branch and open a reviewable PR.

### Task 2: Merge and verify the exact release candidate

Files: GitHub PR and private artifact directory outside the checkout only.

- [ ] Verify exact-head hosted CI, CodeQL, compatibility and browser checks; resolve findings.
- [ ] Merge using expected head SHA; synchronize main and verify exact-main hosted results.
- [ ] Build wheel and source archive from the clean exact-main tree, inspect inventory and
  packaged use policy, then generate/verify SHA256SUMS for precisely the two archives.
- [ ] Clean-install outside the checkout; verify both command versions, installed import path,
  dependency compatibility, both deterministic benchmarks and local workbench health `ok`.
- [ ] Retain source/artifact identity, command outputs, draft release notes and explicit pending
  publication/public-redownload steps in a private candidate packet. Report PR, SHA and limits.
