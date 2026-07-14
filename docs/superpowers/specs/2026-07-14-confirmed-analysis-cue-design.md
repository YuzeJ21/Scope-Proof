# Confirmed Criteria Analysis Cue Design

## Reproduced gap

A clean-installed public v0.1.18 audit at 1280 by 720 reproduced a first-use
transition gap. After the reviewer confirms four demo criteria, the sidebar
correctly changes to `Next — Run deterministic analysis`, but the main viewport
returns to the top of the criteria editor. The enabled analysis button is about
463 CSS pixels below the viewport and no link targets it.

Current-run evidence is saved under
`/tmp/scopeproof-v0.1.18-audit-JQ2XvO`:

- `01-initial-css.png`: initial demo action is visible and healthy;
- `02-demo-loaded.png`: the existing confirmation handoff is visible;
- `04-confirmed.png`: confirmed state remains at the criteria-list top;
- `05-analysis.png`: the flow succeeds after manually finding the button.

## Decision

Reuse the existing prepared-to-confirm handoff pattern for the confirmed-to-
analysis transition.

- Reserve a Streamlit placeholder immediately below the evidence-level guidance
  at the top of `2 · Confirm Criteria`.
- After all edits are evaluated, fill that placeholder with
  `[Continue to run deterministic analysis](#run-deterministic-analysis)` only
  when analysis is currently enabled.
- Add the semantic Markdown heading `### Run deterministic analysis` directly
  before the existing button so the link has a stable native anchor.
- Keep the existing button, state transition, deterministic engine, sidebar,
  and evidence matrix unchanged.

The placeholder lets the cue render near the top without making an early,
incorrect decision before blank or pending edits are known.

## Alternatives

### Auto-scroll after confirmation

Rejected because forced movement is harder to predict, can disrupt keyboard or
screen-reader position, and requires client-side behavior beyond the current
Streamlit pattern.

### Put a link beside the button

Rejected because the user must already discover and scroll to the off-screen
button before seeing it.

### Link to the Evidence Matrix heading

Rejected because it scrolls past the analysis button rather than exposing the
next action.

## Contract

- Before confirmation, no analysis continuation link is rendered.
- After valid confirmation and before analysis, the exact continuation link is
  rendered near the top and the analysis button remains enabled.
- Pending edits do not expose the cue.
- After analysis exists, the cue is absent.
- No gate, analysis, persistence, evidence, schema, or export behavior changes.

## Boundaries

No paid API or LLM, billing, organization, private repository, fork test,
synthetic validation, notification, external evidence, generic review, security
scanner, auto-fix, or untrusted-code execution is introduced.
