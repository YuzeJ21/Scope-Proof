# One-Command Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an installed ScopeProof user review a public PR and write a deterministic report in one command without breaking existing CLI behavior.

**Architecture:** Validate an optional report path before ingestion, then render the saved validated review through the existing exporter selected by suffix. Keep metadata stdout and the separate export command backward compatible; release one exact-main v0.1.13 wheel plus checksum.

**Tech Stack:** Python 3.11+, argparse, pathlib, Pydantic review state, existing exporters, pytest, Hatchling

## Global Constraints

- Never overwrite an existing file.
- Accept only `.md`, `.json`, `.csv`, and `.html` suffixes.
- Render only validated ScopeProof review state through existing exporters.
- Do not execute reviewed repository code or convert static evidence into runtime verification.
- Add no service, account, billing, API, LLM, license, or dependency.

---

### Task 1: Safe one-command report output

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Produces: optional `review --report PATH` with suffix-selected report output and metadata `report` field.
- Consumes: existing `export_markdown`, `export_json`, `export_csv`, and `export_html` renderers over validated review state.

- [ ] **Step 1: Write failing success and safety tests**

Test Markdown creation and metadata, unchanged metadata without `--report`, existing-path refusal before fixture reading, unsupported-suffix refusal, and one representative JSON/CSV/HTML output assertion.

- [ ] **Step 2: Verify RED**

Run the new focused CLI tests. Expected: argparse rejects `--report` because it does not exist.

- [ ] **Step 3: Implement minimal path validation and rendering**

Add the optional argument, a suffix-to-renderer mapping, pre-ingestion suffix/existence validation, UTF-8 report writing, and conditional metadata field. Reuse the existing expected-error boundary.

- [ ] **Step 4: Verify GREEN**

Run all CLI tests. Expected: all pass with concise error output and no overwrite.

### Task 2: Versioned first-use documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Produces: v0.1.13 package metadata and copyable one-command public-PR guidance.
- Consumes: `scopeproof review --report scopeproof-review.md`.

- [ ] **Step 1: Add failing repository contracts**

Require version 0.1.13, v0.1.13 wheel/checksum URLs, the `--report` example, non-overwrite guidance, and the retained `scopeproof export REVIEW_ID` path.

- [ ] **Step 2: Verify RED**

Run the focused repository contracts. Expected: version and README assertions fail.

- [ ] **Step 3: Update package and README**

Bump to 0.1.13, update release URLs, show the one-command Markdown report path first, explain metadata and no-overwrite behavior, and retain repeat export instructions.

- [ ] **Step 4: Run full local gates**

Run Ruff, full pytest, source benchmark, clean-wheel benchmark, one-command Markdown and HTML fixture reports, installed web health, Ctrl+C behavior, and `git diff --check`.

- [ ] **Step 5: Publish protected implementation PR**

Commit scoped files, push the branch, open a ready PR, require verify, evidence review, and CodeQL, merge normally, and require merged-main CI, CodeQL, and Dependency Graph success.

### Task 3: Exact-main v0.1.13 release

**Files:**
- External release assets: `scopeproof-0.1.13-py3-none-any.whl` and matching `.sha256`.

**Interfaces:**
- Consumes: exact protected-main merge commit.
- Produces: one public v0.1.13 release with verified wheel, checksum, benchmark, one-command report, and web health evidence.

- [ ] **Step 1: Build and verify from exact main archive**

Build the wheel from `git archive` of the merge commit; install in a fresh environment; run benchmark, one-command Markdown/HTML fixture reports, and loopback web health.

- [ ] **Step 2: Publish wheel and checksum**

Create v0.1.13 targeting the merge commit with both assets and evidence-limited release notes.

- [ ] **Step 3: Verify public release**

Redownload both assets through public URLs, verify checksum, reinstall, rerun benchmark and one-command report, and require tag CI success.
