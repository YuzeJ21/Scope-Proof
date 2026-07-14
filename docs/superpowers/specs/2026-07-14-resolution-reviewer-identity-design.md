# Resolution Reviewer Identity Design

## Problem

ScopeProof now renders the reviewer stored on every resolution event, but the
Streamlit workflow never asks who is recording the decision. New criterion
resolutions and final-acceptance events therefore use the schema default,
`Local reviewer`, even when a specific person performed the review. The audit
history is structurally complete but not usefully attributable.

This is a locally reproduced product limitation, not external validation.

## Constraints

- Keep resolution and final-acceptance semantics unchanged.
- Do not infer identity from GitHub, the operating system, or browser state.
- Do not add authentication, paid services, or an API dependency.
- Preserve compatibility with existing saved reviews whose events already use
  the schema default.
- Persist the supplied value through the existing validated `ResolutionEvent`.

## Design

Add one shared text input, `Decision reviewer (required)`, immediately before
the criterion-resolution controls. Its value is used for both a criterion
resolution and final acceptance in the current review session.

Until the trimmed value is non-empty:

- show a compact explanation that a reviewer is required for an attributable
  audit event;
- disable `Save resolution`; and
- disable `Record final acceptance`.

When an event is recorded, pass the trimmed value explicitly to
`ResolutionEvent(reviewer=...)`. The existing resolution-history metadata then
shows exactly what was supplied.

At the schema boundary, reject blank or whitespace-only reviewers while keeping
the existing non-blank default for backwards compatibility.

## Alternatives considered

1. Separate reviewer inputs for criterion resolution and final acceptance.
   Rejected because it duplicates identity entry in one continuous workflow.
2. Keep the implicit `Local reviewer` default and only explain it. Rejected
   because a generic label does not create an attributable audit record.
3. Infer the GitHub or OS account. Rejected because local operator identity is
   not equivalent to the human who made the decision.

## Verification

- Schema regression: blank reviewers are rejected.
- Streamlit regressions: both actions are disabled without a reviewer and each
  recorded event stores the trimmed reviewer.
- Existing resolution, gate, export, benchmark, and saved-review tests remain
  green.
- Browser verification confirms the required input and rendered reviewer while
  the deterministic gate boundary remains unchanged.

