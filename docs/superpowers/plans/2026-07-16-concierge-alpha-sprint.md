# ScopeProof Concierge Alpha Sprint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a verified, manual LinkedIn-DM-first activation path that helps one genuine public-PR participant complete ScopeProof without automating outreach or weakening evidence boundaries.

**Architecture:** Keep activation guidance in existing Markdown and static-site surfaces, with `tests/test_repository_contracts.py` enforcing the cross-file contract. Reuse the existing Pydantic alpha records and participant workflow; add no runtime service, persistence model, dependency, analytics, or contact data.

**Tech Stack:** Markdown, dependency-free HTML, Python 3.12, pytest repository contracts, Ruff, existing ScopeProof CLI and Pydantic alpha models.

## Global Constraints

- Public GitHub pull requests and public HTTPS requirement sources only.
- The participant must own or be explicitly authorized to confirm the normalized criteria.
- Every message is selected, personalized, and sent manually by the repository owner.
- No email, message automation, profile scraping, contact harvesting, recurring follow-up, notification workflow, paid API, LLM API, billing, form backend, analytics, or database.
- No participant name, LinkedIn profile, direct-message transcript, or contact list is committed to the repository.
- No private code, confidential requirement, credential, customer data, or secret is requested or retained.
- ScopeProof does not execute pull-request code or present static implementation candidates as test or runtime verification.
- Recruitment, interest, installation, and technical smokes are funnel events, not product validation.
- Report publication and quotation permission remain separate, explicit, and off by default.
- Do not modify, stage, or delete the unrelated untracked `.coverage 2` file.
- Do not modify or comment on GitHub issue #3 until a genuine public LinkedIn post URL exists.

## File map

- `docs/launch/linkedin-alpha-playbook.md`: owner-facing manual outreach, qualification, and routing guidance.
- `docs/alpha/concierge-host-checklist.md`: new owner-facing index for the supervised trial.
- `ROADMAP.md`: Stage 1 navigation to the owner checklist.
- `site/index.html`: public eligibility and participant quickstart actions.
- `tests/test_repository_contracts.py`: deterministic copy, link, privacy, and no-automation contracts.

---

### Task 1: Add a bounded DM-first outreach sequence

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `docs/launch/linkedin-alpha-playbook.md`

**Interfaces:**
- Consumes: the existing public-alpha qualification fields and inbound response routing in `docs/launch/linkedin-alpha-playbook.md`.
- Produces: warm, cold, and one-follow-up manual outreach copy that Task 2 links from the host checklist.

- [ ] **Step 1: Write the failing outreach contract**

Add this test immediately after `test_linkedin_alpha_launch_package_is_current_and_truthful`:

```python
def test_concierge_dm_first_outreach_is_manual_bounded_and_truthful() -> None:
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## DM-first outreach",
        "### Warm-contact message",
        "### Cold-contact message",
        "### One optional follow-up",
        "no sooner than seven days",
        "Do not send another message",
        "sent manually",
        "Do not automate",
        "Do not send private code",
        "genuine public PR",
        "own or are authorized to confirm",
        "No paid LLM API",
    ):
        assert required_text in playbook

    assert "I noticed your public work on [verified public project or PR]" in playbook
    assert "I know your team needs" not in playbook
    assert "ScopeProof customers" not in playbook
    assert "validated accuracy" not in playbook
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_concierge_dm_first_outreach_is_manual_bounded_and_truthful
```

Expected: FAIL because `## DM-first outreach` is absent.

- [ ] **Step 3: Add the minimal outreach section**

Insert this section before `## First-response DM` in `docs/launch/linkedin-alpha-playbook.md`:

