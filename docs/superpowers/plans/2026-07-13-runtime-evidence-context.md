# Runtime-Evidence Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the manual runtime-evidence form identify its target criterion and explain the existing E3/E4 and final-acceptance boundaries.

**Architecture:** Add two presentation-only captions in `apps/web/app.py`, derived from the already selected criterion and the accepted evidence-level contract. Keep all enum values, Pydantic schemas, lifecycle services, persisted data, gates, and exports unchanged.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Never execute pull-request code or infer runtime evidence.
- Keep `RuntimeEvidence` restricted to its existing E3/E4 contract.
- Do not change findings, human resolutions, final acceptance, gate evaluation, exports, or storage.
- Use this exact target copy: `This record will be attached to {criterion_id} — {criterion_text}.`
- Use this exact boundary copy: `E3 means manually recorded external runtime verification. E4 means explicit human acceptance. Saving this record does not resolve the criterion or record final review acceptance.`
- Test fixtures are UI regression inputs, not external validation evidence.

---

### Task 1: Expose Runtime-Evidence Target and Level Boundaries

**Files:**
- Modify: `tests/apps/test_streamlit_app.py:657-685`
- Modify: `apps/web/app.py:592-615`

**Interfaces:**
- Consumes: `selected_id: str`, `selected_criterion: Criterion`, and the existing `EvidenceLevel.E3`/`EvidenceLevel.E4` selectbox.
- Produces: two always-visible Streamlit captions; no new public API, schema field, or persisted state.

- [ ] **Step 1: Write the failing AppTest regression**

Add this test after `test_runtime_evidence_prerequisite_guidance_is_visible`:

```python
def test_runtime_evidence_context_identifies_criterion_and_explains_levels() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)

    assert (
        "This record will be attached to AC-01 — User can export the research list as CSV."
        in caption_text
    )
    assert (
        "E3 means manually recorded external runtime verification. "
        "E4 means explicit human acceptance. Saving this record does not resolve the criterion "
        "or record final review acceptance."
    ) in caption_text

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    target_captions = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("This record will be attached to")
    ]
    assert target_captions == [
        "This record will be attached to AC-03 — Failed export shows an error message."
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_runtime_evidence_context_identifies_criterion_and_explains_levels \
  -q
```

Expected: fail because the target and evidence-level captions are absent.

- [ ] **Step 3: Add the selected-criterion caption**

Immediately after `st.markdown("### Manual runtime evidence")`, add:

```python
    st.caption(
        f"This record will be attached to {selected_id} — {selected_criterion.text}."
    )
```

Keep the existing human-supplied-observation caption immediately after it.

- [ ] **Step 4: Add the evidence-level boundary caption**

Immediately after the `runtime_evidence_level` selectbox, add:

```python
    st.caption(
        "E3 means manually recorded external runtime verification. "
        "E4 means explicit human acceptance. Saving this record does not resolve the "
        "criterion or record final review acceptance."
    )
```

Keep the existing required-field caption immediately after it.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py \
  -q \
  -k 'runtime_evidence_context or runtime_evidence_save or runtime_evidence_prerequisite or manual_runtime_evidence'
'../../.venv/bin/python' -m ruff check apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: the new context test and existing readiness, reset, and unchanged-findings regressions pass; Ruff reports no errors.

- [ ] **Step 6: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git diff --cached --check
git commit -m "clarify runtime evidence context"
```

- [ ] **Step 7: Run complete verification**

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.evals.runner
git diff origin/main...HEAD --check
```

Expected: Ruff passes; the complete offline suite passes with only the documented skip; all 12 benchmark cases execute with zero mismatches, zero must-have False Ready, and zero False Blocker; diff check is clean.

- [ ] **Step 8: Verify packaging and live behavior**

Build a fresh `0.1.15.dev0` wheel, install it in a clean temporary virtual environment, run the installed benchmark, verify `scopeproof-web --version`, and require the packaged workbench health endpoint to return exactly `ok`.

Start the branch workbench with a temporary `HOME`. Use the deliberately constructed demo only to reach the analyzed state. Capture and inspect the same viewport as the current audit and require:

1. `AC-01` and its criterion text appear as the runtime-evidence target;
2. the E3 and E4 meanings are visible without opening the selectbox;
3. the final-acceptance boundary is visible;
4. changing `Inspect criterion` to `AC-03` updates the target caption;
5. the empty save action remains disabled.

Do not submit any fixture record, human resolution, or final acceptance.

- [ ] **Step 9: Publish through protected main**

Push `codex/runtime-evidence-context`, open a pull request without reviewers or comments, wait for required `verify` and CodeQL checks, merge only when green, verify merged-main CI and CodeQL, fast-forward local `main`, and remove the worktree and feature branches. Do not publish a release for this presentation-only clarification.
