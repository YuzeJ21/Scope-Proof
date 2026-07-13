# Human-Decision Impact Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain the deterministic gate impact of each explicit human decision at the moment a reviewer selects it.

**Architecture:** Add a pure `decision_guidance` function beside existing gate guidance, then render its fixed output directly below the Streamlit selector. Preserve all decision, lifecycle, gate, schema, export, and persistence behavior.

**Tech Stack:** Python 3.12, Streamlit, Streamlit AppTest, Pydantic 2, pytest, Ruff.

## Global Constraints

- Guidance must describe existing evaluator behavior exactly and must not change it.
- No decision is preselected, inferred, recommended, or saved automatically.
- The core guidance function remains independent from Streamlit.
- Never represent guidance as evidence or runtime verification.

---

### Task 1: Add deterministic decision-impact guidance

**Files:**
- Modify: `scopeproof_core/gates/guidance.py`
- Modify: `tests/gates/test_guidance.py`
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Produces: `decision_guidance(decision: HumanDecision) -> str`.
- Consumes: the existing Streamlit `resolution_decision: HumanDecision | None` value.

- [ ] **Step 1: Write failing core guidance coverage**

Add `decision_guidance` and `HumanDecision` imports, then parameterize all six decisions and exact
messages in `tests/gates/test_guidance.py`. Require these meanings:

```python
DECISION_CASES = [
    (HumanDecision.ACCEPTED, "Records reviewer acceptance and treats this criterion as resolved."),
    (
        HumanDecision.ACCEPTED_EXCEPTION,
        "Records an explicit exception and makes the review conditional.",
    ),
    (
        HumanDecision.CHANGE_REQUIRED,
        "Makes this criterion blocking until a later decision replaces it.",
    ),
    (
        HumanDecision.REJECTED_FINDING,
        "Rejects the provisional finding but does not resolve this criterion; its finding status "
        "continues to control the gate.",
    ),
    (
        HumanDecision.MANUALLY_VERIFIED,
        "Records external manual verification at the selected evidence level and treats this "
        "criterion as resolved.",
    ),
    (
        HumanDecision.NOT_IN_SCOPE,
        "Records a scope exception, removes this criterion from active blocking and unresolved "
        "checks, and can leave the review conditional.",
    ),
]
```

Run the focused test and require RED because `decision_guidance` does not exist.

- [ ] **Step 2: Implement the pure mapping**

In `scopeproof_core/gates/guidance.py`, import `HumanDecision`, define a complete dictionary with the
six exact messages above, and return `_DECISION_GUIDANCE[decision]` from
`decision_guidance(decision: HumanDecision) -> str`. Run `tests/gates/test_guidance.py` and require
GREEN.

- [ ] **Step 3: Write failing Streamlit integration coverage**

Add an AppTest that requires `Select a decision to see its deterministic gate impact.` before a
selection, selects `HumanDecision.REJECTED_FINDING`, and then requires:

```text
Decision impact: Rejects the provisional finding but does not resolve this criterion; its finding status continues to control the gate.
```

Run the focused test and require RED because the UI does not render guidance.

- [ ] **Step 4: Render the selected impact**

Import `decision_guidance` beside `gate_guidance`. Immediately after the decision selectbox, render:

```python
    if decision is None:
        st.caption("Select a decision to see its deterministic gate impact.")
    else:
        st.caption(f"Decision impact: {decision_guidance(decision)}")
```

Run the focused AppTest, the explicit-selection regression, all gate-guidance tests, and Ruff on the
four changed Python files. Require GREEN and clean lint.

- [ ] **Step 5: Commit**

Stage only the four Python files and commit `clarify human decision impact`.

### Task 2: Verify and publish

**Files:**
- Verify all source, tests, benchmark fixtures, package contents, and the live Streamlit state.

**Interfaces:**
- Produces: a protected-main merge with no release.

- [ ] **Step 1: Run Ruff, full pytest, benchmark, and diff checks**

Require all tests apart from the intentional live skip, all 12 benchmark cases, zero must-have False
Ready, zero False Blocker, zero mismatches, and clean `git diff --check origin/main...HEAD`.

- [ ] **Step 2: Verify installed wheel and browser state**

Build and install a fresh wheel, require both console versions `0.1.15.dev0`, installed benchmark
success, and exact Streamlit health `ok`. In the deliberately constructed demo, capture the empty
decision prompt and a selected `Rejected Finding` impact. Do not save the decision, runtime evidence,
or final acceptance.

- [ ] **Step 3: Publish through protected main**

Review the full diff, push `codex/decision-impact-guidance`, open one ready PR, wait for required
`verify`, ScopeProof evidence review, and CodeQL, merge only when green, and confirm exact post-main
CI and CodeQL success. Synchronize local main and clean the owned worktree and branch. Do not publish
a release for guidance-only behavior.
