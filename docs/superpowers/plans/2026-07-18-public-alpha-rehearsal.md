# Truthful Owner Rehearsal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, separately persisted owner/Codex rehearsal path that proves local intake engineering behavior without becoming genuine public-alpha or Stage 1 evidence, then align participant onboarding contracts.

**Architecture:** New rehearsal Pydantic models and a create-only JSON store remain structurally separate from genuine `AlphaCaseRecord` records. A top-level CLI initializes and reloads the classified rehearsal; the existing fixture review, export, and comparison commands provide the controlled end-to-end engineering exercise. Public documentation and contract tests align the inbound sequence, outcome vocabulary, mobile navigation, and waiting-state token.

**Tech Stack:** Python 3.11+, Pydantic 2, argparse, pytest, Ruff, Streamlit AppTest, GitHub Actions.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Every criterion verdict must cite explicit evidence or state what evidence is missing.
- Implementation evidence must never be presented as test or runtime verification.
- Users must confirm normalized acceptance criteria before analysis.
- Never execute untrusted repository code in the application server.
- Validate every persisted or exported object with Pydantic schemas.
- Keep gate decisions deterministic and reproducible.
- Treat False Ready as more harmful than False Blocked.
- Add regression coverage for every evidence rule and gate change.
- Do not add generic code review, security scanning, or auto-fix features.
- Keep the core engine independent from Streamlit and GitHub UI layers.
- No billing, paid API, LLM API, private repository, organization, new account, fork test, telemetry, outreach, email, DM, scraping, synthetic external validation, or invented participant evidence.
- Owner/Codex rehearsal is engineering evidence only and never advances Stage 1.
- Do not create a public rehearsal issue, comment, release, or notification-only event.

---

### Task 1: Deterministic rehearsal contract and create-only storage

**Files:**
- Create: `scopeproof_core/alpha/rehearsal.py`
- Create: `scopeproof_core/alpha/rehearsal_storage.py`
- Modify: `scopeproof_core/alpha/__init__.py`
- Create: `tests/alpha/test_rehearsal.py`
- Create: `tests/alpha/test_rehearsal_storage.py`

**Interfaces:**
- Produces: `AlphaRehearsalInput`, `AlphaRehearsalRecord`, `REHEARSAL_EXCLUSION_REASON`, `initialize_alpha_rehearsal`, `JsonAlphaRehearsalStore`, and `default_alpha_rehearsal_directory`.
- The record ID format is `rehearsal-` plus the first 32 lowercase hexadecimal characters of the SHA-256 digest of canonical validated input JSON.

- [ ] **Step 1: Write failing schema tests**

Cover a valid input, every fixed classification field, blank authority, empty/duplicate criteria,
HTTP and private/local requirements URLs, false confirmations, forbidden genuine-case fields, and
attempted Stage 1 or external-validation overrides. Assert both genuine alpha models reject a
rehearsal payload.

- [ ] **Step 2: Verify the schema tests fail for missing rehearsal interfaces**

Run: `uv run pytest tests/alpha/test_rehearsal.py -q`

Expected: collection failure because the rehearsal module does not exist.

- [ ] **Step 3: Implement the minimal validated schemas and deterministic initializer**

Use `ConfigDict(extra="forbid")`, `Literal` fixed fields, normalized unique criteria, normalized
nonblank authority, public-shaped HTTPS validation, canonical `model_dump(mode="json")`, sorted
compact JSON, and SHA-256 ID derivation. Do not add participant role, outcome, review, consent,
publication, or free-form notes.

- [ ] **Step 4: Verify schema tests pass**

Run: `uv run pytest tests/alpha/test_rehearsal.py -q`

Expected: all rehearsal schema tests pass.

- [ ] **Step 5: Write failing create-only storage tests**

Cover validated round trip, deterministic sorted listing, duplicate save, unsafe IDs, symlink root,
symlink file, tampered JSON, and isolation from genuine alpha-case IDs.

- [ ] **Step 6: Implement separate rehearsal storage**

Follow the existing atomic temporary-file replacement pattern, but expose no update method and use
only the rehearsal record schema and rehearsal ID regex.

- [ ] **Step 7: Verify all focused tests and commit**

