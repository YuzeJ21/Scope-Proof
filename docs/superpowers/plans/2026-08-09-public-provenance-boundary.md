# Verified Public Provenance Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure only pull requests with verified public GitHub repository metadata can be labeled live-public or counted as genuine alpha evidence.

**Architecture:** GitHub ingestion produces the only trusted verified-public visibility fact. Shared Pydantic models persist that fact through snapshots, reviews, alpha cases, storage, and exports; CLI and Streamlit copy it only through guarded review construction, and alpha transitions independently require it.

**Tech Stack:** Python 3.11+, Pydantic v2, httpx, Typer CLI, Streamlit, pytest

## Global Constraints

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Never execute target-repository code.
- `verified_public` requires unambiguous GitHub metadata; missing or contradictory metadata fails closed.
- Tokens remain session-only and absent from records, errors, logs, and exports.
- Legacy records without the fact remain readable as `unverified` but Stage 1-ineligible.
- Every persisted or exported object remains Pydantic-validated.
- Use named-file staging only and preserve `.coverage 2` untouched.

---

### Task 1: GitHub ingestion establishes verified visibility

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/github/client.py`
- Test: `tests/github/test_client.py`

**Interfaces:**
- Produces: `RepositoryVisibility.UNVERIFIED` and `RepositoryVisibility.VERIFIED_PUBLIC`
- Produces: `PullRequestSnapshot.repository_visibility: RepositoryVisibility`
- Produces: `RepositoryVisibilityUnverified`, a bounded ingestion error

- [ ] **Step 1: Write failing public/private/malformed/mismatched metadata tests**

Add literal GitHub response fixtures asserting that only matching `private: false` plus
`visibility: public` returns a snapshot with `verified_public`; explicit private and
all ambiguous variants raise bounded errors before secondary fetches.

- [ ] **Step 2: Run the focused tests and confirm the intended failures**

Run: `pytest tests/github/test_client.py -q`

Expected: failures because the visibility enum, field, and fail-closed validation do
not exist.

- [ ] **Step 3: Implement the minimal typed ingestion boundary**

Add the enum and snapshot field. Validate `base.repo.full_name`, `private`, and
`visibility` immediately after the PR response, before fetching files, commits, or
checks. Return `verified_public` only for the unambiguous public case.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run: `pytest tests/github/test_client.py -q`

- [ ] **Step 5: Commit the ingestion contract with named files**

Stage only the schema, client, and GitHub client test files.

### Task 2: Review construction, persistence, and exports retain the fact

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/cli.py`
- Modify: `apps/web/app.py`
- Test: `tests/schemas/test_models.py`
- Test: `tests/cli/test_cli.py`
- Test: `tests/apps/test_streamlit_app.py`
- Test: `tests/storage/test_json_store.py`
- Test: `tests/reporting/test_exporters.py`

**Interfaces:**
- Produces: `Review.repository_visibility: RepositoryVisibility`
- Consumes: `PullRequestSnapshot.repository_visibility`
- Enforces: current construction cannot pair `LIVE_PUBLIC_GITHUB` with `unverified`

- [ ] **Step 1: Write failing schema, CLI, Streamlit, reopen, and export regressions**

Assert live review construction rejects unverified snapshots, verified snapshots keep
the fact across CLI/web analysis, save/reopen, and JSON export, and historical payloads
without the field load as `unverified` without receiving invented evidence.

- [ ] **Step 2: Run the focused tests and confirm the intended failures**

Run the named test modules with `pytest -q` and verify each failure names the absent
guard or field.

- [ ] **Step 3: Implement minimal propagation and guards**

Copy snapshot visibility into every review constructor. Guard shared CLI bundle
construction and Streamlit analysis before assigning `LIVE_PUBLIC_GITHUB`. Preserve
legacy readability through the enum default.

- [ ] **Step 4: Run all focused modules and confirm they pass**

Run: `pytest tests/schemas/test_models.py tests/cli/test_cli.py tests/apps/test_streamlit_app.py tests/storage/test_json_store.py tests/reporting/test_exporters.py -q`

- [ ] **Step 5: Commit the propagation contract with named files**

Stage only the touched production and test files.

### Task 3: Genuine alpha requires verified public provenance

**Files:**
- Modify: `scopeproof_core/alpha/models.py`
- Modify: `scopeproof_core/alpha/service.py`
- Modify: `scopeproof_core/alpha/__init__.py`
- Modify: `apps/web/app.py`
- Test: `tests/alpha/test_models.py`
- Test: `tests/alpha/test_service.py`
- Test: `tests/alpha/test_storage.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Produces: `AlphaQualificationInput` for pre-fetch session validation
- Produces: `AlphaQualification.repository_visibility == verified_public`
- Produces: `AlphaCaseRecord.repository_visibility`, defaulting legacy records to `unverified`
- Consumes: the loaded snapshot's verified visibility during alpha-case creation

- [ ] **Step 1: Write failing qualification, legacy, outcome, and UI regressions**

Assert verified visibility is required to create a new alpha case, legacy cases remain
readable but cannot record outcomes, unverified reviews cannot record outcomes, and
the Streamlit alpha flow binds the qualification to the loaded verified snapshot.

- [ ] **Step 2: Run the focused tests and confirm the intended failures**

Run: `pytest tests/alpha/test_models.py tests/alpha/test_service.py tests/alpha/test_storage.py tests/apps/test_streamlit_app.py -q`

- [ ] **Step 3: Implement the minimal alpha boundary**

Separate session intake from verified qualification, persist the verified fact in new
alpha cases, add both case and review checks to outcome and public-summary transitions,
and pass the loaded snapshot fact through Streamlit.

- [ ] **Step 4: Run the focused tests and confirm they pass**

Run the same named modules and confirm no token or private metadata enters output.

- [ ] **Step 5: Commit the alpha contract with named files**

Stage only the touched alpha, app, and test files.

### Task 4: Full verification and owner-ready pull request

**Files:**
- Modify if needed: authoritative trust/status documentation directly affected by this repair
- Test: all repository checks and installed-wheel browser workflow

**Interfaces:**
- Consumes: the completed verified-public implementation
- Produces: a ready-for-review PR with all available checks resolved or classified

- [ ] **Step 1: Run Ruff and the complete suite with combined coverage**

Require at least 95% combined coverage and preserve intentional skip classifications.

- [ ] **Step 2: Run repository contracts and both deterministic benchmarks**

Require zero mismatches, zero must-have False Ready outcomes, zero false blockers, and
zero unexecuted declared categories.

- [ ] **Step 3: Build two wheels and compare SHA-256 values**

Require byte-identical wheel hashes, validate clean dependencies, installed version
equality, both CLI versions, installed benchmarks, and exact loopback workbench health.

- [ ] **Step 4: Run the explicit installed-wheel browser regression**

Require loopback-only networking and zero console or page errors.

- [ ] **Step 5: Audit the diff and request independent review**

Resolve every actionable Critical or Important finding without unrelated refactoring.

- [ ] **Step 6: Commit remaining intentional files, push, and open a ready PR**

Monitor CI, CodeQL, Pages, and every available check. Do not merge; stop only at the
clean owner merge decision.
