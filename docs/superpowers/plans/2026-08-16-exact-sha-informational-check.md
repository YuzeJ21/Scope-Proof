# Exact-SHA Informational GitHub Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one opt-in, neutral GitHub Check Run bound to the exact public pull-request head and validated criteria-source snapshot.

**Architecture:** Extend the existing pure GitHub Action planner with strict Pydantic Check models, then add one bounded same-origin publisher and one runner entry point. The trusted-base workflow invokes the new Check path and stops invoking comment publication; existing comment APIs remain backward compatible.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, pytest, GitHub Actions YAML, uv.

## Global Constraints

- The custom check name is exactly `ScopeProof evidence summary (informational)`.
- Every custom check finishes with GitHub conclusion `neutral`.
- External IDs are exactly `scopeproof-check:v1:{repository}:{pr_number}:{head_sha}`.
- The publisher uses `https://api.github.com`, a 15-second timeout, no redirects, no retries, at
  most one PR read, at most five 100-item Check pages, and at most one write.
- Never execute pull-request code, tests, hooks, installers, build commands, or downloaded artifacts.
- Use the unprivileged `pull_request` event; never use `pull_request_target` to inspect or execute
  pull-request content.
- Keep the workflow opt-in through the exact `scopeproof-review` label.
- Keep `SCOPEPROOF_REQUIRED_CHECK=false`; do not modify branch protection.
- Keep the existing comment planner, publisher, and runner flag backward compatible but unused by
  the updated workflow.
- Every new request, response, plan, and output shape is Pydantic-validated.
- Stage 1 remains `closed_not_pursued_by_owner` and all historical external-evidence counts remain
  zero.
- Preserve `.coverage 2` byte-for-byte and never stage it.

---

### Task 1: Add strict pure Check planning

**Files:**
- Modify: `tests/github_action/test_contract.py`
- Modify: `scopeproof_core/github_action.py`

**Interfaces:**
- Consumes: existing `EventContext`, `CriteriaSourceProvenance`, and rendered ScopeProof report text.
- Produces: `CheckMode`, `ExistingCheckRun`, `CheckRunContext`, `CheckRunOutput`, `CheckRunPlan`,
  `check_external_id(context)`, `render_informational_check(context, verdict, content)`, and
  `plan_check(context, existing_checks, verdict, content)`.

- [ ] **Step 1: Write failing pure-planner tests**

Add literal assertions that a valid non-fork context produces a create plan with exact name,
external ID, head SHA, `neutral` conclusion, criteria-source digests, and evidence-boundary copy.
Add separate tests proving a trusted exact-identity same-head Check updates, a changed or foreign
identity creates, duplicate trusted identities raise, forks skip, and invalid Check IDs, external
IDs, repositories, PR numbers, SHAs, conclusions, and App identities fail Pydantic validation.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run python -m pytest tests/github_action/test_contract.py -q
```

Expected: failures because the Check models and planner do not exist.

- [ ] **Step 3: Implement the minimal pure models and planner**

Use strict, frozen, `extra="forbid"` Pydantic models. Require one positive `check_run_id` only for
update mode, always emit `neutral`, trust only App slug `github-actions`, and raise on more than one
exact trusted existing Check. Render the fixed evidence boundary and criteria-source provenance
before bounded report content.

- [ ] **Step 4: Run pure planner tests and the existing comment tests**

Run:

```bash
uv run python -m pytest tests/github_action/test_contract.py -q
```

Expected: all contract tests pass and existing comment semantics remain unchanged.

- [ ] **Step 5: Commit Task 1 intentionally**

```bash
git add scopeproof_core/github_action.py tests/github_action/test_contract.py
git commit -m "feat: plan neutral exact-head checks"
```

### Task 2: Publish bounded same-origin Check requests

**Files:**
- Modify: `tests/github_action/test_publisher.py`
- Modify: `scopeproof_core/github_action_publisher.py`

**Interfaces:**
- Consumes: `CheckRunContext`, `CheckRunPlan`, and pure `plan_check`.
- Produces: `GitHubCheckPublicationError`, strict private Pydantic API response/request models, and
  `publish_check(context, verdict, content, token, transport=None) -> CheckRunPlan`.

- [ ] **Step 1: Write failing publisher tests**

Add real `httpx.MockTransport` boundary tests with complete GitHub-shaped fixtures. Cover:

- fork and empty-token paths make zero requests;
- live PR repository, number, open state, non-fork status, and head must match exactly before write;
- same-head trusted external ID PATCHes one positive ID;
- changed head or foreign App/external ID POSTs a new Check;
- request payload uses exact name, head, external ID, completed status, neutral conclusion, and
  validated output;
- malformed responses, duplicate trusted checks, status errors, repeated or sixth pages, and PR,
  SHA, repository, check-ID, URL, or actor mismatches fail before mutation;
- every request URL remains under `https://api.github.com/repos/{context.repository}/`; and
- the token appears only in the Authorization header.

