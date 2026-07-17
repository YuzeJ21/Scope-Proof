# Participant Evidence Unblocker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a repo-backed owner handoff that prevents ScopeProof alpha automation from looping when the only remaining gate is genuine participant evidence.

**Architecture:** This is a documentation and contract-test slice. The new alpha document becomes the owner-facing stop/resume artifact; the existing concierge checklist links to it; repository contracts prevent future drift.

**Tech Stack:** Markdown documentation, pytest repository contracts, existing ScopeProof alpha docs.

## Global Constraints

- Do not use paid OpenAI/LLM APIs, billing, organizations, private repos, fork testing, automated outreach, scraping, mass messaging, synthetic validation, invented evidence, or GitHub issue/PR comments.
- Preserve ScopeProof's evidence-first rules from `AGENTS.md`.
- Do not claim alpha success without a real participant case.
- Do not add app, CLI, schema, workflow, release, or GitHub Action behavior changes.

---

### Task 1: Participant Evidence Unblocker

**Files:**
- Create: `docs/alpha/participant-evidence-unblocker.md`
- Modify: `docs/alpha/concierge-host-checklist.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: existing public-alpha quickstart, qualification checklist, outcome form, and LinkedIn alpha playbook.
- Produces: an owner-facing stop/resume artifact named `docs/alpha/participant-evidence-unblocker.md`.

- [ ] **Step 1: Write the repository contract**

Add a test that reads `docs/alpha/participant-evidence-unblocker.md`, `docs/alpha/concierge-host-checklist.md`, and checks for the exact operational boundaries:

```python
def test_participant_evidence_unblocker_prevents_empty_monitoring_loops() -> None:
    unblocker = Path("docs/alpha/participant-evidence-unblocker.md").read_text(
        encoding="utf-8"
    )
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "[participant evidence unblocker](participant-evidence-unblocker.md)" in checklist
    assert "waiting_for_external_participant_evidence" in unblocker
    assert "public PR URL" in unblocker
    assert "public HTTPS requirements source" in unblocker
    assert "explicit authority to confirm criteria" in unblocker
    assert "explicit confirmation that no private or confidential information is included" in unblocker
    assert "Do not start another overnight monitor" in unblocker
    assert "/goal Run ScopeProof's first genuine public-alpha case" in unblocker
    for forbidden in (
        "paid OpenAI/LLM API",
        "billing",
        "automated outreach",
        "scraping",
        "synthetic validation",
        "invented evidence",
        "fork testing",
        "GitHub issue comment",
    ):
        assert forbidden in unblocker
```

- [ ] **Step 2: Run the new contract and verify it fails**

Run: `uv run python -m pytest -q tests/test_repository_contracts.py::test_participant_evidence_unblocker_prevents_empty_monitoring_loops`

Expected: FAIL because the new file or checklist link does not exist yet.

- [ ] **Step 3: Add the unblocker document and checklist link**

Create `docs/alpha/participant-evidence-unblocker.md` with the owner action, hard boundaries,
stop condition, and resume prompt. Add the link to `docs/alpha/concierge-host-checklist.md`.

- [ ] **Step 4: Run focused verification**

Run:

```bash
uv run python -m pytest -q tests/test_repository_contracts.py
uv run ruff check
```

Expected: all checks pass.

- [ ] **Step 5: Commit**

```bash
git add docs/alpha/participant-evidence-unblocker.md docs/alpha/concierge-host-checklist.md tests/test_repository_contracts.py docs/superpowers/specs/2026-07-17-participant-evidence-unblocker-design.md docs/superpowers/plans/2026-07-17-participant-evidence-unblocker.md
git commit -m "docs: add participant evidence unblocker"
```
