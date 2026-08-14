# Stage 2 Readiness Packet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare one authoritative Stage 2 readiness packet while keeping Stage 1 paused at zero and Stage 2 explicitly not started.

**Architecture:** This is a docs-and-contracts slice. `ROADMAP.md` owns the current measured state and owner operating posture; a new commercialization packet indexes dormant post-use discovery materials; a section-scoped repository contract prevents similar wording elsewhere from masking a stale authoritative stage block.

**Tech Stack:** Markdown, Python 3.12, pytest repository contracts, Ruff, existing deterministic ScopeProof benchmarks.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Stage 1 remains `waiting_for_inbound_public_alpha_submission` at 0/5 reviews, 0/3 practitioners, 0/3 repositories, 0/3 independently observed under-ten-minute completions, and 0/2 reuse-intent signals.
- Owner operating posture is Stage 1 paused; Stage 2 readiness materials only; Stage 2 not activated.
- Stage 2 requires every Stage 1 exit condition plus separate owner authorization.
- No outreach, participant contact, recurring monitor, recruitment issue, announcement, commercial claim, pricing offer, release, tag, or package publication is authorized.
- Do not add product code, forms, databases, accounts, billing, private-repository support, hosted processing, integrations, generic code review, security scanning, automatic fixes, or paid APIs.
- Preserve the untracked root `.coverage 2` exactly; never stage, modify, delete, rename, move, or package it.
- Static candidates remain distinct from runtime verification; persisted/exported product objects remain Pydantic-validated; gates remain deterministic and fail closed.
- False Ready remains more harmful than False Blocked.

---

## File structure

- Create `docs/commercialization/stage2-readiness-packet.md`: sole operational index for dormant future Stage 2 discovery materials.
- Modify `ROADMAP.md`: record the paused owner posture in the authoritative Stage 1 and Stage 2 sections and link the packet without changing measured counts or gates.
- Modify `tests/test_repository_contracts.py`: add section-scoped contracts for the authoritative roadmap blocks and packet boundaries.

### Task 1: Lock the paused Stage 1 and not-started Stage 2 status

**Files:**
- Modify: `tests/test_repository_contracts.py` after `test_authoritative_stage_one_docs_record_post_pr193_truth_and_owner_gate`
- Create: `docs/commercialization/stage2-readiness-packet.md`
- Modify: `ROADMAP.md` Stage 1 and Stage 2 sections

**Interfaces:**
- Consumes: current `ROADMAP.md` Stage 1, Stage 2, and Stage 3 headings.
- Produces: packet headings `# ScopeProof Stage 2 Readiness Packet`, `## Current status`, and `## Activation gate`; contract `test_stage_two_readiness_packet_preserves_paused_stage_one_gate`.

- [ ] **Step 1: Write the failing section-scoped repository contract**

Add this test after the existing authoritative Stage 1 contract:

```python
def test_stage_two_readiness_packet_preserves_paused_stage_one_gate() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )

    def section(document: str, start: str, end: str) -> str:
        return document.split(start, maxsplit=1)[1].split(end, maxsplit=1)[0]

    stage_one = section(roadmap, "## Stage 1 — Genuine public alpha", "## Stage 2")
    stage_two = section(roadmap, "## Stage 2 — Commercial discovery", "## Stage 3")
    current_status = section(packet, "## Current status", "## Activation gate")
    activation_gate = section(packet, "## Activation gate", "## Post-use discovery guide")

    assert "waiting_for_inbound_public_alpha_submission" in stage_one
    assert "Owner operating posture: Stage 1 is paused" in stage_one
    for count in (
        "0/5 qualifying reviews",
        "0/3 independent practitioners",
        "0/3 public repositories",
        "0/3 independently observed under-ten-minute completions",
        "0/2 reuse-intent signals",
    ):
        assert count in stage_one
        assert count in current_status
    assert "not a validated False Ready rate" in stage_one
    assert "Stage 2 readiness materials only; Stage 2 has not begun" in stage_two
    assert "Stage 2 cannot begin until every Stage 1 target is satisfied." in stage_two
    assert "separate owner authorization" in stage_two
    assert "does not authorize outreach" in current_status
    assert "Every Stage 1 exit condition" in activation_gate
    assert "separate owner authorization" in activation_gate
    assert "docs/commercialization/stage2-readiness-packet.md" in stage_two
```

- [ ] **Step 2: Run the focused test and verify the red state**

```bash
uv run python -m pytest -q \
  tests/test_repository_contracts.py::test_stage_two_readiness_packet_preserves_paused_stage_one_gate
```

Expected: FAIL because the packet does not exist.

- [ ] **Step 3: Add the minimum packet status and activation sections**

Create the packet with this opening:

```markdown
# ScopeProof Stage 2 Readiness Packet

This packet prepares dormant post-use research materials. It does not activate Stage 2, authorize
outreach, or create product-validation or commercial evidence.

## Current status

Measured product-validation state: `waiting_for_inbound_public_alpha_submission`.

Owner operating posture: Stage 1 is paused. Stage 2 readiness materials only; Stage 2 has not
begun. This preparation does not authorize outreach.

- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews is not a validated
  False Ready rate.

## Activation gate

Every Stage 1 exit condition must have genuine evidence before Stage 2 can be considered. Stage 2
also requires separate owner authorization after those conditions pass. Prepared materials, tests,
demos, releases, downloads, issue activity, owner rehearsals, and elapsed time earn no stage credit.

## Post-use discovery guide
```

