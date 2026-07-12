# ScopeProof First-Use Safety Design

## Problem

A rendered desktop audit of the deliberately constructed demo exposed two first-use risks:

1. The evidence matrix is emitted through separate Markdown calls, so Streamlit displays raw pipe-delimited lines instead of a table.
2. The human-decision control defaults to `Accepted`, allowing a reviewer to save an acceptance decision without deliberately choosing it.

The screenshots and audit notes are stored outside the repository under the Codex visualization workspace. They are product-flow evidence, not evidence that reviewed pull-request behavior is correct.

## Chosen design

Render the filtered matrix as one atomic Markdown table. Escape pipe characters and replace embedded newlines in user-authored cells before joining the rows. Keep the existing per-criterion summary lines because they provide a compact textual status scan and preserve current AppTest-visible wording.

Add a `Select a decision` placeholder to the human-decision control. The placeholder maps to no domain decision. Disable `Save resolution` until the reviewer explicitly selects a real `HumanDecision`. Do not change the resolution model, gate rules, final-acceptance behavior, exports, or persisted schemas.

## Alternatives considered

- Use Streamlit's static table component. Repeated AppTest runs triggered a reproducible pandas/Arrow segmentation fault in the supported local dependency stack, so this path is not safe for the repository's full regression suite.
- Use an interactive dataframe. This adds sorting and grid behavior that the first-use flow does not need, follows the same dataframe dependency path, and can make a small evidence summary harder to scan.
- Redesign the entire app as a wizard. The audit does not establish enough repeated-user evidence for that larger structural change.

## Safety and error behavior

The UI must never construct a `ResolutionEvent` from the placeholder. The save button remains disabled until a domain decision exists. Existing validation remains the final safeguard if state is manipulated outside the normal UI.

## Verification

- Add Streamlit AppTest coverage proving the evidence matrix is assembled as one table block rather than separate raw Markdown lines.
- Add AppTest coverage proving no human decision is preselected and resolution saving is disabled until an explicit choice.
- Run the full offline test suite, Ruff, the deterministic benchmark, and a browser screenshot verification of the corrected states.
