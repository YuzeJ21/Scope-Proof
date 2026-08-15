# Owner-Led Stage 2 Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise PR #195 so Stage 1 is truthfully closed as not pursued and owner-led Stage 2 productization is active without customer-validation claims.

**Architecture:** Keep stage truth in the roadmap, release-status audit, and Stage 2 packet. Align public feedback and commercialization surfaces to one optional external-discovery lane, and enforce the model with section-scoped repository contracts before changing prose.

**Tech Stack:** Markdown, YAML issue templates, Python 3.12, pytest repository contracts, Ruff, existing deterministic ScopeProof benchmarks.

## Global Constraints

- Stage 1 status is `closed_not_pursued_by_owner`; every historical measurement remains exactly zero.
- Stage 1 is not passed, completed, waived, validated, or replaced by engineering evidence.
- Stage 2 status is `owner_led_productization_active`; this task authorizes strategy documentation, not feature implementation or release action.
- External product or commercial discovery is optional, separate, non-validating, and inactive by default.
- Do not contact participants, conduct outreach, merge, release, tag, publish packages, retune R-002, or generate R-003.
- Preserve `.coverage 2` exactly and never stage, modify, delete, rename, move, or package it.
- Preserve confirmed criteria, typed evidence levels, Pydantic validation, deterministic fail-closed gates, non-mutating failures, and non-execution of target code.
- False Ready remains more harmful than False Blocked.

---

### Task 1: Lock the new stage semantics

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `ROADMAP.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/commercialization/stage2-readiness-packet.md`

**Interfaces:**
- Consumes: current Stage 1/2 headings and the release-status gap ledger.
- Produces: section-scoped contract `test_owner_led_stage_two_strategy_preserves_zero_external_evidence`.

- [ ] **Step 1: Write the failing stage contract**

Replace the paused-stage readiness test with a test that extracts the authoritative Stage 1 and
Stage 2 sections from both documents and the status/scope/discovery sections from the packet. Use
literal expectations:

```python
assert "closed_not_pursued_by_owner" in stage_one
assert "owner_led_productization_active" in stage_two
assert "Stage 1 did not pass" in stage_one
assert "owner-led productization" in stage_two
assert "External commercial discovery is optional and separate" in stage_two
for count in (
    "0/5 qualifying reviews",
    "0/3 independent practitioners",
    "0/3 public repositories",
    "0/3 independently observed under-ten-minute completions",
    "0/2 reuse-intent signals",
):
    assert count in stage_one
    assert count in packet_status
for claim in (
    "Stage 1 passed",
    "Stage 1 is complete",
    "customer validation achieved",
    "validated demand",
    "validated price",
    "willingness to pay is validated",
):
    assert claim not in protected_current_sections
```

- [ ] **Step 2: Verify the red state**

Run:

```bash
uv run python -m pytest -q tests/test_repository_contracts.py::test_owner_led_stage_two_strategy_preserves_zero_external_evidence
```

Expected: FAIL because the old documents still contain `waiting_for_inbound_public_alpha_submission`
and keep Stage 2 dormant.

- [ ] **Step 3: Rewrite the authoritative stage sections**

Use this status model in all three files:

```markdown
Stage 1 status: `closed_not_pursued_by_owner`.
Stage 1 did not pass. The owner chose not to pursue it, and every recorded count remains zero.

Stage 2 status: `owner_led_productization_active`.
The owner authorized productization without claiming customer validation.
External commercial discovery is optional and separate from owner-led productization.
```

Retain the exact five zero counts and the zero-participant False Ready denominator limitation.
Enumerate allowed owner-led engineering/product work and separately gated release, outreach,
participant-contact, R-002, R-003, billing, account, private-repository, hosted-processing,
generic-review, security-scanning, automatic-fix, and paid-API actions.

- [ ] **Step 4: Verify the green state**

Run the focused stage test and the surrounding authoritative-document tests. Expected: all pass.

- [ ] **Step 5: Commit the stage model**

Stage only the four named files and commit:

```bash
git commit -m "docs: adopt owner-led Stage 2 strategy"
```

### Task 2: Align public and optional-discovery materials

**Files:**
- Modify: `README.md`
- Modify: `site/index.html`
- Modify: `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`
- Modify: `docs/alpha/outcome-form.md`
- Modify: `docs/alpha/participant-quickstart.md`
- Modify: `docs/alpha/concierge-host-checklist.md`
- Modify: `docs/alpha/participant-evidence-unblocker.md`
- Modify: `docs/commercialization/design-partner-sprint.md`
- Modify: `docs/commercialization/market-positioning-hypotheses.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: Task 1 statuses.
- Produces: one optional external-feedback lane with no pricing field and no customer-validation implication.

- [ ] **Step 1: Write failing public-surface expectations**

Update the public feedback and positioning tests to require these observable boundaries:

```python
for surface in (readme_product_status, site_alpha, quickstart_handoff, outcome_handoff):
    assert "optional" in surface.lower()
    assert "customer validation" in surface.lower()
