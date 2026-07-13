# Criterion-Resolution Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the criterion-level human-decision controls a semantic heading and an explicit selected-criterion/final-acceptance boundary.

**Architecture:** Add one heading and one caption in the Streamlit presentation layer using `selected_id` and `selected_criterion.text`. Preserve the existing decision options, impact guidance, append-only lifecycle, reset behavior, gate evaluator, persistence, and exports.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, pytest, Ruff.

## Global Constraints

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Never execute pull-request code or infer reviewer decisions.
- Use this exact heading: `Criterion resolution`.
- Use this exact target copy: `This decision will be recorded for {criterion_id} — {criterion_text}. It does not record final review acceptance.`
- Preserve every existing `HumanDecision`, dynamic decision-impact message, event, history, final-acceptance, and gate behavior.
- Test fixtures are UI regression inputs, not real reviewer evidence.

---

### Task 1: Add Criterion-Resolution Hierarchy and Scope

**Files:**
- Modify: `tests/apps/test_streamlit_app.py:550-590`
- Modify: `apps/web/app.py:670-690`

**Interfaces:**
- Consumes: `selected_id: str`, `selected_criterion: Criterion`, and the existing resolution controls.
- Produces: a semantic Streamlit heading and one derived caption; no public API, schema field, persisted state, or core behavior.

- [ ] **Step 1: Write the failing AppTest regression**

Add this test after `test_successful_manual_verification_clears_conditional_evidence_level`:

```python
def test_criterion_resolution_context_identifies_target_and_boundary() -> None:
    app = analyzed_demo(new_app())
    markdown_text = "\n".join(markdown.value for markdown in app.markdown)
    caption_text = "\n".join(caption.value for caption in app.caption)

    assert "Criterion resolution" in markdown_text
    assert (
        "This decision will be recorded for AC-01 — User can export the research list as CSV. "
        "It does not record final review acceptance."
    ) in caption_text
    assert "Select a decision to see its deterministic gate impact." in caption_text

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    target_captions = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("This decision will be recorded for")
    ]
    assert target_captions == [
        "This decision will be recorded for AC-03 — Failed export shows an error message. "
        "It does not record final review acceptance."
    ]
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
'../../.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py::test_criterion_resolution_context_identifies_target_and_boundary \
  -q
```

Expected: fail because the criterion-resolution heading and target caption are absent.

- [ ] **Step 3: Add the presentation context**

After the resolution reset marker and notice have been consumed, and immediately before
`decision_options`, add:

```python
    st.markdown("### Criterion resolution")
    st.caption(
        f"This decision will be recorded for {selected_id} — {selected_criterion.text}. "
        "It does not record final review acceptance."
    )
```

Do not change the `Human decision` selectbox, `decision_guidance`, reviewer note, save action,
reset marker, success notice, history, or final-acceptance section.

- [ ] **Step 4: Run focused tests and verify GREEN**

```bash
'../../.venv/bin/python' -m pytest \
  tests/apps/test_streamlit_app.py \
  -q \
  -k 'criterion_resolution_context or decision_impact or resolution_save or manual_verification or final_acceptance'
'../../.venv/bin/python' -m ruff check apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: the new context regression and existing decision-impact, reset, manual-verification, and
final-acceptance regressions pass; Ruff reports no errors.

- [ ] **Step 5: Commit the implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git diff --cached --check
git commit -m "clarify criterion resolution context"
```

- [ ] **Step 6: Run complete verification**

```bash
'../../.venv/bin/python' -m ruff check .
'../../.venv/bin/python' -m pytest -q
'../../.venv/bin/python' -m scopeproof_core.evals.runner
git diff origin/main...HEAD --check
```

Expected: Ruff passes; the complete offline suite passes with only the documented skip; all 12
benchmark cases execute with zero mismatches, zero must-have False Ready, and zero False Blocker;
diff check is clean.

- [ ] **Step 7: Verify packaging and live behavior**

Build and clean-install a fresh `0.1.15.dev0` wheel, run the installed benchmark, verify
`scopeproof-web --version`, and require the packaged workbench health endpoint to return exactly
`ok`.

Start the branch workbench with a temporary `HOME`. Use the deliberately constructed demo only to
reach the analyzed state. Capture and inspect the same viewport as the current audit and require:

1. `Criterion resolution` separates the human decision from runtime evidence and final acceptance;
2. the AC-01 target and final-acceptance boundary are visible;
3. the neutral decision-impact guidance remains visible;
4. changing `Inspect criterion` to AC-03 updates the target caption;
5. `Save resolution` remains disabled until a decision is selected.

Do not submit a runtime record, human decision, or final acceptance.

- [ ] **Step 8: Publish through protected main**

Push `codex/criterion-resolution-context`, open a pull request without reviewers or comments, wait
for required `verify` and CodeQL checks, merge only when green, verify merged-main CI and CodeQL,
fast-forward local `main`, and remove the worktree and feature branches. Do not publish a release
for this presentation-only clarification.
