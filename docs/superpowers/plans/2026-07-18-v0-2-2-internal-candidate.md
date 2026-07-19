# ScopeProof v0.2.2 Internal Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a fully verified, local-only ScopeProof v0.2.2 candidate and an evidence-bound maturity audit without publishing, notifying, or inventing external validation.

**Architecture:** Keep the deterministic core, persisted schemas, and reviewer-first workflow unchanged unless a verified regression requires a narrowly tested fix. Separate the local source version (`0.2.2`) from the latest published install path (`v0.2.1`), and treat build, rehearsal, benchmark, export, and accessibility results as engineering evidence only. Record genuine-alpha and later-stage gates from actual inbound evidence, never from owner rehearsal or constructed fixtures.

**Tech Stack:** Python 3.11+, Hatchling, uv, pytest, pytest-cov, Ruff, Streamlit AppTest, HTMLParser, SHA-256, Git.

## Global Constraints

- Follow `AGENTS.md`: evidence assistant, not correctness oracle; deterministic gates; False Ready is more harmful than False Blocked.
- Do not publish a release, push, create or merge a PR, change GitHub settings, or create a remote tag.
- Do not post or interact on LinkedIn; do not send email, DM, outreach, follow-ups, or contact lists.
- Do not post GitHub comments or create notification-only activity.
- Do not create accounts, organizations, private repositories, forks, billing, subscriptions, or paid API usage.
- Do not execute untrusted repository code in the application server.
- Do not add generic code review, security scanning, automatic fixes, or correctness claims.
- Preserve `/Users/yjian070/Documents/New project 2/.coverage 2` and every unrelated user-owned file.
- Keep the published README install path on v0.2.1 until v0.2.2 is actually published; label v0.2.2 as local and unpublished.
- Owner rehearsal, installed-wheel smoke, benchmarks, and constructed fixtures are engineering evidence only and do not advance Stage 1.
- If an audit finds no defect, record the passing evidence instead of changing code for activity's sake.
- If an audit finds a product defect, use `superpowers:test-driven-development` and add regression coverage before implementation.

---

### Task 1: Define the unpublished v0.2.2 identity contract

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `scopeproof_core/version.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Create: `docs/releases/v0.2.2-internal-candidate.md`
- Include: `docs/superpowers/plans/2026-07-18-v0-2-2-internal-candidate.md`

**Interfaces:**
- Consumes: Hatch dynamic version configuration and the published v0.2.1 README install contract.
- Produces: one local package identity (`0.2.2`) plus an explicit, separately labelled public release identity (`v0.2.1`).

- [ ] **Step 1: Add repository contracts for the identity boundary**

Change `test_hatch_and_reviews_share_one_version_source` to require:

```python
assert '__version__ = "0.2.2"' in version_source
```

Add a contract that reads `README.md`, `CHANGELOG.md`, and
`docs/releases/v0.2.2-internal-candidate.md` and asserts:

```python
assert "v0.2.2 internal candidate" in readme
assert "not published" in readme
assert "Candidate version: 0.2.2 (not published)" in changelog
assert "Internal only; not published" in candidate_notes
assert "releases/download/v0.2.1/" in readme
assert "releases/download/v0.2.2/" not in readme
assert "does not advance Stage 1" in candidate_notes
```

- [ ] **Step 2: Run the focused contract and verify RED**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py
```

Expected: failure because source identity is still `0.2.1` and the unpublished-candidate notes do not exist.

- [ ] **Step 3: Set the local package version**

Change `scopeproof_core/version.py` to:

```python
__version__ = "0.2.2"
```

Keep `pyproject.toml` dynamic so Hatch continues to read this single source.

- [ ] **Step 4: Align README and changelog without inventing a public release**

Add this sentence near the Quickstart release identity in `README.md`:

```markdown
The source checkout is the **v0.2.2 internal candidate** and is not published; the verified public
install path below therefore remains v0.2.1 until a separate publication decision.
```

Add this line immediately below `## Unreleased` in `CHANGELOG.md`:

```markdown
Candidate version: 0.2.2 (not published).
```

Retain all current Unreleased entries and all historical release sections unchanged.

- [ ] **Step 5: Add bounded internal candidate notes**

Create `docs/releases/v0.2.2-internal-candidate.md` with these sections and statements:

