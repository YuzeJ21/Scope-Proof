# ScopeProof Commercial Validation Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a truthful, inbound-only commercial-discovery layer to the existing genuine public-alpha workflow without claiming customers, validated pricing, or demand.

**Architecture:** Keep this sprint in public documentation, GitHub issue forms, the static site, and deterministic repository contracts. Reuse the existing public-alpha qualification and local outcome workflow; add no runtime schema, dependency, service, account, billing path, or private-repository access.

**Tech Stack:** Markdown, GitHub issue-form YAML, static HTML/CSS, Python pytest repository contracts, existing Ruff/pytest/ScopeProof benchmark toolchain.

## Global Constraints

- No paid OpenAI, LLM, or other model APIs.
- No billing, payment processor, checkout, invoice, license key, subscription, organization, or new account.
- No private repositories, hosted customer source code, or fork testing.
- No email, automated outreach, scraping, mass messaging, contact lists, LinkedIn messages, or social posts.
- Do not execute untrusted pull-request code or invent participant evidence.
- Preserve the evaluation-only use policy and `.coverage 2` byte-for-byte.
- USD 99 per team per month and USD 999 per team per year are research hypotheses only.
- A commercial signal requires a completed genuine public-PR review and an explicit participant response.
- Local Pro and every commercial implementation remain deferred until the documented evidence gate passes.

---

### Task 1: Canonical commercial-discovery guide and roadmap gate

**Files:**
- Create: `docs/commercialization/design-partner-sprint.md`
- Modify: `ROADMAP.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: Existing Stage 1 genuine-alpha requirements in `ROADMAP.md` and the approved commercial-validation design.
- Produces: One canonical `docs/commercialization/design-partner-sprint.md` path and a `Stage 2 — Commercial discovery` gate consumed by the public surfaces in Task 3.

- [ ] **Step 1: Write the failing guide and roadmap contract**

Append this test to `tests/test_repository_contracts.py`:

```python
def test_commercial_validation_guide_and_roadmap_are_evidence_gated() -> None:
    guide_path = Path("docs/commercialization/design-partner-sprint.md")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert guide_path.is_file()
    guide = guide_path.read_text(encoding="utf-8")
    for required in (
        "30-day Design Partner Sprint",
        "free",
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "after a genuine participant completes a review",
        "waiting_for_external_participant_evidence",
        "Local Pro",
    ):
        assert required in guide
    for non_evidence in (
        "stars",
        "views",
        "downloads",
        "issue submissions",
        "constructed demos",
        "synthetic cases",
        "owner-authored examples",
    ):
        assert non_evidence in guide

    assert "## Stage 2 — Commercial discovery" in roadmap
    assert "two independent completed participants" in roadmap
    assert "voluntarily agree to discuss the team-price hypothesis" in roadmap
    assert "Local Pro remains deferred" in roadmap
    assert "not revenue, orders, customers, paid demand, or willingness to pay" in roadmap
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_commercial_validation_guide_and_roadmap_are_evidence_gated
```

Expected: FAIL because the guide and Stage 2 gate do not exist.

- [ ] **Step 3: Create the canonical guide**

Create `docs/commercialization/design-partner-sprint.md` with these exact sections:

```markdown
# ScopeProof 30-day Design Partner Sprint

## Current state
## Qualifying case
## Ordered 30-day queue
## Signals recorded only after a completed review
## Research-only price hypotheses
## Evidence that does not count
## Continue, narrow, pivot, and stop gates
## Local Pro decision gate
## Deferred capabilities
## Current waiting condition
```

Define the free inbound review, required public inputs, one participant-selected outcome, completion-time bucket, decision impact, reuse intent, optional price discussion, exact non-evidence list, and every deferred capability from the approved design. State that no billing or paid product is active and that a price response is voluntary and not a purchase agreement.

- [ ] **Step 4: Insert the commercial-discovery stage in the roadmap**

Rename the existing limited beta and expansion sections to Stages 3 and 4. Insert `## Stage 2 — Commercial discovery` after genuine public alpha. Require all Stage 1 gates plus two independent reuse intentions, two voluntary team-price discussions, decision-timing relevance, zero confirmed False Ready, and preserved misleading candidates/friction. State that these are not revenue, orders, customers, paid demand, or willingness to pay and that Local Pro remains deferred.

- [ ] **Step 5: Run the focused contract**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_commercial_validation_guide_and_roadmap_are_evidence_gated
```

Expected: PASS.

- [ ] **Step 6: Commit the guide and roadmap gate**

```bash
git add docs/commercialization/design-partner-sprint.md ROADMAP.md tests/test_repository_contracts.py
git commit -m "docs: define commercial validation gate"
```

### Task 2: Bounded participant feedback intake

**Files:**
- Modify: `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: The existing public-alpha case submission, exact reviewed head SHA, and completed participant outcome.
- Produces: GitHub issue-form fields `alpha_case_issue`, `reviewed_head_sha`, `completion_time`, `useful_gap_category`, `decision_impact`, `reuse_intent`, and `design_partner_interest`.

