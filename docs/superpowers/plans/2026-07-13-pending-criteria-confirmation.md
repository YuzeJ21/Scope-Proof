# Pending Criteria Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ScopeProof distinguish visible pending criterion edits from the last explicitly confirmed criteria before another analysis can run.

**Architecture:** Keep authoritative criteria, lifecycle revisions, and analysis bundles unchanged. Derive one transient Boolean in `apps/web/app.py` by comparing the validated editor output with the authoritative criteria list, then use it for warning copy, analysis readiness, and sidebar status.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff, Hatchling wheel packaging, in-app Browser.

## Global Constraints

- Keep version exactly `0.1.16.dev0`; README continues to install verified release v0.1.15.
- Do not change criteria parsing, `CriteriaRevision`, lifecycle history, evidence retrieval, findings, gates, final acceptance, runtime evidence, persistence, or exports.
- Keep prior confirmed analysis visible while criterion edits are pending.
- Do not add dependencies, CSS, JavaScript, APIs, telemetry, billing, accounts, releases, comments, reviewer requests, or untrusted-code execution.
- Browser captures are controlled local product evidence, not proof of pull-request correctness or external runtime acceptance.

---

### Task 1: Pending Criteria Readiness Contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: authoritative `criteria: list[Criterion]`, validated `edited_criteria: list[Criterion]`, existing `criteria_confirmed`, `bundle`, and `review_state` state.
- Produces: transient `criteria_edits_pending: bool`, warning copy, disabled analysis readiness, and truthful sidebar confirmation status.

- [ ] **Step 1: Write failing text-edit regression**

Add beside the existing confirmation and sidebar AppTests:

```python
def test_pending_criterion_text_edit_requires_reconfirmation_before_analysis() -> None:
    app = analyzed_demo(new_app())
    confirmed_text = app.session_state["criteria"][0].text

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Changed visible criterion"
    ).run()

    assert app.text_input(key="criterion_text_AC-01").value == "Changed visible criterion"
    assert app.session_state["criteria"][0].text == confirmed_text
    assert app.session_state["bundle"].criteria[0].text == confirmed_text
    assert app.button(key="run_analysis").disabled is True
    assert (
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    ) in [item.value for item in app.warning]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Confirm updated criteria" in sidebar_text
    assert "Complete — Criteria confirmed" not in sidebar_text

    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["criteria"][0].text == "Changed visible criterion"
    assert app.session_state["criteria_confirmed"] is True
    assert app.session_state["review_state"].bundle is None
    assert app.session_state["bundle"] is None
    assert app.button(key="run_analysis").disabled is False
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
```

- [ ] **Step 2: Write failing priority-edit regression**

```python
def test_pending_criterion_priority_edit_uses_same_confirmation_boundary() -> None:
    app = analyzed_demo(new_app())

    app = app.selectbox(key="criterion_priority_AC-01").set_value(
        Priority.SHOULD_HAVE
    ).run()

    assert app.session_state["criteria"][0].priority is Priority.MUST_HAVE
    assert app.session_state["bundle"].criteria[0].priority is Priority.MUST_HAVE
    assert app.button(key="run_analysis").disabled is True
    assert "Next — Confirm updated criteria" in "\n".join(
        item.value for item in app.sidebar.markdown
    )
```

- [ ] **Step 3: Run both tests and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_pending_criterion_text_edit_requires_reconfirmation_before_analysis \
  tests/apps/test_streamlit_app.py::test_pending_criterion_priority_edit_uses_same_confirmation_boundary -q
```

Expected: both fail because analysis remains enabled, no pending-edit warning exists, and the sidebar still claims criteria are confirmed.

- [ ] **Step 4: Derive the pending state and apply it to readiness**

Initialize the editor values before the criteria branch:

```python
edited_criteria = criteria
criteria_edits_pending = False
```

After building and validating `edited_criteria`, derive:

```python
criteria_edits_pending = edited_criteria != criteria
```

After the existing `Confirm criteria` handler updates authoritative state, set:

```python
criteria_edits_pending = False
```

Replace the current confirmation message branch with:

```python
if criteria_edits_pending:
    st.warning(
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    )
elif st.session_state["criteria_confirmed"]:
    st.success("Criteria confirmed by the reviewer.")
else:
    st.caption("Analysis remains locked until the criterion set is explicitly confirmed.")
