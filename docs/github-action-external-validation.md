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
3. Commit the workflow and requirements to the base branch before opening the
   test PR. The workflow deliberately runs from the trusted base definition and
   checks out the base SHA, never the PR head.
4. Confirm the workflow remains informational:
   `SCOPEPROOF_REQUIRED_CHECK: false`.
5. Do not add personal access tokens. The workflow uses GitHub's short-lived
   `github.token` only for its scoped, non-fork comment step.

## Capture record

Create a local `action-validation.md` outside the demo repository if desired:

```text
repository: owner/demo-repository
requirements commit: <base SHA>
non-fork run URL: <pending>
rerun URL: <pending>
fork_status: excluded
validated by: <name or role>
validated at: <timestamp>
limitations: public demo only; no customer validation claimed
```

## Test 1 — non-fork PR

1. Open a same-repository PR that makes a small, safe text or code change.
2. Wait for **ScopeProof evidence review** to finish.
3. Preserve its run URL and the ScopeProof comment URL.
4. Verify the summary and comment verdict match the CLI review result for the
   same PR head SHA.
5. Verify the comment ends with `<!-- scopeproof:<head SHA> -->`.

Expected: an informational GitHub check and one ScopeProof comment. This does
not prove the requirement is correct, runtime behavior, or customer value.

## Test 2 — same-head rerun

1. Re-run the ScopeProof job without changing the PR head SHA.
2. Preserve the rerun URL.
3. Verify the existing ScopeProof comment is updated rather than a second
   marker-matched comment being created.

Expected: one marker comment for that head SHA.

## What to return to ScopeProof

Only return public run URLs, PR URL/head SHA, copied summary text, the number
of ScopeProof comments before/after rerun, and any sanitized error. Do not send
tokens, private repository links, or customer source code. ScopeProof can then
add a public, human-labeled regression fixture only if the source and expected
outcome are suitable.

## Optional local record validation

After the owner has collected real evidence for both tests, save it as JSON with
the fields listed in the capture record plus `non_fork_comment_count`,
`scopeproof_comment_marker`, and `rerun_comment_count`.
Copy the exact `<!-- scopeproof:<head SHA> -->` marker from the non-fork
comment. Validate its shape locally:

```bash
scopeproof validate-action-evidence action-validation.json
```

The command checks that the rerun uses the same head SHA and did not increase
the ScopeProof-comment count. With `fork_status: excluded`, it records the
single-account limitation without requiring or accepting fork-run details. It
does not contact GitHub or independently prove the submitted URLs are real.
