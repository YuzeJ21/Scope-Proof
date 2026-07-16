# ScopeProof v0.1.23 Alpha CLI Release Plan

**Goal:** Publish a checksum-verifiable v0.1.23 wheel from protected `main` that actually contains
the public-alpha CLI documented by the participant quickstart.

## Constraints

- No paid APIs, billing, email, automated outreach, fork testing, or synthetic evidence.
- Publish exactly one wheel and one matching SHA-256 asset.
- Keep ScopeProof deterministic, local-first, and evaluation-only.
- Do not update Issue #3 until a genuine public LinkedIn post URL exists.

## Tasks

1. Change release contracts first and confirm they fail against v0.1.22 source.
2. Set version and current public links to v0.1.23, then run focused and full verification.
3. Record the immutable release-tree commit and pin the copyable Action to it in a second commit.
4. Build and install the wheel from a clean archive; verify identity, `scopeproof alpha`, benchmark,
   dependency health, policy provenance, and loopback workbench health.
5. Integrate through one protected pull request and require exact-head CI and CodeQL.
6. Build again from the exact merge SHA, publish v0.1.23, redownload both assets independently,
   and repeat the installed checks.
7. Leave Stage 1 open unless a genuine source-owner participant and outcome exist.
