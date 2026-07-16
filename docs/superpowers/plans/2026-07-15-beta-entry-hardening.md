# ScopeProof Beta-Entry Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the public repository safe and explicit for evaluation-only beta use, enforce a local-only coverage floor, and distinguish historical engineering records from current product evidence.

**Architecture:** Keep all changes at the repository-contract, documentation, and CI layers. Do not change the deterministic core engine, Streamlit behavior, GitHub integration behavior, or evidence semantics. Contract tests define the public promises before their implementation.

**Tech Stack:** Python 3.11/3.12, pytest, pytest-cov, Ruff, GitHub Actions, Markdown.

## Global Constraints

- Work only in `/Users/yjian070/Documents/New project 2` and the existing `codex/beta-entry-hardening` worktree.
- Do not add paid APIs, LLM calls, billing, scheduled monitoring, fork testing, synthetic validation, or invented external evidence.
- Do not execute untrusted repository code in the application server.
- Preserve deterministic gates and the distinction between implementation, test, runtime, and adoption evidence.
- Do not add an SPDX identifier or `LICENSE` file; the approved posture is evaluation-only with no open-source license.
- Do not upload coverage or create an external coverage account.
- Do not publish a release or package in this slice.

---

### Task 1: Define failing repository-contract tests

**Files:**
- Modify: `tests/test_repository_contracts.py`

- [ ] Add `test_public_docs_state_evaluation_only_use_policy` asserting that `USE_POLICY.md` exists, states the no-license/evaluation-only posture, preserves GitHub Terms of Service and applicable-law boundaries, disclaims warranty/correctness/service/support, identifies the repository owner as the permission contact, is linked from `README.md` and `CONTRIBUTING.md`, and is recorded as complete in `ROADMAP.md` without a `LICENSE` file.
- [ ] Add `test_python_312_ci_enforces_local_coverage_floor` asserting `pytest-cov>=6,<7` is a development dependency, Python 3.12 runs coverage over `scopeproof_core` and `apps` with `--cov-fail-under=95`, Python 3.11 retains `python -m pytest -q`, no external coverage uploader is introduced, and `.coverage` is ignored.
- [ ] Add `test_internal_engineering_archive_has_provenance_index` asserting `docs/superpowers/README.md` labels specs/plans as historical engineering records rather than current product status, runtime evidence, adoption evidence, or a sequential user manual, and that `CONTRIBUTING.md` links the index.
- [ ] Run `./.venv/bin/python -m pytest tests/test_repository_contracts.py -q` and confirm the new tests fail for the missing artifacts/configuration before implementation.
- [ ] Commit the red contract tests with `test: define beta entry repository contracts`.

### Task 2: Publish the evaluation-only use posture

**Files:**
- Create: `USE_POLICY.md`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`

- [ ] Create `USE_POLICY.md` stating that the repository is intentionally published without an open-source license and is available for evaluation/review only.
- [ ] State that no additional permission to use, copy, modify, distribute, sublicense, or create derivative works is granted absent a separate written agreement; public visibility remains subject to GitHub Terms of Service and applicable law.
- [ ] State that evaluation access creates no warranty, correctness claim, service commitment, or support obligation, and direct permission requests to the repository owner.
- [ ] Link the policy from `README.md` and `CONTRIBUTING.md` without presenting it as legal advice.
- [ ] Mark the roadmap software-use-policy decision complete and remove it from active waiting conditions while leaving authentic-use evidence open.
- [ ] Record the public documentation change under `CHANGELOG.md` Unreleased.
- [ ] Run the use-policy contract test and confirm it passes.

### Task 3: Enforce the Python 3.12 coverage floor locally and in CI

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.gitignore`
- Modify: `CHANGELOG.md`

- [ ] Add `pytest-cov>=6,<7` to the development dependency group.
- [ ] Change only the Python 3.12 `verify` test command to `python -m pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q`.
- [ ] Keep the Python 3.11 compatibility job test command exactly `python -m pytest -q`.
- [ ] Ignore `.coverage` and `.coverage.*`; do not add upload actions, badges, external tokens, or persisted reports.
- [ ] Update the Unreleased changelog entry.
- [ ] Reinstall the worktree development environment and run the coverage contract test.
- [ ] Run the full coverage command and confirm the measured result is at least 95%.

### Task 4: Add provenance for historical engineering records

**Files:**
- Create: `docs/superpowers/README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `CHANGELOG.md`

- [ ] Explain that `specs/` and `plans/` are historical design and implementation records retained for provenance.
- [ ] Explicitly state that these records are not current product status, runtime evidence, adoption evidence, or a sequential user manual.
- [ ] Point readers to `README.md`, `ROADMAP.md`, `CHANGELOG.md`, and current tests/workflows for current truth.
- [ ] Link the archive index from `CONTRIBUTING.md` and record the change under Unreleased.
- [ ] Run all repository-contract tests and confirm they pass.
- [ ] Commit the implemented slice with `docs: harden beta entry contracts`.

### Task 5: Complete local release-grade verification

**Files:**
- Verify only; repair only defects introduced by Tasks 1-4.

- [ ] Run `./.venv/bin/python -m ruff check .`.
- [ ] Run `./.venv/bin/python -m pytest -q`.
- [ ] Run the Python 3.12 coverage command and confirm the floor.
- [ ] Run `./.venv/bin/python benchmarks/run_benchmark.py --check`.
- [ ] Run `./.venv/bin/python -m pip check`.
- [ ] Build the wheel and install it into a temporary clean virtual environment.
- [ ] Smoke-test `scopeproof --version`, `scopeproof-action --version`, and the Streamlit health endpoint without retaining generated artifacts.
- [ ] Parse the modified workflow as YAML.
- [ ] Run `git diff --check`, inspect the complete diff, and confirm no unrelated files, secrets, paid-service dependencies, scheduled workflows, or evidence overclaims were introduced.

### Task 6: Publish and merge one protected pull request

**Files:**
- Git/GitHub state only.

- [ ] Push `codex/beta-entry-hardening` and open one ready-for-review pull request against `main` with the scope, evidence boundaries, and exact verification results.
- [ ] Confirm the PR changes only the approved beta-entry-hardening files.
- [ ] Wait for `verify`, `compatibility (3.11)`, and `CodeQL` to pass; diagnose real failures rather than weakening gates.
- [ ] Merge the green PR using the repository's existing merge convention.
- [ ] Update local `main` by fast-forward and confirm it matches `origin/main` with a clean worktree.

### Task 7: Require both protected-main checks

**Files:**
- GitHub branch-protection state only.

- [ ] Confirm the merged main commit has successful `verify` and `CodeQL` check runs.
- [ ] Update only the required-status-checks subresource so the exact required contexts are `verify` and `CodeQL`.
- [ ] Preserve strict status checks and administrator enforcement.
- [ ] Read branch protection back and record the exact confirmed state.

### Task 8: Close with an authentic first-use audit

**Files:**
- Read-only repository and GitHub audit unless a genuine eligible case exists.

- [ ] Inspect open public PRs and issue #3 for a genuine source-owner-confirmed ScopeProof evaluation case.
- [ ] Inspect open dependency, CodeQL, secret-scanning, workflow-pinning, documentation-drift, and release-health findings.
- [ ] If a genuine case exists, apply the documented workflow without inventing evidence; if none exists, state the exact waiting condition once and do not create a monitor or synthetic case.
- [ ] Update the roadmap only if new genuine evidence changes project truth.
- [ ] Report completed beta-entry hardening, remaining product gaps, and the next evidence-backed stage.