- [ ] **Step 2: Run publisher tests and verify RED**

Run:

```bash
uv run python -m pytest tests/github_action/test_publisher.py -q
```

Expected: failures because `publish_check` and its validated API boundary do not exist.

- [ ] **Step 3: Implement the minimal publisher**

Use a fixed-base `httpx.Client(follow_redirects=False, timeout=15.0)`. Validate the live PR first.
Construct page paths locally with integer pages 1 through 5 and never follow `Link` URLs. Parse
every response with strict private Pydantic models. Serialize create/update bodies from a strict
request model. Wrap malformed, stale, ambiguous, page-budget, and HTTP failures in
`GitHubCheckPublicationError` without including the token.

- [ ] **Step 4: Run publisher and planner tests**

Run:

```bash
uv run python -m pytest tests/github_action/test_publisher.py tests/github_action/test_contract.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2 intentionally**

```bash
git add scopeproof_core/github_action_publisher.py tests/github_action/test_publisher.py
git commit -m "feat: publish bounded informational checks"
```

### Task 3: Bind the runner to validated criteria and preserve saved reviews

**Files:**
- Modify: `tests/github_action/test_runner.py`
- Modify: `scopeproof_core/github_action_runner.py`
- Modify: `tests/github_action/test_publisher.py`

**Interfaces:**
- Consumes: exact event JSON, exact requirements bytes, validated confirmation JSON, report text,
  optional token, and `publish_check`.
- Produces: `build_check_context(event_path, requirements_path, confirmation_path)`,
  `publish_event_check(...) -> CheckMode`, and runner flags `--requirements`, `--confirmation`, and
  `--publish-check`.

- [ ] **Step 1: Write failing runner and non-mutation tests**

Add tests proving the runner validates criteria-source bytes instead of trusting
`--requirements-confirmed`, includes exact provenance in its plan, skips fork/missing-token paths,
and routes a valid event to the Check publisher. Add a publisher-failure test that writes a real
validated `ReviewState` through `JsonReviewStore`, records file bytes and state fingerprint, forces
a Check API error, and proves both remain unchanged.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run python -m pytest tests/github_action/test_runner.py tests/github_action/test_publisher.py -q
```

Expected: failures because the validated Check runner path does not exist.

- [ ] **Step 3: Implement the minimal runner path**

Reuse `validate_requirements_confirmation`. Do not infer criteria provenance from event text or a
Boolean. Keep existing comment functions and `--publish-comment` behavior unchanged. Check
publication requires both file paths and a token; validation or publication failure returns a
nonzero CLI exit without touching review storage.

- [ ] **Step 4: Run all Action tests**

Run:

```bash
uv run python -m pytest tests/github_action -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 3 intentionally**

```bash
git add scopeproof_core/github_action_runner.py tests/github_action/test_runner.py tests/github_action/test_publisher.py
git commit -m "feat: bind checks to confirmed criteria"
```

### Task 4: Activate the neutral Check in trusted-base workflows

**Files:**
- Modify: `tests/github_action/test_workflow_files.py`
- Modify: `.github/workflows/scopeproof.yml`
- Modify: `examples/github-actions/scopeproof.yml`

**Interfaces:**
- Consumes: the runner flags and exact checked-in requirements/confirmation files.
- Produces: one opt-in trusted-base Check publication step with `checks: write` and no workflow
  comment publication.

- [ ] **Step 1: Write failing executable workflow-contract tests**

Parse both YAML files and assert the `pull_request` event, job label predicate, base-SHA checkout, immutable action
pins, `persist-credentials: false`, `checks: write`, `pull-requests: read`, and
`SCOPEPROOF_REQUIRED_CHECK=false`. Assert the publish command supplies exact requirements,
confirmation, report, verdict, and `--publish-check`; reject head checkout, head execution,
`pull_request_target`, pull-request-head checkout, `git fetch`, `gh pr checkout`, and workflow
`--publish-comment`.

- [ ] **Step 2: Run the workflow tests and verify RED**

Run:

```bash
uv run python -m pytest tests/github_action/test_workflow_files.py -q
```

Expected: failures because checks permission and `--publish-check` are absent.

- [ ] **Step 3: Implement the minimal workflow changes**

Change the trigger to `pull_request`, add `checks: write`, set `pull-requests: read`, and replace the workflow comment publication step
with exact-file Check publication for labeled non-fork PRs. Preserve trusted-base checkout,
no-credential checkout, no target-code execution, step summary, artifact upload, and conservative
missing-report content.

- [ ] **Step 4: Run all Action and repository-contract tests**

Run:

```bash
uv run python -m pytest tests/github_action tests/test_repository_contracts.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4 intentionally**

