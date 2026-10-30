# Browser selection and save synchronization recovery — 2026-10-30

M3 was integrated by [PR #224](https://github.com/YuzeJ21/Scope-Proof/pull/224) after exact-head
CI passed at `43c4eb9af264a9d483004dcc8cfa82df799e7013`. Resulting main
`930690b9714bb09bfab53f490a4885cb8a7c1c1f` passed the full covered suite, compatibility,
CodeQL and base-advance checks, but its [browser job](https://github.com/YuzeJ21/Scope-Proof/actions/runs/41074809759)
failed at the existing JUnit mapping multiselect: twelve checks passed, one failed. The M3
selection/save/restart/reopen/download journey passed in that batch.

## Observed defect and bounds

The trace contains parsed JUnit scopes, an enabled mapping input, and an input with public
`aria-expanded=false` after click/fill. The option was absent during the visibility assertion.
The original reason for popup disappearance remains unproven. An unchanged local targeted
rerun and full thirteen-check confirmation had passed earlier; neither erases these failures.

The helper intended three bounded attempts but used an assertion whose missing-option error is
`AssertionError`, outside its `PlaywrightTimeoutError` recovery path. It also treated an exact
target label appearing as a substring inside a different selected label as an already-selected
value. These are verifiable helper defects, independent of the popup's original trigger.

The bounded repair uses public expanded state and keyboard opening, handles the actual option
wait timeout, then requires a real option click and observed rerun. Exact selected-chip identity
replaces substring-only success. Existing three-attempt and five-second option limits remain.
No unavailable option becomes success; no check is skipped and no sleep is a success criterion.

## Regression contract

A trusted constructed Streamlit fixture renders its backend mapping and run count separately
from the control. Four real-browser cases cover controlled popup dismissal, an already-open
popup, an already-selected prefix distractor, and an unavailable option. Repeating a successful
helper call must preserve the exact committed selection. Setup-only failed constructions are
retained separately and are not presented as successful defect reproduction.

The final targeted matrix first produced two valid failures and two already-passing controls
in 24.01 seconds. After the helper repair, all four passed in 13.98 seconds. Early outside-click,
replacement and Escape setups did not establish the intended boundary and are excluded from
that reproduction claim. Full-suite and hosted results are recorded in the integration PR.

The first full seventeen-check batch passed the JUnit journey and new helper cases but failed
the M3 journey after Save: the test waited for a section heading already present before saving,
then queried downloads while old and new controls overlapped. The trace places Save at 10.880s,
the old-heading check at 10.927s and the download lookup at 11.055s. That failed batch remains
sixteen passes and one failure. The corrected test observes the existing rerun boundary, waits
for the newly created exact reference card and script completion, and requires one enabled JSON
control before the unchanged download helper. Its focused installed-wheel journey passed in
44.11 seconds, retaining all saved-state and export assertions.

The current suite contains seventeen checks: three installed-wheel Chromium journeys, eight
constructed Streamlit selection checks and six helper/capture checks. These are not seventeen
full product journeys or participant reviews. Verification belongs to the follow-up PR's exact
head and resulting-main runs; see its CI and review record for final results.

## Preserved boundaries

This follow-up changes browser test interaction and current count documentation only. Product
Python files, criteria confirmation, M3 references, schemas, gates, decisions, dependencies and
frozen research are unchanged. README metadata may change a newly built wheel's hash; original
public v0.2.4 assets and the private v0.2.5 candidate remain untouched.

The repair demonstrates bounded recovery from a controlled state, not causation or elimination
of the original framework popup loss. The existing automatic candidate parser's uncommon
separator/line-number gap remains a separate product defect; M3 rejects ambiguous sources.
All actors and data are constructed automation. No personal testing, qualifying-review credit,
genuine-use evidence, accessibility-conformance claim, release, deployment or outreach follows.