Run: `uv run pytest tests/alpha/test_rehearsal.py tests/alpha/test_rehearsal_storage.py -q`

Expected: all focused tests pass.

Commit: `feat: add truthful owner rehearsal records`

### Task 2: Rehearsal CLI and genuine-case conversion guards

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `scopeproof_core/alpha/service.py`
- Modify: `tests/cli/test_cli.py`
- Modify: `tests/alpha/test_service.py`

**Interfaces:**
- Consumes: Task 1 rehearsal models, initializer, and store.
- Produces: `scopeproof owner-rehearsal init` and `scopeproof owner-rehearsal show`.

- [ ] **Step 1: Write failing CLI tests**

Assert `init` parses a checked requirements file, persists once, prints every fixed exclusion field,
and `show` reloads the exact record. Assert missing authority or confirmations fail, duplicate input
fails without overwrite, and genuine-only flags such as outcome, reviewed SHA, participant role,
or report consent are rejected.

- [ ] **Step 2: Write failing genuine-service boundary tests**

Pass a validated `AlphaRehearsalRecord` to `record_alpha_outcome` and `public_alpha_summary` with an
intentional type-ignore. Both must raise `ValueError` stating that a genuine alpha-case record is
required.

- [ ] **Step 3: Verify focused tests fail**

Run: `uv run pytest tests/cli/test_cli.py tests/alpha/test_service.py -q`

Expected: new rehearsal command and explicit service guards are missing.

- [ ] **Step 4: Implement the top-level CLI and guards**

Keep `scopeproof alpha init|outcome|show` unchanged. Add `owner-rehearsal` with `init|show`; its init
flags are `--pr`, `--requirements-source`, `--criteria-authority`, `--requirements`,
`--source-owner-confirmed`, `--confirmed-no-confidential-information`, and `--storage-dir` with
default `.scopeproof/alpha-rehearsals`. Add explicit genuine-record checks before outcome or public
summary transitions.

- [ ] **Step 5: Verify focused tests and commit**

Run: `uv run pytest tests/cli/test_cli.py tests/alpha/test_service.py tests/alpha -q`

Expected: all focused tests pass.

Commit: `feat: expose owner rehearsal CLI`

### Task 3: Checked rehearsal input and truthful onboarding contracts

**Files:**
- Create: `evals/rehearsals/owner_rehearsal_requirements.txt`
- Create: `docs/alpha/owner-rehearsal.md`
- Modify: `docs/development-environment.md`
- Modify: `docs/alpha/participant-quickstart.md`
- Modify: `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/alpha/participant-evidence-unblocker.md`
- Modify: `docs/alpha/concierge-host-checklist.md`
- Modify: `docs/commercialization/design-partner-sprint.md`
- Modify: `site/index.html`
- Modify: `site/styles.css`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: Task 2 CLI names and fixed classification fields.
- Produces: one copyable notification-free rehearsal runbook and contract-checked public intake copy.

- [ ] **Step 1: Write failing repository-contract tests**

Require the owner-rehearsal guide to show create, reload, fixture review, export, and comparison
commands; require explicit engineering-only and no-Stage-1 copy; require the participant quickstart
to begin with the inbound case form; require feedback choices to map exactly to the three core
outcomes; require the pricing dropdown copy to acknowledge “Prefer not to answer”; require mobile
Public alpha navigation to remain available; and require active docs to use
`waiting_for_inbound_public_alpha_submission`.

- [ ] **Step 2: Verify the new contract tests fail**

Run: `uv run pytest tests/test_repository_contracts.py -q`

Expected: failures describe the current onboarding and waiting-state drift.

- [ ] **Step 3: Add the checked rehearsal input and guide**

Use the deliberately constructed CSV-export fixture and four atomic requirements. The guide must
use a temporary local output directory, never a public issue, and must state what each command does
and does not prove.

- [ ] **Step 4: Align public onboarding**

Add the case-form preflight to the quickstart and README. Map feedback choices to “Found a useful
previously unknown gap,” “Produced only already-known information,” and “Created material product
friction.” Route incomplete reviews away from the completed-feedback form. Retain a visible compact
Public alpha navigation link on screens under 600px. Remove the site's claim that incomplete review
is a completed honest outcome.

