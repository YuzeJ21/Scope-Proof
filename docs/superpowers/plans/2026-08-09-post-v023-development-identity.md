# Post-v0.2.3 Development Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the post-v0.2.3 source line an unambiguous development identity and reconcile active
documentation without changing published release evidence or product behavior.

**Architecture:** Keep `scopeproof_core/version.py` as the single runtime and package version source.
Extend repository contracts with a published-final-version-to-tag ledger and a real Git-tree
comparison so a divergent committed tree cannot reuse a published final version. Update only active
status surfaces or add historical-boundary notices; never rewrite commit-bound measurements.

**Tech Stack:** Python 3.12, Hatchling, pytest, Ruff, Git, uv, Playwright Chromium.

## Global constraints

- Development version is exactly `0.2.4.dev0`; public install remains v0.2.3.
- Published tag `v0.2.3`, release assets, checksums, and historical evidence remain unchanged.
- No schema, gate, lifecycle, persistence, export, ingestion, dependency, or workflow behavior
  changes.
- Stage 1 remains exactly 0/5, 0/3, 0/3, 0/3, and 0/2; engineering work earns zero credit.
- Real screen-reader, Windows desktop, Linux desktop, non-Chromium, and WCAG evidence remain
  unsupported.
- Stage named files only. Preserve `.coverage 2`. Do not merge, release, tag, publish, or contact
  participants.

---

### Task 1: Add the published-version tree guard test-first

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `scopeproof_core/version.py`

- [ ] Add a focused repository contract that maps final version `0.2.3` to `v0.2.3`, resolves the
  actual Git trees, and rejects the current divergent tree while it still identifies as `0.2.3`.
- [ ] Run the focused test and require RED for the specific published-version/tree mismatch.
- [ ] Change only `scopeproof_core/version.py` to `__version__ = "0.2.4.dev0"`.
- [ ] Rerun the focused contract and existing CLI/version provenance tests; require GREEN.
- [ ] Mentally mutate the version back to `0.2.3` and confirm the new contract is the test that
  would fail.

### Task 2: Record the complete Unreleased engineering ledger

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `tests/test_repository_contracts.py`

- [ ] Add a focused documentation contract for an `Unreleased` section that distinguishes the
  current development version from v0.2.3 and records CLI lifecycle parity, strict saved-record
  envelope validation, packaged Chromium regression, Python 3.13, keyboard/focus and bounded zoom,
  verified-public provenance, and private/ambiguous/malformed/legacy-unverified fail-closed paths.
- [ ] Run that contract and require RED because the current section says no changes are recorded.
- [ ] Replace the empty section with the smallest complete post-release ledger and explicit
  zero-Stage-1 and unsupported-environment boundaries.
- [ ] Rerun the focused contract and require GREEN.

### Task 3: Reconcile current product and roadmap surfaces

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/development-environment.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/releases/v0.2.3-platform-package-matrix.md`
- Modify: `docs/commercialization/market-comparison-2026-07-26.md`
- Modify: `tests/test_repository_contracts.py`

- [ ] Add focused contracts for the public-release/development-line distinction, completed CLI
  lifecycle and Python 3.13/keyboard evidence, exact Stage 1 counts, and unsupported real
  environments.
- [ ] Run the new contracts and require RED on stale current-facing statements.
- [ ] Update the README and development guide with v0.2.3 public-install versus `0.2.4.dev0`
  source identity and Python 3.11/3.12/3.13 engineering-lane wording.
- [ ] Update the roadmap and status page with merged PR #185/#187/#188 post-release engineering,
  remove CLI lifecycle parity from future work, retain passive Stage 1 intake, and preserve every
  product-stage gate.
- [ ] Add a dated post-release boundary to the platform/package matrix. Preserve all historical
  artifact hashes and measurements while recording current Python 3.13 and keyboard/focus evidence
  and the unsupported environment list.
- [ ] Update the market comparison's implemented/gap ledger without changing the product category
  or adding competitor-parity work.
- [ ] Rerun the focused contracts and require GREEN.

### Task 4: Mark superseded audits without rewriting evidence

**Files:**
- Modify only audits whose unqualified status can be mistaken for current truth under
  `docs/audits/`
- Modify: `tests/test_repository_contracts.py`

- [ ] Identify commit-bound audits that describe CLI parity, Python 3.13, keyboard/focus, or public
  provenance as future or unsupported after later merged evidence.
- [ ] Add a contract requiring an explicit historical/superseded notice and a link to the active
  status page; require RED before editing audit prose.
- [ ] Add notices only. Do not alter original SHAs, hashes, counts, versions, results, or limitations.
- [ ] Rerun focused repository contracts and require GREEN.

### Task 5: Verify source, package, and deterministic behavior

**Files:**
- Modify only confirmed in-scope defects found by verification, with a regression first

- [ ] Run `uv run ruff check .` and `git diff --check`.
- [ ] Run `uv run pytest -q tests/test_repository_contracts.py`.
- [ ] Run the complete suite with combined coverage over `scopeproof_core` and `apps` and
  `--cov-fail-under=95`; record exact tests, skips, and coverage.
- [ ] Run `uv run scopeproof benchmark`; require zero mismatches, zero must-have False Ready,
  zero false blockers, and zero unexecuted categories.
- [ ] Run `uv run scopeproof comparison-benchmark`; require zero mismatches.
- [ ] Build the final committed tree twice into separate temporary directories with normalized
  build conditions; require identical wheel SHA-256 values.
- [ ] Inspect wheel and source-distribution inventories for Git state, local review storage,
  coverage, virtual environments, caches, bytecode, or secrets; require zero forbidden matches.
- [ ] Install the wheel into a fresh external virtual environment, run dependency validation,
  require metadata/module/new-review identity equality at `0.2.4.dev0`, run both CLI versions and
  both installed benchmarks, and require exact loopback workbench health `ok`.
- [ ] Install the exact Playwright Chromium required by the lock if needed and run
  `uv run pytest -q -m browser tests/browser`; require loopback-only networking and zero console or
  page errors at both viewports.
- [ ] Confirm the protected CI definition still covers Python 3.11, Python 3.13, the locked
  environment, full verification, packaged browser, CodeQL, and Pages. Classify unsupported desktop
  and browser environments once.

### Task 6: Review, publish the branch, and stop at the owner gate

**Files:**
- Modify only confirmed in-scope defects found by review, with regression coverage where behavioral

- [ ] Audit `git status`, the full diff against `origin/main`, commit contents, dependency/lock
  state, and preserved `.coverage 2` fingerprint.
- [ ] Obtain independent review of the exact head. Resolve every actionable Critical or Important
  finding; challenge incorrect findings with repository evidence.
- [ ] Rerun affected checks and the complete final verification matrix after every repair.
- [ ] Commit named files intentionally with no unrelated files, generated reports, or local state.
- [ ] Push `codex/post-v023-development-identity` to `origin`.
- [ ] Open a ready-for-review PR against `main` titled
  `chore: restore post-v0.2.3 development identity` with exact evidence and limitations.
- [ ] Monitor every available check to a terminal conclusion. Diagnose and repair only confirmed
  in-scope failures on the same branch.
- [ ] Recheck final head/base SHAs, commits, diff, review threads, mergeability, and check
  conclusions. Do not merge; stop for the exact owner merge-or-hold decision.