- [ ] **Step 4: Update the authoritative roadmap sections minimally**

Add to Stage 1:

```markdown
Owner operating posture: Stage 1 is paused. Pausing changes no measured count, satisfies no exit
condition, and does not authorize outreach or activate Stage 2.
```

Add to Stage 2:

```markdown
Owner operating posture: Stage 2 readiness materials only; Stage 2 has not begun. The
[Stage 2 readiness packet](docs/commercialization/stage2-readiness-packet.md) prepares dormant
post-use research materials and creates no stage credit.

Stage 2 activation additionally requires separate owner authorization after every Stage 1 target
is satisfied.
```

- [ ] **Step 5: Run the focused and existing authoritative-stage tests**

```bash
uv run python -m pytest -q \
  tests/test_repository_contracts.py::test_stage_two_readiness_packet_preserves_paused_stage_one_gate \
  tests/test_repository_contracts.py::test_authoritative_stage_one_docs_record_post_pr193_truth_and_owner_gate
```

Expected: 2 passed.

- [ ] **Step 6: Commit the first slice**

```bash
git add -- ROADMAP.md docs/commercialization/stage2-readiness-packet.md \
  tests/test_repository_contracts.py
git commit -m "docs: record paused Stage 1 readiness gate"
```

### Task 2: Complete the dormant discovery materials and evidence rules

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `docs/commercialization/stage2-readiness-packet.md`

**Interfaces:**
- Consumes: Task 1 status/activation sections and existing design-partner/positioning documents.
- Produces: Post-use guide, hypothesis ledger, evidence template, decision rules, and boundaries.

- [ ] **Step 1: Extend the contract with failing content assertions**

Append:

```python
    for heading in (
        "## Post-use discovery guide",
        "## Hypothesis ledger",
        "## Evidence-capture template",
        "## Decision rules",
        "## Boundaries",
    ):
        assert heading in packet
    for required in (
        "unknown",
        "declined",
        "not observed",
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research anchors only",
        "Do not infer any signal from silence",
        "No decision may be calculated while the qualifying denominator is zero",
        "design-partner-sprint.md",
        "market-positioning-hypotheses.md",
    ):
        assert required in packet
    for forbidden_claim in (
        "Stage 1 is complete",
        "Stage 1 passed",
        "Stage 2 is active",
        "validated price",
        "willingness to pay is validated",
    ):
        assert forbidden_claim not in packet
```

- [ ] **Step 2: Run the focused test and verify the red state**

Run the focused command from Task 1.

Expected: FAIL on the first missing heading or boundary phrase.

- [ ] **Step 3: Complete the readiness packet**

Add:

- seven ordered post-use questions for alternative workflow, attributable result, decision impact,
  friction, evidence-boundary understanding, reuse, and optional price discussion;
- a Markdown ledger with `unknown`, `supported`, `mixed`, and `disconfirmed` states;
- a blank Markdown evidence template for case/head, role, source-owner path, outcome, observed timing,
  alternative, result, impact, friction, understanding, reuse, optional price response, and source;
- Continue, Narrow, Pivot, and Stop rules;
- links to `design-partner-sprint.md` and `market-positioning-hypotheses.md`; and
- prohibitions on outreach, contact/private/payment data, inferred signals, and fictional records.

- [ ] **Step 4: Run focused and repository-contract verification**

```bash
uv run python -m pytest -q \
  tests/test_repository_contracts.py::test_stage_two_readiness_packet_preserves_paused_stage_one_gate
uv run python -m pytest -q tests/test_repository_contracts.py
uv run ruff check tests/test_repository_contracts.py
git diff --check
```

Expected: all pass.

- [ ] **Step 5: Commit the completed packet**

```bash
git add -- docs/commercialization/stage2-readiness-packet.md \
  tests/test_repository_contracts.py
git commit -m "docs: complete Stage 2 readiness materials"
```

### Task 3: Run broad verification and review

**Files:**
- Verify only unless a confirmed in-scope defect needs a test-first repair.

**Interfaces:**
- Consumes: committed packet and contract.
- Produces: current-head verification evidence and clean review disposition.

- [ ] **Step 1: Run complete verification**

```bash
uv run ruff check .
uv run python -m pytest \
  --cov=scopeproof_core \
  --cov=apps \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 \
  -q
uv run python -m pytest -q tests/test_repository_contracts.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
git diff --check main...HEAD
```

Expected: Ruff, suite, at least 95 percent coverage, contracts, benchmarks, and diff pass; benchmark
mismatches, must-have False Ready, false blockers, and unexecuted categories remain zero; comparison
reports `does_not_advance_stage_1: true`.

- [ ] **Step 2: Audit commits and preserved state**

```bash
git log --oneline main..HEAD
git diff --stat main...HEAD
git status --short --branch
shasum -a 256 ".coverage 2"
```

Expected: only approved documents and the focused contract changed; `.coverage 2` remains untracked
with SHA-256 `b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`.

- [ ] **Step 3: Obtain independent read-only review**

Review for whole-document presence-only tests, wording that implies Stage 1 completion or Stage 2
activation, inferred commercial signals, and accidental outreach authorization. Require zero
unresolved Critical or Important findings; repair confirmed findings test-first.

- [ ] **Step 4: Stop at publication gate**

Do not push, open a pull request, merge, release, tag, publish, or begin outreach without separate
owner authorization after review of the completed branch.
