# Microsoft R-001 Evidence-Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to
> implement this plan task-by-task with RED-GREEN-REFACTOR evidence and independent task review.

**Goal:** Correct GitHub CI aggregation, diversify relevant static evidence without increasing
False Ready, make evidence boundaries inspectable across every product surface, and publish a
reproducible R-001 engineering research record.

**Architecture:** Add a validated CI observation beside the existing state, keep static retrieval
separate from manual runtime evidence, select relevant static candidates using a bounded
diversity-first pass, and attach an optional validated public-research context to review bundles.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, argparse, Streamlit, pytest, Ruff, uv/hatchling.

## Global constraints

- Preserve the evidence-assistant boundary and conservative gate rules.
- Never execute Microsoft code, persist credentials, create external comments, or claim Alpha
  progress.
- Keep matching thresholds, eight-candidate limit, immutable links, and deterministic ordering.
- Use only Pydantic-validated persisted/exported objects.
- Preserve `/Users/yjian070/Documents/New project 2/.coverage 2` and unrelated worktrees.

---

### Task 1: Correct and explain CI-state aggregation

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/github/client.py`
- Modify: `scopeproof_core/cli.py`
- Modify: `scopeproof_core/demo.py`
- Modify: `apps/web/app.py`
- Test: `tests/github/test_client.py`
- Test: `tests/schemas/test_models.py`
- Test: `tests/cli/test_cli.py`
- Test: `tests/apps/test_streamlit_app.py`

- [ ] Add failing tests for empty legacy pending, real check-run pending, concrete legacy pending,
  failure precedence, no observations, and neutral/skipped-only observations.
- [ ] Add failing schema tests for CI count consistency, state agreement, nonblank reasons, and
  bounded skipped-check names.
- [ ] Implement `CIObservation` and a single deterministic GitHub aggregation function returning
  both state and explanation; keep `_check_state` compatible for focused callers.
- [ ] Transfer the observation from snapshot to review in CLI, demo, and Streamlit analysis paths.
- [ ] Add focused CLI and Streamlit RED tests for state reason and skipped-check display, then make
  them GREEN without altering gate evaluation.
- [ ] Run the focused GitHub, schema, CLI, and Streamlit tests and commit the verified task.

### Task 2: Diversify static evidence while preserving thresholds

**Files:**
- Modify: `scopeproof_core/retrieval/engine.py`
- Test: `tests/retrieval/test_engine.py`
- Add: `tests/fixtures/r001_structural_pr.json`

- [ ] Add a minimal live-inspired fixture with one high-volume instruction/documentation file, one
  relevant implementation line, one relevant eval definition, and unrelated noise; include no
  unnecessary Microsoft content.
- [ ] Add RED tests proving documentation/implementation and eval-definition candidates are
  surfaced, an eval definition is E2 test intent, one file cannot consume all eight slots, ordering
  is stable, irrelevant types are not forced, and thresholds/links/SHA remain unchanged.
- [ ] Extend test/eval path classification narrowly and implement the deterministic diversity-first
  selection pass.
- [ ] Make the test-intent limitation explicit and verify no CI/runtime evidence is synthesized by
  retrieval.
- [ ] Run retrieval, verification, gate, schema, and deterministic benchmark tests; commit the task.

### Task 3: Make report boundaries inspectable everywhere

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/reporting/exporters.py`
- Modify: `scopeproof_core/presentation.py`
- Modify: `scopeproof_core/cli.py`
- Modify: `apps/web/app.py`
- Test: `tests/schemas/test_review_bundle_integrity.py`
- Test: `tests/reporting/test_exporters.py`
- Test: `tests/reporting/test_html_export.py`
- Test: `tests/cli/test_cli.py`
- Test: `tests/apps/test_streamlit_app.py`

