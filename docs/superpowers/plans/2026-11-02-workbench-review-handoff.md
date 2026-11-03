# Workbench saved-review handoff implementation plan

> **For agentic workers:** Use superpowers:executing-plans, followed by independent whole-branch review.

**Goal:** Complete saved-review handoff through the local workbench.
**Architecture:** Byte-based validated core transfer services, typed inspection, bound deferred
saved-record download, explicit upload inspection/import, existing reopen flow.
**Tech Stack:** Python, Pydantic, Streamlit, pytest and installed Playwright Chromium.
**Spec:** docs/superpowers/specs/2026-11-02-workbench-review-handoff-design.md

## Global constraints

64 MiB payload limit; 68 transport/widget headroom; JUnit 1 MiB unchanged. Original record
version and bytes preserved. Full unrounded 95% coverage. No target code execution, automatic
confirmation/acceptance, overwrites, frozen-benchmark changes, release or Stage 3 advancement.

## Review focus

- Changed bytes after preview must fail before writing (task 1).
- Saved record replacement and stale download callbacks must fail closed (task 2).
- Changing upload must consume previous import consent (task 2).
- Importing beside open unsaved work must preserve that work (task 2).
- Full-size payload must reach the exact core cap through real transport (task 3).

## Task 1: Core preview and byte transfer

Files: scopeproof_core/storage/transfer.py; tests/storage/test_transfer_inspection.py.
Interfaces: inspect_review_bytes(raw) -> ReviewTransferPreview;
import_review_bytes(store, raw, expected_sha256=...) -> ReviewTransferReceipt;
read_review_transfer(store, review_id, expected_sha256=None) -> (bytes, ReviewTransferPreview).

- [x] Write/run failing tests for exact metadata, byte/hash binding, malformed/missing facts,
  bounds, no-overwrite and changed saved snapshot.
- [x] Implement using existing decoder/atomic storage, preserving CLI output contract.
- [x] Run focused transfer/storage regressions and lint.

## Task 2: Explicit workbench handoff

Files: apps/web/review_transfer.py, apps/web/app.py, apps/web/launcher.py,
.streamlit/config.toml, tests/apps/test_review_transfer.py, launcher/contracts tests.
Consumes task 1 interfaces; owns a volatile download lease and preview/consent state.

- [x] Write/run failing app tests for preview/import/download, stale callbacks, replacement,
  errors and open-draft preservation.
- [x] Implement the renderer and bounded transport settings, keeping JUnit's widget limit.
- [x] Run app/storage/launcher/contracts tests; update current roadmap and user guidance.

## Task 3: Installed journey and integration

Files: tests/browser/test_workbench_transfer.py, audit note; existing CI covers the new checks.

- [x] Add installed UI download/upload/import/reopen and transport-boundary regressions.
- [ ] Run full covered suite, lint, deterministic benchmarks, clean install/browser and CI.
- [ ] Independently review, fix supported findings and rerun affected checks.
- [ ] Create a reviewable PR, merge only after exact-head checks pass and verify clean main.
