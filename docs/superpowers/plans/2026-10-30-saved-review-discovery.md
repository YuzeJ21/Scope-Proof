# Saved-review discovery implementation plan

> **For agentic workers:** Root implements core/storage and integration; one bounded UI implementer works in owned files. Use RED→GREEN and fresh independent whole-branch review before checked merge.

**Goal:** Find, reopen and compare saved reviews through bounded validated metadata.

**Architecture:** A pure core session-only discovery page reads at most ten fully validated records under a 1 MiB per-record cap. Shared workbench details/search feed existing ID selection, stale-record receipts and comparison guards.

**Tech Stack:** Python/Pydantic, Streamlit/AppTest, pytest, installed-wheel Chromium, protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-saved-review-discovery-design.md`

## Global constraints

- Ten candidates per explicit page; 1 MiB per record and 10 MiB aggregate payload plus bounded overflow probes; query maximum 200 characters.
- Default full saved-record read cap remains 64 MiB; listing IDs does not parse records.
- No record-version, gate/evidence/decision, frozen R-002, release or Stage 3 change; no personal testing/qualifying reviews.

## Review focus

- A large record must remain directly reopenable without a preview and must not prevent neighboring details from loading.
- A valid file containing another review ID must never acquire that other record's label or action authority.
- Changing page/query or deleting a record must not silently retarget a reopen, delete confirmation or comparison lease.
- Metadata staleness must not hydrate/compare changed saved truth under an old descriptive label.
- Search must disclose loaded-page coverage and preserve foreign compatible history beneath an incompatible active analysis.

### Task 1: Bounded validated discovery core

**Files:** new storage/discovery.py, storage/json_store.py; new tests/storage/test_review_discovery.py and tests/reviews/test_discovery_selection.py.

**Interfaces:** Pydantic SavedReviewMetadata/Entry/Page and helpers specified in the design; `JsonReviewStore.load(..., max_bytes=None)`; existing comparison preparation rejects selected file/owner mismatch.

- [ ] Write failing tests for metadata projection, strict paging/search, read limits and unavailable neighbors; observe RED.
- [ ] Add optional bounded loader, full-validated metadata pages and safe label/search helpers; observe GREEN.
- [ ] Test and implement preview-bound reopen and comparison owner/stale checks, preserving legacy/read-only behavior.

### Task 2: Shared discovery workbench and installed journey

**Files:** new apps/web/saved_discovery.py, apps/web/app.py, apps/web/saved_comparison.py; new tests/apps/test_saved_discovery.py; extend tests/browser/test_packaged_workbench.py.

**Interfaces:** `render_saved_discovery(store, saved_review_ids)` returns visible IDs and entry map; shared formatter and expected preview fingerprints feed both existing selectors; direct-ID mode uses core verified load.

- [ ] Observe AppTest RED for explicit metadata loading, scoped search/labels, target clearing and stale actions.
- [ ] Implement session-only page/query controls, selected summary and ID fallback; preserve pending-input/storage/delete/export guards.
- [ ] Reuse descriptive metadata in comparison without changing history or compatibility semantics.
- [ ] Extend one installed restart/reopen/comparison/download journey with repository/PR discovery and unchanged saved-byte checks.

### Task 3: Evidence and exact-head integration

**Files:** README, ROADMAP, current release-status record and dated audit.

- [ ] Record the bounded product outcome, limits, alternatives and genuine-evidence boundary before final verification.
- [ ] Run focused/full 95%-coverage suite, lint/lock/workflow checks, deterministic benchmarks, fresh package/browser and frozen-byte checks.
- [ ] Obtain fresh independent whole-branch review; fix supported findings with regressions and rerun affected checks.
- [ ] Create/attach PR, require reviewed exact-head hosted compatibility/CI/CodeQL, guarded merge, and resulting-main checks.
- [ ] Verify clean synchronized checkouts, archive only the owned ledger, report actual evidence and stop this bounded slice.
