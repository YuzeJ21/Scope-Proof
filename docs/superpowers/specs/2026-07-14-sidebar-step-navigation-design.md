# Sidebar Step Navigation Design

## Evidence

A current-browser first-use audit captured the blank start, loaded criteria, confirmed criteria,
analysis transition, and evidence matrix. The sidebar accurately reports workflow progress, but
its available and next-step statuses are plain paragraphs. In the long single-page workbench,
users cannot use that persistent status area to reach the corresponding section.

## Decision

Render every available or next sidebar step with a verified stable target as a Markdown anchor
link. Keep unavailable `Locked` steps and the unreliable deep Summary fragment as plain text so
the sidebar does not imply an action that cannot be completed reliably.

Anchor mapping:

- Source loaded or source load/reload next action → `#1-start-review`
- Criteria prepared → `#2-confirm-criteria`
- Criteria confirmation complete or next action → `#2-confirm-criteria`
- Analysis complete → `#3-evidence-matrix`
- Analysis next action → `#run-deterministic-analysis`
- Review and export available → plain status text; Streamlit's deep Summary fragment is not
  reliable enough to present as a working navigation control

## Interaction Contract

The visible status copy remains unchanged. Verified links use native Markdown semantics, require
no session state, and do not alter the current review. Clicking a link only changes the page fragment
and scroll position. Locked steps remain visually and semantically non-interactive.

## Boundaries

- Do not add routes, JavaScript, callbacks, hidden state, or new dependencies.
- Do not change analysis, evidence, gate, persistence, export, or lifecycle behavior.
- Do not link locked steps or imply that prerequisites have been met.
- Preserve the existing status order and ruleset caption.

## Verification

Add AppTest coverage for initial, criteria-ready, confirmation-ready, and analyzed states. Require
exact link targets for verified steps and exact plain text for locked steps and Summary & Export.
Run the full offline suite, Ruff, benchmark, packaging, and a browser click-through proving the
Evidence Matrix link changes the fragment and lands on the intended heading.
