# Runtime-Evidence Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent incomplete manual runtime-evidence submissions and replace raw model-validation output with clear reviewer guidance.

**Architecture:** Keep readiness in the Streamlit presentation layer and persistence validation in the existing Pydantic model. The UI derives one Boolean from the five required text widgets, disables submission until it is true, and continues to append through the unchanged core lifecycle service.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- Runtime evidence remains human supplied, append-only, and restricted to E3 or E4.
- Runtime evidence must not change static findings or deterministic gate truth.
- Limitations remain optional; artifact reference, scenario, environment, observed result, and reviewer are required.
- Final acceptance, resolution events, gate evaluation, exports, and persisted schemas remain unchanged.
- Never execute PR code or represent fixtures as external runtime evidence.

---

### Task 1: Make runtime-evidence submission prerequisites explicit

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: Streamlit widget values `runtime_artifact_reference`, `runtime_scenario`, `runtime_environment`, `runtime_result`, and `runtime_reviewer`.
- Produces: a presentation-only `runtime_evidence_ready: bool` and the existing `save_runtime_evidence` button with deterministic disabled state.

- [ ] **Step 1: Write failing AppTests for empty, whitespace-only, and complete inputs**

Add a helper beside `load_demo`:

```python
def analyzed_demo(app: AppTest) -> AppTest:
    app = load_demo(app)
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()
```

Add these tests before the existing complete runtime-evidence test:

```python
def test_runtime_evidence_save_requires_all_required_fields() -> None:
    app = analyzed_demo(new_app())
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_prerequisite_guidance_is_visible() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)
    assert "Artifact, scenario, environment, observed result, and reviewer are required" in caption_text
    assert "Limitations are optional" in caption_text
```

- [ ] **Step 2: Run the new tests and confirm the existing UI fails the contract**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_save_requires_all_required_fields \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_prerequisite_guidance_is_visible -q
```

Expected: FAIL because the empty save button is enabled and the prerequisite caption is absent.

- [ ] **Step 3: Implement presentation readiness and friendly fallback handling**

After the runtime evidence-level selector in `apps/web/app.py`, add:

```python
    st.caption(
        "Artifact, scenario, environment, observed result, and reviewer are required. "
        "Limitations are optional."
    )
    runtime_evidence_ready = all(
        value.strip()
        for value in (
            runtime_artifact,
            runtime_scenario,
            runtime_environment,
            runtime_result,
            runtime_reviewer,
        )
    )
```

Change the button declaration to:

```python
    if st.button(
        "Save manual runtime evidence",
        key="save_runtime_evidence",
        disabled=not runtime_evidence_ready,
    ):
```

Keep Pydantic construction and `append_runtime_evidence` unchanged. Replace only the raw exception rendering:

```python
            except ValueError:
                st.error(
                    "Runtime evidence could not be saved. Check every required field and "
                    "select E3 or E4."
                )
```

- [ ] **Step 4: Run focused runtime-evidence and lifecycle regressions**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py \
  tests/reviews/test_lifecycle.py \
  tests/schemas/test_runtime_evidence.py -q
```

Expected: all selected tests pass; the existing complete-record test still proves append behavior and unchanged static findings.

- [ ] **Step 5: Run Ruff on the changed Python files**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: `All checks passed!`

- [ ] **Step 6: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: require complete runtime evidence input"
```

### Task 2: Verify the complete product and real local UI state

**Files:**
- Verify only: repository-wide source, tests, benchmark fixtures, and installed Streamlit app.

**Interfaces:**
- Consumes: committed implementation from Task 1.
- Produces: deterministic regression evidence plus local runtime evidence that the actual Streamlit server renders the changed UI.

- [ ] **Step 1: Run repository-wide static and regression gates**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; 181 or more tests pass with only the intentional live GitHub test skipped; all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Start the real Streamlit server on an unused loopback port**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m streamlit run apps/web/app.py \
  --server.headless true --server.address 127.0.0.1 --server.port 8513
```

Expected: `http://127.0.0.1:8513/_stcore/health` returns `ok`.

- [ ] **Step 3: Inspect the rendered workflow without recording synthetic evidence**

Use the deterministic demo only to reach the post-analysis screen. Confirm that the prerequisite caption is visible and the empty runtime-evidence save control is disabled. Fill the five required widgets only to confirm the control becomes enabled; do not click it and do not record final acceptance or a human resolution.

Expected: rendered behavior matches the AppTest contract and no runtime evidence or lifecycle event is persisted.

- [ ] **Step 4: Confirm branch hygiene**

Run:

```bash
git status --short --branch
git log --oneline --decorate -3
```

Expected: clean `codex/runtime-evidence-readiness` with the design and implementation commits ahead of `main`.
