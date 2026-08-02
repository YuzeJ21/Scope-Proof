# Exact-head Runtime Evidence Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every effective E3/E4 manual verification to an immutable runtime-evidence ID, repository, pull request, and exact reviewed head while preserving legacy records in a deterministic `Needs Review` state.

**Architecture:** Extend the Pydantic evidence and resolution contracts, validate identity at bundle and lifecycle boundaries, and make unlinked legacy decisions explicitly unresolved in the deterministic gate. Migrate version 1/2 local records to version 3 without inventing resolution links, then project the identity through the workbench and every export. Keep the two UI recovery fixes isolated from core gate semantics.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Streamlit AppTest, Ruff, uv, deterministic JSON/Markdown/CSV/HTML exporters.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Every criterion verdict must cite explicit evidence or state what evidence is missing.
- Implementation evidence must never be presented as test or runtime verification.
- Never execute untrusted repository code in the application server.
- Validate every persisted or exported object with Pydantic schemas.
- Keep gate decisions deterministic and reproducible; False Ready is more harmful than False Blocked.
- Add regression coverage for every evidence rule and gate change.
- Do not add paid APIs, LLM verdicts, billing, accounts, private repositories, generic code review, security scanning, or automatic fixes.
- Preserve the core engine's independence from Streamlit and GitHub UI layers.
- Legacy tuple matching must never be converted into an invented runtime-evidence link.
- No tag, GitHub Release, asset upload, PyPI publication, outreach, or Stage 1 credit is authorized by this plan.

---

### Task 1: Typed runtime identity and fail-closed gate contract

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/resolution_events.py`
- Modify: `scopeproof_core/gates/evaluator.py`
- Modify: `scopeproof_core/gates/guidance.py`
- Modify: `scopeproof_core/gates/validation.py`
- Test: `tests/schemas/test_runtime_evidence.py`
- Test: `tests/schemas/test_manual_verification.py`
- Test: `tests/schemas/test_review_bundle_integrity.py`
- Test: `tests/gates/test_evaluator.py`
- Test: `tests/gates/test_guidance.py`
- Test: `tests/gates/test_validation.py`

**Interfaces:**
- Produces: optional legacy-aware fields `RuntimeEvidence.runtime_evidence_id`, `repository`, `pr_number`, and `head_sha`.
- Produces: optional `HumanResolution.runtime_evidence_id` and `ResolutionEvent.runtime_evidence_id`.
- Produces: gate reason code `runtime_verification_reconfirmation_required`.
- Produces: `current_resolutions()` projection that preserves the link ID.

- [ ] **Step 1: Write failing schema tests for all-or-none runtime provenance**

Add literal payload tests proving that all four fields are accepted together, each partial combination is rejected, blank IDs/heads are rejected, repository and PR validation are reused, and a fully absent identity remains parseable only as legacy-unscoped data.

```python
scoped = {
    "runtime_evidence_id": "runtime-001",
    "repository": "octocat/Hello-World",
    "pr_number": 42,
    "head_sha": "a" * 40,
}
assert RuntimeEvidence(**runtime_evidence_payload(), **scoped).runtime_evidence_id == "runtime-001"
```

Run:

```bash
uv run python -m pytest -q tests/schemas/test_runtime_evidence.py
```

Expected: failures because the identity fields and all-or-none validator do not exist.

- [ ] **Step 2: Add the minimal runtime provenance model**

Add nullable fields with no automatic ID generation so a missing legacy identity stays visibly missing:

```python
runtime_evidence_id: str | None = None
repository: str | None = Field(default=None, pattern=GITHUB_REPOSITORY_PATTERN)
pr_number: int | None = Field(default=None, gt=0)
head_sha: str | None = None
```

Add a model validator that permits exactly zero or four populated provenance fields and field validators that reject whitespace-only IDs and heads without trimming retained values.

- [ ] **Step 3: Write failing resolution-link tests**

Prove that manual resolutions/events preserve an optional link, non-manual decisions reject a link, `current_resolutions()` projects it, and legacy manual records without a link remain parseable.

```python
event = ResolutionEvent(
    criterion_id="AC-01",
    decision=HumanDecision.MANUALLY_VERIFIED,
    comment="Observed",
    reviewer="QA",
    claimed_evidence_level=EvidenceLevel.E3,
    runtime_evidence_id="runtime-001",
)
assert current_resolutions([event], 1)[0].runtime_evidence_id == "runtime-001"
```

Run:

```bash
uv run python -m pytest -q tests/schemas/test_manual_verification.py tests/reviews/test_lifecycle.py -k 'runtime_evidence_id or current_resolutions'
```

Expected: failures because link fields are absent.

- [ ] **Step 4: Implement resolution-link fields and projection**

Add `runtime_evidence_id: str | None = None` to both resolution models. Extend their model validators so a non-manual or final-acceptance record rejects a non-null runtime ID. Preserve legacy manual records with `None`; lifecycle code in Task 2 will reject new unlinked writes. Copy the field in `current_resolutions()`.

- [ ] **Step 5: Write failing bundle-integrity and gate tests**

Cover duplicate runtime IDs, partial identity, foreign repository, wrong PR, wrong head, missing linked ID, and linked criterion/reviewer/level mismatches. Add a legacy manual resolution with no ID and prove its deterministic gate is `Needs Review`, contains the criterion in `unresolved_criteria`, and includes `runtime_verification_reconfirmation_required`. Prove a linked valid manual resolution retains its existing gate meaning.

Run:

```bash
uv run python -m pytest -q tests/schemas/test_review_bundle_integrity.py tests/gates/test_evaluator.py tests/gates/test_validation.py
```

Expected: failures because bundle identity and legacy gate behavior are not enforced.

- [ ] **Step 6: Implement cross-reference validation and legacy-unlinked gate behavior**

In `ReviewBundle.validate_cross_references`, validate unique non-null runtime IDs, full runtime identity equality with `bundle.review`, and every non-null resolution link by ID plus criterion/reviewer/level equality. In trusted gate validation, match linked records by ID and full identity. Permit a missing manual link only as a recoverable unresolved legacy state; never permit it to support `Ready`.

In `evaluate_gate`, treat this case before the normal resolved-decision branch:

```python
if (
    decision is HumanDecision.MANUALLY_VERIFIED
    and resolution.runtime_evidence_id is None
):
    unresolved.add(criterion.criterion_id)
    runtime_reconfirmation_required = True
    continue