- [ ] **Step 5: Normalize active waiting-state copy**

Use `waiting_for_inbound_public_alpha_submission` in active roadmap, changelog, commercial,
concierge, and unblocker documentation. Do not rewrite historical specs or implementation plans.

- [ ] **Step 6: Verify repository contracts and commit**

Run: `uv run pytest tests/test_repository_contracts.py -q`

Expected: all repository contracts pass.

Commit: `docs: align public alpha rehearsal and intake`

### Task 4: Controlled self-test and engineering-maturity verification

**Files:**
- Modify only if a reproducible in-scope defect is found by the specified checks.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: command evidence for rehearsal intake, review, persistence, export, comparison, package, UI, and repository health.

- [ ] **Step 1: Run one owner/Codex rehearsal in a temporary directory**

Use `scopeproof owner-rehearsal init` with public/example-safe URLs, an explicit owner-authorized
rehearsal authority statement, and `evals/rehearsals/owner_rehearsal_requirements.txt`. Reload it
with `show`. Assert all four exclusion/eligibility fields and the stable exclusion reason.

- [ ] **Step 2: Exercise the controlled review path**

Run `scopeproof review --fixture evals/fixtures/csv_export_pr.json` with the checked rehearsal
requirements and a JSON report. Reload and export the saved review. Confirm criteria are normalized,
candidates cite immutable lines or explain missing evidence, and the gate does not become Ready when
must-have evidence is missing.

- [ ] **Step 3: Run deterministic benchmarks**

Run `uv run scopeproof benchmark` and `uv run scopeproof comparison-benchmark`. Require zero
mismatches, zero must-have False Ready, and execution of Unchanged, Relocated, Modified, Added, and
Removed categories.

- [ ] **Step 4: Run full local verification**

Run locked dependency sync, Ruff, full pytest with configured coverage threshold, repository
contracts, an installed-wheel CLI smoke, Streamlit AppTest coverage, `git diff --check`, Action-pin
inspection, and staged/generated/secret hygiene. Fix only reproducible in-scope defects through
focused tests and a narrow commit.

- [ ] **Step 5: Record verification evidence**

Update the progress ledger with exact commands and results. Do not check generated reports,
coverage databases, virtual environments, or temporary rehearsal records into git.

### Task 5: Review and protected-main delivery

**Files:**
- Review the complete branch diff; modify only to address verified review findings.

- [ ] **Step 1: Generate the whole-branch review package and obtain an independent code review**

Use merge base `811d856c75eae6fb9275a0566dc799b78474bd73`. Fix all Critical and Important findings through
focused tests, then repeat review if needed.

- [ ] **Step 2: Re-run final verification**

Run the complete verification bundle after any review fixes. Inspect the final staged paths and
commit history.

- [ ] **Step 3: Push and open one focused ready-for-review PR**

The PR body must state that the rehearsal is owner/Codex engineering evidence only, creates no
public alpha submission, and does not advance Stage 1. Do not create comments or notification-only
updates.

- [ ] **Step 4: Wait for protected checks and merge**

Require `verify` and `CodeQL`. Diagnose real failures, merge only when both pass, then confirm main
CI and Pages. Delete the merged feature branch when safe and synchronize local `main` without
touching unrelated files or worktrees.

- [ ] **Step 5: Make the release decision**

Do not manufacture a release. Record a justified no-release decision unless repository policy and
the actual user-facing change require one.

### Task 6: One-time genuine-alpha check and completion record

- [ ] **Step 1: Inspect genuine inbound state once**

Check `[Alpha case]` issues and non-owner activity on Issue #3 exactly once after merge. Do not
create or modify any issue.

- [ ] **Step 2: Classify the external state**

If no genuine qualified case exists, record exactly
`waiting_for_inbound_public_alpha_submission`. Do not poll again and do not treat this external gate
as blocking completed engineering work.

- [ ] **Step 3: Deliver the completion report**

Report final protected-main SHA, PR, merge and release decisions, changed behavior, exact test and
check results, rehearsal proof and non-proof, remaining gaps, preserved unrelated files/worktrees,
and the next highest-value evidence-bound stage.

