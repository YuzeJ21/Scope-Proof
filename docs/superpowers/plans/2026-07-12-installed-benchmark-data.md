# Installed Benchmark Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include the deterministic benchmark corpus in built wheels so `scopeproof benchmark` works after a clean install.

**Architecture:** Keep the existing top-level `evals` corpus and runner path. Add one Hatch wheel force-include mapping and protect it with a repository contract, then verify the actual wheel from a fresh temporary environment.

**Tech Stack:** Python 3.11+, Hatchling, pytest, pip wheel, ZIP-format wheels.

## Global Constraints

- Add no runtime dependency or network behavior.
- Do not change benchmark labels, fixtures, findings, gates, or metrics.
- Preserve offline deterministic execution after installation.
- Keep the corpus at `evals/fixtures` and `evals/labels` in both source and wheel layouts.

---

### Task 1: Wheel package-data contract

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `[tool.hatch.build.targets.wheel.force-include]` from `pyproject.toml`.
- Produces: an exact `evals = "evals"` source-to-wheel mapping.

- [ ] **Step 1: Write the failing repository contract**

```python
def test_wheel_includes_bundled_benchmark_data() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["force-include"]["evals"] == "evals"
    assert list(Path("evals/fixtures").glob("*.json"))
    assert list(Path("evals/labels").glob("*.json"))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `.venv/bin/python -m pytest tests/test_repository_contracts.py::test_wheel_includes_bundled_benchmark_data -q`

Expected: FAIL because `force-include` is absent.

- [ ] **Step 3: Add the Hatch mapping**

```toml
[tool.hatch.build.targets.wheel.force-include]
"evals" = "evals"
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the focused command from Step 2.

Expected: PASS.

### Task 2: Real artifact verification

**Files:**
- No repository files beyond Task 1.

**Interfaces:**
- Consumes: the wheel built from the current checkout.
- Produces: clean-install evidence that the archive contains both corpus directories and the installed CLI executes all 12 cases.

- [ ] **Step 1: Build and inspect the wheel**

Run `python -m pip wheel . --no-deps --wheel-dir /tmp/scopeproof-wheel-check`, then inspect the ZIP listing for `evals/fixtures/*.json` and `evals/labels/*.json`.

Expected: both directories and their JSON files are present.

- [ ] **Step 2: Install and run from a fresh environment**

Create `/tmp/scopeproof-install-check`, install the wheel, change the working directory to `/tmp`, and run `scopeproof benchmark`.

Expected: 12 cases, zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 3: Run full repository verification**

Run Ruff, the complete offline pytest suite, the source benchmark, and `git diff --check`.

Expected: all checks pass with only the opt-in live test skipped.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/test_repository_contracts.py docs/superpowers/plans/2026-07-12-installed-benchmark-data.md
git commit -m "fix: package bundled benchmark data"
```