```

Append `runtime_verification_reconfirmation_required` deterministically and add guidance telling the reviewer to record new E3/E4 verification at the active head. Update final-acceptance validation so an old positive event may remain audit history only when the resulting deterministic gate is not `Ready` because of an unlinked manual decision.

- [ ] **Step 7: Run the focused contract suite and commit**

```bash
uv run python -m pytest -q \
  tests/schemas/test_runtime_evidence.py \
  tests/schemas/test_manual_verification.py \
  tests/schemas/test_review_bundle_integrity.py \
  tests/gates/test_evaluator.py \
  tests/gates/test_guidance.py \
  tests/gates/test_validation.py \
  tests/reviews/test_lifecycle.py
uv run ruff check scopeproof_core tests/schemas tests/gates tests/reviews
git diff --check
git add scopeproof_core/schemas/models.py scopeproof_core/resolution_events.py \
  scopeproof_core/gates/evaluator.py scopeproof_core/gates/guidance.py \
  scopeproof_core/gates/validation.py tests/schemas/test_runtime_evidence.py \
  tests/schemas/test_manual_verification.py \
  tests/schemas/test_review_bundle_integrity.py tests/gates/test_evaluator.py \
  tests/gates/test_guidance.py tests/gates/test_validation.py \
  tests/reviews/test_lifecycle.py
git commit -m "fix: bind manual verification to runtime evidence"
```

### Task 2: Lifecycle enforcement and version-three persistence migration

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/storage/json_store.py`
- Test: `tests/reviews/test_lifecycle.py`
- Test: `tests/storage/test_json_store.py`
- Test: `tests/schemas/test_review_state_integrity.py`

**Interfaces:**
- Consumes: Task 1 provenance and link fields.
- Produces: atomic exact-review verification and version 1/2 to version 3 migration.

