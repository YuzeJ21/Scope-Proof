# Content-First Source References Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find a static source location by literal content before explicitly selecting its line.

**Architecture:** A separate bounded search-page model reuses the existing eligibility iterator.
The workbench consumes that model for match paging and inert physical-line previews.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit, pytest, installed Chromium.

**Spec:** `docs/superpowers/specs/2026-10-31-source-reference-search-design.md`

## Global Constraints

- Maximum query 200 Unicode characters; result pages at most 100 complete eligible lines.
- Preserve existing eligibility, exact-head save validation, record v7 and frozen R-002.
- Core stays UI-independent; no target code execution, source fetching or ranking.
- Source 0.2.5 unreleased, public v0.2.4 unchanged; no personal testing or qualifying reviews.
- Stage 3 remains dormant; no release, deployment, outreach or standing queue.

## Review Focus

- Search must not reveal excluded source lines or silently replace an unavailable source.
- A changed query/file/page/source must not preserve a stale line selection.
- Empty/no matches and the last partial result page must not auto-select or miscount.
- Casefold matching and literal whitespace/punctuation must preserve original source coordinates.
- Long/hostile-looking excerpts must stay complete, inert and contained on narrow screens.

### Task 1: Bounded selected-file literal search

**Files:** Modify `scopeproof_core/reviews/selected_references.py`;
create `tests/reviews/test_reference_search.py` and independent safety tests.

**Interfaces:** Consumes the existing eligibility iterator and source/line schemas. Produces
`MAX_REFERENCE_QUERY_CHARS`, `SelectableReferenceSearchPage` and
`search_reference_page(state, snapshot, *, source_scope, file_path, query='', page_index=0,
unchanged_files=None)` as specified above.

- [ ] Write failing tests with literal expected physical coordinates, full excerpts, match counts,
  pages and rejected invalid requests; include all five Review Focus cases owned by the core.
- [ ] Run `python -m pytest -q tests/reviews/test_reference_search.py`; expect missing API failures.
- [ ] Implement typed result validation and one selected-file scan retaining only 100 matching lines.
- [ ] Run focused new and existing selected-reference tests; expect all pass and unchanged gates/data.
- [ ] Commit the core, tests, spec and plan.

### Task 2: Explicit content-first workbench and verified integration

**Files:** Modify `apps/web/selected_references.py`, `tests/browser/test_packaged_workbench.py`,
`.github/workflows/ci.yml`, README, ROADMAP and release-status record;
create `tests/apps/test_reference_search.py` and dated audit.

**Interfaces:** Consumes Task 1 search pages; produces the explicit query, reset callbacks, match
counts, inert complete numbered preview and existing unselected physical-line chooser.

- [ ] Write failing UI tests for preview-before-selection, no matches, query/file/page/context reset,
  query draft clearing, explicit attribution/save and unchanged non-gating state.
- [ ] Run focused tests; expect missing UI behavior failures.
- [ ] Add the query and bounded preview using supported code widget settings; preserve existing
  Add/Correct/Withdraw and exact-source append rules.
- [ ] Extend installed browser journey to find source beyond first1,000 by text, preserve existing
  page11 coverage, verify query resets, inert hostile/long source, geometry and save/reopen.
- [ ] Run focused UI/core/browser checks; expect all pass. Add core search tests to Windows lane.
- [ ] Align README/roadmap/release status and dated audit with actual scope and evidence limits.
- [ ] Run exact-head full 95% unrounded coverage, lint/lock/diff, deterministic benchmarks and
  clean install/package/browser checks; expect all pass. Preserve seven frozen R-002 hashes.
- [ ] Commit, obtain independent whole-branch agent review, resolve supported findings and rerun
  affected checks. Open PR and require exact-head hosted CI/CodeQL, guarded merge and verified main.
