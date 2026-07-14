# Local Review Deletion Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make single-record local review deletion discoverable in ScopeProof's primary README without changing product behavior.

**Architecture:** Extend the existing `Local review storage` paragraph rather than creating a new top-level section. Protect the public guidance with one narrow repository-contract test that checks the supported workbench label, CLI command, and deletion limits.

**Tech Stack:** Markdown, Python, pytest.

## Global Constraints

- Preserve the exact CLI command `scopeproof delete REVIEW_ID`.
- Preserve the exact workbench confirmation label `Permanently delete the selected local review`.
- State that deletion removes only the selected app-owned JSON record.
- State that exported reports remain user-owned and are not removed.
- State that deletion is not secure erasure.
- Do not change storage, CLI, Streamlit, schema, evidence, lifecycle, gate, release, or notification behavior.
- Do not add bulk deletion, directory deletion, backup management, hosted storage, private repositories, billing, paid APIs, or external validation claims.

---

### Task 1: README deletion guidance contract

**Files:**
- Modify: `README.md:158-169`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: existing README `Local review storage` section and the implemented workbench/CLI labels
- Produces: a public deletion path and `test_readme_documents_single_record_local_review_deletion()`

- [ ] **Step 1: Add the failing repository-contract test**

Add after the existing public-document contract tests:

```python
def test_readme_documents_single_record_local_review_deletion() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof delete REVIEW_ID" in readme
    assert "Permanently delete the selected local review" in readme
    assert "Exported reports remain user-owned and are not removed" in readme
    assert "not secure erasure" in readme
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
../../.venv/bin/python -m pytest -q \
  tests/test_repository_contracts.py::test_readme_documents_single_record_local_review_deletion
```

Expected: FAIL because the README does not yet contain `scopeproof delete REVIEW_ID`.

- [ ] **Step 3: Extend the existing storage paragraph**

Append to the `Local review storage` section:

```markdown
To delete one saved review in the workbench, select its listed ID, then check
`Permanently delete the selected local review`. From the CLI, run
`scopeproof delete REVIEW_ID`; add `--storage-dir PATH` only for a review saved
outside the default CLI directory. Deletion removes only that app-owned JSON
record. Exported reports remain user-owned and are not removed, and deletion is
not secure erasure of storage media or backups. An open deleted review remains
available as unsaved session work until it is replaced or the session ends.
```

- [ ] **Step 4: Run the focused and complete contract tests and verify GREEN**

Run:

```bash
../../.venv/bin/python -m pytest -q \
  tests/test_repository_contracts.py::test_readme_documents_single_record_local_review_deletion
../../.venv/bin/python -m pytest -q tests/test_repository_contracts.py
```

Expected: the focused test and all repository-contract tests pass.

- [ ] **Step 5: Commit the documentation slice**

```bash
git add README.md tests/test_repository_contracts.py
git commit -m "Document local review deletion"
```

---

### Task 2: Full verification and protected publication

**Files:**
- Verify: all branch changes

**Interfaces:**
- Consumes: completed README and contract regression
- Produces: a verified protected PR and exact-main proof

- [ ] **Step 1: Run repository verification**

Run Ruff, the complete offline pytest suite, the deterministic benchmark, and `git diff --check origin/main...HEAD`.

Expected: Ruff exits `0`; only the intentional live-network test is skipped; the benchmark executes 12 cases and 13 criteria with zero mismatches, must-have False Ready, false blockers, and unexecuted categories; diff hygiene is clean.

- [ ] **Step 2: Review documentation truth**

Compare the README wording against `scopeproof --help`, `scopeproof delete --help`, `docs/privacy-readiness.md`, and the current-run workbench screenshots. Confirm no install path, default-directory, secure-erasure, backup, runtime, or external-validation overclaim.

- [ ] **Step 3: Publish and merge through protection**

Push `codex/document-local-review-deletion`, open a ready PR, wait for required `verify`, both CodeQL analyses, and the GitHub Advanced Security CodeQL summary. Merge only when green, fast-forward local `main`, rerun exact-main checks, clean the worktree/branch, and begin the next evidence-backed loop.
