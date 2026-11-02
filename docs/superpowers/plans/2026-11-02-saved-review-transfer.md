# Saved-review transfer implementation plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task with independent whole-branch review.

**Goal:** Transfer complete saved reviews safely and reopen them in the existing workbench.
**Architecture:** Share the store decoder, preserve UTF-8 bytes, use locked atomic no-overwrite imports and exports, expose a thin CLI and typed receipts.
**Tech Stack:** Python, Pydantic, existing local storage primitives, pytest, Playwright.
**Spec:** docs/superpowers/specs/2026-11-02-saved-review-transfer-design.md

## Global Constraints

64 MiB maximum. Existing record versions 1–9. Unrounded 95% coverage. No authority inflation,
source execution, overwritten records, altered frozen benchmarks, release or Stage 3 advancement.

## Review Focus

- Duplicate JSON keys must fail before writes (task 1).
- Foreign filename owner must not export under a different identity (task 1).
- Legacy gates may migrate in memory but original transfer bytes must survive (task 1).
- Concurrent imports and symlink collisions must never overwrite (task 1).
- Pending criteria and historical-only reviews must reopen without gaining current authority (task 2).

## Task 1: Validated byte-preserving core and CLI

Files: scopeproof_core/storage/{atomic_files,json_store,transfer}.py,
scopeproof_core/cli_transfer.py, scopeproof_core/cli.py, tests/storage/test_review_transfer.py.
Interfaces: JsonReviewStore.decode_record(text: str) -> ReviewState;
export_review(store, review_id, output) -> ReviewTransferReceipt;
import_review(store, source) -> ReviewTransferReceipt.

- [x] Write behavior tests for current/legacy round trips, history, pending confirmation,
  provenance, malformed/version/duplicate/size rejection, unsafe owner/path, collision and concurrency.
- [x] Run tests and confirm missing transfer behavior fails.
- [x] Implement shared decoder, opt-in exact-newline reader, transfer service and CLI registration.
- [x] Run focused storage/CLI tests and lint; commit validated implementation.

## Task 2: Installed reopening and delivery

Files: tests/cli/test_installed_transfer.py, tests/browser/test_review_transfer.py,
.github/workflows/ci.yml, README.md, ROADMAP.md, current release-status record, audit note.
Consumes task 1 commands and receipt fields. No second reopening implementation.

- [x] Add installed CLI round trip and history-only/pending workbench reopening journey.
- [ ] Run installed-wheel/browser checks, full suite and unrounded coverage, lint, benchmarks.
- [x] Update roadmap/current docs and preserve an external verification packet.
- [x] Obtain independent whole-branch review, fix supported findings and rerun affected checks.
- [ ] Create PR, verify exact-head CI, merge with expected-head guard, verify main and clean checkouts.