- [ ] **Step 1: Write failing lifecycle identity tests**

Extend the atomic happy path to use `runtime-001`, the active repository, PR, and head and assert the event and evidence retain the same ID. Add table-driven cases for wrong repository, PR, head, missing identity, mismatched link ID, duplicate runtime ID, and attempted replacement while final acceptance remains recorded. Assert the original state is unchanged after every rejection.

Run:

```bash
uv run python -m pytest -q tests/reviews/test_lifecycle.py -k 'runtime or external_verification'
```

Expected: new rejection tests fail.

- [ ] **Step 2: Enforce active-review identity atomically**

Make `append_runtime_evidence()` and `append_external_verification()` require all four runtime fields to equal the validated active review. Require `event.runtime_evidence_id == evidence.runtime_evidence_id`, reject duplicates, and require final acceptance to be explicitly revoked before replacing a manual verification. Keep validation before mutation and append deep copies only after every check passes.

- [ ] **Step 3: Write failing persistence-migration tests**

Change the new-save assertion to record version 3. Create version 2 fixtures by removing the four runtime fields and all manual link IDs from a valid saved payload. Prove:

- runtime-only legacy records receive deterministic stable UUID5 IDs and bundle identity;
- two loads produce byte-equivalent migrated state;
- legacy manual decisions/events remain unlinked;
- affected gates recompute to `Needs Review` with the reconfirmation reason;
- an older positive final-acceptance event cannot yield `Ready`;
- the parsed source payload is not mutated;
- saving the migrated record writes version 3 and preserves old notes/history.

Use a seed shaped exactly as:

```python
seed = (
    f"scopeproof-runtime-evidence:{review_id}:{bundle_key}:"
    f"{item_index}:{canonical_original_payload}"
)
runtime_evidence_id = str(uuid5(NAMESPACE_URL, seed))
```

Run:

```bash
uv run python -m pytest -q tests/storage/test_json_store.py
```

Expected: failures because record version 3 and migration do not exist.

- [ ] **Step 4: Implement deterministic migration and gate recomputation**

Set `RECORD_VERSION = 3` and `_SUPPORTED_RECORD_VERSIONS = (1, 2, 3)`. After the existing version-one lineage migration, deep-copy and migrate each active and historical bundle. Use canonical JSON with sorted keys, compact separators, and `ensure_ascii=False`; use active revision or stable history position as `bundle_key`. Copy identity from that bundle's `review`. Do not add IDs to legacy resolutions/events. Recompute every affected bundle gate before `validated_review_state()`.

- [ ] **Step 5: Run migration and lifecycle suites and commit**

```bash
uv run python -m pytest -q tests/reviews/test_lifecycle.py \
  tests/storage/test_json_store.py tests/schemas/test_review_state_integrity.py
uv run ruff check scopeproof_core/reviews scopeproof_core/storage tests/reviews \
  tests/storage tests/schemas/test_review_state_integrity.py
git diff --check
git add scopeproof_core/reviews/lifecycle.py scopeproof_core/storage/json_store.py \
  tests/reviews/test_lifecycle.py tests/storage/test_json_store.py \
  tests/schemas/test_review_state_integrity.py
git commit -m "fix: migrate runtime verification provenance safely"
```

### Task 3: Workbench and export provenance projection

