# ScopeProof v0.2.3 Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a protected, checksum-verifiable ScopeProof v0.2.3 release from the exact final `main` SHA while keeping engineering evidence separate from product validation.

**Architecture:** Define one active public-release identity in repository contracts, align only current product and install surfaces to that identity, merge through protected GitHub checks, and build every public artifact from the exact resulting merge commit. Historical audits and manifests remain immutable records of their named trees.

**Tech Stack:** Python 3.11+, pytest, Ruff, uv, Markdown, static HTML, GitHub protected branches, GitHub Releases.

## Global Constraints

- [ ] Use no paid API, LLM API, billing, private repository, account, organization, or fork testing.
- [ ] Send no email, direct message, outreach, GitHub progress comment, or notification-only update.
- [ ] Never execute code from a target repository.
- [ ] Do not change deterministic evidence levels, retrieval thresholds, gate precedence, or False Ready policy.
- [ ] Treat all tests, benchmarks, packaging, and release activity as engineering evidence only; Stage 1 remains at zero.
- [ ] Preserve `.coverage 2` and every unrelated or unknown user artifact.
- [ ] Preserve dated audit hashes, historical v0.2.1 manifests, and archived launch snapshots as historical evidence.
- [ ] Merge through a protected pull request with required `verify` and CodeQL; do not push directly to `main`.
- [ ] Keep workflow and copyable Action pins unchanged in this release-alignment pull request.
- [ ] Build the wheel, source distribution, and checksum manifest from the exact final release merge SHA.
- [ ] Require the `v0.2.3` tag target, GitHub Release target, and release build SHA to match exactly.
- [ ] Publish exactly three assets: wheel, source distribution, and `SHA256SUMS.txt`.

---

## Task 1: Define the active v0.2.3 public-release contract

**Files:**

- Modify: `tests/test_repository_contracts.py`

- [ ] Add shared constants for public version `0.2.3`, tag `v0.2.3`, wheel filename, and release-download root.
- [ ] Update active README, participant quickstart, design-partner, roadmap, status-page, changelog, internal-candidate banner, and public-site assertions to require v0.2.3 alignment.
- [ ] Restrict stale-version rejection to active sections so dated v0.2.1 audits and archived launch materials remain valid.
- [ ] Decouple the historical exact-head verification manifest from the live README install path while retaining its captured v0.2.1 assertions.
- [ ] Require changelog ordering `Unreleased` before `0.2.3` before `0.2.1`, plus explicit evidence and Stage 1 boundaries.
- [ ] Run the focused contracts and confirm they fail only because active surfaces still describe v0.2.1 or a pre-publication v0.2.3 candidate.
- [ ] Commit the fail-first contract as `test: define v0.2.3 public release contracts`.

## Task 2: Align active release surfaces without rewriting history

**Files:**

- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/alpha/participant-quickstart.md`
- Modify: `docs/commercialization/design-partner-sprint.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/releases/v0.2.3-internal-candidate.md`
- Modify: `site/index.html`

- [ ] Move the current changelog material under `## 0.2.3 — Evidence integrity and reviewer loop` and reset `Unreleased` without erasing historical entries.
- [ ] Change the active README install and checksum commands to the v0.2.3 wheel and remove obsolete pre-publication wording.
- [ ] Change the participant quickstart and design-partner current-state version to v0.2.3 while retaining setup-only and zero-validation language.
- [ ] Update the roadmap and current status page to record PR #183 merged at `cd362a85a558645a0f56d6540f6bf035e5821809`, exact-main checks passed, and public v0.2.3 publication alignment underway/completed as appropriate.
- [ ] Add a prominent historical pre-publication banner to the internal-candidate record; leave its captured hashes and measurements unchanged.
- [ ] Point the public-site release CTA to v0.2.3.
- [ ] Run repository contracts, Ruff, and `git diff --check`; confirm the release contracts pass.
- [ ] Commit as `release: prepare ScopeProof v0.2.3`.

## Task 3: Verify the protected release candidate

**Files:**

- Verify only; do not update evidence documents with unreviewed or partial results.

- [ ] Run the locked environment check, full test suite with the 95% coverage gate, Ruff, repository contracts, deterministic benchmark, and deterministic comparison benchmark.
- [ ] Build wheel and source distribution outside the checkout and confirm filenames report version 0.2.3.
- [ ] Inspect both archives for repository metadata, virtual environments, caches, coverage files, `.scopeproof` data, bytecode, and secret-like filenames.
- [ ] Generate and verify `SHA256SUMS.txt` for exactly the wheel and source distribution.
- [ ] Install the wheel in a clean external Python 3.12 environment, run `pip check`, confirm both command versions, run both installed benchmarks, and confirm the packaged workbench health endpoint returns exactly `ok`.
- [ ] Request a whole-branch code/spec review and resolve every Critical or Important finding before publication.

## Task 4: Merge, publish, and verify the exact public release

**Files:**

- GitHub protected pull request, annotated tag, and GitHub Release only.

- [ ] Push `codex/v023-release-alignment` and create a ready pull request without progress comments.
- [ ] Wait for required `verify`, CodeQL, compatibility, and locked-environment checks.
- [ ] Merge only with the expected reviewed head SHA.
- [ ] Sync local `main`, confirm local/remote/main identities match, and wait for exact-main CI, CodeQL, and Pages.
- [ ] Rebuild the three release assets from a clean detached worktree at that exact main SHA and repeat clean-install verification.
- [ ] Create annotated tag `v0.2.3` at that SHA and publish the reviewed GitHub Release with exactly the wheel, source distribution, and checksum manifest.
- [ ] Redownload all three public assets, verify checksums, clean-install the public wheel, rerun both benchmarks and workbench health, and confirm the release/tag target SHA exactly matches `main`.
- [ ] Confirm public README/quickstart/site URLs resolve, the latest public release is v0.2.3, and no release note claims correctness, customer validation, or Stage 1 progress.
