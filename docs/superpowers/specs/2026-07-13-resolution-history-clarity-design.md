# Resolution History Clarity Design

## Problem

ScopeProof keeps every `ResolutionEvent` as append-only audit history, while the latest event for
each criterion in the active criteria revision is the only human decision passed into the
deterministic gate. The latest final-acceptance event in that revision similarly controls the
review-level acceptance flag.

The Streamlit history currently renders every event as an identical bullet. Two decisions for the
same criterion therefore look equally active, use raw enum values such as `rejected_finding`, and
do not expose their criteria revision. A reviewer cannot tell from the history which event is the
current input, which event has been superseded, or which event belongs to a prior revision.

## Evidence

- `current_resolutions()` retains only the latest criterion event in the selected revision.
- `_final_acceptance()` retains only the latest review-level acceptance event in that revision.
- `revise_criteria()` creates a new criteria revision while preserving existing resolution events.
- The current browser audit showed two equal-weight bullets for AC-01 even though the later
  `accepted` event replaced the earlier `rejected_finding` event for gate evaluation.

## Approaches Considered

1. **Annotate the existing chronological history (selected).** Preserve every event and its order,
   but label it `Current`, `Superseded`, or `Prior revision`, show its revision number, and use
   human-readable outcome labels. This is the smallest change that preserves auditability.
2. **Separate current decisions from history.** This creates a strong visual distinction but
   duplicates information already present in the evidence matrix and increases page length.
3. **Collapse superseded events.** This reduces visual noise but makes the append-only audit trail
   easier to overlook and conflicts with the product's transparency goal.

## Design

Add a core lifecycle classification helper because the meaning of current versus historical events
is a review-semantic rule, not a Streamlit styling rule. The helper returns one status per input
event, aligned with the original append order:

- `current`: the latest event for its criterion or the latest final-acceptance event in the active
  revision;
- `superseded`: an earlier event for the same target in the active revision;
- `prior_revision`: any event bound to a different criteria revision.

The helper must not mutate events, recalculate the gate, or manufacture resolution evidence.

The Streamlit history remains chronological. It adds a short explanation and renders each event as:

`Current · revision 1 — AC-01: Accepted — Evidence reviewed`

Historical events use `Superseded` or `Prior revision` in the same position. Human decisions use
the app's existing title-style labels. Final-acceptance outcomes use `Recorded` and `Not recorded`
instead of raw booleans.

## Boundaries

- No gate, evidence, final-acceptance, or replacement semantics change.
- No event is deleted, reordered, rewritten, or hidden.
- No new persisted or exported object is introduced.
- The core helper has no Streamlit dependency.
- The UI does not imply that a current event makes the overall gate Ready.

## Verification

- Lifecycle tests cover current, superseded, prior-revision, and final-acceptance classification.
- Streamlit AppTest records two decisions for one criterion and verifies both labels, revision
  context, readable decision names, and the explanatory copy.
- Full Ruff, offline pytest, deterministic benchmark, installed-wheel smoke, and live browser
  comparison remain required before publication.
