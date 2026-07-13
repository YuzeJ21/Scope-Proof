# Release Checksum Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give ScopeProof users a machine-verifiable v0.1.12 wheel checksum and an optional pre-install verification path.

**Architecture:** Generate one standard checksum file from the public release wheel and attach it to the same release. Protect matching versioned documentation with a repository contract; keep direct installation as the default path.

**Tech Stack:** GitHub Releases, SHA-256, shasum, sha256sum, Markdown, pytest repository contracts

## Global Constraints

- Do not alter or replace the existing v0.1.12 wheel.
- Do not create a tag, release, package version, Action, service, account, API, license, or dependency.
- A matching checksum proves file integrity against the published digest only; it does not establish publisher identity or reviewed-PR correctness.
- Preserve the simple direct-install path and public-repository-only product boundaries.

---

### Task 1: Public checksum asset

**Files:**
- External release asset: `scopeproof-0.1.12-py3-none-any.whl.sha256`

**Interfaces:**
- Consumes: public v0.1.12 wheel download.
- Produces: a checksum file accepted by `shasum -a 256 -c` and `sha256sum -c`.

- [ ] **Step 1: Download and hash the public wheel**

Download the versioned wheel URL into a fresh temporary directory, compute SHA-256, and require exact equality with `d3fea0a8810fcc5934586948c97037cb9299dc1a42a0f78891eea73429b9aa9f`.

- [ ] **Step 2: Generate and upload the checksum**

Write one line containing the digest, two spaces, and `scopeproof-0.1.12-py3-none-any.whl`; upload it to the existing v0.1.12 release without clobbering the wheel.

- [ ] **Step 3: Verify public assets**

Redownload both assets into a second clean directory, run macOS `shasum -a 256 -c`, run Linux `sha256sum -c` when available, and require the release asset list to contain exactly the wheel and checksum.

### Task 2: Optional verification documentation

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the two versioned v0.1.12 release URLs.
- Produces: copyable optional verification commands before local wheel installation.

- [ ] **Step 1: Add the failing README contract**

Require the checksum URL, `shasum -a 256 -c`, `sha256sum -c`, the local wheel install command, direct release-wheel install URL, and explicit checksum-limit language.

- [ ] **Step 2: Verify RED**

Run `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_readme_documents_optional_release_checksum_verification -q`.

Expected: fail because the checksum URL is absent.

- [ ] **Step 3: Add the minimal optional verification block**

Document downloading both assets, platform-specific verification, and installing the local verified wheel. State that checksum matching verifies bytes against the published digest but is not a code-signing or product-correctness claim.

- [ ] **Step 4: Verify GREEN and repository gates**

Run the focused test, Ruff, full pytest, source benchmark, and `git diff --check`.

Expected: all pass.

- [ ] **Step 5: Publish through protected main**

Commit the spec, plan, README, and contract; push the branch; open a ready PR; require verify, evidence review, and CodeQL; merge normally; then require merged-main CI and CodeQL. Do not create a release.
