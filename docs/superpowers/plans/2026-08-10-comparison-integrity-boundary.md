# Comparison Integrity Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every ScopeProof comparison fail closed unless both bundles describe the same pull request, the same ordered confirmed criteria, and a compatible criteria-source snapshot with candidates bound to valid exact heads.

**Architecture:** `scopeproof_core.reviews.comparison` owns one relational validator and `compare_reviews` always calls it. CLI removes duplicate relationship logic; Streamlit catches the same core error and invalidates its stale base. The comparison benchmark uses one compatible positive source snapshot and pressure-tests changed-source rejection.

**Tech Stack:** Python 3.11+, Pydantic 2, pytest, Streamlit AppTest, local JSON storage, deterministic JSON/Markdown exporters, uv, Ruff.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Never execute target-repository code.
- Users must confirm normalized acceptance criteria before analysis.
- Static implementation and test candidates are not runtime verification.
- Every persisted or exported object remains Pydantic-validated.
- Failed comparisons must not mutate saved records or create output files.
- Gate decisions remain deterministic and fail closed; False Ready is more harmful than False Blocked.
- Reviewer and source-owner identity remain asserted, not authenticated.
- Product Stage 1 remains exactly zero across all five targets.
- Do not change R-002, generate R-003, release, tag, publish, contact participants, or begin Workstreams 4–5.

---

### Task 1: Core relational eligibility

**Files:**
- Modify: `scopeproof_core/reviews/comparison.py`
- Modify: `scopeproof_core/reviews/__init__.py`
- Test: `tests/reviews/test_comparison.py`

**Interfaces:**
- Produces: `validate_comparison_relationship(previous: ReviewBundle, current: ReviewBundle) -> tuple[ReviewBundle, ReviewBundle]`
- Produces: `compare_reviews(previous, current)` that always calls the validator before projection.
- Consumes: `validated_review_bundle`, `ReviewInputOrigin`, and complete Pydantic `Criterion` and `CriteriaSourceProvenance` values.

- [ ] **Step 1: Add failing relationship tests**

Add tests that construct independently valid bundles and assert deterministic rejection for:

```python
with pytest.raises(ValueError, match="same repository and pull request"):
    compare_reviews(previous, different_repository)

with pytest.raises(ValueError, match="identical ordered confirmed criteria"):
    compare_reviews(previous, reordered_criteria)

with pytest.raises(ValueError, match="compatible criteria source provenance"):
    compare_reviews(previous, changed_source_revision)

with pytest.raises(ValueError, match="evidence candidates must match the reviewed head"):
    compare_reviews(previous, candidate_from_other_head)
```

Also test that live-public non-40-hex heads are rejected, missing provenance is rejected, and two
provenance objects that differ only in `confirmed_by` and `confirmed_at` remain eligible.

- [ ] **Step 2: Run the tests and observe the intended failures**

Run:

```bash
uv run pytest -q tests/reviews/test_comparison.py -k 'relationship or provenance or ordered or reviewed_head'
```

Expected: the new relationship cases fail because `compare_reviews` currently validates only each
bundle independently.

- [ ] **Step 3: Implement the minimal core validator**

Add private helpers for live head format, candidate/head binding, ordered criteria equality, and
semantic source identity. The public validator must follow this shape:

```python
def validate_comparison_relationship(
    previous: ReviewBundle,
    current: ReviewBundle,
) -> tuple[ReviewBundle, ReviewBundle]:
    previous = validated_review_bundle(previous)
    current = validated_review_bundle(current)
    # deterministic relational checks
    return previous, current
```

The source identity tuple is exactly:

```python
(
    provenance.source_uri,
    provenance.source_revision,
    provenance.source_text_sha256,
    provenance.normalized_criteria_sha256,
)
```

Do not include `confirmed_by` or `confirmed_at`. Require all static evidence `commit_sha` values to
equal the owning bundle's `review.head_sha`. Require live-public heads to match `[0-9a-f]{40}`;
constructed fixtures keep their named identities. Call the validator at the top of
`compare_reviews` and export it from `scopeproof_core.reviews`.

- [ ] **Step 4: Run focused core tests**

Run:

```bash
uv run pytest -q tests/reviews/test_comparison.py
uv run ruff check scopeproof_core/reviews tests/reviews/test_comparison.py
```