```markdown
## DM-first outreach

Use this sequence for five to ten carefully selected product managers, QA practitioners, or
engineers whose relevant role or public work the owner has verified. Every message is personalized,
reviewed, and sent manually. Do not automate messages, scrape profiles, harvest contacts, invent
familiarity, or commit contact details or transcripts to the repository.

Before sending, verify the person's current role or relevant public work from information they made
public. Reference only a fact you inspected. Do not imply knowledge of private work, team needs, or
acceptance criteria.

### Warm-contact message

> Hi [first name] — I built ScopeProof, a local-first evidence assistant for one narrow question:
> does a public PR contain auditable implementation and test evidence for acceptance criteria its
> source owner confirmed? I am looking for one supervised public-alpha case. Do you currently have
> a genuine public PR whose requirements you own or are authorized to confirm? No paid LLM API is
> involved. Please do not send private code, credentials, customer information, or confidential
> requirements. If the answer is no, there is nothing else you need to do.

### Cold-contact message

> Hi [first name] — I noticed your public work on [verified public project or PR], so I am asking a
> narrow question rather than assuming anything about your private work. I built ScopeProof, a
> local-first evidence assistant that maps source-owner-confirmed acceptance criteria to auditable
> implementation and test candidates in a genuine public PR. Do you have a public PR whose criteria
> you own or are authorized to confirm and would you consider one supervised ten-minute alpha
> review? No paid LLM API is involved. Please do not send private code, credentials, customer
> information, or confidential requirements. A no or no response ends the request.

### One optional follow-up

Send this manually no sooner than seven days after the first message and only when the recipient has
not replied:

> One brief follow-up on ScopeProof's supervised public-PR alpha. If you do not have a qualifying
> public PR or are not interested, no reply is needed and I will not follow up again. Please do not
> send private or confidential material.

Do not send another message after this follow-up, after any decline, or after a request to stop.
Interest, replies, and message counts are not product validation.
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
uv run pytest -q \
  tests/test_repository_contracts.py::test_linkedin_alpha_launch_package_is_current_and_truthful \
  tests/test_repository_contracts.py::test_concierge_dm_first_outreach_is_manual_bounded_and_truthful
```

Expected: `2 passed`.

- [ ] **Step 5: Commit the outreach slice**

```bash
git add tests/test_repository_contracts.py docs/launch/linkedin-alpha-playbook.md
git diff --cached --check
git commit -m "docs: add bounded alpha outreach sequence"
```

Expected: one commit containing only the test and playbook.

---

### Task 2: Add the concierge host checklist and navigation

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Create: `docs/alpha/concierge-host-checklist.md`
- Modify: `docs/launch/linkedin-alpha-playbook.md`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: existing release installation, qualification, confirmation, quickstart, dogfood protocol, outcome, and outreach documents.
- Produces: a single owner-facing index and stable navigation from the roadmap and playbook.

- [ ] **Step 1: Write the failing host-checklist contract**

Add this test after the outreach contract:

```python
def test_concierge_host_checklist_indexes_real_alpha_without_contact_data() -> None:
    checklist_path = Path("docs/alpha/concierge-host-checklist.md")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(
        encoding="utf-8"
    )
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert checklist_path.is_file()
    checklist = checklist_path.read_text(encoding="utf-8")
    for required_link in (
        "../../README.md#quickstart",
        "public-pr-qualification-checklist.md",
        "acceptance-criteria-confirmation-template.md",
        "participant-quickstart.md",
        "../dogfood/public-pr-protocol.md",
        "outcome-form.md",
    ):
        assert required_link in checklist

    for status in (
        "not_started",
        "qualified",
        "criteria_confirmed",
        "review_completed",
        "outcome_received",
        "declined",
        "withdrawn",
    ):
        assert f"`{status}`" in checklist

    prohibited_fields = (
        "participant name",
        "email address",
        "linkedin profile",
        "dm transcript",
        "contact list",
    )
    assert all(field not in checklist.lower() for field in prohibited_fields)
    assert "../alpha/concierge-host-checklist.md" in playbook
    assert "docs/alpha/concierge-host-checklist.md" in roadmap
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_concierge_host_checklist_indexes_real_alpha_without_contact_data
```

Expected: FAIL because `docs/alpha/concierge-host-checklist.md` does not exist.

- [ ] **Step 3: Create the owner checklist**

Create `docs/alpha/concierge-host-checklist.md` with this content:

