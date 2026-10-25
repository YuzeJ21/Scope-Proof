# Bounded Saved JSON Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound app-owned review, alpha-case, and owner-rehearsal JSON files to 64 MiB on reads and writes, with consistent behavior across supported storage backends.

**Architecture:** Add a shared bounded binary-to-UTF-8 read helper in `atomic_files.py`. Keep the existing descriptor and portable path checks, feed their already-opened file into the helper, and make the three validated stores enforce the same limit before writes. Reuse Pydantic parsing and existing atomicity.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, Ruff, uv.

**Spec:** `docs/superpowers/specs/2026-10-26-bounded-saved-json-design.md`

## Global Constraints

- Maximum saved-record size: `64 * 1024 * 1024` UTF-8 bytes; exactly the maximum is allowed.
- Read no more than the maximum plus one byte from an opened record.
- Preserve no-follow, regular-file, identity, lock, write-atomicity, migration, and Pydantic behavior.
- Do not alter gate inputs, evidence levels, or Stage 1 and Stage 3 claims.

## Review Focus

- A regular file larger than the cap is rejected before JSON parsing.
- A file that grows after metadata inspection cannot make the reader consume unlimited data.
- Both descriptor and portable paths enforce the same cap.
- A failed oversized write preserves any existing review and creates no rehearsal file.
- At-limit UTF-8 data and ordinary saved records remain readable.
- Windows newline translation cannot expand accepted review bytes past the limit.

---

### Task 1: Bounded cross-platform reader

**Files:** Modify `scopeproof_core/storage/atomic_files.py`; test `tests/storage/test_atomic_files.py`.

**Interface:** `MAX_SAVED_RECORD_BYTES = 64 * 1024 * 1024`; `read_text_no_follow(path, *, claim=None, max_bytes=MAX_SAVED_RECORD_BYTES)`; shared bounded UTF-8 reader for an already-opened binary file.

- [ ] Add tests for exact-limit, over-limit, and portable and descriptor branches, including one read whose reported size is below its content length.
- [ ] Run the tests and verify they fail for the unbounded implementation.
- [ ] Implement metadata rejection and a maximum-plus-one binary read before UTF-8 decoding.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Saved review and rehearsal boundaries

**Files:** Modify `scopeproof_core/storage/json_store.py` and `scopeproof_core/alpha/rehearsal_storage.py`; test `tests/storage/test_json_store.py` and `tests/alpha/test_rehearsal_storage.py`.

**Interface:** Both stores use `MAX_SAVED_RECORD_BYTES` for load and save; oversized files raise a clear `ValueError` and leave stored bytes unchanged.

- [ ] Add tests for over-limit review and rehearsal loads on both backends, exact-limit read behavior via the shared helper, Windows newline translation, and rejected review replacement and rehearsal creation.
- [ ] Run the new tests and verify the expected failures.
- [ ] Route review load and both rehearsal load paths through bounded reading; reject an oversized serialized record before write side effects.
- [ ] Run focused storage tests, then lint, benchmark, and the full suite with the repository's coverage threshold.
- [ ] Review the diff and commit the verified change.

### Task 3: Genuine alpha-case symmetry

**Files:** Modify `scopeproof_core/alpha/storage.py`; test `tests/alpha/test_storage.py`.

**Interface:** Alpha-case existence, load, update, and save paths use `MAX_SAVED_RECORD_BYTES`; an oversized update leaves existing bytes unchanged.

- [ ] Add failing tests for exact-limit and over-limit alpha-case reads on both backends, oversized creation, and oversized update.
- [ ] Run the tests and confirm the expected failures.
- [ ] Apply the cap to every alpha-case read and to serialized save and update payloads before publication.
- [ ] Run the focused alpha-case suite, then repeat final branch verification and review.
