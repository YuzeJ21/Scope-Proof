# GitHub Action advanced preview

The local reviewer workbench is ScopeProof's default product. This guide is an advanced,
non-blocking integration preview for repository maintainers who make a separate adoption decision;
it is not part of first use or evidence of product validation.

ScopeProof includes a repository-local workflow starter at
`.github/workflows/scopeproof.yml`, an isolated withdrawal workflow at
`.github/workflows/scopeproof-withdraw.yml`, a default-base revocation workflow at
`.github/workflows/scopeproof-base-advance.yml`, and matching copyable examples under
`examples/github-actions/`.

It is deliberately a **safe preview**, not an enforcement integration:

- It runs on the unprivileged `pull_request` event, checks out the immutable
  base SHA with persisted credentials disabled, and never checks out or
  executes the pull request head.
- Label removal is handled separately by a minimal trusted-base
  `pull_request_target` workflow because GitHub does not deliver `pull_request`
  activity for conflicted PRs. That workflow runs only for the exact unlabeled
  event, checks out only the immutable base SHA, performs no analysis, and
  invokes the bounded withdrawal publisher with constant command text.
- Default-base pushes use a separate trusted workflow that revokes stale
  exact-head displays on affected open, labeled, same-repository PRs without
  checking out or executing any pull-request head.
- It needs a checked-in `.scopeproof/requirements.txt` plus
  `.scopeproof/requirements-confirmation.json`. The confirmation records the
  source URI and optional revision, exact SHA-256 of the requirements text,
  SHA-256 of the ordered normalized criteria, who confirmed them, and when. If
  either file is missing or either digest differs, the step summary says
  **Needs Review** and cannot say Ready or publish a Check.
- It compares the head repository identity with the target repository identity.
  Cross-repository PRs receive no write plan; same-repository PRs remain eligible
  even when the target repository is itself a fork.
- For a labeled, same-repository PR with checked-in confirmed requirements, it may
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
Review, its prior criteria-bound evidence is retained byte-for-byte for audit, and no replacement
Check is created when no exact identity exists. Withdrawal permits an otherwise identity-matched
closed or merged PR because label applicability can still be revoked after closure; new analysis
publication still requires an open PR. The publisher revalidates the live label state immediately
before either analysis publication or withdrawal, so delayed runs cannot restore stale
applicability.

If the checked-in requirements or confirmation are missing or no longer match, the workflow does
not leave a prior same-head Ready display in place. It updates only an existing trusted exact-head
Check to neutral Needs Review, preserves the prior validated detail, and creates no new Check when
no prior exact identity exists. Repeated revocation runs canonicalize the summary and converge
rather than appending duplicate notices.

Every write also binds the event's immutable base SHA as well as its head SHA. The live PR base and
head must still match in a second live read immediately before publication. Analysis runs only
coalesce redundant events for the same repository, PR, and exact head. Revocation writers are not
placed in a GitHub concurrency group, because GitHub may replace an older pending run even when
`cancel-in-progress` is false. After an analysis write, the publisher reads the live PR once more;
if identity or applicability changed, it immediately neutralizes the exact Check it just wrote and
fails closed. The review command
emits both identities, and the workflow validates them against the event before it accepts a
verdict or exports a report; mixed-snapshot results fail before publication.

Because GitHub does not emit a pull-request `synchronize` event when only the default target branch
advances, the companion `scopeproof-base-advance.yml` runs on trusted default-branch pushes. It
uses GitHub's fixed GraphQL endpoint to enumerate only open PRs carrying `scopeproof-review` and
targeting the pushed default branch, with at most two 55-item pages. GraphQL `pageInfo` accepts
exactly 110 eligible PRs when the second page is terminal and fails closed before any write when
more eligible PRs exist. Unlabeled or differently targeted open PRs do not consume this bound. The
110-PR bound includes two live-identity
reads, up to five Check-list pages, one Check-detail read, and one write per eligible PR. The
worst-case path is therefore 992 GitHub API requests, below the standard 1,000-request-per-repository
hourly limit for an Actions
`GITHUB_TOKEN`. Deleted-fork records are skipped, and work remains limited to labeled
same-repository PRs. Each eligible PR is attempted independently so one failed revocation does not
prevent later revocations; any failed PR numbers produce a final nonzero result. The publisher
updates only an existing trusted exact-head Check to neutral Needs Review. It never analyzes a PR
or checks out its head. Non-default target branches are not covered by this automatic revocation
workflow.

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
`50058cffd28fb3d4b9bf6da97d05f77ab4dcb509`, the immutable source-candidate commit
containing the exact-head informational Check lifecycle, typed criteria-source confirmation,
bounded exact-name publisher, same-head analysis coalescing, ungrouped revocation writers,
immediate pre-write and compensating post-write live identity revalidation, fail-closed report export, label-removal
withdrawal for conflicted PRs, repository-identity fork classification, and isolated base-SHA-only
workflows with the eligible 110-PR, 992-request token-budget bound used by these examples. The copyable
workflows invoke the installed `scopeproof-github-action` entry point; the base-advance workflow
does not check out target-repository files. It remains a
source-candidate installation; it is
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
scopeproof-github-action \
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
