# GitHub Action advanced preview

The local reviewer workbench is ScopeProof's default product. This guide is an advanced,
non-blocking integration preview for repository maintainers who make a separate adoption decision;
it is not part of first use or evidence of product validation.

ScopeProof includes a repository-local workflow starter at
`.github/workflows/scopeproof.yml` and a copyable example at
`examples/github-actions/scopeproof.yml`.

It is deliberately a **safe preview**, not an enforcement integration:

- It runs on the unprivileged `pull_request` event, checks out the immutable
  base SHA with persisted credentials disabled, and never checks out or
  executes the pull request head.
- It needs a checked-in `.scopeproof/requirements.txt` plus
  `.scopeproof/requirements-confirmation.json`. The confirmation records the
  source URI and optional revision, exact SHA-256 of the requirements text,
  SHA-256 of the ordered normalized criteria, who confirmed them, and when. If
  either file is missing or either digest differs, the step summary says
  **Needs Review** and cannot say Ready or publish a Check.
- It uses the event's head-repository fork flag to create a non-mutating plan.
  Fork PRs receive no write plan.
- For a labeled, non-fork PR with checked-in confirmed requirements, it may
  create or update the `ScopeProof evidence summary (informational)` Check
  using GitHub's short-lived `github.token`. The Check is bound to the exact
  repository, PR number, head SHA, and criteria-source provenance. A same-head
  rerun updates the exact trusted identity without a duplicate; a new head
  creates a new auditable Check identity. Fork and missing token paths make no
  write request. A stale head, duplicate trusted identity, malformed response,
  or GitHub identity mismatch fails closed before mutation.
- Every published Check has a `neutral` conclusion. **Ready**, **Blocked**, and
  **Needs Review** are informational titles, never GitHub pass/fail conclusions.
  The Check is not a required branch-protection check, and this workflow does
  not modify branch protection.
- Legacy comment APIs remain backward compatible for existing callers, but the
  workflow does not invoke them.
- `SCOPEPROOF_REQUIRED_CHECK=false` is a documented non-blocking default. Do
  not promote this Check into branch protection without a separate owner
  decision and genuine evidence.

ScopeProof is an evidence assistant, not a correctness oracle. Candidate implementation and test
matches are not runtime verification; runtime evidence must be externally supplied. Missing
evidence and unresolved human decisions remain missing and unresolved. Reviewer and source-owner
identities are asserted, not authenticated. A Check run does not prove correctness, runtime
behavior, accessibility, demand, adoption, or customer validation and creates no Stage 1 credit.

## Per-PR requirements applicability

Create the exact `scopeproof-review` repository label during setup. Opening a PR does not authorize
ScopeProof to apply the repository's checked-in requirements. A repository maintainer must first
confirm that the checked-in requirements apply to this PR, then apply `scopeproof-review`.

The requirements-confirmation record binds the approved requirements bytes. The label separately
confirms their applicability to the current PR. Without the label, the review job is skipped: the PR
is not reviewed, not Ready. Keeping the label on the PR allows `synchronize` and `reopened` events to
review later heads under the same checked-in requirements. Removing the label triggers a separate
base-SHA-only withdrawal job: an existing trusted exact-head Check is updated to neutral Needs
Review, its prior criteria-bound evidence is retained for audit, and no replacement Check is created
when no exact identity exists.

If the checked-in confirmed requirements bytes change, maintainers must remove
`scopeproof-review`, review the new confirmed text for applicability to the PR, and reapply the label
before another ScopeProof review. This is an operator requirement: the workflow checks the current
label and confirmation record and revokes the current exact-head display on label removal, but it
does not reconstruct older label history.

The workflow's public-PR evidence command is informational and
`continue-on-error`; GitHub API limits, temporary network failures, or an
incomplete diff must remain visible for human review, not become a false pass.
When a review completes, the workflow uploads its Markdown export as the
`scopeproof-report` artifact for seven days. If no report was produced, the
artifact step is explicitly ignored and the summary remains conservative.

The copyable example installs ScopeProof from a public, full-SHA-pinned source
revision because ScopeProof is not distributed on PyPI. The reviewed pin is
`8061b0c830b6301d3e6e8f54d047b003c402b60c`, the immutable source-candidate commit
containing the exact-head informational Check lifecycle, typed criteria-source confirmation,
bounded exact-name publisher, same-head concurrency, fail-closed report export, label-removal
withdrawal, and unprivileged base-SHA-only workflow used by this example. It remains a source-candidate installation; it is
not a published v0.2.3 release. Review and update that pin deliberately when adopting a newer
public release; do not replace it with an unpinned package or branch reference.

The workflow grants Check write access only for same-repository publication; GitHub downgrades
fork pull-request tokens and the workflow skips the write path. Do not add a pull-request-head
checkout, `git fetch`, `gh pr
checkout`, downloaded artifact execution, cache writes, or arbitrary PR text in
shell commands. Those changes would defeat the base-SHA isolation.

## Local fixture check

The event runner does not call GitHub. To inspect its output with a saved event
payload, run:

```bash
python -m scopeproof_core.github_action_runner \
  --event-path path/to/pull_request_event.json \
  --requirements-confirmed
```

The JSON output includes the trusted event context, human-readable summary, and
the backward-compatible comment plan. It contains no token and does not mutate GitHub. The live
workflow separately uses `--requirements`, `--confirmation`, and `--publish-check` to construct a
validated criteria-bound Check plan.

## Requirements confirmation record

Have the requirements owner or authorized role inspect the exact requirements
file first. Then use the no-network preparation command to compute the exact
UTF-8 text digest and ordered normalized-criteria digest and record their human
attestation. `--confirmed-by` does not verify identity, authority, or correctness.

```bash
scopeproof prepare-requirements-confirmation \
  --requirements .scopeproof/requirements.txt \
  --source-uri https://github.com/OWNER/REPOSITORY/blob/FULL_SHA/.scopeproof/requirements.txt \
  --source-revision FULL_SHA \
  --confirmed-by "Requirements owner or authorized role" \
  --output .scopeproof/requirements-confirmation.json
```

The command refuses to overwrite an existing record. Inspect the generated
JSON, commit it only when the attestation remains accurate, then validate it
before opening the PR:

```bash
scopeproof validate-requirements-confirmation \
  --requirements .scopeproof/requirements.txt \
  --confirmation .scopeproof/requirements-confirmation.json
```
