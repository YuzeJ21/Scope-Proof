# Resolution History Audit Metadata Design

## Problem

`ResolutionEvent` persists reviewer identity, a timezone-aware timestamp, and—when the decision is
`manually_verified`—the claimed evidence level. The Streamlit resolution history renders none of
those fields. A reviewer can therefore see that manual verification was recorded, but cannot
audit who recorded it, when it was recorded, or which evidence level was claimed without opening
the saved JSON or an export.

The current-browser audit reproduced the omission with a deliberately constructed demo decision:
the history showed only `Current · revision 1 — AC-01: Manually Verified — Controlled verification
note`. The screenshot is saved at
`/Users/yjian070/.codex/visualizations/2026/07/14/scopeproof-resolution-history-audit-current/01-resolution-history-current.png`.
This fixture proves presentation behavior only; it is not external verification or adoption
evidence.

## Approaches Considered

1. **Add a compact metadata line below each event (selected).** Preserve the existing chronological
   event summary and add reviewer plus recorded UTC time beneath it. Add claimed evidence level
   only when the persisted event contains one. This keeps chronology scannable while exposing the
   complete audit context.
2. **Expand the existing bullet into one long line.** This minimizes vertical space but makes
   superseded histories hard to scan and mixes the decision summary with provenance details.
3. **Put metadata in a collapsed expander.** This reduces visual density but hides the exact facts
   needed to audit a manual-verification claim.

## Design

Keep the current event bullet unchanged. Immediately below each event, render one subdued metadata
line in this order:

`Reviewer: Local reviewer · Recorded at (UTC): 2026-07-14T19:45:00Z · Claimed evidence level: E3`

- Reviewer and recorded UTC time appear for every event because both are required persisted event
  facts.
- Claimed evidence level appears only when `claimed_evidence_level` is not `None`; the schema
  already restricts that field to manually verified decisions.
- Use the Pydantic JSON representation of the timestamp so the visible value matches persisted and
  exported data and remains deterministic across local timezones.
- Preserve the current chronological order, status classification, revision labels, outcome,
  comment, and final-acceptance wording.

## Data And Error Boundaries

The UI reads already validated `ResolutionEvent` fields. It does not mutate events, infer reviewer
identity, derive evidence levels, recalculate the gate, or create new persistence. Existing load,
save, export, lifecycle, and Pydantic validation paths remain unchanged.

## Verification

- Add AppTest coverage with a fixed reviewer, fixed UTC timestamp, and E3 claimed evidence level.
- Require non-manual decisions to omit the claimed-level label while still showing reviewer and
  timestamp.
- Preserve existing current, superseded, prior-revision, final-acceptance, and gate-boundary tests.
- Run focused and adjacent AppTests, Ruff, the complete offline suite, deterministic benchmark,
  `git diff --check`, dependency consistency, and exact loopback health.
- Reload the current browser flow and compare the same deliberately constructed manual-verification
  state. Treat the screenshot and AppTest as UI evidence only.

## Exclusions

No schema, event, reviewer-entry, evidence URL, lifecycle, persistence, export, gate, final-
acceptance, workflow, dependency, release, API, billing, fork, external evidence, or notification
behavior changes.

## Approval Basis

The persistent goal explicitly authorizes autonomous bounded product improvements without routine
approval pauses. This design stays inside the accepted auditability boundary, selects the smallest
of three reviewed approaches, and does not change any decision or evidence semantics.
