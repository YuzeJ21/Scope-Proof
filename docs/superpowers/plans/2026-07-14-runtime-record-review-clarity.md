# Runtime Record Review Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show the complete validated manual runtime-evidence record in the criterion-detail workbench, including reviewer and limitations.

**Architecture:** Keep `RuntimeEvidence`, lifecycle, persistence, exporters, findings, resolutions, final acceptance, and gates unchanged. Replace the presentation-only compact runtime row in `apps/web/app.py` with one bordered container per record and lock the visible contract with Streamlit AppTests.

**Tech Stack:** Python 3.12, Streamlit, Pydantic v2, pytest, Streamlit AppTest, Ruff.

## Global Constraints

- Runtime evidence remains human-supplied, append-only, and unable to change static findings or gate truth.
- Do not execute PR code or claim controlled fixtures as external runtime verification.
- Preserve safe artifact-reference rendering through `render_artifact_reference_markdown()`.
- Preserve runtime-record order and limitation order.
- Keep final acceptance and criterion resolution behavior unchanged.
- Add no dependency, API, billing, telemetry, schema, persistence, or export change.

---

### Task 1: Lock the complete runtime-record display contract

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `ReviewBundle.runtime_evidence: list[RuntimeEvidence]` and `render_artifact_reference_markdown(value: str) -> str`.
- Produces: visible runtime-record containers with labels `Environment`, `Observed result`, `Evidence level`, `Reviewer`, and `Limitations`.

- [ ] **Step 1: Write the failing reviewer-and-limitations test**

Extend the controlled runtime-evidence AppTest to save a record with two limitations,
then require the visible workbench output to contain the reviewer and both limitations
alongside the existing artifact, scenario, environment, result, and E3 level.

- [ ] **Step 2: Write the failing empty-limitations test**

Save a complete runtime record with no limitations and require the visible copy
`No limitations recorded.`

- [ ] **Step 3: Run the focused tests to verify RED**

Run:

```bash
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/pytest' -q \
  tests/apps/test_streamlit_app.py -k 'runtime_artifact_identifier or runtime_record_shows'
```

Expected: the new tests fail because reviewer, limitations, and the explicit empty
state are absent from the current compact row.

- [ ] **Step 4: Implement the minimal presentation correction**

In the existing `for item in selected_runtime` loop, preserve the safe artifact helper
and render one `st.container(border=True)` per record. Show:

```python
st.markdown(f"{artifact_reference} — {item.scenario}")
st.markdown(f"**Environment:** {item.environment}")
st.markdown(f"**Observed result:** {item.result}")
st.markdown(f"**Evidence level:** {item.evidence_level.value}")
st.markdown(f"**Reviewer:** {item.reviewer}")
st.markdown("**Limitations**")
if item.limitations:
    for limitation in item.limitations:
        st.markdown(f"- {limitation}")
else:
    st.caption("No limitations recorded.")
```

- [ ] **Step 5: Run focused and adjacent tests to verify GREEN**

Run the two new tests plus runtime evidence rendering, save-reset, validation recovery,
append-only lifecycle, and safe artifact-reference tests. Expected: all selected tests
pass without warnings or raw validation output.

- [ ] **Step 6: Commit the bounded implementation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git diff --cached --check
git commit -m "Show complete runtime evidence records"
```

### Task 2: Verify and publish the protected slice

**Files:**
- Verify: `apps/web/app.py`
- Verify: `tests/apps/test_streamlit_app.py`
- Verify: `docs/superpowers/specs/2026-07-14-runtime-record-review-clarity-design.md`
- Verify: `docs/superpowers/plans/2026-07-14-runtime-record-review-clarity.md`

**Interfaces:**
- Consumes: committed implementation from Task 1.
- Produces: protected GitHub PR with exact-main verification evidence.

- [ ] **Step 1: Run full local verification**

Run Ruff, complete pytest, deterministic benchmark, `git diff --check`, and a loopback
Streamlit health smoke. Expected: zero failures, zero benchmark mismatches, zero
must-have False Ready cases, and HTTP health `ok`.

- [ ] **Step 2: Perform current-browser comparison**

Reload the local workbench, reach the analyzed demo without recording external
evidence, and inspect the runtime-record presentation through controlled local fixture
state. Save and inspect the accepted screenshot. Confirm labels and layout are visible;
do not claim the fixture as real runtime evidence.

- [ ] **Step 3: Publish through the protected workflow**

Push `codex/runtime-record-review-clarity`, open a ready PR against `main`, wait for
required `verify` and CodeQL, fix genuine failures, and squash-merge only when every
required check is green and the PR head SHA is unchanged.

- [ ] **Step 4: Verify exact main and continue**

Fast-forward local `main`, verify CI and CodeQL on the exact merge commit, confirm
`origin/main...HEAD` is `0 0`, then immediately resume the persistent audit loop.
