# Honest Workflow Status Design

## Evidence and problem

The 2026-07-12 local Chrome audit captured the deterministic demo from start through export. After
criteria confirmation, the page displayed `Criteria confirmed. Analysis can now begin.` while the
sidebar still marked Step 2 current. After analysis, the full criterion-detail and summary/export
surfaces were available while the sidebar remained on Step 3. This is deterministic: the sidebar
renders before action handlers, and `active_step` is assigned only 1, 2, or 3.

The same audit's accessibility tree exposed repeated controls named only `Priority`, `Required
evidence`, `Remove`, and `Move up`, so a keyboard or assistive-technology user cannot identify which
criterion each control affects from its accessible name.

## Decision

Replace the false current-step state with an honest milestone summary rendered at the end of the
Streamlit script inside `st.sidebar`. Derive status from authoritative session state after all action
handlers have run:

- Source loaded when `snapshot` exists.
- Criteria prepared when the criteria list is non-empty.
- Criteria confirmed when `criteria_confirmed` is true.
- Analysis generated when a bundle or review state exists.
- Review and export available when analysis exists.

Use visible text prefixes `Complete —`, `Next —`, and `Locked —`; do not rely on circle symbols alone.
The sidebar is informational, not fake navigation, so its title becomes `Review status`.

Give repeated criterion controls criterion-specific visible labels:

- `Priority for AC-01`
- `Required evidence for AC-01`
- `Remove AC-01`
- `Move AC-02 up`

Keep existing widget keys unchanged so Streamlit session behavior and saved review data remain stable.

## Alternatives considered

1. Keep `active_step` and call `st.rerun()` after every action. This still cannot represent Steps 4
   and 5 because they have no transition, and it would require extra status persistence to avoid
   losing success messages.
2. Turn the sidebar into clickable anchor navigation. This helps scrolling but does not define honest
   completion state, and it expands the slice into navigation design.
3. Recommended: derived milestones rendered after handlers. It matches the actual single-page
   architecture, removes stale mutable state, and remains deterministic.

## Boundaries

Do not change criteria parsing, confirmation, retrieval, findings, resolutions, gate evaluation,
storage, exports, or the deliberately constructed demo. Do not add CSS, JavaScript, dependencies,
paid services, or synthetic review decisions. Do not claim accessibility compliance; this slice only
fixes the two screenshot/DOM-confirmed labeling risks.

## Verification

Before implementation, AppTest regressions must fail because confirmation still leaves the sidebar
on Step 2 and analysis still leaves it on Step 3. Source-contract tests must also fail on generic
criterion labels. After implementation:

- Confirmation shows `Complete — Criteria confirmed` and `Next — Run deterministic analysis` in the
  same run.
- Analysis shows `Complete — Analysis generated` and `Complete — Review and export available`.
- `active_step` no longer exists.
- Criterion-specific labels appear in AppTest and browser DOM.
- Full Ruff, pytest, deterministic benchmark, installed/local Streamlit runtime, and a fresh Chrome
  screenshot comparison pass before protected publication.
