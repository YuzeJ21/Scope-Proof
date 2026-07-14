# Criteria-Confirmation Feedback Design

## Context

A fresh packaged-browser audit of the deliberately constructed demo reproduced two simultaneous
success banners immediately after `Confirm criteria`:

1. `Criteria confirmed. Analysis can now begin.`
2. `Criteria confirmed by the reviewer.`

The same state is already communicated in the sidebar as `Complete — Criteria confirmed`, while
`Run deterministic analysis` is visibly enabled and identified as the next action. The duplicate
banners add vertical movement and make one state transition look like two separate events.

Source screenshot:
`/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-confirmation-feedback-audit/01-duplicate-confirmation-accepted.png`

## Options

1. **Keep the persistent reviewer-confirmation banner and remove the transient handler banner —
   selected.** One success message remains visible after confirmation and after later reruns. The
   sidebar and enabled analysis action continue to communicate the next step.
2. Keep only the transient handler banner. Rejected because it disappears on the next Streamlit
   rerun even though the criterion set remains confirmed.
3. Replace both banners with a caption. Rejected because confirmation is a required trust boundary
   and should retain the established success treatment.

## Decision

Remove only `st.success("Criteria confirmed. Analysis can now begin.")` from the confirmation
handler. Keep the existing persistent `Criteria confirmed by the reviewer.` success banner and do
not add replacement copy.

After a successful click, the rendered state must contain exactly one success message whose value
is `Criteria confirmed by the reviewer.`. The sidebar must still show `Complete — Criteria
confirmed` and `Next — Run deterministic analysis`, and the analysis button must remain enabled.

The same single-message contract applies when a reopened review's criteria are revised and
reconfirmed because both paths use the same handler and persistent state.

## Boundaries

- No criteria normalization, confirmation, revision, analysis-lock, evidence, finding, gate,
  persistence, export, runtime-evidence, resolution, or final-acceptance change.
- No version change; development remains `0.1.16.dev0`.
- No new dependency, service, API, release, issue comment, or notification-generating activity.
- Browser and AppTest fixtures remain controlled product evidence, not external validation.

## Verification

- Add a failing AppTest that requires exactly one success message after confirmation and preserves
  the sidebar plus enabled analysis action.
- Remove the redundant handler banner and verify the focused test turns green.
- Run adjacent Streamlit tests, Ruff, the complete offline suite, deterministic benchmark, clean
  wheel identity and installed benchmark, exact packaged health, and an in-app browser comparison.
- Capture the same 1280×720 post-confirmation state and compare it beside the source screenshot;
  require one banner, stable control alignment, no clipping, and no browser console errors.
- Integrate only through green protected-main checks. Do not publish a release.
