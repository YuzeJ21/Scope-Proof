# First-Use Demo Visibility Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the existing contract that the deliberately constructed demo entry is visible in
the initial 1280 by 720 workbench viewport without changing ScopeProof evidence or gate behavior.

**Architecture:** Reorder two existing Streamlit actions while retaining their keys, handlers, and
disablement rules. Add an AppTest tree-order contract so later presentation changes cannot silently
push the safe first-use action behind public-PR-only controls again.

**Tech Stack:** Python 3.11+, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Candidate evidence, implementation, tests, runtime observations, human acceptance, and external
  validation remain distinct.
- Do not change core evidence, gate, schema, persistence, export, or GitHub ingestion behavior.
- Do not add paid APIs, billing, accounts, private repositories, fork tests, outreach, telemetry,
  generic code review, security scanning, or automatic fixes.
- Preserve unrelated local files and worktrees.

---

### Task 1: Lock the first-use widget order with a failing AppTest

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `new_app() -> AppTest` and Streamlit widget keys `alpha_feedback_mode`, `load_demo`,
  `pr_url`, `candidate_paths`, `fetch_pr`, and `requirements_input`.
- Produces: `_main_widget_keys(app: AppTest) -> list[str]` and a regression proving the intended
  cross-widget order.

- [ ] **Step 1: Add a small recursive AppTest key helper**

Add after `evidence_matrix_table`:

```python
def _main_widget_keys(app: AppTest) -> list[str]:
    keys: list[str] = []

    def collect(node: object) -> None:
        key = getattr(node, "key", None)
        if isinstance(key, str):
            keys.append(key)
        children = getattr(node, "children", {})
        for child in children.values():
            collect(child)

    collect(app.main)
    return keys
```

- [ ] **Step 2: Add the failing ordering regression**

Add after `test_reopen_review_is_a_collapsed_secondary_path_before_start_review`:

```python
def test_first_use_demo_precedes_public_pr_inputs() -> None:
    app = new_app()
    keys = _main_widget_keys(app)

    assert keys.count("load_demo") == 1
    assert keys.index("alpha_feedback_mode") < keys.index("load_demo")
    assert keys.index("load_demo") < keys.index("pr_url")
    assert keys.index("candidate_paths") < keys.index("fetch_pr")
    assert keys.index("fetch_pr") < keys.index("requirements_input")
```

- [ ] **Step 3: Run the focused test and confirm RED**

Run:

```bash
uv run pytest tests/apps/test_streamlit_app.py::test_first_use_demo_precedes_public_pr_inputs -q
```

Expected: one assertion failure because `pr_url` currently appears before `load_demo`.

### Task 2: Move the existing demo action into the first-use viewport

**Files:**
- Modify: `apps/web/app.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: existing `replacement_blocked`, `alpha_feedback_mode`, `_record_reopened_source_reload`,
  `_reset_analysis`, `load_demo_labels`, and `load_demo_snapshot` behavior.
- Produces: the same `load_demo` and `fetch_pr` actions in a safer presentation order.

- [ ] **Step 1: Move the existing demo action after the alpha feedback toggle**

Immediately after the `alpha_feedback_mode = st.checkbox(...)` block, render the existing
`load_demo` button and keep its current handler unchanged:

```python
if st.button(
    "Load deliberately constructed demo",
    key="load_demo",
    disabled=replacement_blocked or alpha_feedback_mode,
):
    labels = load_demo_labels()
    snapshot = load_demo_snapshot()
    _record_reopened_source_reload(snapshot)
    st.session_state["snapshot"] = snapshot
    st.session_state["source_text"] = labels["source_text"]
    st.session_state["requirements_input"] = labels["source_text"]
    st.session_state["criteria"] = [
        Criterion.model_validate(item) for item in labels["criteria"]
    ]
    st.session_state["candidate_files"] = []
    st.session_state["comparison_base_bundle"] = None
    _reset_analysis()
    st.rerun()
```

Delete the old two-column `load_demo` block so the widget is rendered exactly once.

- [ ] **Step 2: Keep public-PR fetching after its inputs**

Replace the former two-column wrapper with the existing `fetch_pr` button as a direct full-width
button after `Advanced source options`. Preserve the current disabled expression, ingestion
handler, error recovery, and `use_container_width=True`.

- [ ] **Step 3: Document the user-visible correction**

Add this bullet under `CHANGELOG.md` → `Unreleased` → `Changed`:

```markdown
- Restored the safe first-use hierarchy so the deliberately constructed demo entry appears before
  public-PR-only inputs and remains visible in the initial desktop viewport.
```

- [ ] **Step 4: Run the focused test and relevant adjacent contracts**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_first_use_demo_precedes_public_pr_inputs \
  tests/apps/test_streamlit_app.py::test_standard_review_hides_alpha_research_fields \
  tests/apps/test_streamlit_app.py::test_alpha_mode_creates_case_after_confirming_criteria \
  tests/apps/test_streamlit_app.py::test_reopen_review_is_a_collapsed_secondary_path_before_start_review \
  -q
```

Expected: four passing tests.

### Task 3: Verify the complete engineering and product boundary

**Files:**
- Verify only: all changed files and package output.

**Interfaces:**
- Consumes: the completed presentation-only change.
- Produces: current verification evidence and accepted desktop/mobile screenshots.

- [ ] **Step 1: Run static, repository, and complete test verification**

Run:

```bash
uv run ruff check .
uv run pytest -q tests/test_repository_contracts.py
uv run pytest \
  --cov=scopeproof_core \
  --cov=apps \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 \
  -q
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
git diff --check
```

Expected: Ruff and repository contracts pass, the complete suite passes with at least 95 percent
coverage, both benchmarks report zero mismatches, and the diff check is clean.

- [ ] **Step 2: Build and verify the installed artifact**

Build an sdist and wheel, install the wheel into a clean temporary environment, then run:

```bash
scopeproof --version
scopeproof benchmark
scopeproof comparison-benchmark
scopeproof-web --version
```

Expected: package and CLI versions agree, both installed benchmarks pass, and the installed web
launcher responds successfully to its health endpoint.

- [ ] **Step 3: Capture the corrected desktop flow**

Start the worktree app, open a fresh 1280 by 720 in-app browser session, inspect the DOM, and save a
screenshot. Require exactly one `Load deliberately constructed demo` button with `top >= 0` and
`bottom <= 720`, no page-level horizontal overflow, and no console errors from ScopeProof code.

- [ ] **Step 4: Capture the corrected mobile flow**

Open a fresh 390 by 844 session, inspect and save the start screen, and require
`scrollWidth == clientWidth == 390`. Confirm the collapsed sidebar, Start Review path, demo action,
and public-PR field remain reachable without page-level horizontal overflow.

- [ ] **Step 5: Review the diff against product boundaries**

Inspect the complete diff for duplicate widget keys, altered evidence or gate behavior, unrelated
files, generated artifacts, secrets, paid-service references, notification-only files, and claims
of external validation. Fix any material finding and repeat affected checks.

- [ ] **Step 6: Commit the verified slice**

Stage only:

```text
apps/web/app.py
tests/apps/test_streamlit_app.py
CHANGELOG.md
docs/superpowers/specs/2026-07-18-first-use-demo-visibility-regression-design.md
docs/superpowers/plans/2026-07-18-first-use-demo-visibility-regression.md
```

Commit with:

```text
fix: restore first-use demo visibility
```

Do not push or open a pull request until the complete verification and review pass.