**Files:**
- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/reporting/exporters.py`
- Test: `tests/apps/test_streamlit_app.py`
- Test: `tests/reporting/test_exporters.py`
- Test: `tests/reporting/test_lifecycle_exports.py`
- Test: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: Task 1 identity fields and Task 2 lifecycle/migration behavior.
- Produces: non-editable current-review provenance in UI and all exports.

- [ ] **Step 1: Write failing workbench identity tests**

Extend the external-verification AppTest to assert the stored runtime record contains the active repository, PR, head, and a nonblank ID; assert its paired event carries the same ID. Add visible-card and resolution-history assertions for runtime ID and bound head, plus a migrated-unlinked warning that keeps final acceptance disabled.

Run:

```bash
uv run python -m pytest -q tests/apps/test_streamlit_app.py -k 'external_verification or runtime_evidence'
```

Expected: failures because the app neither creates nor renders provenance.

- [ ] **Step 2: Create and render immutable workbench provenance**

When saving external verification, generate `runtime_evidence_id=str(uuid4())`, copy `review_state.review.repository`, `pr_number`, and `head_sha`, and pass the same ID to the event. Do not add editable controls. Render ID, repository/PR, and head through `st.text` or `st.code`; render an unlinked legacy decision warning without raw exception details.

- [ ] **Step 3: Write failing export identity tests**

Assert JSON contains all runtime fields and the manual link. Assert Markdown and HTML show runtime ID, repository/PR, bound head, and linked/unlinked state. Add CSV fields with literal expected values:

```text
runtime_evidence_ids
runtime_repositories
runtime_pr_numbers
runtime_head_shas
manual_runtime_evidence_id
```

Preserve array ordering and CSV formula escaping. Add forged-link export rejection and a CLI export regression showing that migrated legacy data exports as `Needs Review`, never `Ready`.

Run:

```bash
uv run python -m pytest -q tests/reporting/test_exporters.py \
  tests/reporting/test_lifecycle_exports.py tests/cli/test_cli.py
```

Expected: failures because identity is absent from formatted exports.

- [ ] **Step 4: Project validated identity through every exporter**

Keep `_validated_exportable()` as the mandatory entry gate. JSON uses Pydantic output. Add explicit Markdown/HTML labels and the five CSV columns. Use `"Legacy unlinked; re-record at the active head"` for missing manual link IDs and never imply that recorded runtime evidence proves correctness.

- [ ] **Step 5: Run focused workbench/export suites and commit**

```bash
uv run python -m pytest -q tests/apps/test_streamlit_app.py \
  tests/reporting/test_exporters.py tests/reporting/test_lifecycle_exports.py \
  tests/cli/test_cli.py
uv run ruff check apps/web/app.py scopeproof_core/reporting tests/apps \
  tests/reporting tests/cli
git diff --check
git add apps/web/app.py scopeproof_core/reporting/exporters.py \
  tests/apps/test_streamlit_app.py tests/reporting/test_exporters.py \
  tests/reporting/test_lifecycle_exports.py tests/cli/test_cli.py
git commit -m "feat: expose runtime verification provenance"
```

### Task 4: Scoped workbench warning and draft recovery

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: existing `_render_ci_observation_summary()`, `_clear_criterion_detail_drafts()`, pending-input guards, and autosave.
- Produces: one visible skipped-CI warning and one bundle-less draft-clear recovery path.

- [ ] **Step 1: Write and observe the skipped-CI warning regression**

Create a complete passing observation with one successful and one skipped run. Assert the visible page contains:

```text
Observed CI includes skipped checks. Skipped checks were not executed; review its deterministic reason and CI details before relying on the gate.
```

Assert the check state remains `PASSING` and skipped names stay in the details expander.

Run the new test alone and confirm it fails because the warning is absent.

- [ ] **Step 2: Add the minimal warning predicate**

Extend only the existing visible-warning condition with
`observation.skipped_check_runs > 0`. Do not alter CI aggregation, reason
codes, gate evaluation, schemas, or export state.

- [ ] **Step 3: Write and observe the bundle-less draft recovery regression**

Start from a saved analyzed demo, populate a criterion-detail draft, revise and
confirm criteria so `bundle is None`, then assert the clear action is enabled.
After clicking it, assert authoritative `ReviewState` equality, cleared session
fields, visible success feedback, and resumed autosave. After reanalysis, assert
downloads become enabled.

Run the new test alone and confirm it fails because the clear action is absent.

- [ ] **Step 4: Reuse the existing clear helper in the bundle-less branch**

Render `clear_criterion_detail_drafts` before local storage only when an active
review exists and a criterion-detail draft is pending. Use this exact copy:

```text
Pending criterion inputs are not part of the review, local save, or exports. Clear them to continue with this revised review.
```

Clear session drafts, set the existing success notice, and rerun. Do not mutate
the review, persist drafts, or create exports before analysis.

- [ ] **Step 5: Run the complete AppTest suite and commit**

```bash
uv run python -m pytest -q tests/apps/test_streamlit_app.py
uv run ruff check apps/web/app.py tests/apps/test_streamlit_app.py
git diff --check
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: clarify skipped CI and draft recovery"
```

### Task 5: Repository truth, release alignment, and full verification

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/releases/v0.2.3-post-merge-release-readiness.md`
- Modify: `docs/releases/v0.2.3-internal-candidate.md`
- Modify: `docs/releases/v0.2.3-platform-package-matrix.md`
- Modify: `docs/releases/v0.2.3-pr-review-map.md`
- Create: `docs/audits/exact-head-runtime-evidence/verification.md`
- Test: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: final implementation tree and its exact SHA.
- Produces: honest unreleased v0.2.3 engineering record and GitHub-ready branch.

