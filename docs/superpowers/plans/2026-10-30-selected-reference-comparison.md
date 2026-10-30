# Selected-reference Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> bounded task inline, with one fresh independent whole-branch review at the end.

**Goal:** Expose recorded selected-reference context in compatible saved re-review comparisons.

**Architecture:** Separate typed core projection and full-record distinctions; existing comparison
owns head/criteria validation. Dedicated workbench renderer and existing JSON/Markdown exporters
consume the same non-gating projection. Existing saved-record leases remain authoritative.

**Tech Stack:** Existing Python/Pydantic/Streamlit/pytest/Playwright, no new dependency.

**Spec:** `docs/superpowers/specs/2026-10-30-selected-reference-comparison-design.md`

## Global Constraints

- Maximum 32 references per side, full recorded identity only; no cross-head text equivalence.
- Kinds: `identical_record`, `only_previous`, `only_current`; deterministic canonical ordering.
- Missing historical projection means unavailable; explicit empty snapshots mean no recorded refs.
- Preserve automatic changes/counts, decision-review criteria, findings, gates, scope and decisions.
- No v6 rewrite/migration, frozen research change/rescore, release/deploy/outreach or human credit.

## Review Focus

- Same reference ID with different rationale/head/attribution must not become an identical record.
- Empty-side and historical missing-section states must remain distinguishable.
- Forged nested owners/criteria and mutable objects must fail export validation.
- Selected-only saved-record changes must expire existing selections and deferred downloads.
- UI/Markdown must show raw source and attribution safely without implying execution or acceptance.

### Task 1: Complete the selected-reference comparison journey

**Files:** Create core `reviews/selected_reference_comparison.py`, dedicated
`apps/web/selected_reference_comparison.py`, and core/report/UI tests. Modify
`reviews/comparison.py`, `reporting/exporters.py`, `apps/web/app.py`, saved/browser fixtures and
the existing browser comparison journey; align README/ROADMAP/current release-status guidance.

**Interfaces:** `SelectedReferenceComparison.from_bundles(previous: ReviewBundle,
current: ReviewBundle) -> SelectedReferenceComparison`; `previous`, `current`, `record_changes`,
`change_counts`; `render_selected_reference_comparison(comparison: SelectedReferenceComparison
| None) -> None`. `ReviewComparison.selected_reference_comparison` is optional for legacy imports.

- [ ] Write new core tests: exact same full record → identical; different attribution or immutable
      head → only_previous + only_current; shuffled order → identical canonical JSON; nested owner,
      criteria, duplicates and exported mutation → rejected; old projection → unavailable.
- [ ] Observe failing assertions before production changes; implement typed projection and bind
      both sides to scope snapshots. Assert automatic projection and saved input bytes unchanged.
- [ ] Add report/UI regressions and observe RED, then render separate attributed context and
      safe Markdown. Preserve selected-only fingerprint/download invalidation.
- [ ] Extend constructed saved fixture and installed comparison/restart/download journey; verify
      both snapshots, identity boundary and unchanged record bytes. Run focused tests.
- [ ] Align current roadmap and status with this newly authorized bounded follow-on, keeping prior
      M3 scope/history, frozen R-002 and external evidence unchanged.
- [ ] Run full 95% coverage, lint/lock/diff, both deterministic benchmarks, fresh installed browser
      and hosted Python/Windows checks. Obtain independent whole-branch review and verify supported
      fixes RED→GREEN. Merge only after exact-head protected CI, then verify clean main and its CI.
