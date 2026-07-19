# ScopeProof Market Positioning Hypotheses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a source-backed, explicitly hypothetical account of ScopeProof's market position
without changing product behavior or claiming external validation.

**Architecture:** Keep the canonical research in one commercialization document and add only
discoverability links from the README and roadmap. External capability facts use official sources;
product, ICP, buyer, and differentiation statements remain clearly labelled facts or hypotheses.

**Tech Stack:** Markdown, repository contract tests, Ruff, and deterministic documentation checks.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Customer, market, demand, buyer, and pricing statements remain hypotheses until supported by
  genuine external evidence.
- Do not add billing, paid APIs, accounts, private repositories, outreach, or integrations.
- Do not change product code, evidence rules, schemas, gates, persistence, or exports.

---

### Task 1: Publish the market-positioning research artifact

**Files:**
- Create: `docs/commercialization/market-positioning-hypotheses.md`

**Interfaces:**
- Consumes: official Qase, Microsoft, TestRail, and GitHub documentation plus the current ScopeProof
  README, roadmap, and design-partner sprint.
- Produces: one durable research artifact that distinguishes verified facts from hypotheses.

- [ ] **Step 1: Write the evidence boundary and source table**

  State the current waiting condition, then summarize each adjacent workflow with a direct official
  source link and without a superiority claim.

- [ ] **Step 2: Write the falsifiable ScopeProof hypotheses**

  Include the ICP, job-to-be-done, user, likely buyer, differentiated value, adoption friction,
  trust requirements, non-goals, and disconfirming evidence.

- [ ] **Step 3: Run documentation hygiene checks**

  Run:

  ```bash
  rg -n "TBD|TODO|customer-proven|market-validated" \
    docs/commercialization/market-positioning-hypotheses.md
  git diff --check
  ```

  Expected: no placeholder or prohibited-claim matches; clean diff.

### Task 2: Make the research discoverable without promoting it to validation

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: `docs/commercialization/market-positioning-hypotheses.md`.
- Produces: two descriptive links that preserve the research-only boundary.

- [ ] **Step 1: Add the README research link**

  Add one sentence beside the design-partner guide stating that the market-positioning document
  compares adjacent workflows and records only hypotheses.

- [ ] **Step 2: Add the Stage 2 roadmap link**

  Link the same artifact from commercial discovery and state that genuine completed reviews are
  required to validate or reject it.

- [ ] **Step 3: Verify repository contracts and lint**

  Run:

  ```bash
  uv run pytest -q tests/test_repository_contracts.py tests/github_action/test_contract.py
  uv run ruff check .
  git diff --check
  ```

  Expected: all tests pass, Ruff passes, and the diff is clean.

- [ ] **Step 4: Commit the reviewed documentation slice**

  ```bash
  git add README.md ROADMAP.md docs/commercialization/market-positioning-hypotheses.md \
    docs/superpowers/specs/2026-07-18-market-positioning-hypotheses-design.md \
    docs/superpowers/plans/2026-07-18-market-positioning-hypotheses.md
  git commit -m "docs: define market positioning hypotheses"
  ```
