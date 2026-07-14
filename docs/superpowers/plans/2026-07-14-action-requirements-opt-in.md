# Action Requirements Opt-In Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require an explicit maintainer-controlled `scopeproof-review` label before ScopeProof applies checked-in requirements or publishes a PR comment.

**Architecture:** Gate the complete trusted-base review job at the GitHub workflow boundary rather than changing the evidence engine. Keep the repository workflow and copyable example identical for trigger and condition, and document the label as a per-PR applicability confirmation that is separate from requirements-byte confirmation.

**Tech Stack:** GitHub Actions YAML, Python 3.12 repository-contract tests, pytest, Ruff, Markdown.

## Global Constraints

- Use the exact label `scopeproof-review`.
- Missing applicability means not reviewed, never Ready.
- Preserve trusted-base checkout at `github.event.pull_request.base.sha` with `persist-credentials: false`.
- Never checkout, fetch, or execute pull-request-head code.
- Preserve the existing fork no-write rule and informational `SCOPEPROOF_REQUIRED_CHECK: false` default.
- Do not change evidence matching, findings, gates, schemas, storage, or exports.
- Do not add paid services, APIs, accounts, fork testing, synthetic validation, or notification churn.
- Do not publish a release for this workflow-and-guidance correction.

---

### Task 1: Gate repository and copyable workflows on explicit applicability

**Files:**
- Modify: `tests/github_action/test_workflow_files.py`
- Modify: `.github/workflows/scopeproof.yml`
- Modify: `examples/github-actions/scopeproof.yml`

**Interfaces:**
- Consumes: GitHub's `pull_request_target` event payload and its `pull_request.labels.*.name` projection.
- Produces: one job-level applicability condition with exact label `scopeproof-review`; all existing review steps remain downstream of that condition.

- [ ] **Step 1: Add a failing workflow-contract test**

Add this test to `tests/github_action/test_workflow_files.py`:

```python
def test_action_requires_explicit_per_pr_requirements_applicability() -> None:
    for path in (
        Path(".github/workflows/scopeproof.yml"),
        Path("examples/github-actions/scopeproof.yml"),
    ):
        workflow = path.read_text(encoding="utf-8")
        assert "types: [opened, reopened, synchronize, labeled]" in workflow
        assert (
            "if: contains(github.event.pull_request.labels.*.name, 'scopeproof-review')"
            in workflow
        )
        assert "paths:" not in workflow
        assert "github.event.pull_request.user" not in workflow
```

- [ ] **Step 2: Run the focused test and verify the current workflow fails the contract**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/github_action/test_workflow_files.py::test_action_requires_explicit_per_pr_requirements_applicability -q
```

Expected: FAIL because the current trigger omits `labeled` and the job has no applicability condition.

- [ ] **Step 3: Add the minimal job-level gate to both workflows**

In `.github/workflows/scopeproof.yml` and `examples/github-actions/scopeproof.yml`, change the event list and review job header to:

```yaml
on:
  pull_request_target:
    types: [opened, reopened, synchronize, labeled]

jobs:
  review:
    if: contains(github.event.pull_request.labels.*.name, 'scopeproof-review')
    name: ScopeProof evidence review
```

Do not move or change any review step, permission, base-SHA checkout, fork check, publication command, or Action pin.

- [ ] **Step 4: Run all workflow contracts**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/github_action/test_workflow_files.py -q
```

Expected: all workflow-contract tests pass.

- [ ] **Step 5: Commit the workflow boundary**

```bash
git add tests/github_action/test_workflow_files.py \
  .github/workflows/scopeproof.yml examples/github-actions/scopeproof.yml
git diff --cached --check
git commit -m "fix: require Action review opt-in"
```

### Task 2: Document per-PR applicability separately from byte confirmation

**Files:**
- Modify: `tests/github_action/test_workflow_files.py`
- Modify: `docs/github-action.md`
- Modify: `docs/github-action-external-validation.md`

**Interfaces:**
- Consumes: the exact `scopeproof-review` workflow contract from Task 1.
- Produces: operator guidance that defines who applies the label, when to apply it, and what an absent label means.

- [ ] **Step 1: Add a failing documentation-contract test**

Add this test to `tests/github_action/test_workflow_files.py`:

```python
def test_action_guidance_requires_maintainer_applicability_opt_in() -> None:
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")

    for document in (guide, runbook):
        assert "`scopeproof-review`" in document
        assert "not reviewed, not Ready" in document
    assert "repository maintainer" in guide
    assert "checked-in requirements apply to this PR" in guide
```

- [ ] **Step 2: Run the documentation contract and verify it fails**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/github_action/test_workflow_files.py::test_action_guidance_requires_maintainer_applicability_opt_in -q
```

Expected: FAIL because neither public document explains the opt-in label.

- [ ] **Step 3: Update the Action guide**

In `docs/github-action.md`, add an opt-in section immediately after the safe-preview behavior list that states:

```markdown
## Per-PR requirements applicability