- [ ] **Step 1: Write the failing intake contract**

Append:

```python
def test_public_alpha_feedback_collects_bounded_commercial_signals() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(
        encoding="utf-8"
    )
    for field_id in (
        "public_pr",
        "alpha_case_issue",
        "reviewed_head_sha",
        "public_requirements_url",
        "source_owner",
        "outcome",
        "completion_time",
        "useful_gap_category",
        "decision_impact",
        "reuse_intent",
        "design_partner_interest",
        "friction",
        "limitations",
        "safety",
    ):
        assert f"id: {field_id}" in template

    for required_text in (
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "only after completing a genuine review",
        "Prefer not to answer",
        "submission alone is not validation",
    ):
        assert required_text in template

    forbidden_ids = (
        "name",
        "email",
        "linkedin_profile",
        "employer",
        "private_repository",
        "payment",
        "purchase_commitment",
        "sales_contact",
    )
    assert all(f"id: {field_id}" not in template for field_id in forbidden_ids)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_public_alpha_feedback_collects_bounded_commercial_signals
```

Expected: FAIL on `alpha_case_issue`.

- [ ] **Step 3: Extend the issue form**

Keep the existing safety boundary and add bounded inputs/dropdowns with the exact produced IDs. Require the public PR, alpha-case issue, public HTTPS requirements source, exact head SHA, source-owner confirmation, outcome, completion time, gap category, decision impact, reuse intent, limitations, and safety confirmation. Make `design_partner_interest` required but include `Prefer not to answer` so the response remains voluntary.

Use these exact completion-time options:

```yaml
- Under 5 minutes
- 5 to 10 minutes
- More than 10 minutes
- Did not reach an inspectable report
```

Use these exact reuse options:

```yaml
- Yes, I intend to use ScopeProof on another PR
- No
- Unsure
- Prefer not to answer
```

Label both prices as research hypotheses only, ask only after genuine use, and state that the response is not a purchase agreement or permission for sales contact.

- [ ] **Step 4: Parse the issue form and run the contract**

Run:

```bash
ruby -e 'require "yaml"; YAML.safe_load(File.read(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml"), aliases: true); puts "valid"'
uv run pytest -q tests/test_repository_contracts.py::test_public_alpha_feedback_collects_bounded_commercial_signals
```

Expected: `valid` and PASS.

- [ ] **Step 5: Commit the intake**

```bash
git add .github/ISSUE_TEMPLATE/public-alpha-feedback.yml tests/test_repository_contracts.py
git commit -m "docs: collect bounded commercial signals"
```

### Task 3: Truthful public positioning and participant handoff

**Files:**
- Modify: `README.md`
- Modify: `site/index.html`
- Modify: `docs/alpha/participant-quickstart.md`
- Modify: `docs/alpha/outcome-form.md`
- Modify: `docs/alpha/concierge-host-checklist.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `docs/commercialization/design-partner-sprint.md` and the participant feedback issue template.
- Produces: One public inbound route to the case form, one post-review feedback route, and consistent free/research-only commercial copy across public surfaces.

- [ ] **Step 1: Write the failing public-surface contract**

Append:

```python
def test_public_design_partner_positioning_is_free_inbound_and_noncommercial() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(encoding="utf-8")
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(
        encoding="utf-8"
    )
    public_surfaces = "\n".join((readme, site))

    guide = "docs/commercialization/design-partner-sprint.md"
    feedback_url = (
        "https://github.com/YuzeJ21/Scope-Proof/issues/new?"
        "template=public-alpha-feedback.yml"
    )
    assert guide in readme
    assert guide in quickstart
    assert "docs/commercialization/design-partner-sprint.md" in site
    assert feedback_url in site
    assert feedback_url in quickstart
    assert "../commercialization/design-partner-sprint.md" in outcome
    assert "../commercialization/design-partner-sprint.md" in checklist

    for required in (
        "free design-partner review",
        "No paid product or billing is active",
        "pricing question is optional research after product use",
        "public-repository-only",
        "acceptance-coverage assistant",
        "not an AI code reviewer",
    ):
        assert required in public_surfaces
    for unsupported_claim in (
        "ScopeProof customers",
        "validated pricing",
        "paid plan is available",
        "proven commercial demand",
    ):
        assert unsupported_claim not in public_surfaces

    assert "incomplete review" in site
    assert "participant-selected outcome" in quickstart
    assert "not commercial validation" in outcome
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_public_design_partner_positioning_is_free_inbound_and_noncommercial
```

Expected: FAIL because the guide and feedback route are not linked.

- [ ] **Step 3: Update README and the static site**

Add a short `Free design-partner review` paragraph to README Product status and the site alpha section. Keep the existing case-submission CTA as the only inbound entry. Add a secondary post-review feedback CTA and a link to the canonical sprint guide. State the exact free/no-billing/public-only/research-only boundaries without publishing the numeric price anchors on the landing page.

- [ ] **Step 4: Update participant and owner handoffs**

In the participant quickstart, preserve Minutes 1–10 and add a post-review section linking the feedback issue and guide. In the outcome form, distinguish the validated local outcome from optional public commercial research. In the concierge checklist, link the guide and feedback issue after the participant records the local outcome; preserve the passive owner rule and separate report/quote consent.

- [ ] **Step 5: Run focused and existing public-alpha contracts**

Run:

```bash
uv run pytest -q \
  tests/test_repository_contracts.py::test_public_design_partner_positioning_is_free_inbound_and_noncommercial \
  tests/test_repository_contracts.py::test_public_alpha_participant_kit_is_safe_complete_and_actionable \
  tests/test_repository_contracts.py::test_inbound_alpha_case_submission_path_is_public_safe_and_owner_passive \
  tests/test_repository_contracts.py::test_public_pages_site_and_captioned_demo_are_truthful_and_self_contained
