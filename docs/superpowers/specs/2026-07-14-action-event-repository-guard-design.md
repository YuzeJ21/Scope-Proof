# ScopeProof Action-Event Repository Guard Design

## Problem

`EventContext.repository` controls the repository path used by the GitHub Action publisher. Its
current pattern, `^[^/]+/[^/]+$`, enforces exactly two nonempty slash-separated segments but accepts
spaces, leading/trailing whitespace, tabs, and other characters that are not part of ScopeProof's
supported public GitHub repository identity.

A deterministic probe on current `main` accepted `" / "`, `"ac me/de mo"`, `" acme/demo"`, and
`"acme/demo\t"`. `github_action_runner._event_context` copies `repository.full_name` into this field
before comment planning or publication.

## Existing Contract Evidence

`ActionValidationRecord.repository` already uses the supported canonical shape:

```text
^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$
```

This permits the GitHub owner/repository characters already covered by repository tests while
rejecting whitespace and malformed identities. Action runner and publisher fixtures already use
`acme/widget`, so no valid controlled fixture migration is needed.

## Approaches Considered

### 1. Reuse the canonical Action-validation pattern

Chosen. Both models represent the same public GitHub `owner/repository` identity. One exact
contract prevents the Action planner from accepting an identity that offline Action evidence later
rejects.

### 2. Trim or normalize repository strings

Rejected. Silent rewriting could make the persisted or published identity differ from the supplied
event evidence.

### 3. Keep the two-segment shape and only prohibit whitespace

Rejected. This would still accept characters outside the supported GitHub slug contract and leave
the two Action boundaries inconsistent.

## Design

Replace the `EventContext.repository` pattern with
`^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$`. Add regression coverage that:

- rejects whitespace-only, embedded-space, leading/trailing-whitespace, extra-segment, and
  unsupported-character identities at direct model construction;
- rejects a malformed `repository.full_name` through `build_event_plan` before a plan is emitted;
- preserves a supported identity containing owner hyphens and repository dot/underscore/hyphen
  characters exactly.

The model remains the single validation boundary used by both planning and publication.

## Safety and Error Behavior

- Rejection is deterministic Pydantic `string_pattern_mismatch` output.
- Values are not trimmed or normalized.
- No HTTP request occurs before `EventContext` construction in either runner path.
- Head-SHA validation, trusted-base checkout, requirements confirmation, fork skipping, marker
  idempotency, summary rendering, and publisher behavior remain unchanged.
- No workflow, dependency, API, billing, release, comment, or notification change is required.

## Verification

Use a regression-first focused test cycle, Ruff, the complete offline suite, deterministic benchmark,
clean wheel installation, installed direct-model and runner probes, diff review, and protected
PR/CI/CodeQL integration.

## Evidence Limits

This validates local identity shape. It does not contact GitHub, prove that the repository exists,
or create external Action evidence.