Create the exact `scopeproof-review` repository label during setup. Opening a PR does not authorize
ScopeProof to apply the repository's checked-in requirements. A repository maintainer must first
confirm that the checked-in requirements apply to this PR, then apply `scopeproof-review`.

The requirements-confirmation record binds the approved requirements bytes. The label separately
confirms their applicability to the current PR. Without the label, the review job is skipped: the PR
is not reviewed, not Ready. Keeping the label on the PR allows `synchronize` and `reopened` events to
review later heads under the same checked-in requirements.
```

Also update the opening behavior bullets so they no longer imply every confirmed same-repository PR is automatically reviewed or commented on.

- [ ] **Step 4: Update the external-validation runbook**

In `docs/github-action-external-validation.md`:

- add creation of the exact `scopeproof-review` label to Preconditions;
- in Test 1, open the PR, verify the unlabeled job is skipped, have the repository owner confirm the checked-in requirements apply, and then apply the label;
- state exactly: `Without the label, the PR is not reviewed, not Ready.`;
- retain the label for same-head rerun and subsequent head synchronization.

Do not claim this local policy is genuine external evidence.

- [ ] **Step 5: Run all GitHub Action tests**

Run:

```bash
'/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest tests/github_action -q
```

Expected: all GitHub Action tests pass.

- [ ] **Step 6: Commit documentation and its contract**

```bash
git add tests/github_action/test_workflow_files.py \
  docs/github-action.md docs/github-action-external-validation.md
git diff --cached --check
git commit -m "docs: explain Action review applicability"
```

### Task 3: Verify, publish, and reconcile the protected change

**Files:**
- Verify: all branch changes relative to `origin/main`
- Create outside repository: temporary archive under `/tmp`

**Interfaces:**
- Consumes: Tasks 1 and 2 as one coherent review boundary.
- Produces: a protected merged-main commit with exact-head CI/CodeQL evidence and a synchronized clean local checkout.

- [ ] **Step 1: Run fresh complete local verification**

Run:

```bash
PYTHON='/Users/yjian070/Documents/New project 2/.venv/bin/python'
"$PYTHON" -m ruff check .
"$PYTHON" -m pytest -q
PYTHONPATH="$PWD" "$PYTHON" -m scopeproof_core.cli benchmark
git diff --check origin/main...HEAD
```

Expected: Ruff passes; all offline tests pass with only the intentional live skip; 12 benchmark cases and 13 criteria execute with zero mismatches, zero must-have False Ready, and zero false blockers; diff check is clean.

- [ ] **Step 2: Verify the committed archive carries the same workflow boundary**

After all intended commits exist, create a fresh `/tmp/scopeproof-action-opt-in-archive` directory, extract `git archive HEAD`, and run:

```bash
cd /tmp/scopeproof-action-opt-in-archive
PYTHONPATH="$PWD" '/Users/yjian070/Documents/New project 2/.venv/bin/python' -m pytest \
  tests/github_action/test_workflow_files.py -q
```

Expected: the archived committed workflow contracts pass outside the worktree.

- [ ] **Step 3: Review exact branch scope**

Run:

```bash
git status --short --branch
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- \
  .github/workflows/scopeproof.yml examples/github-actions/scopeproof.yml \
  tests/github_action/test_workflow_files.py docs/github-action.md \
  docs/github-action-external-validation.md
```

Expected: only the design, plan, two workflows, Action docs, and workflow-contract tests are in scope.

- [ ] **Step 4: Push and open one ready protected PR**

Push `codex/action-requirements-opt-in` once and open a ready PR targeting `main`. The PR must explain the PR #87 reproduction, the label applicability boundary, the expected one final old-base automatic comment, and the no-release decision. Do not post manual issue or status comments.

- [ ] **Step 5: Require exact-head protected checks before merge**

Confirm the PR head SHA matches the pushed branch. Wait for both `verify` runs, ScopeProof evidence review, both CodeQL analyses, and aggregate CodeQL. The old base workflow can publish one final unrelated comment; do not rerun or duplicate it. Fix only genuine failures regression-first.

- [ ] **Step 6: Squash-merge, verify exact main SHA, and clean owned state**

Squash-merge only with `--match-head-commit`. Then require main CI and CodeQL success on the exact merge SHA. Fast-forward local `main`, remove `.worktrees/action-requirements-opt-in`, prune worktrees, and delete only the local feature branch. Confirm local `main == origin/main` and the worktree is clean.

- [ ] **Step 7: Select the next evidence-backed goal item**

Recheck issue #3 external responses, open PRs, release, required check, Action pins, Dependabot and CodeQL alerts, and documentation drift. Do not release for this slice. Keep the persistent goal active and rotate immediately to the next justified local improvement or exact external waiting condition.