```markdown
# ScopeProof v0.2.2 internal candidate

Status: **Internal only; not published**.

This candidate contains every merged change after the v0.2.1 tag, including the owner-rehearsal
engineering workflow, Unchanged comparison benchmark coverage, first-use demo visibility, and
market-positioning hypotheses. The published install path remains v0.2.1.

## Evidence boundary

Builds, clean installs, owner rehearsals, UI checks, exports, and constructed benchmarks are
engineering evidence only. This candidate does not advance Stage 1, establish independent use,
validate product demand, validate pricing, prove correctness, or replace human review.

## Publication boundary

No remote tag, GitHub Release, push, pull request, issue comment, email, direct message, LinkedIn
activity, billing, paid API, private repository, account, organization, or fork is part of this
candidate.

## Candidate contents

- Owner-rehearsal records that remain permanently ineligible for genuine-alpha counting.
- Deterministic comparison benchmark coverage for Unchanged, Relocated, Modified, Added, and Removed.
- First-use demo visibility before public-PR inputs.
- Evidence-bound market-positioning hypotheses awaiting genuine participant testing.
```

- [ ] **Step 6: Verify and commit Task 1**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py
uv run ruff check scopeproof_core/version.py tests/test_repository_contracts.py
git diff --check
```

Expected: repository contracts pass, Ruff passes, and the diff is clean.

Commit only the five product/documentation files plus this plan:

```bash
git add scopeproof_core/version.py tests/test_repository_contracts.py README.md CHANGELOG.md \
  docs/releases/v0.2.2-internal-candidate.md \
  docs/superpowers/plans/2026-07-18-v0-2-2-internal-candidate.md
