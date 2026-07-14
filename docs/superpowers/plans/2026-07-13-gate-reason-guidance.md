# Gate-Reason Guidance Implementation Plan

**Goal:** Replace internal gate-reason identifiers in the Streamlit summary with deterministic,
readable labels while preserving the validated codes and every export contract.

**Architecture:** Reuse the app's existing `_status_label` presentation helper at the single
summary render site. Add AppTest coverage for the visible labels, absence of raw identifiers in the
rendered Markdown, and preservation of the underlying gate codes.

**Tech Stack:** Python 3.11+, Streamlit AppTest, Pydantic 2, pytest, Ruff, Hatchling.

## Constraints

- Keep gate evaluation, schemas, persistence, exports, guidance, and version identity unchanged.
- Keep unknown reason codes visible through deterministic title-casing.
- Preserve raw reason codes in the validated bundle and exported artifacts.
- Do not add paid APIs, external services, dependencies, issue comments, or releases.

### Task 1: Humanize the rendered reason line

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

- [ ] **Step 1: Write a failing AppTest**

Add:

```python
def test_demo_summary_humanizes_gate_reasons_without_mutating_codes() -> None:
    app = analyzed_demo(new_app())
    markdown_text = "\n".join(item.value for item in app.markdown)

    assert (
        "Gate reasons: Blocking Criteria · Conditional Criteria · Unresolved Criteria"
    ) in markdown_text
    assert "blocking_criteria, conditional_criteria, unresolved_criteria" not in markdown_text
    assert app.session_state["bundle"].gate.reason_codes == [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
    ]
```

- [ ] **Step 2: Verify RED**

Run the new test alone. Expected: it fails because the UI still renders comma-separated raw codes.

- [ ] **Step 3: Implement the bounded presentation change**

Replace the current reason rendering with:

```python
        labels = [_status_label(code) for code in bundle.gate.reason_codes]
        st.write("Gate reasons: " + " · ".join(labels))
```

- [ ] **Step 4: Verify GREEN and adjacent tests**

Run the new test, then all `tests/apps/test_streamlit_app.py` tests.

- [ ] **Step 5: Commit**

Commit the two changed files with `humanize gate reasons in review summary`.

### Task 2: Verify the packaged review flow

- [ ] Run Ruff, full pytest, the deterministic benchmark, and `git diff origin/main...HEAD --check`.
- [ ] Build exactly one `scopeproof-0.1.16.dev0-py3-none-any.whl` in a fresh temporary directory.
- [ ] Install the wheel with declared dependencies in a fresh venv; verify distribution, module,
  CLI, web launcher, and new-review identity are all `0.1.16.dev0`.
- [ ] Run the installed benchmark and require exact `ok` from the packaged workbench health route.
- [ ] In the in-app browser, load the packaged demo, confirm criteria, run analysis, and require the
  readable reason line while the raw comma-separated identifiers are absent.
- [ ] Save `09-gate-reason-guidance.png` and compare it beside `06-summary.png` in one combined
  image. Check hierarchy, wrapping, alignment, and clipping at the same 1280×720 viewport.
- [ ] Require no browser console errors and stop the server without a traceback.

### Task 3: Integrate through protected main

- [ ] Push `codex/gate-reason-guidance` and open one ready PR with the audit finding, evidence
  boundary, and verification results. Do not comment on issue #3 or request reviewers.
- [ ] Require both verify jobs, CodeQL jobs and aggregate, and the informational ScopeProof job to
  pass before merge.
- [ ] Merge through protected main, require merged-main CI and CodeQL success, synchronize local
  main, remove the owned worktree and branch, and verify v0.1.15 remains the latest release.
