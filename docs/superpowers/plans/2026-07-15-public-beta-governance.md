# Public Beta Governance Implementation Plan

**Goal:** Make ScopeProof's public-alpha status, beta entry gates, release history, and contribution
requirements discoverable without creating notification automation or overstating validation.

**Constraints:** No paid service, scheduled workflow, bot comment, Dependabot enablement, license
choice, synthetic validation, or invented evidence.

## Tasks

1. Add failing repository contract tests for the roadmap, changelog, issue forms, pull-request
   template, and their public links.
2. Add `ROADMAP.md` with truthful current status, staged exit gates, explicit external decisions,
   and a no-passive-monitor stop rule.
3. Add `CHANGELOG.md` with an Unreleased section and authoritative release-history link.
4. Add defect and public-alpha feedback issue forms plus a pull-request template.
5. Link the governance surfaces from README and CONTRIBUTING.
6. Run focused tests, Ruff, the full test suite, the deterministic benchmark, and `git diff --check`.
7. Publish one protected-main pull request and merge only after required checks pass.

