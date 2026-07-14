# Action-Evidence SHA Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject malformed GitHub commit identifiers in offline Action validation records while preserving the existing exact-marker and same-head evidence rules.

**Architecture:** Put an exact lowercase 40-hex pattern on the three `ActionValidationRecord` SHA fields, keep semantic equality checks in the existing model validator, and exercise the same contract through the existing CLI JSON-validation boundary. Controlled fixtures move from shorthand labels to deterministic full-length identifiers.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, Hatchling, Click.

## Global Constraints

- Keep development version exactly `0.1.17.dev0`; README continues to install verified release `v0.1.16`.
- Validate shape only; do not claim that an accepted SHA exists on GitHub.
- Preserve accepted SHA values exactly; do not trim, lowercase, expand, or contact GitHub.
- Keep marker equality, same-head rerun, comment-count idempotency, repository identity, fork-exclusion, and offline CLI behavior unchanged.
- Do not change workflows, releases, branch protection, Streamlit, gates, findings, storage versions, dependencies, paid services, forks, comments, or notifications.
- Never execute pull-request code.

---

### Task 1: Regression-first schema contract

**Files:**
- Modify: `tests/schemas/test_action_validation_record.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**
- Consumes: owner-supplied `requirements_base_sha`, `non_fork_head_sha`, and `rerun_head_sha` strings.
- Produces: Pydantic field-level `string_pattern_mismatch` errors unless each value matches `^[0-9a-f]{40}$`.

- [ ] **Step 1: Migrate the canonical schema fixture to full SHAs**

Define deterministic values:

```python
BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40
OTHER_SHA = "3" * 40
```

Use `BASE_SHA` for `requirements_base_sha`, `HEAD_SHA` for both head fields, and `scopeproof-action:{HEAD_SHA}` for the marker. Update changed-head and mismatched-marker tests to use `OTHER_SHA` so they continue reaching model-level semantic checks.

- [ ] **Step 2: Add failing invalid-shape and preservation tests**

Parameterize every SHA field over empty/whitespace, abbreviated, non-hex, 39-character, 41-character, and uppercase values. For head fields, update both head values and the marker together so current `main` accepts the internally consistent malformed record and the new test fails for the intended missing field contract. Assert `string_pattern_mismatch` after implementation.

Add one canonical acceptance test that asserts all three valid SHA values and the marker are preserved exactly.

- [ ] **Step 3: Run focused schema tests and verify RED**

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
```

Expected before production changes: new invalid-shape cases fail because current fields require only `min_length=1`; pre-existing semantic tests pass with migrated valid fixtures.

- [ ] **Step 4: Add the minimal field patterns**

In `ActionValidationRecord`, replace `Field(min_length=1)` on the three SHA fields with:

```python
Field(pattern=r"^[0-9a-f]{40}$")
```

Remove the SHA fields from the whitespace-only human-context validator; keep that validator on `validated_by` only. SHA whitespace is now rejected by the exact pattern.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
'../../.venv/bin/python' -m pytest tests/schemas/test_action_validation_record.py -q
'../../.venv/bin/python' -m ruff check scopeproof_core/schemas/models.py tests/schemas/test_action_validation_record.py
```

- [ ] **Step 6: Commit the schema contract**

```bash
git add scopeproof_core/schemas/models.py tests/schemas/test_action_validation_record.py
git diff --cached --check
git commit -m "fix: validate Action evidence commit SHAs"
```

### Task 2: CLI boundary coverage

**Files:**
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: an Action-validation JSON path passed to `scopeproof validate-action-evidence`.
- Produces: exit `0` and validated JSON for canonical evidence, or exit `2`, a deterministic Pydantic error on stderr, and no validated JSON on stdout for malformed SHAs.

- [ ] **Step 1: Migrate only the Action-validation CLI fixture**

Replace its `base123` and `head123` values with deterministic 40-character lowercase values and update the marker to the exact full head SHA. Do not change unrelated GitHub Action planner/publisher fixtures that use different models.

- [ ] **Step 2: Add an invalid-SHA CLI regression test**

Start from the valid helper, set `non_fork_head_sha` and `rerun_head_sha` to `not-a-sha`, and set the marker to `scopeproof-action:not-a-sha`. Invoke the command and require exit `2`, `string_pattern_mismatch` in stderr, and no validated JSON on stdout.

- [ ] **Step 3: Run focused CLI and schema tests**

```bash
'../../.venv/bin/python' -m pytest tests/cli/test_cli.py tests/schemas/test_action_validation_record.py -q
'../../.venv/bin/python' -m ruff check tests/cli/test_cli.py
```

- [ ] **Step 4: Commit the CLI regression**

```bash
git add tests/cli/test_cli.py
git diff --cached --check
git commit -m "test: cover invalid Action evidence SHA input"
```

### Task 3: Source and installed-package verification

**Files:**
- Verify: repository source and a fresh wheel under `/tmp/scopeproof-action-sha-*`.

**Interfaces:**
- Consumes: checked-in source, deterministic benchmark, package metadata, and Action evidence JSON.
- Produces: full source-gate evidence plus clean-installed valid and invalid CLI results.

- [ ] **Step 1: Run source gates**

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.evals.runner
git diff main...HEAD --check
```

Require all tests and Ruff to pass. Require 12 benchmark cases, 13 criteria, zero mismatches, zero must-have False Ready, and zero false blockers.

- [ ] **Step 2: Build and install one clean wheel**

Build with `pip wheel . --no-deps`, install it in a fresh virtual environment, and run `pip check`. Record the wheel SHA-256.

- [ ] **Step 3: Exercise the installed CLI**

Require the installed version to be `0.1.17.dev0`. Validate a canonical record and require exit `0`. Validate an internally consistent `not-a-sha` record and require exit `2`, `string_pattern_mismatch` on stderr, and empty stdout. Run the installed benchmark and require every release gate to remain zero.

- [ ] **Step 4: Review the complete diff**

Run `git diff main...HEAD`, `git diff main...HEAD --check`, and a placeholder scan. Confirm the diff contains only the design, plan, schema contract, and focused tests.

### Task 4: Protected integration and continuation

**Files:**
- Publish: `codex/action-evidence-sha-guard`.

**Interfaces:**
- Consumes: a fresh passing verification run and reviewed branch diff.
- Produces: a green protected PR, verified merged main, clean local synchronization, and the next evidence-backed bounded loop.

- [ ] **Step 1: Rerun all source gates immediately before publishing**

Do not rely on earlier output. Require Ruff, complete pytest, benchmark, and diff checks to pass again.

- [ ] **Step 2: Push and open a ready PR**

Describe the reproduced arbitrary-ID gap, exact 40-lowercase-hex contract, regression-first proof, package validation, and explicit offline/existence limitation. Do not request reviewers or create comments/releases.

- [ ] **Step 3: Merge only after every required check passes**

Wait for protected `verify`, ScopeProof evidence review, and CodeQL checks. Repair genuine failures regression-first. Squash-merge only when all checks are green.

- [ ] **Step 4: Verify merged main and clean up**

Require main CI on the exact merge SHA to pass, fast-forward local `main`, verify local/remote tree equality, remove the owned worktree, and delete the squash-only local branch. Confirm no open PRs and leave release `v0.1.16` unchanged.

- [ ] **Step 5: Rotate into the next safe loop**

Re-audit current repository and live GitHub truth. If no genuine external evidence exists, identify the next deterministic local evidence-boundary defect and continue without inventing validation evidence or marking the persistent goal complete.
