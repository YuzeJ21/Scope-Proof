# Reviewer-selected References Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for the integrated task. The owner
> delegates routine design/execution choices and requests autonomous checked merge.

**Goal:** Explicitly save and inspect attributable exact-head static references without changing
automatic findings, gates or reviewer acceptance.

**Architecture:** Separate strict reference models plus a source-validating core append service;
default-empty version-6 persistence; small criterion selector and separate report projections.

**Tech Stack:** Existing Python/Pydantic/Streamlit/pytest/Playwright; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-30-reviewer-selected-evidence-design.md`

## Global Constraints

- First 1,000 eligible lines; maximum 4,096 UTF-8 bytes per line; 32 saved references.
- Review/source/provenance/fingerprint binding and frozen Pydantic records; no source execution.
- Non-gating static references; preserve all automatic/human/runtime truth and frozen research.
- Pre-6 nonempty/malformed reference metadata rejects; historical empty records remain readable.
- No personal testing, qualifying reviews, releases, deployment, outreach or new dependencies.

## Review Focus

- Reusing a line number after source/head/criterion/revision change must not silently retarget.
- Renamed/current and unchanged sources must not bypass skipped/truncated/ambiguous source guards.
- Pending selection/rationale must invalidate downloads and final acceptance like existing drafts.
- A stale local store update must not overwrite newer decisions or claim successful persistence.
- Source references must not be misreported as automated candidates, runtime proof or scope closure.

### Task 1: Deliver the integrated M3 reference workflow

**Files:** New `scopeproof_core/reviews/selected_references.py`, `apps/web/selected_references.py`,
`tests/reviews/test_selected_references.py`, `tests/storage/test_selected_reference_migration.py`,
`tests/apps/test_selected_references.py`, `tests/reporting/test_selected_references.py`;
modify schemas/models.py, storage/json_store.py, reporting/exporters.py, apps/web/app.py,
installed-browser tests, README/ROADMAP/current Stage 2/release guidance/CHANGELOG.

**Interfaces:** Use `SelectableReferenceLine`, `ReviewerSelectedReference`,
`selectable_reference_lines(...)`, `append_reviewer_selected_reference(...)` exactly as the spec.
Workbench module exposes pending/clear helpers, `render_selected_references(...)` returning a new
ReviewState or None, and `render_selected_reference_records(bundle, criterion_id)`.

- [ ] Write failing core and migration tests for the spec's identity/source/limits/history and
      non-gating invariants; run to confirm RED; implement strict models, append service and v6.
- [ ] Write failing report and AppTest cases for attributed exact-head exports, no candidate
      inflation, pending/reset/stale behavior; implement reports, selector and app hooks.
- [ ] Add a trusted constructed installed-wheel browser select/save/restart/reopen/download
      journey; observe missing-entry RED before UI implementation and verify final GREEN.
- [ ] Run focused cases, complete covered suite at 95%, lint/benchmarks/lock, packaged browser;
      refresh current docs accurately; perform independent whole-branch review and fix findings
      with RED→GREEN regressions and affected/full verification.
- [ ] Commit/push PR; exact final-head CI and review findings must be resolved before guarded
      merge. Verify resulting main, clean local sync, archive owned execution ledger and report.

Expected: selected references survive save/reopen/export with explicit source and attribution;
no automatic gate/findings/decision/runtime upgrade occurs, and stale/unsupported inputs reject.