assert "id: price_discussion" not in feedback_form
assert "id: design_partner_interest" not in feedback_form
assert "This optional feedback does not reopen Stage 1" in feedback_form
assert "commercial discovery is separate" in feedback_form.lower()
assert "pricing question is optional research after product use" not in public_surfaces
```

Add section-scoped negative guards against the former current statuses:

```python
for current_surface in current_surfaces:
    assert "waiting_for_inbound_public_alpha_submission" not in current_surface
    assert "every Stage 1 exit target genuinely passes" not in current_surface
    assert "Stage 2 has not begun" not in current_surface
```

- [ ] **Step 2: Verify the red state**

Run the focused public-alpha, public-positioning, and owner-led stage tests. Expected: failures on
the old pricing promise, old waiting status, and old Stage 1 dependency.

- [ ] **Step 3: Align each current-facing surface**

Apply these exact rules:

- README and site: owner-led Stage 2 is active; optional external discovery is separate; no paid
  product or billing exists; no customer validation is claimed.
- Feedback template: retain outcome/timing/impact/reuse fields, remove Stage 1 credit language,
  keep price and design-partner fields absent, and state that submission neither reopens Stage 1
  nor validates a customer or market.
- Outcome, quickstart, checklist, and unblocker: treat public-alpha naming as a legacy channel name;
  voluntary feedback is optional and not required for Stage 2 productization.
- Design-partner sprint: make it a dormant optional research protocol that requires a separate
  owner authorization before use, but no Stage 1 target.
- Market-positioning hypotheses: preserve all hypotheses as unvalidated and mark discovery
  optional.
- Changelog: record the owner strategy decision under Unreleased without presenting it as product
  validation.

- [ ] **Step 4: Verify the public surface and repository contracts**

Run:

```bash
uv run python -m pytest -q tests/test_repository_contracts.py
uv run ruff check tests/test_repository_contracts.py
git diff --check
```

Expected: every repository contract passes, Ruff reports no findings, and the diff check exits 0.

- [ ] **Step 5: Commit the aligned surfaces**

Stage only the named Task 2 files and commit:

```bash
git commit -m "docs: separate optional discovery from productization"
```

### Task 3: Verify, review, and publish the revised PR head

**Files:**
- Verify only unless a confirmed defect requires a test-first repair.

**Interfaces:**
- Consumes: completed strategy and aligned surfaces.
- Produces: reviewed exact-head evidence and a ready-for-owner-review PR.

- [ ] **Step 1: Run local verification**

```bash
uv run ruff check .
uv run python -m pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run python -m pytest -q tests/test_repository_contracts.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
git diff --check origin/main...HEAD
```

Expected: Ruff and tests pass; combined coverage is at least 95 percent; the acceptance benchmark
has zero mismatches, zero must-have False Ready outcomes, zero false blockers, and no unexecuted
categories; the comparison benchmark has zero mismatches.

- [ ] **Step 2: Audit and preserve local state**

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git log --oneline origin/main..HEAD
stat -f '%N|%z|%m|%i' '.coverage 2'
shasum -a 256 '.coverage 2'
```

Expected: `.coverage 2` remains the only untracked file with SHA-256
`b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`, size 53248,
mtime 1784162591, and inode 184803784.

- [ ] **Step 3: Push and update PR #195**

Push `codex/stage2-readiness-packet`. Change the PR title to
`docs: adopt owner-led Stage 2 productization`. The body must record both exact statuses, five zero
counts, the optional external-discovery boundary, local verification, and the no-merge/no-release
boundary. Keep the PR draft during review.

- [ ] **Step 4: Obtain independent review**

Review the exact pushed head for stale Stage 1 dependencies, Stage 2 activation contradictions,
pricing-form mismatch, whole-document presence-only contracts, and customer-validation overclaims.
Resolve every actionable Critical or Important finding test-first and repeat affected verification.

- [ ] **Step 5: Make the reviewed PR ready and monitor checks**

Mark the PR ready only after independent review reports zero unresolved Critical or Important
findings. Monitor every exact-head check until terminal. Repair only confirmed in-scope failures on
the same branch.

- [ ] **Step 6: Stop at the owner merge decision**

Confirm the PR is current with `origin/main`, clean, mergeable, reviewed, and green or truthfully
classified. Do not merge.
