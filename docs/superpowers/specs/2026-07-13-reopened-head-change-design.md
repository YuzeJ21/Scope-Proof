# Reopened Review Head-Change Design

## Problem

ScopeProof can reopen a saved review, but loading the same pull request again immediately clears the reopened review before comparing its saved head SHA with the newly loaded snapshot. The core store already provides deterministic head-change detection, while the Streamlit flow does not use it. This makes the README and the accepted durability design overstate the current UI behavior.

## Decision

When a user reloads the same repository and pull-request number after reopening a saved review, ScopeProof compares the saved review head SHA with the newly loaded snapshot before invalidating the current analysis.

- A changed head shows both SHAs and warns that the saved evidence remains anchored to the old head.
- An unchanged head confirms that the source was reloaded at the same SHA.
- In both cases, the current analysis is cleared and the user must explicitly reconfirm the criteria before running a new analysis.
- Loading a different repository or pull-request number does not present a head comparison.
- The saved review record is never mutated by source reload.

## Architecture

The existing `JsonReviewStore.detect_head_change` service remains the only comparison rule. The Streamlit layer adds transient session metadata identifying whether the active review came from the reopen flow and a transient comparison result for display. No new persisted or exported object is introduced.

Before either the demo loader or GitHub loader replaces the active snapshot, a small UI helper checks all of these conditions:

1. an active validated `ReviewState` exists;
2. that state was loaded through the reopen flow;
3. its repository and pull-request number match the new snapshot.

Only then does it call the deterministic core comparison service. The result survives analysis reset long enough to render the notice. The reopened-review marker is cleared during reset so later unrelated loads cannot compare against stale session state.

## Data Flow

1. Reopen validates a saved record and hydrates the review state, bundle, criteria, and history.
2. Reopen marks the validated review ID as the comparison source and clears any older reload notice.
3. A source loader obtains a new validated `PullRequestSnapshot` without executing repository code.
4. The UI compares matching reopened state to the new snapshot before replacing session state.
5. The UI stores only the transient `HeadChange` result, replaces the snapshot, and invalidates the current analysis.
6. The notice reports changed or unchanged head status. Analysis stays unavailable until criteria are reconfirmed.
7. A successful new analysis clears the notice because its evidence is now anchored to the current snapshot.

## Safety and Error Handling

- No old bundle is shown as evidence for the newly loaded snapshot.
- A repository or pull-request mismatch suppresses comparison rather than implying continuity.
- Existing safe public error messages remain unchanged; raw validation details are not exposed.
- The feature adds no network provider, credential, billing, paid API, fork, or repository-code execution.
- The existing saved file remains immutable unless the user explicitly saves a later review.

## Verification

Regression coverage will prove:

- changed-head reload reports old and current SHAs;
- changed-head reload clears the old review and bundle;
- criteria confirmation is reset and analysis cannot reuse old evidence;
- same-head reload reports deterministic same-head status;
- unrelated source identity does not produce a misleading comparison;
- the existing core head-change unit test continues to pass.

A real Streamlit browser run will exercise the available same-head demo path after a saved review is reopened. The controlled changed-head path will be verified through deterministic AppTest coverage, not represented as external runtime evidence.

## Documentation

The README statement remains valid only after the UI regression coverage and runtime flow are implemented. No release is required for this bounded correctness fix.
