# Runtime-Evidence Required Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every manual runtime-evidence field identify its required or optional status in its visible and accessible label without changing runtime-evidence, final-acceptance, or gate semantics.

**Architecture:** Keep the improvement entirely in the existing Streamlit presentation layer. Update six supported widget labels while preserving their stable keys, values, readiness calculation, Pydantic construction, lifecycle mutation path, and final-acceptance boundary.

**Tech Stack:** Python 3.12, Streamlit 1.59, Streamlit AppTest, Pydantic 2, pytest, Ruff, Hatchling.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Every verdict must cite explicit evidence or state what evidence is missing.
- Implementation evidence must never be presented as test or runtime verification.
- Users must confirm normalized acceptance criteria before analysis.
- Never execute untrusted repository code in the application server.
- Validate every persisted or exported object with Pydantic schemas.
- Keep gate decisions deterministic and reproducible; False Ready is more harmful than False Blocked.
- Do not change runtime-evidence, criterion-resolution, final-acceptance, gate, export, storage, or record-version semantics.
- Do not add billing, paid services, paid APIs, OpenAI/LLM APIs, organizations, accounts, private repositories, forks, telemetry, dependencies, synthetic validation, or invented evidence.
- Do not publish a release for this presentation-only improvement.

---

### Task 1: Implement runtime-field status labels with TDD

**Files:**
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `analyzed_demo(new_app())`, the six existing stable widget keys, and the existing final-acceptance caption.
- Produces: `test_runtime_evidence_fields_identify_required_and_optional_status()` plus six exact visible and accessible labels while returning the same widget values to the unchanged readiness and Pydantic paths.

- [ ] **Step 1: Add the failing label contract test**

Add this test immediately after `test_runtime_evidence_save_requires_all_required_fields`:

```python
def test_runtime_evidence_fields_identify_required_and_optional_status() -> None:
    app = analyzed_demo(new_app())

    assert app.text_input(key="runtime_artifact_reference").label == (
        "Artifact or URL (required)"
    )
    assert app.text_area(key="runtime_scenario").label == "Runtime scenario (required)"
    assert app.text_input(key="runtime_environment").label == "Environment (required)"
    assert app.text_input(key="runtime_result").label == "Observed result (required)"
    assert app.text_input(key="runtime_reviewer").label == "Runtime reviewer (required)"
    assert app.text_area(key="runtime_limitations").label == (
        "Runtime limitations (optional)"
    )
    assert app.button(key="save_runtime_evidence").disabled is True
    assert (
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    ) in [caption.value for caption in app.caption]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_fields_identify_required_and_optional_status -q
```

Expected: FAIL because the first label is still `Artifact or URL` rather than `Artifact or URL (required)`.

- [ ] **Step 3: Update only the six labels**

Replace the current input declarations with:

```python
runtime_artifact = st.text_input(
    "Artifact or URL (required)", key="runtime_artifact_reference"
)
runtime_scenario = st.text_area(
    "Runtime scenario (required)", key="runtime_scenario"
)
runtime_environment = st.text_input(
    "Environment (required)", key="runtime_environment"
)
runtime_result = st.text_input(
    "Observed result (required)", key="runtime_result"
)
runtime_reviewer = st.text_input(
    "Runtime reviewer (required)", key="runtime_reviewer"
)
runtime_limitations = st.text_area(
    "Runtime limitations (optional)", key="runtime_limitations"
)
```

Do not change widget keys, readiness logic, exception handling, evidence level choices, runtime record construction, or the existing caption.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_fields_identify_required_and_optional_status -q
```

Expected: `1 passed`.

- [ ] **Step 5: Run the adjacent runtime and acceptance regressions**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py -k 'runtime_evidence or final_acceptance' -q
```

Expected: all selected tests pass, with unrelated tests deselected.