Expected: all comparison tests pass with no lint output.

- [ ] **Step 5: Commit the core boundary**

```bash
git add scopeproof_core/reviews/comparison.py scopeproof_core/reviews/__init__.py tests/reviews/test_comparison.py
git commit -m "fix: centralize comparison relationship validation"
```

### Task 2: CLI, storage, and export fail-closed behavior

**Files:**
- Modify: `scopeproof_core/cli.py`
- Test: `tests/cli/test_cli.py`
- Test: `tests/storage/test_json_store.py`
- Test: `tests/reporting/test_comparison_exports.py`

**Interfaces:**
- Consumes: core `compare_reviews`; no adapter-specific relationship helper.
- Preserves: `JsonReviewStore.locked_load_many` snapshot lock and existing renderers.

- [ ] **Step 1: Add failing adapter regressions**

Add CLI tests that save valid records but alter the current active bundle and lifecycle review in a
Pydantic-valid way to create:

- reordered criteria with the same IDs;
- a changed criteria-source URI or revision with identical criteria;
- a candidate bound to a different head;
- a live-public malformed head.

For each failure, capture both saved files as bytes, supply an unused output path, replace the
selected comparison renderer with a function that would fail if called, and assert:

```python
assert error.value.code == 2
assert not output.exists()
assert previous_record.read_bytes() == previous_before
assert current_record.read_bytes() == current_before
```

Add focused storage/export tests proving a failed relationship does not invoke save/mutate or a
comparison renderer.

- [ ] **Step 2: Run the adapter tests and observe the intended failures**

Run:

```bash
uv run pytest -q tests/cli/test_cli.py -k 'compare_command'
uv run pytest -q tests/storage/test_json_store.py -k 'comparison'
uv run pytest -q tests/reporting/test_comparison_exports.py
```

Expected: reordered criteria and provenance cases demonstrate the adapter/core gap before the CLI
duplicate checks are removed and the core rules are used.

- [ ] **Step 3: Remove duplicate CLI eligibility rules**

Keep active-bundle validation and the multi-record lock. Delete the repository/PR tuple comparison
and criterion dictionary comparison from `_compare`. Call `compare_reviews` directly and render
only its validated result. Do not add writes or mutations to the command.

- [ ] **Step 4: Run CLI/storage/export tests**

Run:

```bash
uv run pytest -q tests/cli/test_cli.py -k 'compare_command or comparison_benchmark'
uv run pytest -q tests/storage/test_json_store.py -k 'comparison or locked_load_many'
uv run pytest -q tests/reporting/test_comparison_exports.py
uv run ruff check scopeproof_core/cli.py tests/cli/test_cli.py tests/storage/test_json_store.py tests/reporting/test_comparison_exports.py
```

Expected: all selected tests pass and failed commands remain non-mutating.

- [ ] **Step 5: Commit adapter integrity**

```bash
git add scopeproof_core/cli.py tests/cli/test_cli.py tests/storage/test_json_store.py tests/reporting/test_comparison_exports.py
git commit -m "test: enforce comparison integrity at CLI boundaries"
```

### Task 3: Streamlit stale-base invalidation

**Files:**
- Modify: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: core `compare_reviews` and its deterministic `ValueError` boundary.
- Preserves: a compatible reopened `ReviewBundle` in `comparison_base_bundle` until current analysis exists.

- [ ] **Step 1: Add failing AppTest regressions**

Extend the reopened-review flow with two tests:

1. Reconfirm changed ordered criteria, run analysis, and assert the stale base is cleared.
2. Keep criteria identical but change source URI or revision, run analysis, and assert the stale
   base is cleared.

Both tests assert:

```python
assert app.session_state["comparison_base_bundle"] is None
assert not any(button.key.startswith("download_comparison_") for button in app.download_button)
assert app.session_state["review_state"].bundle.resolutions == []
```

They also require bounded warning copy without raw paths or traceback text. Preserve the existing
compatible same-head and changed-head comparison tests.

