# Gate Recovery Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn deterministic gate reason codes into consistent, non-prescriptive recovery guidance without changing gate truth.

**Architecture:** Add a pure core helper that consumes a validated `GateDecision` and derives ordered guidance from its reason codes and criterion-ID lists. Reuse that helper in Streamlit, Markdown, and HTML while keeping raw reasons and all persisted schemas intact.

**Tech Stack:** Python 3.11+, Pydantic models, pytest, Streamlit AppTest, Markdown/HTML exporters, Ruff.

## Global Constraints

- Do not change gate evaluation, reason-code order, GateDecision schema, evidence rules, or human acceptance requirements.
- Unknown reason codes must produce a conservative fallback and retain the exact code.
- Guidance must not tell users to accept, waive, or mark evidence sufficient.
- JSON and CSV formats remain unchanged.
- No new dependency, paid API, billing, fork, PR-code execution, or synthetic decision.

---

### Task 1: Pure gate guidance

**Files:**
- Create: `scopeproof_core/gates/guidance.py`
- Create: `tests/gates/test_guidance.py`

**Interfaces:**
- Consumes: `GateDecision`.
- Produces: `gate_guidance(gate: GateDecision) -> list[str]`.

- [ ] **Step 1: Write failing mapping tests**

Create a parameterized test covering all nine known reason codes. Add a combined decision with
blocking `AC-01`, conditional `AC-02`, and unresolved `AC-03` to require IDs in stable reason-code
order. Add duplicate-code and `future_reason` cases to require de-duplication and exact-code fallback.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/gates/test_guidance.py -q`

Expected: import failure because `scopeproof_core.gates.guidance` does not exist.

- [ ] **Step 3: Implement the minimal pure helper**

Implement explicit `if` branches for the nine codes, join sorted criterion IDs with `, `, skip
duplicate codes while preserving first occurrence, and use
`Review gate reason `<code>` before acceptance.` for unknown codes.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/gates/test_guidance.py -q`

Expected: all guidance tests pass.

### Task 2: Consistent UI and report guidance

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `tests/reporting/test_exporters.py`
- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/reporting/exporters.py`

**Interfaces:**
- Consumes: `gate_guidance(bundle.gate)` from Task 1.
- Produces: Streamlit `What to do next`, Markdown `## What To Do Next`, and escaped HTML guidance.

- [ ] **Step 1: Write failing surface tests**

Require the deterministic Blocked demo AppTest to show `What to do next`, include `AC-01`, and state
that unresolved criteria require an explicit human decision. Require Markdown to retain
`blocking_criteria` and add `## What To Do Next`; require HTML to contain both `Gate Reasons` and
`What To Do Next` with escaped content.

- [ ] **Step 2: Run surface tests and verify RED**

Run: `.venv/bin/python -m pytest tests/apps/test_streamlit_app.py tests/reporting/test_exporters.py -q`

Expected: failures because current surfaces show raw codes only or omit gate reasons in HTML.

- [ ] **Step 3: Integrate the shared helper**

Import `gate_guidance` in the UI and exporters. Render bullet guidance only when the helper returns
messages. Preserve raw gate reasons. Escape every HTML reason and guidance string with `html.escape`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/gates/test_guidance.py tests/apps/test_streamlit_app.py tests/reporting/test_exporters.py -q`

Expected: all focused tests pass.

- [ ] **Step 5: Commit implementation**

```bash
git add scopeproof_core/gates/guidance.py scopeproof_core/reporting/exporters.py apps/web/app.py tests/gates/test_guidance.py tests/reporting/test_exporters.py tests/apps/test_streamlit_app.py
git commit -m "feat: explain gate recovery actions"
```

### Task 3: Verification and protected publication

**Files:**
- Verify only; no planned source edits.

**Interfaces:**
- Consumes: exact branch and protected-main commits.
- Produces: test, benchmark, runtime, CI, and GitHub reconciliation evidence.

- [ ] **Step 1: Run all local gates**

Run Ruff, full pytest, deterministic benchmark, `git diff --check`, and clean-tree inspection.
Expected: no lint errors; all tests pass; 12 cases with zero mismatches, zero False Ready, and zero
false blocker.

- [ ] **Step 2: Verify runtime summary without creating decisions**

Run the deterministic local demo through analysis with Streamlit AppTest and a local HTTP smoke.
Require Blocked summary guidance and raw reason codes together. Do not record runtime evidence,
resolution, or final acceptance.

- [ ] **Step 3: Publish through protected main**

Push `codex/gate-recovery-guidance`, open a ready PR, wait for both `verify` checks, evidence review,
and CodeQL, merge normally only if all pass, then wait for merged-main CI and CodeQL.

- [ ] **Step 4: Reconcile without release churn**

Keep package version and latest release at v0.1.14. Require zero open PRs, only main remote branch,
ignored notifications, required `verify`, SHA-pinned Actions, and zero open security/dependency alerts.
Do not post an issue announcement.
