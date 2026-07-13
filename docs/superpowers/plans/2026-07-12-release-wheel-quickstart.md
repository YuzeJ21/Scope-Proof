# Release Wheel Quickstart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give first-time users a verified, versioned ScopeProof installation path that does not require cloning the repository.

**Architecture:** Treat the exact v0.1.11 wheel asset as the user-facing distribution and keep editable installation as a contributor-only path. Protect the public installation contract with a repository test, then verify the documented commands in a clean environment.

**Tech Stack:** Markdown, pytest repository contracts, Python wheel, GitHub Releases

## Global Constraints

- Use only `scopeproof-0.1.11-py3-none-any.whl` built from tag commit `6f6353adc5a6b8057f66eb8c993cb69dbb47e177`.
- Do not add or choose a software license.
- Do not add PyPI, package registries, Actions, services, accounts, billing, or paid APIs.
- Do not claim that artifact installation proves reviewed pull-request behavior.
- Do not create a new release.

---

### Task 1: User and contributor installation paths

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the public v0.1.11 GitHub Release wheel URL and installed `scopeproof` console commands.
- Produces: a stable first-use Quickstart and a separate editable contributor setup.

- [ ] **Step 1: Add the failing README contract**

Require the versioned release-wheel URL, `scopeproof benchmark`, a `Contributor setup` heading, the editable `.[dev]` command, and the repository-local Streamlit command. Reject the nonexistent `scopeproof web` command.

- [ ] **Step 2: Verify RED**

Run `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_readme_separates_release_install_from_contributor_setup -q`.

Expected: fail because the release-wheel URL and contributor heading are absent.

- [ ] **Step 3: Rewrite the Quickstart minimally**

Make the release wheel the default CLI installation, point directly to the public-PR CLI workflow, retain the review-flow explanation, and move editable installation plus Streamlit startup into `Contributor setup`.

- [ ] **Step 4: Verify GREEN**

Run `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_readme_separates_release_install_from_contributor_setup -q`.

Expected: `1 passed`.

- [ ] **Step 5: Verify the documented artifact path**

Download the public asset into a fresh temporary directory, compare SHA-256 with `d9a92c047e901b7370b3a09b0480b9cae527ec4dc2e302ec7546cf8832234634`, install it in a fresh virtual environment, and run `scopeproof benchmark` outside the repository.

Expected: 12 cases, no mismatches, no must-have False Ready, and no false blockers.

- [ ] **Step 6: Run complete repository gates**

Run Ruff, full pytest, source benchmark, and `git diff --check`.

Expected: all pass.

- [ ] **Step 7: Publish through protected main**

Commit only the design, plan, README, and contract test; push the branch; open a PR; require `verify` and CodeQL; merge without bypass; and confirm merged-main checks pass.
