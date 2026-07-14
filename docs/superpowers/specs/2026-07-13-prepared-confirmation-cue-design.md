# Prepared-to-Confirm Transition Design

## Context

A browser audit of the clean-installed public `v0.1.16` wheel reproduced one first-use transition gap at 1280 by 720. After `Load deliberately constructed demo`, the sidebar correctly reports `Next — Confirm criteria`, but the main viewport still focuses the completed demo action, leaves `Prepare criteria` enabled, and places `Confirm criteria` below the fold.

Current-run evidence is stored in:

- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.16-post-release-audit/02-demo-loaded.png`
- `/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.16-post-release-audit/audit-notes.md`

The confirmation gate is intentional. ScopeProof must not confirm criteria automatically or hide the requirement and criterion editors.

## Goal

Make the transition from prepared criteria to explicit reviewer confirmation unmistakable without changing the review lifecycle or moving user-owned content.

## Approaches considered

1. **Mark unchanged prepared input complete and show a native in-page continuation link.** Disable `Prepare criteria` while the current requirements exactly match the already prepared source text, then show a concise success message and a `Continue to 2 · Confirm Criteria` anchor. Editing the requirements makes preparation available again.
2. **Automatically scroll after preparation.** This is intrusive and brittle across Streamlit reruns, and can disorient users who want to verify the prepared source.
3. **Collapse Start Review after preparation.** This hides editable PR and requirement context and adds disclosure state to a safety-relevant transition.

Choose approach 1. It exposes the actual next action, prevents accidental repeat preparation, preserves editing, and uses the existing page structure.

## Product behavior

- When criteria exist and the visible requirements text exactly matches the prepared source text, `Prepare criteria` is disabled.
- Before explicit confirmation, the Start Review section shows `Criteria prepared. Review the set before explicitly confirming it.`
- The same state shows a native link labelled `Continue to 2 · Confirm Criteria` targeting the existing `#2-confirm-criteria` heading.
- Editing the requirements text re-enables `Prepare criteria` and removes the completion cue until the updated text is prepared.
- Explicit criterion confirmation remains required before deterministic analysis.
- Demo load, public PR fetch, criterion editing, source replacement protection, analysis, gates, persistence, and exports are otherwise unchanged.

## Version contract

The verified public release remains `v0.1.16`. New mainline development identifies itself as `0.1.17.dev0`; README release-install instructions continue to point to the verified `v0.1.16` assets.

## Boundaries

- Change only Streamlit transition presentation, development version identity, and their regression contracts.
- Do not change evidence extraction, evidence levels, findings, human decisions, gate logic, schemas, persistence, or exports.
- Do not add dependencies, services, billing, paid APIs, telemetry, comments, reviewers, forks, or untrusted-code execution.

## Verification

- Add AppTests for the prepared cue, disabled repeat action, editable-input reactivation, and unchanged confirmation lock.
- Update the version-source contract to `0.1.17.dev0` while retaining README `v0.1.16` release contracts.
- Run Ruff, the full offline suite, deterministic benchmark, and diff checks.
- Build and clean-install one wheel; verify all version identities, dependency consistency, benchmark, and exact web health.
- Browser-test the packaged first-use transition at the same viewport and capture the resulting state.

## Evidence limits

The browser capture verifies the audited viewport and interaction path. It does not prove every responsive breakpoint, assistive-technology behavior, or product correctness.
