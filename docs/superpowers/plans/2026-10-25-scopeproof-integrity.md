# ScopeProof Integrity and Portfolio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair evidence integrity, make automated verification safe and reproducible, reconcile current project truth, and prepare a version-bound portfolio package.

**Architecture:** Keep GitHub ingestion and semantic validation in the core; keep Streamlit storage and presentation at the UI edge. Establish test isolation before any complete suite run, then harden revision binding and persisted/exported state with focused regressions. Treat dependency PRs, JUnit integration, documentation, and portfolio artifacts as separate reviewable decisions after the core is sound.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, Streamlit, pytest, Playwright, uv, GitHub Actions.

**Spec:** ScopeProof goal attachment at `/Users/yjian070/.codex/attachments/ea187ecc-e8a6-4db0-bde0-07fba55c925d/Pasted text.txt`; repository rules in `AGENTS.md`.

## Global Constraints

- Never execute target-repository code in the application server.
- Candidate implementation/test references, external runtime records, and human acceptance stay distinct.
- Criterion verdicts cite explicit support or name missing evidence; persist/export only schema-valid state.
- Gate changes are deterministic, fail closed, and receive regression coverage.
- Preserve existing user data, frozen R-002 inputs/results, and pre-existing untracked files.
- Keep the core independent of Streamlit and GitHub UI.
- Do not merge, release, deploy, post, or contact people under this goal.

## Review Focus

- PR head changes during any mutable list page: ingestion rejects the mixed revision.
- PR base changes while head stays fixed: ingestion rejects the mixed comparison.
- Empty candidate lists and partial pagination: normal bounded ingestion still behaves deterministically.
- Legacy review records with supported migrations: validation preserves historical state without granting new evidence.
- UI tests without explicit storage configuration: each test writes only to its own temporary directory.

---

### Task 1: Isolate app tests and establish a safe baseline

**Files:** Create `tests/apps/conftest.py`; create `tests/apps/test_storage_isolation.py`; inspect `tests/browser/test_packaged_workbench.py`.

**Interfaces:** The test fixture changes `Path.home()` for app tests only and leaves application code untouched. Packaged browser tests use their existing temporary runtime home.

- [ ] Write an app regression proving all default review, alpha, and rehearsal paths resolve below a per-test temporary root and that a no-setup app cannot see a sentinel in the real store.
- [ ] Run the regression before the fixture and confirm the expected failure.
- [ ] Add the smallest autouse app-test fixture to isolate `Path.home()` per test.
- [ ] Run the focused app tests with the repository interpreter, then the safe full baseline through a normal Python module invocation compatible with multiprocessing.
- [ ] Commit the independently reviewable isolation change.

### Task 2: Bind GitHub ingestion to a stable PR revision

**Files:** Modify `scopeproof_core/github/client.py`; extend `tests/github/test_client.py` and `tests/github/test_pagination_and_candidates.py`.

**Interfaces:** `GitHubClient.fetch_pull_request(url) -> PullRequestSnapshot` either returns one stable head/base pair or raises `GitHubIngestionError` with a safe movement reason.

- [ ] Add mocked regressions for head movement, base-only movement, movement during multi-page files/commits, and unchanged PR identity; run to observe the expected failures.
- [ ] Re-read PR identity after collection with the same request budget and reject movement or unverifiable identity before returning a snapshot.
- [ ] Verify all focused ingestion tests and dependent candidate/permalink tests.
- [ ] Commit the independently reviewable revision-binding change.

### Task 3: Validate evidence semantics across save and export

**Files:** Modify `scopeproof_core/schemas/models.py` and, if needed, `scopeproof_core/gates/validation.py`; extend `tests/schemas/test_review_bundle_integrity.py`, `tests/gates/test_validation.py`, and storage/export boundary tests.

**Interfaces:** `ReviewBundle.model_validate`, `validated_review_bundle`, and `validated_review_state` reject unsupported finding/evidence/runtime relationships; approved human overrides remain explicit and reproducible.

- [ ] Add regressions for unsupported finding levels, absent support and missing explanation, incompatible candidate type/level, review-head and permalink mismatch, and invalid runtime links; observe expected failures.
- [ ] Add narrow schema and shared-integrity checks without changing the allowed human decision vocabulary.
- [ ] Verify focused schema, gate, storage, export, comparison, and lifecycle tests; commit.

### Task 4: Reconcile pending integration and release truth

**Files:** Review PRs #199-#201 and their lockfile changes; edit narrowly scoped docs and `.gitignore` as supported by live evidence.

**Interfaces:** Each dependency and JUnit disposition records exact PR head, tests, and reason. Published-version instructions match the published tag; development-only behavior is explicitly labeled.

- [ ] Recheck live PR state, dependency advisories, JUnit boundaries, archival commits, and the untracked comparison file.
- [ ] Prepare narrowly scoped integration/follow-up changes and run relevant tests; avoid bulk merging divergent history.
- [ ] Correct current docs, version examples, feature ledger, roadmap, and ignore rules while preserving historical records.
- [ ] Commit and prepare reviewable draft PRs for completed units.

### Task 5: Verify and prepare exact-version portfolio assets

**Files:** Create a concise case study, architecture diagram, automated walkthrough, refreshed screenshots, and LinkedIn draft under a version-bound portfolio directory.

**Interfaces:** Every claim names the demonstrated commit/version and distinguishes constructed automation from human/customer evidence.

- [ ] Run the complete isolated suite, lint, deterministic benchmarks, packaging/clean-install checks, and installed browser journey; record exact commands and results.
- [ ] Obtain independent agent review, repair supported findings, and rerun affected checks.
- [ ] Generate and inspect portfolio assets against the tested head; keep publication local.
- [ ] Provide PR links, exact heads, archival dispositions, verification limits, and remaining owner decisions.