```markdown
# Concierge public-alpha host checklist

This is the repository owner's operational index for one supervised ScopeProof trial. It does not
replace the linked participant instructions or create validation evidence. Use public information
only. Never retain credentials, private source, customer data, or confidential requirements.

## Stage status reference

| Status | Use only when |
| --- | --- |
| `not_started` | No qualification decision exists. |
| `qualified` | Every public-PR qualification condition is explicit. |
| `criteria_confirmed` | The source owner confirmed the normalized atomic criteria before analysis. |
| `review_completed` | ScopeProof completed the deterministic review for the recorded head SHA. |
| `outcome_received` | The participant selected and recorded exactly one bounded outcome. |
| `declined` | The case was out of scope or the recipient declined. |
| `withdrawn` | The participant stopped after initially agreeing. |

Do not fill this repository file with a person or case. Persist only a qualified case through the
existing Pydantic-validated `scopeproof alpha` commands after the required confirmations.

## Host sequence

- [ ] Install and verify the current release using the [README quickstart](../../README.md#quickstart).
- [ ] Select and manually send one approved message from the [LinkedIn alpha playbook](../launch/linkedin-alpha-playbook.md#dm-first-outreach).
- [ ] Apply every [public-PR qualification check](public-pr-qualification-checklist.md).
- [ ] Normalize criteria with the [acceptance-criteria confirmation template](acceptance-criteria-confirmation-template.md), then return them to the source owner for confirmation before analysis.
- [ ] Follow the [ten-minute participant quickstart](participant-quickstart.md), including `scopeproof alpha init` before the review.
- [ ] Conduct the review under the [confirmed dogfood protocol](../dogfood/public-pr-protocol.md). Do not execute the PR or convert static evidence into runtime verification.
- [ ] Let the participant accept, reject, or mark findings ambiguous; do not choose for them.
- [ ] Ask the participant to select exactly one value from the [public-alpha outcome form](outcome-form.md).
- [ ] Record report and quotation consent independently. Both remain off unless explicitly granted.
- [ ] Use a public summary only when the validated case has report consent. Never publish local notes or infer quotation consent.

## Stop and route rules

- Stop on private source, confidential material, missing criteria authority, decline, or withdrawal.
- A public PR without source-owner-confirmed criteria may be a technical smoke only.
- Installation, replies, and technical smokes do not close the roadmap's external validation gate.
- Preserve incomplete and negative outcomes without rewriting them as successes.
```

- [ ] **Step 4: Add navigation without duplicating instructions**

Add this sentence after the opening paragraph in `docs/launch/linkedin-alpha-playbook.md`:

```markdown
The owner runs an accepted case through the single [concierge host checklist](../alpha/concierge-host-checklist.md), which links to the authoritative qualification, confirmation, review, and outcome instructions.
```

Add this sentence after the activation-readiness paragraph in `ROADMAP.md`:

```markdown
The repository owner uses `docs/alpha/concierge-host-checklist.md` as the operational index for a manually recruited supervised trial; the checklist does not itself satisfy either external gate.
```

- [ ] **Step 5: Run the host and existing participant-kit contracts**

Run:

```bash
uv run pytest -q \
  tests/test_repository_contracts.py::test_concierge_host_checklist_indexes_real_alpha_without_contact_data \
  tests/test_repository_contracts.py::test_public_alpha_participant_kit_is_safe_complete_and_actionable
```

Expected: `2 passed`.

- [ ] **Step 6: Commit the host-checklist slice**

```bash
git add tests/test_repository_contracts.py docs/alpha/concierge-host-checklist.md \
  docs/launch/linkedin-alpha-playbook.md ROADMAP.md
git diff --cached --check
git commit -m "docs: add concierge alpha host checklist"
```

Expected: one commit containing the test, checklist, and two navigation edits.

---

### Task 3: Replace the generic LinkedIn destination with qualification

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `site/index.html`

**Interfaces:**
- Consumes: the existing static alpha section and checked-in public-PR qualification checklist.
- Produces: a useful public eligibility action without inventing a personal LinkedIn destination.

- [ ] **Step 1: Change the site contract first and verify RED**

In `test_public_pages_site_and_captioned_demo_are_truthful_and_self_contained`, replace the existing `linkedin_links` block with:

```python
    qualification_url = (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/"
        "docs/alpha/public-pr-qualification-checklist.md"
    )
    assert qualification_url in parser.links
    assert "Check whether your PR qualifies" in html
    assert not any(
        urlsplit(link).hostname == "www.linkedin.com" for link in parser.links
    )
```

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py::test_public_pages_site_and_captioned_demo_are_truthful_and_self_contained
```

Expected: FAIL because the site still links to the generic LinkedIn homepage.

- [ ] **Step 2: Implement the qualification action**

Replace this button in `site/index.html`:

```html
<a class="button button-secondary" href="https://www.linkedin.com/">Open LinkedIn to DM</a>
```

with:

```html
<a class="button button-secondary" href="https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/alpha/public-pr-qualification-checklist.md">Check whether your PR qualifies</a>
```

Keep the adjacent safety copy and primary quickstart action unchanged.

- [ ] **Step 3: Run the site and full repository contracts**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py
```

