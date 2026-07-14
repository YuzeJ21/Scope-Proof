# ScopeProof Action-Event SHA Guard Design

## Problem

`EventContext` is the trusted input to Action comment planning and publication. Its `head_sha`
currently requires only one character. An internally supplied event payload can therefore produce
markers such as `<!-- scopeproof:not-a-sha -->` and carry that arbitrary identifier into the
publisher URL/body decision.

The runner normally receives a GitHub-authored event payload, but the Pydantic boundary currently
does not encode the GitHub commit-identifier shape that the policy relies on.

## Current Evidence

- Public PR #72 and its merge response use 40-character lowercase hexadecimal commit IDs.
- `github_action_runner._event_context` copies `pull_request.head.sha` directly into
  `EventContext` before planning or publication.
- The Action checks out only the trusted base commit and never executes pull-request code.
- Current tests use the controlled shorthand `head123`; this is fixture convenience, not observed
  GitHub compatibility evidence.
- A deterministic probe on current `main` accepted `x`, `not-a-sha`, non-hex 40-character strings,
  39/41-character hex strings, and uppercase 40-character strings.

## Chosen Design

Require `EventContext.head_sha` to match exactly:

```text
^[0-9a-f]{40}$
```

Migrate only Action contract, publisher, and runner fixtures to deterministic full-length lowercase
SHAs. Keep `comment_marker` as a pure formatter; callers that need a trusted publication context
must construct `EventContext` first.

Add regression coverage at two boundaries:

1. Direct `EventContext` construction rejects invalid shapes and preserves a valid SHA.
2. `build_event_plan` rejects an invalid `pull_request.head.sha` before emitting a serializable plan
   or comment marker.

## Safety and Compatibility

- No string is normalized, truncated, lowercased, or expanded.
- The schema validates shape only and does not claim the commit exists.
- Fork skipping, confirmed-requirements gating, comment idempotency, summary rendering, publisher
  behavior, trusted-base checkout, permissions, and HTTP behavior are unchanged.
- No workflow, dependency, release, API, billing, fork, or notification changes are required.

## Verification

Use regression-first focused tests, Ruff, the complete offline suite, deterministic benchmark, a
clean wheel install, installed direct-schema and runner probes, and the existing protected PR/CI/
CodeQL path.

## Evidence Limits

This proves deterministic local validation of the event field. It does not create a new Action
runtime claim, prove commit existence, or replace GitHub's event authenticity boundary.
