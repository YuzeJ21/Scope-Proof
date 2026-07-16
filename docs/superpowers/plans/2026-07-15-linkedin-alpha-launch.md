# ScopeProof LinkedIn Alpha Recruitment Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish to GitHub a complete, truthful LinkedIn launch package that recruits
qualified ScopeProof public-alpha participants through LinkedIn DM.

**Architecture:** Keep the public post concise and move operational detail into a dedicated launch
playbook. Add one LinkedIn-specific visual and repository contracts that make the release links,
disclosure, CTA, qualification fields, prohibited claims, alt text, and image dimensions
regression-testable.

**Tech Stack:** Markdown, Python repository contracts, Pillow image inspection, PNG launch asset,
pytest, Ruff, GitHub Actions, CodeQL.

## Global Constraints

- Primary audience: product managers, QA practitioners, and engineers with genuine public PRs.
- Primary call to action: LinkedIn direct message.
- Current public release: `v0.1.22`.
- Required disclosure: `This is a deliberately constructed demo case. ScopeProof uses
  deterministic evidence rules and human review; it does not guarantee correctness or replace
  QA.`
- The visual is exactly 1200x1200 pixels and stored as PNG.
- Do not claim customers, adoption, production accuracy, runtime correctness, market validation,
  or external validation.
- Do not create an Issue comment, participant record, recurring monitor, LinkedIn post, or direct
  message as part of this repository change.

---

### Task 1: Define the launch-package repository contracts

**Files:**
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: the approved design's exact release, disclosure, CTA, qualification, and asset rules.
- Produces: `test_linkedin_alpha_launch_package_is_current_and_truthful()` and
  `test_linkedin_alpha_visual_has_publishable_dimensions()`.

- [ ] **Step 1: Add the failing copy contract**

Add a test that reads `docs/launch/linkedin-draft.md` and
`docs/launch/linkedin-alpha-playbook.md`. Require the draft to contain the v0.1.22 release URL,
repository URL, exact disclosure, `DM me`, `genuine public pull request`, and the three audience
roles. Require the playbook to contain `Public PR URL`, `Source-owner confirmation`, `Public
criteria`, `No confidential information`, `Technical smoke only`, and `Decline`.

- [ ] **Step 2: Add the failing visual contract**

Require `docs/assets/scopeproof-linkedin-alpha.png` to exist, begin with the PNG signature, exceed
40,000 bytes, and report `(1200, 1200)` through `PIL.Image.open`.

- [ ] **Step 3: Verify RED**

Run both focused tests. Require failures because the playbook and visual do not exist and the old
draft lacks the current release/CTA contract.

- [ ] **Step 4: Commit the red contracts**

Commit only `tests/test_repository_contracts.py` as `test: define LinkedIn alpha launch contract`.

### Task 2: Write the final post and participant playbook

**Files:**
- Modify: `docs/launch/linkedin-draft.md`
- Create: `docs/launch/linkedin-alpha-playbook.md`

**Interfaces:**
- Consumes: the contract strings and evidence boundaries from Task 1.
- Produces: copy-ready public text, alt text, DM templates, qualification routing, and manual
  posting steps.

- [ ] **Step 1: Replace the draft with final copy**

Write a problem-first post under LinkedIn's 3,000-character post limit. Include repository and
release URLs, the exact disclosure, the DM-first CTA, and a short qualification statement. Keep
the post readable without assuming prior ScopeProof knowledge.

- [ ] **Step 2: Add the operational playbook**

Document the exact image-led post sequence, image alt text, initial DM response, qualification
questions, accepted/technical-smoke/declined routing, follow-up demo checklist, and evidence-safe
results logging.

- [ ] **Step 3: Run the copy contract**

Run `test_linkedin_alpha_launch_package_is_current_and_truthful` and require it to pass while the
visual contract remains red.

- [ ] **Step 4: Review prohibited claims**

Search the two files for `customer`, `adoption`, `accuracy`, `correctness`, `validated`, and
`production`. Each occurrence must be a negation, limitation, or checklist prohibition rather
than a positive claim.

- [ ] **Step 5: Commit the copy package**

Commit the draft and playbook as `docs: prepare LinkedIn alpha recruitment`.

### Task 3: Create and verify the LinkedIn visual

**Files:**
- Create: `docs/assets/scopeproof-linkedin-alpha.png`

**Interfaces:**
- Consumes: the problem-first positioning and constructed-demo disclosure from Task 2.
- Produces: one 1200x1200 social image referenced by the playbook.

- [ ] **Step 1: Generate the visual**

Create a high-contrast 1200x1200 product card with ScopeProof, the hook `Green CI is not the same
as complete product intent`, `Public alpha`, and `Deliberately constructed demo` visibly present.
Do not add metrics, customer logos, testimonials, or correctness claims.

- [ ] **Step 2: Inspect the rendered image**

Open the generated image at original detail. Require legible product name, hook, alpha label, demo
disclosure, balanced spacing, and no malformed UI or text.

- [ ] **Step 3: Run the visual contract**

Run `test_linkedin_alpha_visual_has_publishable_dimensions` and require it to pass.

- [ ] **Step 4: Commit the visual**

Commit the PNG as `docs: add LinkedIn alpha visual`.

### Task 4: Verify public wording and repository integrity

**Files:**
- Verify only: the complete branch.

**Interfaces:**
- Consumes: the complete launch package.
- Produces: a protected-PR-ready candidate.

- [ ] **Step 1: Run focused launch contracts**

Require both new repository contract tests and every existing repository contract to pass.

- [ ] **Step 2: Run repository-wide gates**

Require full pytest, Ruff, deterministic benchmark, `pip check`, and `git diff --check` to pass.
The benchmark must report 12 executed cases, 13 criteria, zero mismatches, zero false blockers, and
zero must-have False Ready outcomes.

- [ ] **Step 3: Verify post length and links**

Extract only the final post body and require no more than 3,000 characters. Require HTTP success
for the public repository and v0.1.22 release URLs without treating reachability as adoption or
product evidence.

- [ ] **Step 4: Review the final diff**

Require the diff to contain only the design, plan, contracts, final post, playbook, and PNG. Require
no unfixed Critical or Important finding.

### Task 5: Integrate through protected GitHub

**Files:**
- Publish: branch `codex/linkedin-alpha-launch` and one ready pull request.

**Interfaces:**
- Consumes: the verified launch candidate.
- Produces: synchronized protected `main` containing the launch package.

- [ ] **Step 1: Push and open one ready PR**

Describe the audience, DM-first CTA, asset, verification, and evidence boundaries. Do not add
labels, reviewers, issue comments, or release activity.

- [ ] **Step 2: Require protected checks**

Require Python 3.11 compatibility, `verify`, and CodeQL Python/Actions to pass. Merge only if the
PR head still equals the reviewed candidate SHA.

- [ ] **Step 3: Verify exact merged main**

Fast-forward local `main`, require local/remote equality, one successful push CI, successful
CodeQL, and a clean worktree.

- [ ] **Step 4: Clean up and hand off**

Remove the owned worktree and feature branches. Give the owner the final post, image path, alt
text, posting sequence, and DM workflow. Do not post to LinkedIn on the owner's behalf.
