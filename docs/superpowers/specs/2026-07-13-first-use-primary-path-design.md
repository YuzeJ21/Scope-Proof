# First-Use Primary Path Design

## Context

A clean-installed `0.1.16.dev0` audit at the default 1280 by 720 viewport shows the complete
`Reopen saved review` form before `1 · Start Review`. The easiest safe first-use action,
`Load deliberately constructed demo`, is below the initial viewport. This makes a returning-user
utility visually outrank the primary adoption path.

Current-run evidence:

- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.16dev0-continuation-audit/01-start.png`
- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.16dev0-continuation-audit/02-demo-loaded.png`

The fresh-session reopen capability is intentional and must remain available before analysis.
Saved reviews are reopened by validated review ID; loading one clears the unpersisted source
snapshot and does not silently enable re-analysis.

## Goal

Make the safe first-use Start Review path visible in the initial viewport without weakening or
hiding the durable local-review workflow.

## Approaches considered

1. **Collapse the reopen controls in a standard Streamlit expander.** Keep a visible
   `Reopen saved review` label before Start Review, but reveal its ID field and button only when a
   returning operator chooses it. This preserves discoverability and moves the demo entry point
   upward with no new navigation or state.
2. **Move reopen below Start Review.** This gives the primary path stronger hierarchy but makes a
   returning operator scan past the full PR and requirements form before reaching the saved-review
   path.
3. **Add a first-screen mode chooser.** Separate `New review` and `Reopen review` choices would be
   explicit, but add navigation state and another decision before either task can begin.

Choose approach 1. It is the smallest complete hierarchy correction and reuses an existing
Streamlit disclosure pattern.

## Product behavior

- The initial screen shows one collapsed expander labelled `Reopen saved review` immediately before
  `1 · Start Review`.
- Expanding it reveals the existing Review ID field and `Reopen local review` button.
- Missing, incompatible, corrupt, and successful reopen outcomes retain their existing copy and
  validated behavior.
- Successful reopen feedback remains visible after the expander rerun.
- The Start Review fields, offline demo, public-PR fetch, criteria preparation, sidebar stages, and
  all post-analysis behavior remain unchanged.

## Boundaries

- Change only Streamlit presentation and its regression tests.
- Do not change `JsonReviewStore`, review schemas, session hydration, replacement protection,
  criteria confirmation, findings, resolutions, gates, persistence, or exports.
- Do not add dependencies, services, APIs, telemetry, billing, accounts, releases, comments, or
  untrusted-code execution.
- Keep version `0.1.16.dev0`; README continues to install the verified v0.1.15 release.

## Error handling

The existing reopen handler stays inside the disclosure. It continues to translate missing files,
unsupported record versions, I/O failures, and validation failures into stable user-facing copy.
No exception surface or recovery rule changes.

## Verification

- Add an AppTest requiring one `Reopen saved review` expander before first-use analysis while
  preserving the fresh-session ID field and disabled reopen button.
- Preserve all save, reopen, invalid-record, source-reload, and unsaved-replacement tests.
- Run Ruff, all offline tests, the deterministic benchmark, and `git diff --check`.
- Build and clean-install one wheel; verify package identity, dependency consistency, installed
  benchmark, exact web health, and the first-use flow.
- Capture the same initial viewport before and after. Confirm Start Review and the demo entry point
  move into the initial viewport, the collapsed reopen label remains visible, DOM order is correct,
  and the current packaged app reports no console errors.

## Evidence limits

The default viewport can prove visible hierarchy for that captured size. It cannot establish every
responsive breakpoint, keyboard order, screen-reader announcement, zoom behavior, contrast ratio,
or WCAG conformance; those remain separate verification work.