- [ ] Add RED schema tests for an optional `ResearchContext` that can never claim Stage 1 credit.
- [ ] Add RED Markdown, JSON, CSV, and HTML tests for CI state/reason/counts, test intent versus
  execution, skipped/unavailable runtime verification, reviewer state, blocking reason, and the
  candidate-not-correctness boundary.
- [ ] Add `--research-case-id` to `scopeproof review`; persist the context and include it in CLI
  metadata without affecting ordinary reviews.
- [ ] Render the same validated facts in Streamlit for active and reopened reviews, preserving
  accessibility and formula-neutralization contracts.
- [ ] Run all schema, reporting, CLI, Streamlit, lifecycle, and storage tests; commit the task.

### Task 4: Rerun and document R-001

**Files:**
- Add: `docs/research/r001-microsoft-hve-core/requirements.txt`
- Add: `docs/research/r001-microsoft-hve-core/before.md`
- Add: `docs/research/r001-microsoft-hve-core/after.md`
- Add: `docs/research/r001-microsoft-hve-core/summary.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_repository_contracts.py`

- [ ] Verify the live PR head before each review. If changed, preserve the prior identity and run a
  re-review comparison; never replace the old report silently.
- [ ] Preserve the exact six issue criteria and hash the prior report before producing new output.
- [ ] Run anonymous review into a fresh temporary store and report; run authenticated mode only if
  a session token already exists, without printing or persisting it.
- [ ] Normalize allowed identity/timestamp fields and compare deterministic candidates, findings,
  and gate output. Record exact differences and artifact hashes.
- [ ] Confirm complete ingestion, no skipped changed files/warnings, corrected CI aggregation,
  surfaced relevant eval definitions, no claim that skipped eval jobs executed, no decisions/final
  acceptance, a conservative gate, and zero Stage 1 credit.
- [ ] Add repository-contract tests for the research manifest and roadmap boundary. Update only
  completed engineering status; keep Stage 1 waiting and Stages 2-4 gated. Commit the task.

### Task 5: Full verification and package proof

**Files:** Verify all changed files and generated temporary artifacts; do not commit build output.

- [ ] Run focused regression groups and inspect complete output.
- [ ] Run `uv run ruff check .`, repository contracts, and the full suite with configured coverage.
- [ ] Run `uv run scopeproof benchmark` and `uv run scopeproof comparison-benchmark`; require zero
  mismatches and no unexecuted declared cases.
- [ ] Run `uv sync --locked --extra dev` and verify lock consistency.
- [ ] Build sdist/wheel, inspect metadata, install wheel in a clean temporary environment, and run
  installed version, benchmark, comparison benchmark, and public-review smoke.
- [ ] Validate all R-001 exports through Pydantic/format parsers, inspect evidence links, and run
  `git diff --check` plus tracked-worktree cleanliness.
- [ ] Review the complete diff for secrets, third-party content, generated churn, notification
  behavior, and evidence-boundary regressions. Fix and repeat affected checks.

### Task 6: Publish, merge, sync, and final audit

- [ ] Push `codex/r001-evidence-quality` and open one ready ScopeProof PR containing exact R-001
  before/after findings, verification output, limitations, and Stage boundary.
- [ ] Do not request reviewers or add progress comments. Observe required CI once.
- [ ] Diagnose any genuine required-check failure, fix locally with affected verification, push,
  and observe the replacement run once.
- [ ] Merge only after required checks pass and no unresolved review or policy gate remains.
- [ ] Fast-forward local `main` to `origin/main`, confirm equality, remove the merged worktree and
  local branch, and confirm `.coverage 2` remains untouched.
- [ ] Audit the merged roadmap and repository for one further bounded evidence-trust improvement.
  Implement it only if repository evidence identifies a concrete False-Ready or evidence-integrity
  risk; otherwise record that no additional safe bounded item is justified.
- [ ] Record once that Stage 1 waits for a genuine non-owner public Alpha submission and that
  Stages 2-4 remain evidence-gated; do not poll or perform outreach.