```bash
git add .github/workflows/scopeproof.yml examples/github-actions/scopeproof.yml tests/github_action/test_workflow_files.py
git commit -m "feat: emit opt-in exact-head checks"
```

### Task 5: Align public guidance and pin the copyable implementation

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/github-action.md`
- Modify: `docs/github-action-external-validation.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `examples/github-actions/scopeproof.yml`
- Modify: `tests/github_action/test_workflow_files.py`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: the full SHA of Task 4's implementation commit.
- Produces: current, non-overclaiming setup guidance and one full-SHA-pinned copyable workflow.

- [ ] **Step 1: Write failing documentation and source-pin contracts**

Require public guidance to state the exact check name, exact-head history behavior, same-head
idempotency, neutral-only conclusion, criteria-source binding, fork/missing-token/stale-head skip or
fail-closed behavior, comment backward-compatibility boundary, and absence from required branch
protection. Update the source-pin contract to require the full Task 4 commit SHA and prove that
commit contains `--publish-check`, `publish_check`, and `CheckRunPlan`.

- [ ] **Step 2: Run focused contracts and verify RED**

Run:

```bash
uv run python -m pytest tests/github_action/test_workflow_files.py tests/test_repository_contracts.py -q
```

Expected: failures because guidance and the copyable pin still describe comment-only behavior.

- [ ] **Step 3: Update guidance and pin the preceding implementation commit**

Describe engineering evidence only. Keep Stage 1 at 0/5, 0/3, 0/3, 0/3, and 0/2. State that the
Action remains advanced, opt-in, neutral, and non-required; no customer validation, correctness,
runtime, accessibility, demand, or adoption claim is created. Pin the copyable example to Task 4's
full commit SHA.

- [ ] **Step 4: Run focused contracts and lint**

Run:

```bash
uv run python -m pytest tests/github_action tests/test_repository_contracts.py -q
uv run ruff check .
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit Task 5 intentionally**

```bash
git add README.md ROADMAP.md docs/github-action.md docs/github-action-external-validation.md docs/releases/v0.2.3-status-and-next-stages.md examples/github-actions/scopeproof.yml tests/github_action/test_workflow_files.py tests/test_repository_contracts.py
git commit -m "docs: explain exact-head informational checks"
```

### Task 6: Complete verification, review, and PR handoff

**Files:**
- Modify only files required by confirmed in-scope test or review findings.

**Interfaces:**
- Consumes: final feature branch.
- Produces: a clean, independently reviewed, ready-for-review PR; no merge.

- [ ] **Step 1: Run final local verification**

Run Ruff, all Action tests, complete suite with combined coverage at least 95 percent, repository
contracts, acceptance benchmark, comparison benchmark, two clean wheel builds, artifact inventory,
dependency validation, source/installed version equality, installed CLI and benchmarks, loopback
workbench health, installed-wheel Chromium, supported Python lanes, Windows compatibility where
locally available, diff check, commit audit, and `.coverage 2` hash verification.

- [ ] **Step 2: Obtain independent review**

Request review of the exact final head. Repair every actionable Critical or Important finding with
a failing regression first, rerun affected and full verification, and request another exact-head
review until none remain.

- [ ] **Step 3: Push and open the ready PR**

Push `codex/exact-sha-informational-check` and open a ready PR titled
`feat: add exact-head informational check lifecycle`. Include exact base/head/tree, behavior,
boundaries, local evidence, review result, and protected-file proof.

- [ ] **Step 4: Monitor hosted checks**

Wait for every available check to reach a terminal conclusion. Repair only confirmed in-scope
failures test-first on the same branch. Do not merge.

- [ ] **Step 5: Audit and hand off**

Confirm the PR is current, clean, mergeable, independently reviewed, and green or truthfully
classified. Report the exact owner decision: merge or hold.
