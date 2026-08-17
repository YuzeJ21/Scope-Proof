# ScopeProof GitHub Action External Validation Runbook

This runbook is for a repository owner. It is not evidence that a real Action
run has occurred until the owner fills in the run URLs and preserves the output.

## Single-account public alpha policy

For this public alpha, fork testing is permanently excluded. Do not create an
organization, second account, billing arrangement, or synthetic fork to satisfy
this runbook. Keep the workflow's local fork-safety tests, but state clearly
that no external fork-run claim is being made.

## Preconditions

1. Use a user-owned **public demo repository**; do not use a customer or private
   repository for first validation.
2. Copy `.github/workflows/scopeproof.yml`, create
   `.scopeproof/requirements.txt` on the base branch with one confirmed
   criterion per line, and add the hash-bound confirmation record described in
   [the Action guide](github-action.md#requirements-confirmation-record).
3. Commit both workflows and the requirements to the base branch before opening
   the test PR. Analysis uses `pull_request`; the isolated withdrawal workflow
   uses `pull_request_target` only so label removal is delivered for conflicted
   PRs. Both check out the base SHA and never the PR head.
4. Confirm the workflow remains informational:
   `SCOPEPROOF_REQUIRED_CHECK: false`.
5. Create the exact `scopeproof-review` repository label. A repository owner
   applies it only after confirming the checked-in requirements apply to the
   specific PR.
6. If the checked-in confirmed requirements bytes change, maintainers must
   remove `scopeproof-review`, review the new confirmed text for applicability
   to the PR, and reapply the label before another ScopeProof review. This is an
   operator requirement; removing the label revokes the current exact-head
   Ready display, but the workflow does not reconstruct older label history.
7. Do not add personal access tokens. The workflow uses GitHub's short-lived
   `github.token` only for its scoped, non-fork Check step. A fork or missing
   token produces no write. A stale head or GitHub identity mismatch fails
   closed before mutation.

## Capture record

Create a local `action-validation.md` outside the demo repository if desired:

```text
repository: owner/demo-repository
requirements commit: <base SHA>
non-fork run URL: <pending>
check run URL: <pending>
check name: ScopeProof evidence summary (informational)
check conclusion: neutral
rerun URL: <pending>
new-head run URL: <pending>
fork_status: excluded
validated by: <name or role>
validated at: <timestamp>
limitations: public demo only; no customer validation claimed
```

## Test 1 — non-fork PR

1. Open a same-repository PR that makes a small, safe text or code change, but
   do not apply `scopeproof-review` yet.
2. Verify the unlabeled **ScopeProof evidence review** job is skipped. Without
   the label, the PR is not reviewed, not Ready.
3. Have the repository owner confirm the checked-in requirements apply to this
   PR, then apply `scopeproof-review`.
4. Wait for **ScopeProof evidence review** to finish.
5. Preserve its run URL and the ScopeProof Check URL. Keep the
   `scopeproof-review` label on the PR for the same-head rerun and subsequent
   head synchronization.
6. Verify the summary and Check title match the CLI review result for the
   same PR head SHA.
7. Verify the Check is named `ScopeProof evidence summary (informational)`, has
   conclusion `neutral`, and records the confirmed criteria-source provenance.
8. Remove `scopeproof-review`. Verify the separate withdrawal job updates that
   exact-head Check to neutral **Needs Review**, retains its prior evidence for
   audit, and does not execute another PR analysis.
9. Repeat label removal on a deliberately conflicted same-repository PR and
   verify the trusted-base withdrawal job still reaches the same neutral result.

Expected: one neutral informational GitHub Check for the exact head. This does
not prove the requirement is correct, runtime behavior, accessibility, demand,
adoption, or customer value. Reviewer and source-owner identities are asserted,
not authenticated. The Check is not a required branch-protection check.

## Test 2 — same-head rerun

1. With `scopeproof-review` still applied, re-run the ScopeProof job without
   changing the PR head SHA.
2. Preserve the rerun URL.
3. Verify the same-head rerun updates the existing exact-identity Check rather
   than creating a duplicate.

Expected: one Check identity for that head SHA.

## Test 3 — new head history

1. Push another safe change to the same-repository PR while keeping the
   confirmed requirements and `scopeproof-review` label applicable.
2. Wait for the workflow and preserve its run URL.
3. Verify the new head creates a new exact-head Check identity and does not
   rewrite the previous head's Check history.

Expected: one separately auditable neutral Check identity per observed head.

## What to return to ScopeProof

Only return public run URLs, PR URL/head SHA, copied summary text, Check URL and
name, neutral conclusion, same-head identity count, and any sanitized error. Do not send
tokens, private repository links, or customer source code. ScopeProof can then
add a public, human-labeled regression fixture only if the source and expected
outcome are suitable.

## Optional local record validation

The legacy `validate-action-evidence` schema records the earlier comment-based
preview and remains readable for backward compatibility. It does not validate
this Check lifecycle. Preserve current Check observations as the local text
capture above until a separately designed Pydantic record exists; do not force
Check evidence into legacy comment fields or infer hosted evidence locally.

Legacy records may still be validated locally with:

```bash
scopeproof validate-action-evidence action-validation.json
```

The command checks only the legacy record contract. It does not contact GitHub,
validate a current Check Run, or independently prove submitted URLs are real.
