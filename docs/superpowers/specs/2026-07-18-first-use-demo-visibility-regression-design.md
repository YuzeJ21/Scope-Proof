# First-Use Demo Visibility Regression Design

## Problem

The current `main` workbench at commit `fbb0f9978a29b7dcd3989dffecbe91c5ae79961f`
does not satisfy the existing first-use hierarchy contract. In a fresh 1280 by 720 browser
session, the `Load deliberately constructed demo` button begins at CSS pixel 805 and ends at
845, below the initial viewport. The `1 · Start Review` section and public-PR input remain visible,
but the safest no-network first-use action requires scrolling.

This is current browser evidence for the workbench layout. It does not establish product value,
customer validation, runtime behavior of a reviewed pull request, or correctness.

At 390 CSS pixels, a fresh load correctly collapses the sidebar, has no page-level horizontal
overflow, and keeps the Start Review section usable. The regression is therefore the placement of
the existing desktop first-use action, not a general responsive-layout failure.

## Existing contract

`docs/superpowers/specs/2026-07-13-first-use-primary-path-design.md` requires the safe first-use
Start Review path and demo entry point to appear in the initial 1280 by 720 viewport. The current
collapsed `Reopen saved review` behavior remains correct and must not change.

## Decision

Move the existing `Load deliberately constructed demo` button directly after the optional alpha
feedback toggle and before the public-PR URL field. Keep it as one compact button with the same
key, handler, replacement guard, and alpha-feedback exclusion rule.

Render the existing `Fetch public PR` button after the advanced source options, where the complete
public-PR input and qualification state are already available. Keep its key, handler, validation,
and full-width behavior.

This ordering makes the no-network first-use path visible without duplicating actions, changing the
hero, compressing typography, introducing custom CSS, or changing the public-PR workflow.

## Alternatives rejected

1. Compress the hero and vertical spacing. This would make the acceptance threshold depend on
   fragile font and framework spacing and would change the established visual language.
2. Add a second demo shortcut near the hero. Duplicate actions would create two visual sources of
   truth and complicate Streamlit widget identity.
3. Put both demo and fetch actions above the public-PR input. A disabled fetch action before its
   required input would reverse the task sequence.

## Behavior and boundaries

- `load_demo` remains enabled only when replacement is safe and alpha feedback mode is off.
- `fetch_pr` remains enabled only for a valid public PR, complete alpha qualification when
  applicable, and safe replacement state.
- Demo loading continues to use only the checked-in deliberately constructed fixture.
- No core engine, schema, evidence rule, gate, persistence, export, GitHub ingestion, alpha record,
  billing, API, notification, or release behavior changes.
- No new dependency, account, private-repository path, fork test, outreach, or telemetry is added.

## Verification

- Add an AppTest ordering regression requiring exactly one `load_demo` widget after
  `alpha_feedback_mode` and before `pr_url`, and requiring `fetch_pr` after the advanced source
  inputs but before the requirements editor.
- Preserve the existing alpha-mode and unsaved-replacement disablement tests.
- Run the focused AppTest, all Streamlit AppTests, Ruff, the complete suite with at least 95 percent
  coverage, both deterministic benchmarks, repository contracts, and `git diff --check`.
- Capture and inspect a fresh 1280 by 720 start screen. Require the demo button rectangle to fit
  entirely inside the viewport.
- Capture and inspect a fresh 390 CSS pixel start screen. Require no page-level horizontal overflow
  and a usable Start Review path.

Screenshots and DOM measurements verify only the captured layouts and interaction surface. They do
not prove keyboard, screen-reader, zoom, contrast, or WCAG conformance.
