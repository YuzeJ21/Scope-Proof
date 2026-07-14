# Saved review CLI discovery implementation plan

**Goal:** Let local CLI users safely discover saved review IDs without inspecting files or loading
review contents.

**Architecture:** Reuse `JsonReviewStore.list_review_ids()` at the CLI boundary. Validate the
machine-readable response with a small Pydantic schema and serialize its JSON form. Preserve the
existing storage safety and error handling paths.

**Tech stack:** Python, argparse, Pydantic, pytest, Ruff.

---

### Task 1: Lock the CLI contract with failing tests

**Files:**
- Modify: `tests/cli/test_cli.py`
- Modify: `tests/test_repository_contracts.py`

Add tests proving that `scopeproof list` returns an empty validated result for an absent store,
returns sorted safe IDs without parsing corrupt JSON, fails closed for an unsafe store root, and is
documented next to export/delete guidance. Run the focused tests and confirm they fail because the
command and documentation do not exist.

### Task 2: Implement the schema-validated command

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/cli.py`

Add a Pydantic response model, implement the handler with `JsonReviewStore.list_review_ids()`, and
register `list` with the same `--storage-dir` default used by export/delete. Run the focused tests
until green.

### Task 3: Document local discovery

**Files:**
- Modify: `README.md`

Add the exact list command and explain that it returns local identifiers only, does not parse review
contents, and is not evidence. Keep release-install guidance pinned to verified v0.1.20 artifacts.

### Task 4: Verify and publish

Run Ruff, the complete offline test suite, deterministic benchmark, `git diff --check`, archived
wheel build/install identity, installed `scopeproof list` probes, dependency check, and packaged
workbench health. Commit intentionally, push the `codex/` branch, open a ready PR, wait for protected
`verify` and CodeQL, merge only the exact reviewed head, verify exact-main checks, then remove the
owned worktree and continue the next safe loop.