- [ ] **Step 6: Commit the tested slice**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: label runtime evidence requirements"
```

### Task 2: Verify source, package, and rendered behavior

**Files:**
- Verify: `apps/web/app.py`
- Verify: `tests/apps/test_streamlit_app.py`
- Verify: `docs/superpowers/specs/2026-07-14-runtime-evidence-required-labels-design.md`
- Verify: `docs/superpowers/plans/2026-07-14-runtime-evidence-required-labels.md`

**Interfaces:**
- Consumes: the complete branch, repository test and benchmark entry points, Hatch wheel configuration, and the trusted local Streamlit demo.
- Produces: independent source, package, health, and visual evidence for protected integration.

- [ ] **Step 1: Run source verification**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m ruff check .
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest -q
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m scopeproof_core.evals.runner
git diff origin/main...HEAD --check
```

Expected: Ruff passes; the complete suite passes with only the intentional live GitHub skip; the benchmark executes 12 cases and 13 criteria with zero mismatches, zero must-have False Ready, and zero false blockers; the diff check is clean.

- [ ] **Step 2: Build and clean-install the wheel**

Create a fresh directory under `/tmp`, build one wheel with `python -m pip wheel . --no-deps`, create a new virtual environment, and install the wheel plus its declared dependencies. Then require:

```bash
python -m pip check
scopeproof --version
scopeproof-web --version
scopeproof benchmark
```

Expected: dependency consistency; all version identities equal the current development version; the installed benchmark reports the same 12 cases, 13 criteria, and zero release-gate failures.

- [ ] **Step 3: Verify exact installed workbench health**

Start the clean-installed `scopeproof-web` on an unused loopback port with a fresh temporary `HOME`. Require `/_stcore/health` to return exactly `ok`, then stop the process cleanly.

- [ ] **Step 4: Compare the rendered form without recording evidence**

Start the branch workbench against a fresh temporary `HOME`, load the deliberately constructed demo, confirm criteria, and run deterministic analysis. Capture the same viewport and require:

- all five required labels visibly end in `(required)`;
- limitations visibly ends in `(optional)`;
- empty Save remains disabled;
- the final-acceptance boundary copy and enabled first acceptance action remain unchanged;
- no runtime evidence, resolution, final acceptance, or saved review is submitted.

Use DOM inspection to require the six exact accessible names. Treat screenshots as product evidence only, not complete accessibility, runtime-evidence, or adoption proof.

- [ ] **Step 5: Review branch scope**

Run:

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: only the design, plan, focused AppTest, and six label strings changed.

### Task 3: Integrate through the protected repository workflow

**Files:**
- Verify: complete branch and GitHub pull request state.

**Interfaces:**
- Consumes: reviewed local commits and all verification evidence from Task 2.
- Produces: one protected pull request, a green exact merge SHA on `main`, synchronized local main, and removed branch/worktree state.

- [ ] **Step 1: Obtain an independent scope and correctness review**

Require no Critical or Important findings. Fix every genuine finding using a failing regression first when behavior changes, then rerun the full Task 2 verification.

- [ ] **Step 2: Push one branch and open one ready pull request**

Push `codex/runtime-field-requiredness` and open a ready PR. Do not create issue comments, release announcements, or routine status comments.

- [ ] **Step 3: Wait for every protected check**

Require both push and pull-request `verify`, both CodeQL analyses, the CodeQL aggregate check, and the ScopeProof evidence review to succeed on the exact branch head SHA. Inspect and fix genuine failures; do not bypass protection.

- [ ] **Step 4: Merge and verify exact main state**

Squash-merge only after all checks pass. Require main `verify` and both CodeQL analyses to succeed on the exact merge SHA. Confirm no new Dependabot, CodeQL, or secret-scanning alert was introduced.

- [ ] **Step 5: Synchronize and clean up**

Fast-forward local `main` to `origin/main`, remove the owned worktree and local feature branch, confirm the remote feature branch is deleted, and require a clean synchronized checkout before selecting the next evidence-backed gap.
