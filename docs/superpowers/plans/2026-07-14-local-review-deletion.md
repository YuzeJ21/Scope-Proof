# Local Review Deletion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users safely delete one exact app-owned local review through the storage API, CLI, and Streamlit workbench.

**Architecture:** Put the only filesystem mutation in `JsonReviewStore.delete(review_id)`, reusing the existing identifier and safe-record lookup boundary. The CLI and Streamlit UI call that method; the UI requires explicit confirmation and preserves any open in-memory review as unsaved work.

**Tech Stack:** Python 3.11+, pathlib, argparse, Streamlit, Pydantic, pytest, Streamlit AppTest.

## Global Constraints

- Delete only an exact regular, non-symlink `<review_id>.json` record inside the configured safe store.
- Never delete the review directory, neighboring records, exports, source repositories, GitHub data, symlink targets, or the open in-memory review.
- Do not parse the target before deletion; a corrupt but safely named regular record remains deletable.
- Do not claim secure media erasure or backup deletion.
- Preserve deterministic, local-first behavior with no billing, paid API, external validation, repository-code execution, bulk delete, force flag, wildcard, or auto-delete.
- Keep the core storage operation independent from Streamlit and validate all persisted review objects through the existing Pydantic boundary.

---

### Task 1: Safe storage deletion boundary

**Files:**
- Modify: `scopeproof_core/storage/json_store.py`
- Test: `tests/storage/test_json_store.py`

**Interfaces:**
- Consumes: `JsonReviewStore._existing_record_path(review_id: str) -> Path`
- Produces: `JsonReviewStore.delete(review_id: str) -> None`

- [ ] **Step 1: Write failing deletion-safety tests**

Add tests that save `review-1` and `review-2`, delete only `review-1`, and prove `review-2` still loads. Add a corrupt regular `corrupt.json` and prove it can be deleted without parsing. Parametrize invalid IDs (`../review-1`, `review-1.json`, `/tmp/review-1`) and assert `ValueError` with all files unchanged. Add missing-record, symlink-root, symlink-record, and directory-named-`record.json` cases and assert the exact target/neighbor/external file remains.

```python
store.delete("review-1")
assert not (tmp_path / "review-1.json").exists()
assert store.load("review-2") == second_state

with pytest.raises(FileNotFoundError):
    store.delete("missing")
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest -q tests/storage/test_json_store.py -k delete`

Expected: failures report that `JsonReviewStore` has no `delete` attribute.

- [ ] **Step 3: Add the minimal store method**

Add immediately after `list_review_ids`:

```python
def delete(self, review_id: str) -> None:
    """Delete one exact safe local record without parsing its contents."""
    self._existing_record_path(review_id).unlink()
```

- [ ] **Step 4: Run storage tests and verify GREEN**

Run: `pytest -q tests/storage/test_json_store.py`

Expected: all storage tests pass, including traversal, symlink, missing, corrupt, and neighboring-record cases.

- [ ] **Step 5: Commit the storage boundary**

```bash
git add scopeproof_core/storage/json_store.py tests/storage/test_json_store.py
git commit -m "Add safe local review deletion"
```

---

### Task 2: Deterministic CLI delete command

**Files:**
- Modify: `scopeproof_core/cli.py`
- Test: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `JsonReviewStore.delete(review_id: str) -> None`
- Produces: `scopeproof delete REVIEW_ID [--storage-dir PATH]`

- [ ] **Step 1: Write failing CLI tests**

Save a review into a temporary custom store, invoke `main(["delete", review_id, "--storage-dir", str(store_dir)])`, and assert exit code `0`, removal, and exact parsed output:

```python
assert json.loads(capsys.readouterr().out) == {
    "deleted_review_id": review_id,
    "storage_dir": str(store_dir),
}
```

Add missing and invalid-ID cases that assert `SystemExit(2)`, `scopeproof: error:` recovery text, no traceback, and no neighboring deletion.

- [ ] **Step 2: Run focused CLI tests and verify RED**

Run: `pytest -q tests/cli/test_cli.py -k delete`

Expected: argparse rejects the unknown `delete` command.

- [ ] **Step 3: Implement the command and parser entry**

Add:

```python
def _delete(args: argparse.Namespace) -> int:
    storage_dir = Path(args.storage_dir)
    JsonReviewStore(storage_dir).delete(args.review_id)
    print(
        json.dumps(
            {"deleted_review_id": args.review_id, "storage_dir": str(storage_dir)},
            sort_keys=True,
        )
    )
    return 0
```

Register after `export`:

```python
delete = commands.add_parser("delete", help="Delete one saved local review")
delete.add_argument("review_id")
delete.add_argument("--storage-dir", default=".scopeproof/reviews")
delete.set_defaults(handler=_delete)
```

- [ ] **Step 4: Run CLI tests and verify GREEN**

Run: `pytest -q tests/cli/test_cli.py`

Expected: all CLI tests pass and failures use existing top-level argparse error handling.

- [ ] **Step 5: Commit the CLI surface**

```bash
git add scopeproof_core/cli.py tests/cli/test_cli.py
git commit -m "Add local review delete command"
```

---

