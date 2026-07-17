# Inbound Alpha Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an inbound-only public-alpha case submission path so the owner does not need to manually DM participants.

**Architecture:** Use GitHub issue forms as the no-cost public intake surface. Update static site/docs to point to the issue template, and add repository contracts to preserve the no-private-data and no-fake-validation boundaries.

**Tech Stack:** GitHub issue forms, static HTML/CSS site, Markdown docs, pytest repository contracts.

## Global Constraints

- No paid OpenAI/LLM API, billing, organizations, private repos, fork testing, automated outreach, scraping, mass messaging, email, synthetic validation, invented evidence, or noisy GitHub comments.
- Preserve ScopeProof's evidence-first rules from `AGENTS.md`.
- Do not claim alpha success without a completed real participant case.
- Do not add app, CLI, schema, workflow, release, or GitHub Action behavior changes.

---

### Task 1: Inbound Alpha Intake

**Files:**
- Create: `.github/ISSUE_TEMPLATE/public-alpha-case.yml`
- Modify: `site/index.html`
- Modify: `docs/alpha/participant-evidence-unblocker.md`
- Modify: `docs/alpha/concierge-host-checklist.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: existing alpha quickstart, qualification checklist, and outcome workflow.
- Produces: an inbound issue URL and public CTA for real participants to submit candidate public PRs.

- [ ] **Step 1: Add failing contract**

Add repository assertions that require the issue template, its four inputs, site CTA, and no-private-data boundaries.

- [ ] **Step 2: Run the contract and verify it fails**

Run: `uv run python -m pytest -q tests/test_repository_contracts.py::test_inbound_alpha_case_submission_path_is_public_safe_and_owner_passive`

Expected: FAIL before the template/site/doc changes exist.

- [ ] **Step 3: Implement template and docs/site copy**

Add the issue form and update the site/unblocker/checklist copy to prefer inbound-only submission over manual outreach.

- [ ] **Step 4: Run focused verification**

Run:

```bash
uv run python -m pytest -q tests/test_repository_contracts.py
uv run ruff check
uv lock --check
uv pip check
uv run scopeproof benchmark
```

Expected: all pass.

- [ ] **Step 5: Commit and publish through PR**

Commit the narrow slice on a `codex/` branch, push, open a PR, wait for required checks, merge if green, and resync local `main`.