- [ ] **Step 2: Run the tests and observe the intended failure**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'comparison and (criteria or provenance or source)'
```

Expected: the current direct `compare_reviews` call raises into the app or retains the stale base.

- [ ] **Step 3: Add fail-closed rendering behavior**

Wrap the comparison call only. On `ValueError`, set `comparison_base_bundle` to `None`, show:

```text
The previous review cannot be compared with this analysis because the pull request,
confirmed criteria, or criteria source changed. No prior decisions were carried forward.
```

Render comparison status, candidate changes, and downloads only in the success branch. Do not
clear the current analysis or restore old decisions.

- [ ] **Step 4: Run focused and broader Streamlit tests**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k 'comparison or rereview'
uv run ruff check apps/web/app.py tests/apps/test_streamlit_app.py
```

Expected: invalid bases fail closed and legitimate rereview comparisons remain available.

- [ ] **Step 5: Commit Streamlit invalidation**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "fix: invalidate incompatible rereview comparisons"
```

### Task 4: Comparison benchmark relationship coverage

**Files:**
- Modify: `evals/comparisons/previous_labels.json`
- Modify: `evals/comparisons/current_labels.json`
- Test: `tests/evals/test_comparison_runner.py`

**Interfaces:**
- Consumes: unchanged `run_comparison_benchmark(root)` and core relationship validator.
- Preserves: two positive benchmark cases, aggregate counts, engineering-only boundary, and zero Stage 1 credit.

- [ ] **Step 1: Add the failing changed-source benchmark test**

Copy the bundled corpus into `tmp_path`, change only the current labels' `source_text`, and assert:

```python
with pytest.raises(ValueError, match="compatible criteria source provenance"):
    run_comparison_benchmark(target)
```

Run:

```bash
uv run pytest -q tests/evals/test_comparison_runner.py -k 'source_provenance'
```

Expected: the test fails before the core relationship boundary is active.

- [ ] **Step 2: Align the positive benchmark source snapshot**

Set `source_text` in `previous_labels.json` and `current_labels.json` to the same exact constructed
requirements text. Keep their criteria and expected evidence-change counts unchanged.

- [ ] **Step 3: Run the comparison benchmark suite and CLI**

Run:

```bash
uv run pytest -q tests/evals/test_comparison_runner.py
uv run scopeproof comparison-benchmark
```

Expected: two executed positive cases, zero mismatches, and deterministic rejection of the negative
changed-source pressure test.

- [ ] **Step 4: Commit benchmark coverage**

```bash
git add evals/comparisons/previous_labels.json evals/comparisons/current_labels.json tests/evals/test_comparison_runner.py
git commit -m "test: bind comparison benchmark source identity"
```

### Task 5: Complete verification and handoff

**Files:**
- Modify only confirmed defects found by verification or review, with a failing regression first.

**Interfaces:**
- Produces: verified branch head, reproducible artifact hash, independent review, and ready PR.

- [ ] **Step 1: Run static, focused, and complete tests**

```bash
uv run ruff check .
uv run pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run pytest -q tests/test_repository_contracts.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Require zero failures, at least 95% combined coverage, zero benchmark mismatches, zero must-have
False Ready, zero false blockers, and zero unexecuted declared categories.

- [ ] **Step 2: Verify reproducible packages and installed runtime**

Build two wheels with one fixed `SOURCE_DATE_EPOCH`, require equal SHA-256, inspect wheel and source
inventories for excluded local state, install the wheel into clean Python environments, run
dependency checks, module/distribution/review version equality, both CLI versions, both installed
benchmarks, and exact loopback health `ok`.

- [ ] **Step 3: Run installed-wheel browser regression and supported Python lanes**

```bash
uv run pytest -q -m browser tests/browser
```

Also execute the repository's Python 3.11 and genuine Python 3.13 package/CLI/health checks. Do not
claim Windows, Linux desktop, non-Chromium, screen-reader, or WCAG evidence.

- [ ] **Step 4: Audit and independently review the final diff**

Run `git diff --check`, inspect every changed file and commit, confirm `.coverage 2` is untouched,
and obtain an independent read-only review. Repair every actionable Critical or Important finding
test-first and rerun affected plus broad checks.

- [ ] **Step 5: Push and open the ready PR**

Push `codex/comparison-integrity-boundary` and open a ready PR titled:

```text
fix: centralize comparison relationship integrity
```

Monitor CI, CodeQL, and every available check to terminal conclusions. Do not merge the PR or begin
Workstream 4.