```

Expected: 4 passed.

- [ ] **Step 6: Commit public positioning**

```bash
git add README.md site/index.html docs/alpha/participant-quickstart.md docs/alpha/outcome-form.md docs/alpha/concierge-host-checklist.md tests/test_repository_contracts.py
git commit -m "docs: publish design partner validation path"
```

### Task 4: Final verification, GitHub synchronization, and honest handoff

**Files:**
- Verify only: all changed files and existing product/test surfaces

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: A verified PR merged to protected `main`, synchronized local checkout, verified Pages deployment, and one honest external state.

- [ ] **Step 1: Validate deterministic docs and issue contracts**

Run:

```bash
uv sync --frozen --extra dev
ruby -e 'require "yaml"; Dir[".github/ISSUE_TEMPLATE/*.yml"].each { |path| YAML.safe_load(File.read(path), aliases: true) }; puts "valid"'
uv run ruff check .
uv run pytest -q tests/test_repository_contracts.py
uv run pytest -q tests/alpha tests/cli/test_cli.py
uv run scopeproof benchmark
```

Expected: YAML valid, Ruff passed, focused suites passed, benchmark 12 cases with zero mismatches and zero must-have False Ready.

- [ ] **Step 2: Run the complete verified suite**

Run:

```bash
uv run pytest -q --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95
```

Expected: full suite passes with at least 95% coverage.

- [ ] **Step 3: Run documentation, terminology, and sensitive-field audits**

Run:

```bash
git diff --check origin/main...HEAD
! rg -ni 'ScopeProof customers|validated pricing|paid plan is available|proven commercial demand' README.md site/index.html
! rg -n '^\s+id: (name|email|linkedin_profile|employer|private_repository|payment|purchase_commitment|sales_contact)$' .github/ISSUE_TEMPLATE/public-alpha-feedback.yml
test "$(shasum -a 256 '.coverage 2' | awk '{print $1}')" = "b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb"
git status --short
```

Expected: diff check passes, both prohibited searches return no matches, the hash comparison passes, and status shows only intentional branch changes plus the unchanged untracked `.coverage 2`.

- [ ] **Step 4: Verify the public site at desktop and 390 px**

Serve `site/` locally, inspect desktop and 390 px layouts, and assert `scrollWidth == clientWidth`, visible CTAs, no clipped text, and correct free/no-billing/public-only disclosure.

- [ ] **Step 5: Push one branch and open one ready PR**

```bash
git push -u origin codex/scopeproof-commercial-validation-sprint
gh pr create --base main --head codex/scopeproof-commercial-validation-sprint \
  --title "Add commercial validation sprint" \
  --body $'## Summary\n- add a canonical 30-day inbound commercial-validation guide and evidence-gated roadmap stage\n- collect bounded timing, decision-impact, reuse, and optional design-partner signals after genuine reviews\n- align the public site, README, and participant handoffs with the free, no-billing research boundary\n\n## Verification\n- YAML issue-form parsing\n- Ruff\n- repository contracts and alpha/CLI suites\n- deterministic benchmark\n- full pytest suite with at least 95% coverage\n- desktop and 390 px public-site checks\n\n## Evidence boundary\nThis PR creates a validated intake and research workflow. It does not claim participants, customers, revenue, validated pricing, paid demand, or willingness to pay. Local Pro, private repositories, billing, commercial licensing, integrations, and enterprise capabilities remain deferred.'
```

Do not add issue or PR progress comments.

- [ ] **Step 6: Wait for protected checks and merge**

Require `verify` and `CodeQL` success. Fix real failures, rerun the affected local checks, push the fix, and merge normally only after every required check succeeds.

- [ ] **Step 7: Synchronize and verify public Pages**

Fast-forward local `main` to `origin/main`, confirm identical SHAs, wait for the merge-triggered Pages/CI/CodeQL runs, and verify the public site returns HTTP 200 with the design-partner copy and links.

- [ ] **Step 8: Record the exact external state**

Use the one Stage 1 audit already completed for this goal. If there is no non-owner qualifying completed case, report exactly `waiting_for_external_participant_evidence`; do not create or poll for evidence.
