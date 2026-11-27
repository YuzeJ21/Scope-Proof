# CI context comparison implementation plan

> **For agentic workers:** Use superpowers:executing-plans in this session.

**Goal:** Explain a supplied CI update for one reviewed commit in a single offline handoff.

**Architecture:** A strict core comparison object validates one review bundle and two
manifests through existing snapshot projection. Derived test/run rows stay read-only.
An explicit flag on the existing CLI produces a separate HTML comparison.

**Tech Stack:** Existing Python/Pydantic/pytest/Playwright; no added dependencies.

**Spec:** `docs/superpowers/specs/2026-11-27-ci-context-comparison-design.md`

## Global constraints

- No changes to deterministic gates, evidence rules, saved records or review decisions.
- Both inputs must match confirmed criteria and the same exact reviewed commit.
- File order is not authenticated chronology; supplied reports are not runtime proof.
- Preserve frozen research and the PR #305 example. No release, deployment or outreach.

## Review focus

- Added run records with explicit skips must not look like three newly executed tests.
- Reused IDs with changed URL/head/outcomes must never look like retained records.
- Changed mappings and absent tests must not turn into a pass or explicit skip.
- Stale, conflicting, malformed or pending inputs must fail or remain visibly unresolved.
- Output/layout/error handling must preserve input bytes, citations and confidentiality.

### Task 1: Core comparison and offline renderer

**Files:** Create `scopeproof_core/reviews/ci_comparison.py`,
`scopeproof_core/reporting/ci_comparison.py`, `tests/ci_comparison_fixture.py`,
`tests/reviews/test_ci_comparison.py`, `tests/reporting/test_ci_comparison.py`.

**Interfaces:** `compare_ci_status(bundle, previous_payload: bytes,
current_payload: bytes) -> CIStatusComparison`; `comparison.test_changes()` and
`comparison.run_changes()` return Pydantic rows; `export_ci_comparison_html(comparison) -> str`.

- [x] Write and observe failing tests for B/targeted-B, same inputs, mapping changes,
  reused/removed run records, conflicts, mismatched context and unchanged review state.
- [x] Implement comparison using existing CI projection and strict context validation.
- [x] Write/observe renderer tests, then implement provenance, delta tables, run
  records, recorded gate and explicit evidence boundaries.
- [x] Run core/report tests and Ruff; commit the verified task in the isolated checkout.

### Task 2: CLI, installed handoff, roadmap and verification

**Files:** Modify `scopeproof_core/cli.py`, `tests/cli/test_ci_snapshot.py`,
`tests/cli/test_installed_ci_snapshot.py`, `.github/workflows/ci.yml`, current docs;
create `tests/browser/test_ci_comparison.py` and a bounded audit record.

**Interfaces:** `ci-snapshot REVIEW CURRENT --previous-manifest PREVIOUS --output NEW.html`.

- [x] Add failing CLI tests for valid comparison, old behavior, wrong/oversized
  previous manifests, pending review, existing output and sanitized errors.
- [x] Implement the optional flag and preserve bounded reads, locked review loading
  and atomic output creation. Verify exact input-byte preservation.
- [ ] Extend the installed CLI rehearsal and add an offline Chromium case using
  only constructed inputs; preserve skips as skips and old records unchanged.
- [x] Update the current roadmap around completed priorities, this new outcome,
  workbench follow-on and gated adoption/expansion stages.
- [x] Run focused checks and one independent whole-change review; fix material findings.
- [ ] Sync a follow-on PR against #305, verify exact-head CI and report next stages.