Expected: all repository contracts PASS.

- [ ] **Step 4: Commit the site slice**

```bash
git add tests/test_repository_contracts.py site/index.html
git diff --cached --check
git commit -m "fix: route alpha site to qualification"
```

Expected: one commit containing only the site contract and HTML change.

---

### Task 4: Verify, review, publish, and synchronize

**Files:**
- Modify only if verification finds an in-scope defect in a file already named by this plan.

**Interfaces:**
- Consumes: Tasks 1–3 and the existing protected GitHub workflow.
- Produces: reviewed commits, a passing pull request, merged `main`, updated Pages, and a manual handoff report.

- [ ] **Step 1: Run formatting and lint verification**

```bash
git diff --check origin/main...HEAD
uv run ruff check .
```

Expected: both commands exit 0.

- [ ] **Step 2: Run the deterministic benchmark**

```bash
uv run scopeproof benchmark
```

Expected: the benchmark exits 0 with zero known must-have False Ready results.

- [ ] **Step 3: Run the full coverage gate**

```bash
uv run pytest -q --cov=scopeproof_core --cov=apps \
  --cov-report=term-missing:skip-covered --cov-fail-under=95
```

Expected: 769 or more tests pass, the one opt-in live test may remain skipped, and total coverage is at least 95 percent.

- [ ] **Step 4: Review the final diff and repository boundary**

```bash
git status --short --branch
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- AGENTS.md ROADMAP.md docs/launch/linkedin-alpha-playbook.md \
  docs/alpha/concierge-host-checklist.md site/index.html tests/test_repository_contracts.py
```

Expected: `.coverage 2` remains untracked and untouched; no issue, workflow, dependency, runtime, contact-data, or unrelated file change appears.

- [ ] **Step 5: Push and open the protected pull request**

```bash
git push -u origin codex/concierge-alpha-sprint-design
gh pr create --repo YuzeJ21/Scope-Proof \
  --base main \
  --head codex/concierge-alpha-sprint-design \
  --title "Improve concierge public-alpha activation" \
  --body $'## Summary\n- add bounded warm, cold, and one-follow-up manual LinkedIn DM guidance\n- add a single owner-facing concierge trial checklist\n- route the public site to public-PR qualification instead of the generic LinkedIn homepage\n\n## Verification\n- uv run ruff check .\n- uv run scopeproof benchmark\n- uv run pytest -q --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95\n- git diff --check origin/main...HEAD\n\n## Evidence boundary\nThese repository changes improve readiness for a manually recruited trial. They are not real-user validation. Stage 1 remains open until a genuine source owner confirms criteria for a real public PR and records an honest participant outcome.'
```

Expected: GitHub returns a new pull-request URL whose body contains the verified summary, test evidence, explicit external-evidence limitation, and no claim of real-user validation.

- [ ] **Step 6: Monitor checks and repair only demonstrated failures**

```bash
gh pr checks --repo YuzeJ21/Scope-Proof --watch --interval 10
```

Expected: required `verify` and all configured checks pass. For a failure, inspect its exact log, reproduce it locally where possible, make the smallest in-scope test-first correction, commit, push, and rerun.

- [ ] **Step 7: Merge and verify remote synchronization**

```bash
gh pr merge --repo YuzeJ21/Scope-Proof --merge --delete-branch
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main
```

Expected: the two SHAs match and contain all sprint commits. Do not create a release solely for documentation and static-site copy.

- [ ] **Step 8: Verify Pages and final repository state**

```bash
gh run list --repo YuzeJ21/Scope-Proof --workflow pages.yml --limit 1
curl -fsSL https://yuzej21.github.io/Scope-Proof/ | \
  grep -F "Check whether your PR qualifies"
git status --short --branch
```

Expected: the latest Pages run passed, the deployed page contains the new action, local and remote `main` match, and only the preserved unrelated `.coverage 2` file remains untracked.

- [ ] **Step 9: Prepare the manual handoff without sending outreach**

Report the exact owner-only sequence from `docs/alpha/concierge-host-checklist.md`: select five to ten relevant practitioners without scraping, personalize one approved DM, qualify a public PR, confirm criteria before analysis, conduct the supervised review, and record the participant-selected outcome and consent. Leave Stage 1 open until genuine evidence exists.
