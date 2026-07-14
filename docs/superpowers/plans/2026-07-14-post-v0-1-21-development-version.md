# Post-v0.1.21 Development Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark protected source after the v0.1.21 release as the unreleased v0.1.22 development
line.

**Architecture:** Change the existing single version source and its repository contract only.
Verify dynamic wheel metadata, module identity, both CLIs, and new-review provenance without
changing release-install documentation or the immutable Action pin.

**Tech Stack:** Python 3.12, Hatchling, pytest, Ruff.

## Global Constraints

- Source version is exactly `0.1.22.dev0`.
- README and the copyable Action remain pinned to verified v0.1.21 artifacts.
- No product behavior, schema, gate, lifecycle, dependency, workflow, release, issue comment,
  label, reviewer request, or manually sent email.

---

### Task 1: Advance the development identity

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `scopeproof_core/version.py`

- [ ] **Step 1: Change the contract first**

Change `test_hatch_and_reviews_share_one_version_source` to require
`__version__ = "0.1.22.dev0"`.

- [ ] **Step 2: Verify RED**

Run the focused repository contract and require one assertion failure because source still reports
`0.1.21`.

- [ ] **Step 3: Update the single version source**

Set `scopeproof_core/version.py` to `0.1.22.dev0`.

- [ ] **Step 4: Verify GREEN and identity propagation**

Repeat the focused test and require one pass. Build a wheel from `git archive HEAD`, install it in
a fresh environment, and require distribution metadata, module version, both CLIs, and new-review
`tool_version` to equal `0.1.22.dev0`.

- [ ] **Step 5: Run repository-wide gates and publish**

Run Ruff, the complete offline suite, deterministic benchmark, `pip check`, and `git diff --check`.
Push `codex/post-v0-1-21-development`, open one ready protected PR without comments or labels,
merge only when `verify` and CodeQL pass, verify the exact merge SHA on `main`, clean up, and
resume the next evidence-backed audit loop.
