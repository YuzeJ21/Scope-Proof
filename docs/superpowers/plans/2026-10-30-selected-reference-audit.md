# Selected-reference audit implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline; independent design audit and one fresh whole-branch review.

**Goal:** Correct and withdraw selected references with preserved attribution and history.

**Architecture:** Immutable references plus bounded terminal events; derive active status. Pure core transitions and version-seven storage feed lifecycle-aware UI, comparison and exports.

**Tech Stack:** Python/Pydantic, Streamlit, pytest/AppTest, installed-wheel Playwright, protected GitHub CI.

**Spec:** `docs/superpowers/specs/2026-10-30-selected-reference-audit-design.md`

## Global constraints

- Maximum 32 active references, 128 retained records and 128 terminal events per analysis.
- Preserve exact-head/source validation, explicit confirmed criteria/decisions, source-authority and optimistic persistence guards.
- Preserve frozen R-002 bytes/results, release identity and Stage 3 boundaries; no personal testing or qualifying reviews.

## Review focus

- Same-location rationale corrections must not fail legacy duplicate-location checks or resurrect the original.
- A withdrawal made after reopen must work without source, without converting inaccessible source to permission.
- Old comparisons must not imply their missing lifecycle history is an empty/verified-active snapshot.
- Corrected/withdrawn unchanged-file references must not require later retrieval, while automatic references still do.
- Concurrent save/queued export and source/criterion retarget must not apply a stale action to a different reference.

### Task 1: Validated audit and transitions

**Files:** models.py, new reviews/reference_audit.py, reviews/selected_references.py, storage/json_store.py; focused schemas/reviews/storage tests.

**Interfaces:** `SelectedReferenceEvent`; `active_reviewer_selected_reference_ids` derived on ReviewBundle; `reference_status(references, events, reference_id)`; `withdraw_reviewer_selected_reference(state, *, reference_id, reviewer, reason, expected_state_fingerprint)`; `correct_reviewer_selected_reference` additionally takes snapshot, selected, rationale and optional unchanged_files.

- [ ] Write regression tests for audited correction/withdrawal, same-location chains and unchanged gate/history; observe RED.
- [ ] Implement terminal-event integrity validation, strict bounds and exact-context pure transitions; observe GREEN.
- [ ] Test and implement pre-7 active/history downgrade rejection and read-only safe migration; update writer-version assertions.

### Task 2: Consistent product surfaces

**Files:** selected_reference_comparison.py (core/UI), reporting/exporters.py, reviews/source_attachment.py, apps/web/selected_references.py, apps/web/app.py; corresponding tests/browser journey.

**Interfaces:** Comparison carries optional per-side lifecycle snapshots, derives active IDs and validates terminal chains. Existing selected-reference renderer returns the same validated state transition for all three actions.

- [ ] Write export/comparison/source/UI regression tests and observe RED.
- [ ] Show explicit lifecycle status/events, preserve old-comparison unknown state, and use active references for source continuation.
- [ ] Add explicit action/target/actor/reason UI, preserve pending/conflict/acceptance guards and reset consumed drafts safely.
- [ ] Extend installed-wheel restart/reopen/download journey through correction and withdrawal; verify unchanged deterministic analysis.

### Task 3: Evidence and checked integration

**Files:** README, ROADMAP, current release-status record and dated audit.

- [ ] Refresh current product outcome and limits; keep candidate/release evidence historical.
- [ ] Run focused/full 95%-covered suite, lint/lock, deterministic benchmarks, isolated package/browser checks and frozen manifest comparison.
- [ ] Obtain independent whole-branch review, fix supported findings with RED→GREEN and rerun affected checks.
- [ ] Commit/create/attach PR; require exact reviewed-head hosted compatibility/CI/CodeQL and resolved findings; guarded merge.
- [ ] Verify resulting main, clean synchronized checkouts and unchanged frozen bytes; archive only the owned execution ledger.
