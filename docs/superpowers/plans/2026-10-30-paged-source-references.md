# File-scoped source reference paging implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with independently authored tests and one fresh whole-branch review.

**Goal:** Reach eligible exact-head static references beyond the global first 1,000 through bounded file pages.

**Architecture:** Share existing eligibility in one iterator; retain the legacy prefix API. Add validated file/page models and core functions, then use them in the workbench without changing saved schemas or gate truth.

**Tech Stack:** Python, Pydantic, Streamlit, pytest/AppTest, Playwright, existing GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-paged-source-references-design.md`

## Global constraints

- Page size 100 eligible lines; saved reference limit 32; line limit 4,096 UTF-8 bytes.
- Preserve source policy, exact-head/fingerprint binding, confirmed criteria and non-gating references.
- Preserve frozen R-002 bytes, record v6, releases and Stage 3 gates; no target-code execution.
- User delegates routine choices and declines personal testing and qualifying reviews.

## Review focus

- A queued save after source/page changes must never save a different line.
- Sparse eligible lines retain physical Git coordinates and cannot fall through to another file.
- Invalid page requests and mutated Pydantic instances fail closed.
- Duplicate paths, rename aliases and unavailable source cannot bypass existing exclusions.
- Saving later lines changes references only; reopening/export does not reconstruct evidence.

### Task 1: Validated file/page core and workbench

**Files:** `scopeproof_core/reviews/selected_references.py`, `apps/web/selected_references.py`, new `tests/reviews/test_reference_pages.py`, new `tests/apps/test_reference_pages.py`.

**Interfaces:** `selectable_reference_sources(state, snapshot, unchanged_files=None)` returns frozen `SelectableReferenceSource` objects (`source_scope`, `file_path`, `eligible_line_count`). `selectable_reference_page(state, snapshot, *, source_scope, file_path, page_index=0, unchanged_files=None)` returns frozen `SelectableReferencePage` (`source`, `page_index`, `lines`, computed `page_count`). `MAX_REFERENCE_PAGE_LINES=100`. Existing append signature and legacy API remain.

- [ ] Write core tests independently and UI regressions; record expected RED before production changes.
- [ ] Extract shared ordered eligibility iteration, validate page requests/results and exact source saves.
- [ ] Add file/page selectors, line reset on page/source changes and explicit ordinal range copy.
- [ ] Run affected core/UI/store/report tests; fix failures and verify nongating invariants.
- [ ] Extend installed-wheel journey with constructed >1,000-line source and later-file selection.

### Task 2: Verification, current documentation and integration

**Files:** README, ROADMAP, release-status record and dated audit; browser regression.

- [ ] Update current wording to the selected outcome while retaining dated historical facts.
- [ ] Run lint/lock/diff, deterministic benchmarks, full covered suite and fresh installed-browser checks; preserve logs and frozen manifests.
- [ ] Commit, obtain one independent whole-branch review, resolve supported findings and rerun affected checks.
- [ ] Create/attach PR, await exact-head protected CI including compatibility lanes and check review threads.
- [ ] Guarded merge, verify resulting-main CI/tree/frozen bytes and synchronize clean main checkouts.
- [ ] Archive only this task's execution ledger and report evidence with remaining genuine-use gate.