- [ ] **Step 1: Add or update repository-contract assertions before documentation edits**

Where machine-enforced wording or version inventory already has a repository
contract, update its literal expectation first and observe the focused test
fail. Do not add tests that merely grep arbitrary human prose.

```bash
uv run python -m pytest -q tests/test_repository_contracts.py
```

- [ ] **Step 2: Align current-state documentation without rewriting history**

Record PR #179 at merge `6e3dec784f7cad9931999d4c5eac1cfe2a9006de`
as the last completed UX merge before this branch. Describe this branch as an
unreleased exact-head runtime-evidence hardening candidate. Preserve all prior
SHA-bound R-002, package, browser, and PR #177 evidence as historical. Keep
v0.2.1 as the public install and keep Stage 1 at zero qualifying external use.
Do not change the intentionally reviewed GitHub Action pin in
`docs/github-action.md`.

- [ ] **Step 3: Run full source and deterministic verification**

```bash
uv sync --extra dev --extra research --locked
uv lock --check
uv run ruff check .
uv run python -m pytest -q
uv run python -m pytest --cov=scopeproof_core --cov=apps \
  --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
git diff --check
```

Record exact counts, coverage, benchmark results, HEAD, and evidence boundaries
in the new verification audit.

- [ ] **Step 4: Build and verify clean installed artifacts**

Build wheel and source distribution into a new temporary directory. Create a
new temporary virtual environment outside the checkout, install the wheel, and
run:

```bash
scopeproof --version
scopeproof-web --version
scopeproof benchmark
scopeproof comparison-benchmark
```

Run installed workbench health and package-inventory checks using the existing
repository scripts or documented commands. Record SHA-256 hashes as pre-release
engineering artifacts only, then remove temporary directories.

- [ ] **Step 5: Commit the alignment and verification record**

```bash
git add README.md ROADMAP.md CHANGELOG.md \
  docs/releases/v0.2.3-status-and-next-stages.md \
  docs/releases/v0.2.3-post-merge-release-readiness.md \
  docs/releases/v0.2.3-internal-candidate.md \
  docs/releases/v0.2.3-platform-package-matrix.md \
  docs/releases/v0.2.3-pr-review-map.md \
  docs/audits/exact-head-runtime-evidence/verification.md \
  tests/test_repository_contracts.py
git commit -m "docs: align v0.2.3 integrity candidate"
```

- [ ] **Step 6: Perform final branch review and publish a draft PR**

Run a broad final review over `origin/main...HEAD`, resolve every Critical or
Important finding through one reviewed fix wave, repeat the full verification
affected by fixes, push `codex/exact-head-runtime-evidence`, and create a draft
PR targeting `main`. The PR body must state that all evidence is engineering
evidence, Stage 1 remains unchanged, and publication is not included.

- [ ] **Step 7: Merge only after exact-head required checks pass**

Confirm the PR head has not moved, required `verify` and `CodeQL` pass, the PR
is mergeable, and no unresolved review finding remains. Then mark Ready and
merge with the repository's merge-commit convention. Fetch the resulting
`origin/main`, verify its exact SHA and required main checks, and update only
the final current-main fields in a separate alignment commit/PR if the merge
SHA cannot be known before merge.

- [ ] **Step 8: Stop at the publication decision**

Confirm no `v0.2.3` tag or GitHub Release was created. Report the exact final
main SHA, checks, package hashes, remaining environment gaps, Stage 1 waiting
condition, and the explicit owner decision still required before publication.
