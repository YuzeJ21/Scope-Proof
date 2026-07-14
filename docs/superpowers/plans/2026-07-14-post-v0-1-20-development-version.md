# Post-v0.1.20 Development Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark protected source after the v0.1.20 release as the unreleased v0.1.21 development
line.

**Architecture:** Change the existing single version source and its repository contract only.
Verify dynamic wheel metadata, module identity, both CLIs, and new-review provenance without
changing release-install documentation or the immutable Action pin.

**Tech Stack:** Python 3.12, Hatchling, pytest, Ruff.

## Global Constraints

- Source version is exactly `0.1.21.dev0`.
- README and the copyable Action remain pinned to verified v0.1.20 artifacts.
- No product behavior, schema, gate, lifecycle, dependency, workflow, release, or issue change.

---

### Task 1: Advance the development identity

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `scopeproof_core/version.py`

**Interfaces:**
- Consumes: the v0.1.20 release identity on protected `main`.
- Produces: the single v0.1.21.dev0 development identity used by Hatch and review provenance.

- [ ] **Step 1: Change the contract first**

Change `test_hatch_and_reviews_share_one_version_source` to require:

```python
assert '__version__ = "0.1.21.dev0"' in version_source
```

- [ ] **Step 2: Verify RED**

```bash
PYTHONPATH=. "/Users/yjian070/Documents/New project 2/.venv/bin/python" -m pytest \
  tests/test_repository_contracts.py::test_hatch_and_reviews_share_one_version_source -q
```

Expected: one assertion failure because source still reports `0.1.20`.

- [ ] **Step 3: Update the single version source**

Set `scopeproof_core/version.py` to:

```python
"""Single checked-in source for ScopeProof package and review provenance."""

__version__ = "0.1.21.dev0"
```

- [ ] **Step 4: Verify GREEN and identity propagation**

Repeat the focused test and require one pass. Build a wheel from `git archive HEAD`, install it in
a fresh environment, and require distribution metadata, module version, `scopeproof --version`,
`scopeproof-web --version`, and new-review `tool_version` to equal `0.1.21.dev0`.

- [ ] **Step 5: Run repository-wide gates and publish**

Run Ruff, the complete offline suite, deterministic benchmark, `pip check`, and `git diff --check`.
Push `codex/post-v0-1-20-development`, open one ready protected PR without comments or labels,
merge only when `verify` and CodeQL pass, verify the exact merge SHA on `main`, clean up, and
resume the next audit loop.