git commit -m "release: prepare local ScopeProof v0.2.2 candidate"
```

---

### Task 2: Prove packaging and clean installed behavior

**Files:**
- Modify only files implicated by a reproducible packaging defect.
- Create all build, checksum, virtual-environment, and runtime artifacts under unique `/tmp` directories.

**Interfaces:**
- Consumes: Task 1 source identity and Hatch build configuration.
- Produces: a wheel, source distribution, package inventory, checksums, and installed CLI/runtime evidence without repository artifact churn.

- [ ] **Step 1: Build isolated candidate artifacts**

Run:

```bash
dist_dir="$(mktemp -d /tmp/scopeproof-v0.2.2-dist.XXXXXX)"
uv build --out-dir "$dist_dir"
ls -la "$dist_dir"
shasum -a 256 "$dist_dir"/*
```

Expected: exactly one `scopeproof-0.2.2-py3-none-any.whl` and one `scopeproof-0.2.2.tar.gz`.

- [ ] **Step 2: Inspect wheel and source-distribution inventories**

Run Python `zipfile` and `tarfile` inventory commands and verify that the distributions include:

```text
scopeproof_core/
apps/
evals/
scopeproof_core/USE_POLICY.md
```

Reject `.coverage`, `.venv`, `.git`, `.worktrees`, local review storage, caches, secrets, and unrelated files.

- [ ] **Step 3: Install the wheel into a clean environment**

Run:

```bash
venv_dir="$(mktemp -d /tmp/scopeproof-v0.2.2-venv.XXXXXX)"
uv venv "$venv_dir"
uv pip install --python "$venv_dir/bin/python" "$dist_dir/scopeproof-0.2.2-py3-none-any.whl"
cd /tmp
"$venv_dir/bin/scopeproof" --version
"$venv_dir/bin/scopeproof" benchmark
"$venv_dir/bin/scopeproof" comparison-benchmark
"$venv_dir/bin/scopeproof-web" --help
```

Expected: version `0.2.2`; both benchmarks pass with zero mismatches; both console scripts work outside the checkout.

- [ ] **Step 4: Run representative installed review and exports**

Copy only the checked constructed fixture and requirements into a temporary run directory. Run installed-wheel review, save it, and export Markdown, JSON, CSV, and HTML. Validate JSON with the repository Pydantic schema and verify every format contains the PR identity, exact head SHA, criterion identity, candidate provenance, and missing-evidence boundary.

- [ ] **Step 5: Handle defects narrowly**

If any command fails because of product or packaging code, invoke `superpowers:systematic-debugging`, add a failing regression, implement the smallest fix, and re-run Steps 1–4. If all commands pass, do not change packaging code.

---

### Task 3: Rehearse and time the first-use journey

**Files:**
- Modify only files implicated by a reproducible first-use defect.
- Keep rehearsal records and exports in a unique `/tmp` directory.

**Interfaces:**
- Consumes: `docs/alpha/owner-rehearsal.md`, the deliberately constructed fixture, Streamlit AppTest, and the installed candidate.
- Produces: timed engineering evidence for requirements confirmation, analysis, evidence inspection, decisions, exports, and changed-head comparison.

- [ ] **Step 1: Execute the owner-rehearsal runbook exactly**

Use the copyable commands in `docs/alpha/owner-rehearsal.md`, record start/end timestamps for each command, and preserve the fixed `owner_rehearsal` and Stage-1-ineligible classification.

- [ ] **Step 2: Execute the first-use Streamlit flow**

Run the focused AppTest cases that cover demo visibility, criteria confirmation, analysis, candidate inspection, reviewer resolutions, save/reopen, all four exports, and changed-head comparison. Record elapsed runtime separately from estimated human active time; do not call AppTest execution a participant session.

- [ ] **Step 3: Apply the ten-minute boundary honestly**

Report whether the complete constructed rehearsal is operable in under ten minutes. Label the result `owner_rehearsal_engineering_evidence`; do not increment any Stage 1 count.

- [ ] **Step 4: Fix only observed friction**

For any reproducible unclear state, missing next action, broken recovery path, candidate/proof confusion, or inaccessible evidence location, invoke `superpowers:brainstorming` and `superpowers:test-driven-development`, implement the smallest bounded correction, and re-run the complete focused journey. If none exists, make no product change.

---

### Task 4: Audit exports, accessibility, and evidence integrity

**Files:**
- Modify only files implicated by a reproducible defect.

**Interfaces:**
- Consumes: all four exporters, Pydantic models, Streamlit presentation, comparison engine, and constructed benchmark corpus.
- Produces: focused pass/fail evidence for export identity, accessibility, deterministic ordering, ambiguity handling, immutable-head comparison, and False Ready protections.

- [ ] **Step 1: Run export and schema suites**

Run:

```bash
uv run pytest -q tests/reporting tests/schemas tests/test_presentation.py
```

Verify Markdown, JSON, CSV, and HTML identity, exact head SHA, criterion source, candidate path/line/excerpt/provenance, missing-evidence explanations, reviewer-decision separation, stable ordering, escaping, encoding, and empty states.

- [ ] **Step 2: Run accessibility and responsive contracts**

Run the Streamlit and public-site tests covering semantic headings, labels, keyboard-operable controls, status text independent of color, focus/read order, reduced motion, responsive CSS, and readable errors/next actions. Perform a local 1280x720 and 390x844 browser smoke only if an existing local-browser path is available without publishing or installing a paid service.

- [ ] **Step 3: Run evidence-integrity and gate suites**

Run:

```bash
uv run pytest -q tests/evals tests/gates tests/retrieval tests/reviews tests/storage \
  tests/verification tests/criteria tests/alpha
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Confirm zero must-have False Ready, zero benchmark mismatches, incorrect-line-citation rate zero, conservative missing/ambiguous evidence, immutable previous/current references, and all five comparison classifications.

- [ ] **Step 4: Fix only demonstrated defects**

For a failure, invoke `superpowers:systematic-debugging` and `superpowers:test-driven-development`; add one regression per evidence rule or gate change. Do not weaken a gate to improve apparent completion. If all checks pass, record the result and do not expand the corpus speculatively.

---

### Task 5: Complete the internal candidate and maturity audit

**Files:**
- Modify: `docs/releases/v0.2.2-internal-candidate.md` only if verified candidate contents or boundaries need correction.
- Keep generated reports outside the repository unless they are stable, reviewed documentation.

**Interfaces:**
- Consumes: Tasks 1–4 and the one-time read-only GitHub intake audit.
- Produces: final local candidate evidence, a clean branch, and exact Stage 1–4 waiting conditions.

- [ ] **Step 1: Run final verification from the final state**

Run:

```bash
uv run ruff check .
uv run pytest -q --cov=scopeproof_core --cov=apps --cov-report=term-missing \
  --cov-fail-under=95
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
uv build --out-dir "$(mktemp -d /tmp/scopeproof-v0.2.2-final-dist.XXXXXX)"
git diff --check main...HEAD
git status --short --branch
```

Expected: all checks pass, coverage is at least 95%, both benchmarks report zero mismatches, artifacts build, and the worktree contains no generated churn.

- [ ] **Step 2: Review genuine-alpha evidence exactly once**

Use read-only GitHub issue and PR state. Qualify only a non-owner real public PR with public source-owner-confirmed criteria, exact head SHA, confirmed normalized criteria, saved review, reviewer decisions, no confidential material, and a participant-selected outcome. Do not comment, contact, follow up, or poll again when no new case exists.

- [ ] **Step 3: Record the stage table**

Report actual counts for reviews, practitioners, repositories, under-ten-minute participant sessions, False Ready outcomes, reuse intent, and price-discussion intent. A missing value is `0` or `not observed`, never inferred.

- [ ] **Step 4: Run final independent review**

Use `superpowers:requesting-code-review` on the complete `main...HEAD` diff. Fix every Critical or Important issue with focused regression evidence, then re-run Step 1.

- [ ] **Step 5: Finish locally without publication**

Use `superpowers:finishing-a-development-branch`, select the local-only preservation path required by the goal, and do not push, create a PR, merge, tag, or publish. Report the exact local branch and commit.

- [ ] **Step 6: Close at the truth boundary**

Mark internal engineering work complete only after all internal deliverables pass. Keep Stage 1–4 incomplete unless genuine external evidence meets every entry and exit condition. Report the single waiting condition and stop without recurring monitoring or busywork.
