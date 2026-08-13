# Platform-Safe Alpha Storage Implementation Plan

> **For agentic workers:** Execute each task test-first and keep named-file commits. Do not advance
> product stages or broaden the feature boundary.

**Goal:** Make ScopeProof's alpha/rehearsal persistence and CLI report publication portable,
exclusive, interruption-safe, and fail-closed on supported platforms.

**Architecture:** A core atomic-files module provides conservative path validation, exclusive
same-directory publication, and per-record mutation claims. Alpha and rehearsal stores retain
Pydantic validation and use the strongest available backend; the CLI calls the same final
no-overwrite publication boundary. Hosted Windows CI proves the portable package/CLI/storage lane.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, multiprocessing, uv, Ruff, GitHub Actions.

### Task 1: Define the red portability and atomic-publication contract

**Files:** `tests/storage/test_atomic_files.py`, `tests/alpha/test_storage.py`,
`tests/alpha/test_rehearsal_storage.py`, `tests/cli/test_cli.py`

- [ ] Add a subprocess import regression with POSIX-only constants absent.
- [ ] Add deterministic concurrent-process create and update races; require exactly one success.
- [ ] Add interrupted-write, symlink/reparse, malformed data, mismatched-ID, cleanup, and CLI report
  destination-race regressions.
- [ ] Run the focused selection and record the intended failures before implementation.

### Task 2: Implement portable filesystem primitives

**Files:** `scopeproof_core/storage/atomic_files.py`, `scopeproof_core/storage/__init__.py`,
`tests/storage/test_atomic_files.py`

- [ ] Validate all existing path components and reject links, reparse points, and wrong types.
- [ ] Implement private temporary creation, flush, exclusive publication, and cleanup.
- [ ] Implement an exclusive mutation claim with deterministic competing-writer failure.
- [ ] Make unsupported capabilities fail closed with user-safe errors.
- [ ] Run focused storage tests and Ruff until green; commit named files intentionally.

### Task 3: Migrate both alpha stores without weakening POSIX behavior

**Files:** `scopeproof_core/alpha/storage.py`, `scopeproof_core/alpha/rehearsal_storage.py`,
`tests/alpha/test_storage.py`, `tests/alpha/test_rehearsal_storage.py`

- [ ] Make POSIX capability detection import-safe and retain descriptor-relative POSIX operations.
- [ ] Use the portable backend only where the POSIX primitives are unavailable.
- [ ] Make alpha creates no-clobber and alpha updates claim, reread, validate, then replace.
- [ ] Validate requested IDs against Pydantic-validated payload IDs on every load.
- [ ] Run focused alpha tests and Ruff until green; commit named files intentionally.

### Task 4: Close the CLI report race and add Windows CI

**Files:** `scopeproof_core/cli.py`, `tests/cli/test_cli.py`, `.github/workflows/ci.yml`,
`tests/test_repository_contracts.py`, `CHANGELOG.md`, relevant status/roadmap docs

- [ ] Publish CLI reports exclusively at the final write boundary and keep failed commands
  non-mutating.
- [ ] Add a hosted Windows package/CLI/storage job and include it in the aggregate verification
  dependency graph.
- [ ] Document Windows evidence narrowly and keep Product Stage 1 at exact zero.
- [ ] Run focused CLI/contracts tests and Ruff until green; commit named files intentionally.

### Task 5: Verify, review, and publish the engineering PR

- [ ] Run Ruff, full suite with at least 95% coverage, repository contracts, both deterministic
  benchmarks, two byte-identical wheels, artifact inventory, clean install/dependency/version/CLI
  checks, loopback health, packaged Chromium, and supported Python lanes.
- [ ] Audit the final diff and commits; run an independent `codex review` of the exact head.
- [ ] Fix every actionable Critical or Important finding test-first and repeat affected checks.
- [ ] Push `codex/platform-safe-alpha-storage`, open a ready PR, and monitor every available check
  to a terminal green or truthfully classified conclusion.
- [ ] Do not merge the new PR. Hand off its URL, exact SHAs, evidence, unsupported environments,
  preserved `.coverage 2` proof, Stage 1 zero counts, and the next owner merge decision.
