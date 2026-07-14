# Runtime-Evidence Prerequisite Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tell users exactly which required runtime-evidence fields still prevent Save without changing evidence, gate, or final-acceptance semantics.

**Architecture:** Derive one ordered `missing_runtime_fields` list from the five current widget values in the Streamlit presentation layer. Use that same list for neutral prerequisite guidance and the existing Save disabled state; retain Pydantic validation as defense in depth.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic v2, pytest, Ruff.

## Global Constraints

- Final acceptance remains an independently recordable append-only review event.
- Final acceptance must not resolve criteria or override deterministic gate precedence.
- Runtime evidence remains human supplied, append only, and separate from static findings and criterion resolution.
- Never execute PR code or represent controlled UI fixtures as external runtime evidence.
- Do not change schemas, lifecycle, gates, persistence, exporters, GitHub workflows, or package version.
- No billing, paid APIs, LLM APIs, organizations, second accounts, private repositories, forks, synthetic validation, comments, issue updates, or release.

---

### Task 1: Lock the missing-field recovery contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: Streamlit widget keys `runtime_artifact_reference`, `runtime_scenario`, `runtime_environment`, `runtime_result`, `runtime_reviewer`, and `save_runtime_evidence`.
- Produces: AppTest assertions for one ordered caption beginning `Complete required fields to enable Save:`.

- [ ] **Step 1: Add the initial and partial-state failing test**

```python
def test_runtime_evidence_guidance_lists_only_missing_required_fields() -> None:
    app = analyzed_demo(new_app())

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Artifact or URL, Runtime scenario, "
        "Environment, Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True
```

- [ ] **Step 2: Add the whitespace and complete-state failing test**

```python
def test_runtime_evidence_guidance_disappears_when_save_is_ready() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save: Artifact or URL." in guidance
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save:" not in guidance
    assert app.button(key="save_runtime_evidence").disabled is False
```

- [ ] **Step 3: Run both tests and verify RED**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_guidance_lists_only_missing_required_fields \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_guidance_disappears_when_save_is_ready -q
```

Expected: both tests fail because no caption begins `Complete required fields to enable Save:`.

### Task 2: Render deterministic prerequisite guidance

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: the five required runtime widget values as `str`.
- Produces: `missing_runtime_fields: list[str]` and `runtime_evidence_ready: bool`.

- [ ] **Step 1: Replace the duplicated readiness tuple with named field pairs**

Replace the existing `runtime_evidence_ready = all(...)` block with:

```python
    required_runtime_fields = (
        ("Artifact or URL", runtime_artifact),
        ("Runtime scenario", runtime_scenario),
        ("Environment", runtime_environment),
        ("Observed result", runtime_result),
        ("Runtime reviewer", runtime_reviewer),
    )
    missing_runtime_fields = [
        label for label, value in required_runtime_fields if not value.strip()
    ]
    runtime_evidence_ready = not missing_runtime_fields
    if missing_runtime_fields:
        st.caption(
            "Complete required fields to enable Save: "
            + ", ".join(missing_runtime_fields)
            + "."
        )
```

Keep the existing Save button declaration and `disabled=not runtime_evidence_ready` unchanged.

- [ ] **Step 2: Run focused GREEN verification**

Run:

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_guidance_lists_only_missing_required_fields \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_guidance_disappears_when_save_is_ready \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_save_requires_all_required_fields \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_fields_identify_required_and_optional_status \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_prerequisite_guidance_is_visible \
  tests/apps/test_streamlit_app.py::test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat \
  tests/apps/test_streamlit_app.py::test_final_acceptance_is_labeled_as_review_level_without_overriding_gate -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check \
  apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: seven tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 3: Commit the bounded implementation**

```bash
git diff --check
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "clarify runtime evidence prerequisites"
```

Expected: one intentional implementation commit with no schema, lifecycle, gate, or final-acceptance changes.

### Task 3: Verify and publish through protected main

**Files:**
- Verify: all repository source, tests, benchmark fixtures, package contents, and the local Streamlit workbench.

**Interfaces:**
- Consumes: the committed presentation-only change.
- Produces: full local, package, runtime, independent-review, PR, and exact merged-main evidence.

- [ ] **Step 1: Run repository-wide verification**

```bash
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m ruff check .
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m pytest -q
/Users/yjian070/Documents/New\ project\ 2/.venv/bin/python -m scopeproof_core.evals.runner
git diff --check
```

Expected: Ruff passes; all offline tests pass except the intentional live skip; all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Verify clean packaging and local runtime**

Build a fresh wheel under `/tmp/scopeproof-runtime-guidance-wheel`, install it with dependencies into `/tmp/scopeproof-runtime-guidance-venv`, require `pip check`, exact `scopeproof 0.1.18.dev0`, and an installed 12-case benchmark with the same zero-error metrics. Start installed `scopeproof-web` on `127.0.0.1:8515` with a fresh temporary HOME and require `/_stcore/health` to return exactly `ok`.

- [ ] **Step 3: Inspect the real branch workbench safely**

Reach the analyzed deliberately constructed demo in the local workbench and verify the initial empty form shows the ordered missing-field caption and disabled Save action. Populate fields only if necessary to inspect readiness, but do not click Save, record a resolution, or record final acceptance. Treat this as controlled product evidence only.

- [ ] **Step 4: Obtain independent review and protected integration**

Review the exact base-to-head commit range. Push `codex/runtime-evidence-prerequisite-guidance`, create one ready PR with verification evidence, add no comments or release, require both `verify` runs and CodeQL Python/Actions success, squash merge, then require exact merged-main CI and CodeQL success.

- [ ] **Step 5: Synchronize and continue**

Fast-forward local main to the exact merge SHA, remove the owned `.worktrees/runtime-evidence-prerequisite-guidance` worktree, prune the local and remote feature branch, confirm a clean single-worktree checkout, and immediately begin the next evidence-backed goal loop.
