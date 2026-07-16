# ScopeProof CI Trigger Deduplication Design

## Reproduced finding

ScopeProof's CI workflow currently listens to every `push` and every `pull_request`. A pushed
feature branch with an open PR therefore runs the complete CI workflow twice for the same head
SHA.

This was reproduced on two consecutive protected PRs:

- PR #145 head `aefce3350ec6da201db68477e71ba76931b79e81` ran CI once for event `push`
  and once for event `pull_request`.
- PR #146 head `1fdb90743387eed175e40aba1899d2a5852185ec` ran CI once for event `push`
  and once for event `pull_request`.

Both executions repeated Python 3.11 compatibility, the coverage-gated `verify` job, the
deterministic benchmark, and installed-wheel smoke checks. This is duplicate check activity and
can create redundant GitHub notifications even though ScopeProof itself sends no email.

## Root cause

The workflow trigger is:

```yaml
on:
  push:
  pull_request:
```

The unfiltered `push` trigger includes feature branches, while `pull_request` independently runs
for the same feature SHA. The jobs and branch-protection settings are not the cause.

## Decision

Limit the workflow's push trigger to `main` and retain the pull-request trigger:

```yaml
on:
  push:
    branches: [main]
  pull_request:
```

This produces one full CI run for each PR head SHA and one full CI run after that PR merges to
main. It preserves the protected `verify` context on PRs and on main.

## Rejected approaches

1. **Cross-event concurrency cancellation.** A shared concurrency key could race the push and PR
   runs, producing a cancelled check and making required-check behavior harder to reason about.
2. **Remove push entirely.** This would eliminate the independent merged-main CI proof required by
   the project workflow.
3. **Keep both runs.** Rejected because two consecutive PRs already demonstrate the duplicate
   behavior and no evidence boundary benefits from running identical jobs twice.

## Repository changes

- `.github/workflows/ci.yml` changes only the `push` branch filter.
- `tests/test_repository_contracts.py` adds a deterministic contract for main-only pushes plus all
  pull requests.
- `CHANGELOG.md` records the unreleased CI-noise reduction.

No job definition, permission, dependency, application behavior, version, release, branch
protection, CodeQL configuration, Action behavior, API, billing, or monitoring changes.

## Verification and publication

Use test-driven development: add the repository contract first and confirm it fails against the
broad push trigger, then apply the minimal YAML change and confirm it passes. Run repository
contracts, Ruff, the full coverage gate, the 12-case benchmark, dependency integrity, YAML parsing,
and `git diff --check`.

Publish one ready protected-main PR. The PR should demonstrate one `pull_request` CI run and no
feature-branch `push` CI run. Merge only after Python 3.11, `verify`, and CodeQL pass. Require one
merged-main `push` CI run and successful CodeQL on the merge SHA, then clean the owned worktree and
branch. Do not publish a release or create a recurring monitor.
