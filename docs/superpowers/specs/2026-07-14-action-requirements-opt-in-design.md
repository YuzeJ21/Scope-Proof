# ScopeProof Action Requirements Opt-In Design

## Problem

ScopeProof's trusted-base Action currently treats a checked-in, hash-confirmed
`.scopeproof/requirements.txt` as applicable to every same-repository pull request. PR #87 changed
runtime-evidence labels, but the workflow evaluated it against the repository's older demo
criterion, "The README must state that this repository is used for ScopeProof Action validation."
The workflow then published an unrelated **Blocked** comment.

The gate result was conservative and internally consistent with the supplied criterion. The defect
is earlier in the data flow: requirements-byte confirmation proves which text an owner confirmed,
but there is no separate, auditable signal that those requirements apply to the current PR.

## Goals

- Require an explicit repository-maintainer opt-in before applying checked-in requirements to a PR.
- Generate no ScopeProof report, artifact, or PR comment for ordinary unlabeled maintenance PRs.
- Preserve the current informational review, verdict, idempotent-comment, rerun, and head-SHA behavior
  after opt-in.
- Preserve trusted-base execution and never execute pull-request-head code.
- Keep missing applicability conservative: it means **not reviewed**, never Ready.

## Non-goals

- Infer requirements applicability from changed paths, keywords, PR prose, or author identity.
- Change evidence matching, findings, gate decisions, schemas, storage, or exports.
- Turn ScopeProof into a required check.
- Add a generic review, security, or auto-fix feature.
- Add fork testing, paid services, tokens, accounts, or synthetic validation.

## Considered approaches

### 1. Maintainer-controlled label opt-in — selected

Use the exact label `scopeproof-review`. The `pull_request_target` workflow listens for `labeled` in
addition to its existing events, and the review job runs only while the event's PR contains that
label. A maintainer applies the label only after confirming that the checked-in requirements are
intended for that PR.

Advantages:

- The applicability decision is explicit and visible on the PR.
- GitHub restricts label management to users with repository triage or greater permission.
- Keeping the label on the PR naturally allows `synchronize` and `reopened` events to rerun the
  review for the new head.
- Unlabeled PRs create no ScopeProof comment or report.

Cost: repositories must create and apply one documented label. This is a small, free operator step
and is preferable to silently applying unrelated criteria.

### 2. Changed-path inference — rejected

The workflow could run only when a PR changes files suggested by the requirement text or a path
configuration. Paths are not acceptance criteria, and the relationship can be incomplete or
cross-cutting. This would replace an explicit applicability decision with another heuristic and
could produce both irrelevant reviews and missed reviews.

### 3. Manual `workflow_dispatch` — rejected

A manually dispatched workflow would minimize automatic activity, but it would require a separate
PR-number input and weaken the existing PR-event audit and rerun path. It is more operator work than
a maintainer label and makes the review less discoverable on the PR.

## Workflow contract

Both the repository workflow and copyable example use this event and job boundary:

```yaml
on:
  pull_request_target:
    types: [opened, reopened, synchronize, labeled]

jobs:
  review:
    if: contains(github.event.pull_request.labels.*.name, 'scopeproof-review')
```

The job-level condition is intentional. It prevents checkout, installation, analysis, artifact
upload, and comment publication when applicability is absent. GitHub may display the job as skipped;
that is workflow-state evidence only and must not be presented as a ScopeProof verdict.

### Event behavior

| Event state | Review job | Report/artifact | PR comment |
| --- | --- | --- | --- |
| Opened without label | Skipped | None | None |
| Reopened without label | Skipped | None | None |
| Synchronized without label | Skipped | None | None |
| `scopeproof-review` applied | Runs | Existing behavior | Existing non-fork behavior |
| Synchronized with label retained | Runs | Existing behavior | Existing head-SHA behavior |
| Any fork PR without label | Skipped | None | None |
| Fork PR with label | Runs trusted base only | Existing behavior | No write request |

Removing the label does not delete an existing comment. Destructive comment cleanup is outside this
slice; the label prevents subsequent runs until a maintainer opts in again.

## Confirmation semantics

Two independent confirmations are required for a reviewed PR:

1. `.scopeproof/requirements-confirmation.json` binds the confirmed requirements bytes, confirmer,
   and timestamp.
2. The maintainer-controlled `scopeproof-review` label binds those checked-in requirements to the
   current PR's review lifecycle.

The label does not make a verdict Ready, confirm individual evidence, or replace human acceptance.
It only authorizes applying the already-confirmed requirements to that PR.

## Security and notification boundaries

- Continue using `pull_request_target` only with the immutable base SHA checkout.
- Preserve `persist-credentials: false` and the existing minimal permissions.
- Do not inspect, checkout, fetch, or execute pull-request-head code.
- Do not interpolate arbitrary PR text into shell commands.
- Preserve the fork no-write rule.
- Publish no manual issue or PR status comments during implementation.
- The implementation PR itself will initially be evaluated by the old base workflow and can produce
  one final automatic comment. After merge, unlabeled maintenance PRs no longer do so.

## Documentation

The Action guide and external-validation runbook must state:

- create the exact `scopeproof-review` label;
- open the PR without expecting a ScopeProof review;
- a repository maintainer must first confirm that the checked-in requirements apply, then apply the
  label;
- absence of the label means not reviewed, not Ready;
- retaining the label permits same-PR head updates and reruns.

The copyable workflow must match the repository workflow exactly for the trigger and condition.

## Verification

Regression contracts will require:

- `labeled` in both `pull_request_target` trigger lists;
- the exact job-level label condition in both workflows;
- no path or PR-author heuristic as a substitute;
- docs that distinguish requirements-byte confirmation from per-PR applicability;
- the existing trusted-base, immutable-action, nonblocking, report, and fork no-write contracts.

Run focused workflow tests first, then Ruff, the complete offline suite, the deterministic benchmark,
`git diff --check`, and a source/archive workflow inspection. No browser smoke is required because
this slice changes GitHub workflow activation and documentation, not the local Streamlit runtime.

## Release decision

Do not publish a release for this repository workflow and guidance correction. Reassess release
readiness only after a later coherent distribution-facing boundary is justified.
