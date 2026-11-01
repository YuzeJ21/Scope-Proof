# Scope-file Inspection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect loaded changed-file diff context before recording an explicit scope decision.

**Architecture:** Typed core projection validates active source and returns bounded parsed records. A small Streamlit renderer and draft callbacks expose that projection beside existing controls; no storage/gate change.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest/AppTest, Playwright.

**Spec:** docs/superpowers/specs/2026-11-01-scope-file-inspection-design.md

## Global Constraints

- 100 records/page, 4,096 UTF-8 bytes/line; explicit omission, no silent truncation.
- No network calls, code execution, citations, automatic decisions or gate changes.
- Revalidate active review and source identity, inventory and observations; preserve partial-ingestion gate.
- Source remains unreleased 0.2.5, public v0.2.4 unchanged, Stage 3 dormant.
- Preserve saved records, confirmation, explicit decisions and seven frozen R-002 files.
- No personal testing, qualifying reviews, release, deployment or outreach.

## Review Focus

- Renamed/deleted old lines must retain base coordinates, never head evidence claims.
- A same-head source with different inventory or observations must be unavailable.
- Skipped/truncated/oversized content must not leak through a convenience preview.
- Changing file or source context must not retarget an old disposition or explanation.
- Reopened records without source must remain inspectable as metadata without invented excerpts.

### Task 1: Validated bounded core preview

**Files:** Create scopeproof_core/reviews/scope_file_preview.py and tests/reviews/test_scope_file_preview.py; independent safety cases in tests/reviews/test_scope_file_preview_safety.py.

**Interfaces:** Consumes ReviewState and PullRequestSnapshot. Produces `build_scope_file_preview(state: ReviewState, snapshot: PullRequestSnapshot, path: str, *, page_index: int = 0) -> ScopeFilePreview`; fields/availability as specified in design, page_count computed.

- [ ] Write failing behavior tests for literal base/head coordinates, renamed/removed paths, pages beyond 100, oversized omission, source mismatch/unavailability, matching partial source and unchanged state.
- [ ] Run `.venv/bin/python -m pytest -q tests/reviews/test_scope_file_preview.py`; expect missing-feature failures, after validating constructed fixture.
- [ ] Implement smallest typed projection and context checks; no changes to existing source policy or gate.
- [ ] Run core and safety files plus tests/reviews/test_selected_references.py; expect all pass.
- [ ] Commit core and tests with design/plan.

### Task 2: Workbench inspection and automated journey

**Files:** Create apps/web/scope_file_preview.py and tests/apps/test_scope_file_preview.py; modify apps/web/app.py, tests/browser/test_packaged_workbench.py, .github/workflows/ci.yml, README.md, ROADMAP.md and docs/releases/v0.2.3-status-and-next-stages.md; add dated audit.

**Interfaces:** Consume Task 1 projection; produce `render_scope_file_preview(state, snapshot, path, *, source_allowed=True)`, `prepare_scope_draft_context(state, snapshot)` and `scope_file_changed()` in the UI module. The renderer has no mutation controls. Context reset occurs before scope widgets, path callback clears dependent controls/page.

- [ ] Write failing AppTest cases for read-only preview, source absence/conflict, page changes, inert hostile text, file/context draft reset and form order in actual workbench.
- [ ] Run AppTest file; expect missing-feature failures, then implement renderer/callbacks and integration.
- [ ] Extend existing installed-browser journey with real chooser/preview/reset and responsive captures; preserve all existing assertions and counts.
- [ ] Run focused AppTest, browser collection and lint; expect pass. Add core/AppTest files to bounded Windows checks and update outcome/boundaries docs.
- [ ] Commit implementation; run full covered suite with 95% unrounded threshold, lint/lock/diff, deterministic benchmarks, isolated installed wheel and full packaged browser. Preserve exact commands/results externally.
- [ ] Fresh whole-branch independent review; resolve supported findings with regressions. Create/attach PR, wait exact-head CI/CodeQL and reviews, expected-head squash merge, verify tree and resulting-main CI/CodeQL. Sync both clean checkouts. Archive only this plan's owned execution ledger. Mark goal complete.