```

Extend the existing analysis readiness expression with:

```python
and not criteria_edits_pending
```

Derive sidebar confirmation truth with:

```python
criteria_are_confirmed = (
    st.session_state["criteria_confirmed"] and not criteria_edits_pending
)
```

Render its confirmation line with:

```python
st.markdown(
    "Next — Confirm updated criteria"
    if criteria_edits_pending
    else (
        "Complete — Criteria confirmed"
        if criteria_are_confirmed
        else ("Next — Confirm criteria" if has_criteria else "Locked — Confirm criteria")
    )
)
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the exact command from Step 3, then:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest tests/apps/test_streamlit_app.py -q
```

Expected: both new regressions pass and 55 Streamlit AppTests pass.

- [ ] **Step 6: Commit the behavior and regressions**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git diff --cached --check
git commit -m "clarify pending criteria confirmation"
```

### Task 2: Source and Package Verification

**Files:**
- Verify: repository source and a generated wheel under a fresh `/tmp/scopeproof-pending-criteria-*` directory.

**Interfaces:**
- Consumes: branch source, `pyproject.toml`, console scripts `scopeproof` and `scopeproof-web`.
- Produces: full source-gate evidence and one clean-installed `0.1.16.dev0` wheel.

- [ ] **Step 1: Run source gates**

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.evals.runner
git diff main...HEAD --check
```

Expected: Ruff passes; 243 tests pass with 1 intentional skip; the benchmark executes 12 cases and 13 criteria with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Build and clean-install the wheel**

```bash
package_dir=$(mktemp -d /tmp/scopeproof-pending-criteria-XXXXXX)
python3 -m pip wheel . --no-deps --wheel-dir "$package_dir/dist"
python3 -m venv "$package_dir/venv"
"$package_dir/venv/bin/python" -m pip install \
  "$package_dir/dist/scopeproof-0.1.16.dev0-py3-none-any.whl"
```

Expected: exactly one ScopeProof wheel builds and installs with declared dependencies.

- [ ] **Step 3: Verify installed identity, requirements, benchmark, and health**

Require `pip check`, both console `--version` commands, distribution metadata, imported
`__version__`, and a new `Review.tool_version` to equal `0.1.16.dev0`. Run the installed benchmark
and require 12/13/0/0/0. Start the packaged app with temporary `HOME`, host `127.0.0.1`, and an
unused local port; require exact `GET /_stcore/health -> ok`.

### Task 3: Browser Evidence and Protected Integration

**Files:**
- Create: audit evidence under `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-pending-criteria-confirmation/`.

**Interfaces:**
- Consumes: clean-installed packaged branch app and current-run mismatch captures `04-pending-criteria-mismatch.png` plus `05-stale-analysis-after-pending-edit.png`.
- Produces: accepted after-state captures, audit notes, ready PR, and verified protected-main merge.

- [ ] **Step 1: Verify the packaged pending-edit boundary**

Use the deliberately constructed demo only to confirm criteria and run deterministic analysis. Edit
AC-01 without confirming it. Require the pending warning, disabled analysis action, sidebar next
action, prior confirmed requirement in the evidence matrix, and no packaged-app console errors.
Capture the edited criterion and matrix states at the same 1280 by 720 viewport.

- [ ] **Step 2: Confirm and rerun**

Confirm the edited set. Require the warning to clear, the sidebar to show confirmed criteria and
`Next — Run deterministic analysis`, and prior analysis to disappear. Rerun analysis and require the
matrix and criterion detail to display the updated criterion. Do not record runtime evidence, a
human resolution, or final acceptance.

- [ ] **Step 3: Compare and document**

Inspect before/after images together. Document strengths, the resolved trust gap, accessibility
benefit from explicit state text, and limits: screenshots do not establish keyboard, screen-reader,
responsive, or external-PR correctness evidence.

- [ ] **Step 4: Integrate through protected main**

Push `codex/pending-criteria-confirmation`, open a ready PR, and wait for required `verify`,
ScopeProof evidence review, and CodeQL. Merge only when all checks pass. Then require merged-main CI
and CodeQL success on the merge SHA, fast-forward local `main`, remove the owned worktree and merged
branch, and verify no open PRs or security alerts, latest release remains v0.1.15, and local main is
clean.