### Task 3: Confirmed Streamlit deletion and privacy copy

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`
- Modify: `docs/privacy-readiness.md`

**Interfaces:**
- Consumes: `JsonReviewStore.delete(review_id: str) -> None`, existing `saved_reopen_review_id`, `saved_review_fingerprint`, and `review_state` session fields
- Produces: `delete_saved_review_confirmed`, `delete_saved_review_reset_pending`, and `saved_review_delete_notice` session fields plus the `delete_saved_review` button

- [ ] **Step 1: Write failing AppTest coverage**

Using a temporary `HOME`, prove the delete button appears only after selecting a saved ID and remains disabled until `delete_saved_review_confirmed` is checked. Delete one of two saved records and assert only that ID disappears after rerun. Reopen a saved record, delete that same ID, and assert the exact `review_state` remains while `saved_review_fingerprint is None`; verify success text says the open review remains available as unsaved work. Add a raced-missing-record case with fixed recovery text and no traceback/raw path.

```python
app = app.checkbox(key="delete_saved_review_confirmed").check().run()
app = app.button(key="delete_saved_review").click().run()
assert app.session_state["review_state"] == open_state
assert app.session_state["saved_review_fingerprint"] is None
```

- [ ] **Step 2: Run focused AppTest cases and verify RED**

Run: `pytest -q tests/apps/test_streamlit_app.py -k delete_saved`

Expected: the deletion confirmation and button keys are absent.

- [ ] **Step 3: Implement session reset and confirmed deletion**

Add the three state defaults. Before listing records, if `delete_saved_review_reset_pending` is true, set it false and clear both `saved_reopen_review_id` and `delete_saved_review_confirmed`. Inside the saved-record branch, render:

```python
delete_confirmed = st.checkbox(
    "Permanently delete the selected local review",
    key="delete_saved_review_confirmed",
)
if st.button(
    "Delete saved review",
    key="delete_saved_review",
    disabled=not reopen_id or not delete_confirmed,
):
    try:
        review_store.delete(reopen_id)
    except FileNotFoundError:
        st.session_state["saved_review_delete_notice"] = (
            "The selected saved review was already removed. Refresh the saved review list."
        )
    except (OSError, ValueError):
        st.session_state["saved_review_delete_notice"] = (
            "The saved review could not be deleted. Verify the local review directory and try again."
        )
    else:
        current = st.session_state["review_state"]
        if current is not None and current.review.review_id == reopen_id:
            st.session_state["saved_review_fingerprint"] = None
            st.session_state["saved_review_delete_notice"] = (
                "Saved review deleted. The open review remains available as unsaved work."
            )
        else:
            st.session_state["saved_review_delete_notice"] = "Saved review deleted."
    st.session_state["delete_saved_review_reset_pending"] = True
    st.rerun()
```

Render the one-rerun notice after the expander, using success styling for deletion and warning/error styling for recovery. Keep all copy fixed and do not expose exception text.

- [ ] **Step 4: Update privacy guidance**

Change the retention table to describe deleting one record through `scopeproof delete REVIEW_ID` or the workbench. State that exported files, backups, and secure-media remnants are not removed, and that a deleted open review stays in session memory as unsaved work until replaced or the session ends. Replace the future-delete threat-model requirement with the tested atomic-delete control.

- [ ] **Step 5: Run UI and documentation tests and verify GREEN**

Run: `pytest -q tests/apps/test_streamlit_app.py tests/github_action/test_workflow_files.py tests/test_repository_contracts.py`

Expected: all tests pass; deletion requires explicit confirmation, never replaces the active review, and docs retain single-account/public-only boundaries.

- [ ] **Step 6: Commit the workbench and documentation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py docs/privacy-readiness.md
git commit -m "Add confirmed saved review deletion"
```

---

### Task 4: Integrated verification and publication

**Files:**
- Verify all changed files from Tasks 1-3

**Interfaces:**
- Consumes: completed storage, CLI, Streamlit, and documentation changes
- Produces: one verified `codex/local-review-deletion` pull request and exact-main proof after merge

- [ ] **Step 1: Run repository gates**

Run Ruff, the complete offline pytest suite, bundled deterministic benchmark, repository verification scripts, and `git diff --check` using the commands documented in `Makefile`, `pyproject.toml`, and `.github/workflows/verify.yml`.

Expected: every command exits `0`; benchmark reports zero false-ready, false-blocker, mismatch, and unexecuted-category counts.

- [ ] **Step 2: Verify clean-package behavior**

Build a wheel, install it into a fresh temporary virtual environment, save a fixture review in a temporary store, run the installed `scopeproof delete REVIEW_ID --storage-dir STORE`, and prove only the selected JSON record disappears. Launch the packaged workbench with a fresh temporary `HOME` and confirm its health endpoint plus the confirmed-delete flow without touching real user records.

- [ ] **Step 3: Independently review the complete diff**

Compare every changed line against `docs/superpowers/specs/2026-07-14-local-review-deletion-design.md`, the engineering rules, and the security/privacy boundaries. Fix any correctness, safety, UX, or coverage finding and rerun the affected gates.

- [ ] **Step 4: Publish, validate, and merge**

Push `codex/local-review-deletion`, open a ready PR, wait for required `verify` and CodeQL checks, merge only when green, then update local `main` and rerun the exact-main verification gates.

- [ ] **Step 5: Reconcile live state and continue the persistent goal**

Confirm local `main == origin/main`, no open PR remains, and the merged checks are green. Reinspect issue #3, public PRs, Dependabot, CodeQL, pinned Actions, docs/workflow drift, and the next highest-value first-use or maintainability gap; continue unless the user cancels.
