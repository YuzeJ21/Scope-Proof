# ScopeProof Packaged Use-Policy Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every future ScopeProof wheel built from protected source carry the exact evaluation-only use policy and expose its canonical URL without adding license metadata.

**Architecture:** Keep `USE_POLICY.md` as the sole source document. Use Hatch's existing wheel `force-include` table to place it inside `scopeproof_core`, and use standard project URL metadata for online discovery. Protect the configuration with a deterministic repository-contract test and verify the built artifact independently.

**Tech Stack:** Python 3.11/3.12, Hatchling, TOML, pytest, pytest-cov, Ruff, wheel ZIP metadata, GitHub Actions.

## Global Constraints

- Work only in the `codex/policy-package-provenance` ScopeProof worktree.
- Do not add SPDX, `License`, `License-Expression`, `License-File`, `license-files`, or an open-source classifier.
- Do not duplicate the policy source in the repository; the wheel mapping consumes root `USE_POLICY.md`.
- Do not change application code, schemas, gates, exporters, Streamlit, GitHub Action behavior, dependencies, or version `0.1.22.dev0`.
- Do not publish v0.1.22, use paid APIs, create billing, create monitoring, or manufacture external evidence.

---

### Task 1: Protect and implement package-policy provenance

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: root `USE_POLICY.md` and the existing Hatch wheel `force-include` configuration.
- Produces: `project.urls["Use Policy"]` and `wheel.force-include["USE_POLICY.md"]` repository contracts.

- [ ] **Step 1: Write the failing repository contract**

Add this test beside the existing use-policy and wheel contracts:

```python
def test_wheel_packages_use_policy_without_license_metadata() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert project["urls"]["Use Policy"] == (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md"
    )
    assert wheel["force-include"]["USE_POLICY.md"] == "scopeproof_core/USE_POLICY.md"
    assert "license" not in project
    assert "license-files" not in project
    assert not any(
        classifier.startswith("License ::") for classifier in project.get("classifiers", [])
    )
```

- [ ] **Step 2: Run the focused test and confirm the red state**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_wheel_packages_use_policy_without_license_metadata -q
```

Expected: fail because `project.urls` and the use-policy wheel mapping do not exist.

- [ ] **Step 3: Commit the red contract**

```bash
git add tests/test_repository_contracts.py
git commit -m "test: define packaged use policy contract"
```

- [ ] **Step 4: Add the minimal Hatch and project URL configuration**

Add this table after the project dependencies:

```toml
[project.urls]
"Use Policy" = "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md"
```

Extend the existing force-include table without changing its benchmark entry:

```toml
[tool.hatch.build.targets.wheel.force-include]
"evals" = "evals"
"USE_POLICY.md" = "scopeproof_core/USE_POLICY.md"
```

- [ ] **Step 5: Record the unreleased provenance improvement**

Under `CHANGELOG.md` Unreleased / Added, add:

```markdown
- Future wheels built from protected source carry the evaluation-only use policy and expose its
  canonical project URL without declaring an open-source license.
```

- [ ] **Step 6: Run the focused and repository-contract tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_repository_contracts.py::test_wheel_packages_use_policy_without_license_metadata -q
.venv/bin/python -m pytest tests/test_repository_contracts.py -q
```

Expected: the focused test passes, followed by all repository-contract tests passing.

- [ ] **Step 7: Commit the implementation**

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "build: package evaluation use policy"
```

### Task 2: Verify artifact bytes and repository health

**Files:**
- Verify only; repair only a defect introduced by Task 1.

**Interfaces:**
- Consumes: the current worktree and its `0.1.22.dev0` wheel.
- Produces: local implementation, test, package, and install evidence; no runtime or adoption claim.

- [ ] **Step 1: Run code and deterministic gates**

Run:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest \
  --cov=scopeproof_core \
  --cov=apps \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 \
  -q
.venv/bin/python -m scopeproof_core.evals.runner
.venv/bin/python -m pip check
```

Expected: Ruff passes; all tests pass with at least 95% coverage; 12 benchmark cases execute with
zero mismatches and zero must-have False Ready; dependency integrity passes.

- [ ] **Step 2: Build and inspect a fresh wheel outside the checkout**

Build one wheel under a fresh temporary directory. Inspect it with `zipfile` and require exactly
one `scopeproof_core/USE_POLICY.md`, byte equality with root `USE_POLICY.md`, a `Project-URL: Use
Policy` metadata line, and no metadata header beginning with `License:`, `License-Expression:`, or
`License-File:`.

- [ ] **Step 3: Clean-install and smoke-test the wheel**

Install the wheel into a temporary Python 3.12 environment and run:

```bash
scopeproof --version
scopeproof-web --version
scopeproof benchmark
```

Expected: both commands report `0.1.22.dev0`; the installed benchmark stays 12 cases, zero
mismatches, and zero must-have False Ready.

- [ ] **Step 4: Complete repository hygiene checks**

Run workflow YAML parsing, `git diff --check`, inspect `git diff origin/main...HEAD`, and confirm
the branch contains no application behavior, dependency, version, license metadata, release,
notification, or unrelated changes.

### Task 3: Publish through protected main and resume audit

**Files:**
- Git and GitHub state only.

**Interfaces:**
- Consumes: the verified two-commit implementation branch.
- Produces: one merged protected-main PR and a clean synchronized repository.

- [ ] Push `codex/policy-package-provenance` and open one ready PR describing the reproduced wheel gap and evidence boundaries.
- [ ] Wait for Python 3.11, `verify`, and CodeQL; diagnose failures without weakening gates.
- [ ] Merge only when green, fast-forward local `main`, and wait for merged-main CI and CodeQL.
- [ ] Confirm branch protection still requires exactly `verify` and `CodeQL` with strict and admin enforcement.
- [ ] Remove the owned worktree and local/remote feature branch after successful merge verification.
- [ ] Recheck authentic first-use eligibility, security alerts, dependency health, release state, SHA-pinned Actions, and documentation drift once; do not create a recurring monitor.
