# First-Use Primary Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the offline demo visible in ScopeProof's initial viewport while preserving validated fresh-session review reopening.

**Architecture:** Keep all existing session and storage behavior in `apps/web/app.py`. Change only the disclosure hierarchy by placing the current reopen controls inside one collapsed Streamlit expander, and lock that contract with Streamlit AppTest coverage.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff, Hatchling wheel packaging, in-app Browser.

## Global Constraints

- Keep version exactly `0.1.16.dev0`; README continues to install verified release v0.1.15.
- Do not change `JsonReviewStore`, schemas, hydration, replacement protection, criteria confirmation, findings, resolutions, gates, persistence, or exports.
- Do not add dependencies, services, APIs, telemetry, billing, accounts, releases, comments, reviewer requests, or untrusted-code execution.
- Preserve every existing reopen success and error message.
- Treat screenshots as controlled local product evidence, not PR runtime or correctness evidence.

---

### Task 1: Collapsed Reopen Disclosure

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: existing Streamlit keys `reopen_review_id` and `reopen_review`, `JsonReviewStore.load(review_id: str)`, and `_hydrate_reopened_review(state: ReviewState) -> None`.
- Produces: one `st.expander("Reopen saved review", expanded=False)` containing the unchanged review-ID input, reopen button, and validated handler.

- [ ] **Step 1: Write the failing first-use disclosure test**

Add this test beside the existing first-use AppTests:

```python
def test_reopen_review_is_a_collapsed_secondary_path_before_start_review() -> None:
    app = new_app()

    assert [item.label for item in app.expander] == ["Reopen saved review"]
    assert app.text_input(key="reopen_review_id").value == ""
    assert app.button(key="reopen_review").disabled is True
    assert "### Reopen saved review" not in [item.value for item in app.markdown]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_reopen_review_is_a_collapsed_secondary_path_before_start_review -q
```

Expected: FAIL because no expander exists and the reopen form is rendered as a level-three Markdown heading.

- [ ] **Step 3: Wrap the existing reopen controls without changing the handler**

Replace the current `st.markdown("### Reopen saved review")` block with:

```python
with st.expander("Reopen saved review", expanded=False):
    reopen_id = st.text_input("Review ID", key="reopen_review_id")
    if st.button(
        "Reopen local review",
        key="reopen_review",
        disabled=not reopen_id.strip() or replacement_blocked,
    ):
        try:
            reopened_state = review_store.load(reopen_id.strip())
        except FileNotFoundError:
            st.error("No saved review was found for that review ID.")
        except UnsupportedRecordVersion:
            st.error("This saved review requires a different ScopeProof record version.")
        except (OSError, ValueError):
            st.error("The saved review could not be opened. Verify its ID and record integrity.")
        else:
            _hydrate_reopened_review(reopened_state)
            st.session_state["review_reopen_notice"] = (
                "Review reopened from local storage after validation."
            )
            st.rerun()
```

Keep `review_reopen_notice = ...` and its success message immediately after the expander.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the exact command from Step 2.

Expected: PASS.

The production call's explicit `expanded=False` contract and the packaged browser
capture together verify that the disclosure is initially collapsed; AppTest verifies
its stable label and contained controls without depending on an undocumented expander
state attribute.

- [ ] **Step 5: Run all Streamlit AppTests**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest tests/apps/test_streamlit_app.py -q
```

Expected: 53 tests pass with no failures.

- [ ] **Step 6: Commit the behavior and regression**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git diff --cached --check
git commit -m "improve first-use review hierarchy"
```

### Task 2: Source and Package Verification

**Files:**
- Verify: repository source and generated wheel under a fresh `/tmp/scopeproof-first-use-primary-*` directory.

**Interfaces:**
- Consumes: `pyproject.toml`, `scopeproof_core/version.py`, console scripts `scopeproof` and `scopeproof-web`.
- Produces: one clean-installed wheel and runtime evidence for the exact branch tree.

- [ ] **Step 1: Run source gates**

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.evals.runner
git diff main...HEAD --check
```

Expected: Ruff passes; 241 tests pass with 1 intentional skip; benchmark executes 12 cases and 13 criteria with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Build and clean-install one wheel**

```bash
package_dir=$(mktemp -d /tmp/scopeproof-first-use-primary-XXXXXX)
python3 -m pip wheel . --no-deps --wheel-dir "$package_dir/dist"
python3 -m venv "$package_dir/venv"
"$package_dir/venv/bin/python" -m pip install --upgrade pip
"$package_dir/venv/bin/python" -m pip install \
  "$package_dir/dist/scopeproof-0.1.16.dev0-py3-none-any.whl"
```

Expected: exactly one ScopeProof wheel is built and installed with declared dependencies.

- [ ] **Step 3: Verify installed identity and benchmark**

```bash
"$package_dir/venv/bin/python" -m pip check
"$package_dir/venv/bin/scopeproof" --version
"$package_dir/venv/bin/scopeproof-web" --version
"$package_dir/venv/bin/scopeproof" benchmark
```

Also assert distribution metadata, imported `__version__`, and a new `Review.tool_version` all equal `0.1.16.dev0`.

Expected: no broken requirements; both console versions and all three programmatic identities equal `0.1.16.dev0`; installed benchmark remains 12/13/0/0/0.

- [ ] **Step 4: Start the packaged app and require exact health**

Run `scopeproof-web` from the clean environment with temporary `HOME`, host `127.0.0.1`, and an unused local port. Require:

```text
GET /_stcore/health -> ok
```

### Task 3: Browser Evidence and Protected Integration

**Files:**
- Create audit evidence under `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.16dev0-continuation-audit/`.

**Interfaces:**
- Consumes: clean-installed packaged app and the current-run `01-start.png` reference.
- Produces: accepted after-state screenshot, DOM checks, audit notes, ready PR, and verified protected-main merge.

- [ ] **Step 1: Capture and inspect the after-state**

At the same default 1280 by 720 viewport, capture the initial page before any interaction. Require:

- one collapsed `Reopen saved review` disclosure before `1 · Start Review`;
- the offline demo button visible in the initial screenshot;
- Review ID and reopen button present when the disclosure is expanded;
- no changed sidebar stages or first-use copy;
- no current packaged-app console errors.

Inspect the saved screenshot and compare it in the same visual input with `01-start.png` before accepting it.

- [ ] **Step 2: Re-run the demo and reopen flows**

Load the deliberately constructed demo, confirm criteria, and run analysis. Save the review, copy its validated review ID, start a fresh app session, expand reopen, and reopen the saved record. Require the existing validated success copy, matching review ID, visible exports, and disabled re-analysis until source reload.

- [ ] **Step 3: Push and open a ready protected PR**

Push `codex/first-use-primary-path`. Open a ready PR describing the captured gap, unchanged lifecycle boundary, source/package/browser verification, and no-cost/no-notification constraints.

- [ ] **Step 4: Merge only after all checks pass**

Wait for required `verify`, ScopeProof evidence review, and CodeQL checks. Fix genuine failures with regression-first changes. Merge only when all checks pass.

- [ ] **Step 5: Verify merged main and clean up**

Wait for merged-main CI and CodeQL on the merge SHA. Fast-forward local `main`, require `HEAD == origin/main`, remove the owned worktree and merged branch, and verify:

- latest release remains v0.1.15;
- no open PRs;
- zero open Dependabot, CodeQL, and secret-scanning alerts;
- local main is clean.
