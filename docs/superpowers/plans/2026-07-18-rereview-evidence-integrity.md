# Re-review Evidence Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace positional evidence-ID comparison with a conservative deterministic classifier that exposes validated re-review evidence deltas in the core model, exports, local workbench, and a separately labelled constructed benchmark.

**Architecture:** Keep persisted `EvidenceItem` and lifecycle schemas unchanged. Build comparison-only Pydantic projections and one-to-one matching in `scopeproof_core.reviews.comparison`; make exporters and Streamlit consume that model without duplicating matching; run a dedicated paired constructed benchmark separately from the existing 12-case acceptance benchmark.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit AppTest, pytest, Ruff, Hatchling, uv.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Every comparison fact cites the previous candidate, current candidate, or both.
- `unchanged` never means satisfied, correct, passed, or verified.
- Uncertain correspondence must fail closed to `removed` plus `added`.
- Re-analysis keeps current lifecycle behavior: prior decisions remain audit history but do not control the active revision.
- Matching is deterministic, local, and independent of Streamlit.
- Do not execute pull-request code.
- Do not change persisted `EvidenceItem`, `ReviewBundle`, or `ReviewState` schemas.
- Do not add LLMs, paid APIs, billing, private repositories, accounts, integrations, generic review, security scanning, or automatic fixes.
- Constructed comparison fixtures are engineering evidence only and do not advance Stage 1.
- Preserve `/Users/yjian070/Documents/New project 2/.coverage 2` byte-for-byte; expected SHA-256 is `b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`.

---

## File map

- `scopeproof_core/reviews/comparison.py`: comparison-only Pydantic models, validation, normalization, deterministic pairing, and compatibility views.
- `tests/reviews/test_comparison.py`: classification, fail-closed ambiguity, model invariants, ordering, and original-defect regressions.
- `scopeproof_core/reporting/exporters.py`: validated comparison JSON and Markdown renderers.
- `tests/reporting/test_comparison_exports.py`: comparison export structure, validation, escaping, limitation, and deterministic output.
- `apps/web/app.py`: render the core comparison model, counts, two-sided references, reasons, and review-again guidance.
- `tests/apps/test_streamlit_app.py`: re-review comparison AppTest assertions.
- `scopeproof_core/evals/comparison_runner.py`: dedicated paired constructed comparison benchmark.
- `tests/evals/test_comparison_runner.py`: benchmark execution, mismatch, and missing-file behavior.
- `evals/comparisons/previous_pr.json`: deliberately constructed previous PR snapshot.
- `evals/comparisons/previous_labels.json`: previous snapshot criteria labels.
- `evals/comparisons/current_pr.json`: deliberately constructed current PR snapshot.
- `evals/comparisons/current_labels.json`: current snapshot criteria labels.
- `evals/comparisons/rereview_evidence_integrity.json`: manifest and exact expected kind counts.
- `scopeproof_core/cli.py`: `comparison-benchmark` command with a nonzero mismatch exit.
- `tests/cli/test_cli.py`: installed-facing command contract.
- `README.md`: separate acceptance and comparison benchmark instructions and evidence boundaries.
- `docs/development-environment.md`: local comparison benchmark command.
- `tests/test_repository_contracts.py`: packaging and boundary contracts for the new constructed corpus.

---

### Task 1: Comparison models and exact/relocated/modified classification

**Files:**
- Modify: `tests/reviews/test_comparison.py`
- Modify: `scopeproof_core/reviews/comparison.py`

**Interfaces:**
- Produces: `EvidenceChangeKind(StrEnum)` with `UNCHANGED`, `RELOCATED`, `MODIFIED`, `ADDED`, and `REMOVED`.
- Produces: `EvidenceReference.from_item(item: EvidenceItem) -> EvidenceReference`.
- Produces: `EvidenceChange` with validated `previous`/`current` shape.
- Produces: `EvidenceChangeCounts` and `ReviewComparison.evidence_change_counts`.
- Preserves: `compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison`.
- Preserves: derived `ReviewComparison.added_evidence_ids` and `removed_evidence_ids` properties.

- [ ] **Step 1: Replace the single ID-only test helper with an evidence factory and write failing classification tests**

Add helpers that create valid bundles and evidence with explicit ID, criterion, SHA, path, line,
excerpt, type, scope, and matching rule. Add one focused test for each classification and the
original defect:

```python
def test_same_positional_id_with_changed_excerpt_is_modified() -> None:
    previous = bundle_with(evidence("EV-AC-01-01", sha="old", path="src/export.py", line=10, excerpt="return csv"))
    current = bundle_with(evidence("EV-AC-01-01", sha="new", path="src/export.py", line=10, excerpt="return safe_csv"))

    comparison = compare_reviews(previous, current)

    assert [change.kind for change in comparison.evidence_changes] == [EvidenceChangeKind.MODIFIED]
    assert comparison.evidence_changes[0].previous.commit_sha == "old"
    assert comparison.evidence_changes[0].current.commit_sha == "new"
```

Also cover exact unchanged, SHA-only relocation, line-only relocation, path-only relocation,
addition, removal, and derived added/removed ID compatibility views.

- [ ] **Step 2: Run the focused tests and verify the expected RED state**

Run:

```bash
uv run pytest -q tests/reviews/test_comparison.py
```

Expected: failures because `EvidenceChangeKind`, `EvidenceReference`, `EvidenceChange`, and
`evidence_changes` do not exist and ID-only comparison misclassifies reused IDs.

- [ ] **Step 3: Implement the Pydantic comparison models and conservative matching passes**

Implement the models and validators in `scopeproof_core/reviews/comparison.py`. Revalidate both
bundles with `validated_review_bundle()` before projecting evidence. Normalize excerpts only by
line-ending conversion and per-line edge trimming. Partition by criterion and match in this order:

```python
class EvidenceChangeKind(StrEnum):
    UNCHANGED = "unchanged"
    RELOCATED = "relocated"
    MODIFIED = "modified"
    ADDED = "added"
    REMOVED = "removed"


def compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison:
    previous = validated_review_bundle(previous)
    current = validated_review_bundle(current)
    evidence_changes = _compare_evidence(previous.evidence, current.evidence)
    return ReviewComparison(
        previous_head_sha=previous.review.head_sha,
        current_head_sha=current.review.head_sha,
        evidence_changes=evidence_changes,
        changed_finding_statuses=_changed_finding_statuses(previous, current),
        changed_human_resolutions=_changed_resolutions(previous, current),
        previous_gate=previous.gate.verdict,
        current_gate=current.gate.verdict,
        ruleset_version_changed=previous.review.ruleset_version != current.review.ruleset_version,
    )
```

Exact pairing includes SHA, path, line range, normalized excerpt, type, source scope, matching rule,
and permalink. Relocation requires a unique unmatched signature of normalized excerpt, type,
source scope, and matching rule. Modification requires a unique unmatched signature of path, type,
source scope, and matching rule. Use no fuzzy matching.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/reviews/test_comparison.py
```

Expected: all comparison tests pass.

- [ ] **Step 5: Commit the core classifier**

```bash
git add scopeproof_core/reviews/comparison.py tests/reviews/test_comparison.py
git commit -m "feat: classify re-review evidence changes"
```

---

### Task 2: Ambiguity, invariants, and deterministic ordering

**Files:**
- Modify: `tests/reviews/test_comparison.py`
- Modify: `scopeproof_core/reviews/comparison.py`

**Interfaces:**
- Consumes: Task 1 comparison models and `_compare_evidence()`.
- Produces: stable one-to-one pairing and fail-closed duplicate handling.

- [ ] **Step 1: Write failing tests for duplicate signatures, model invariants, and permutation stability**

Add tests proving:

```python
def test_ambiguous_relocation_falls_back_to_removed_and_added() -> None:
    previous = bundle_with(
        evidence("EV-old-1", sha="old", path="src/a.py", line=1, excerpt="export_csv()"),
        evidence("EV-old-2", sha="old", path="src/b.py", line=1, excerpt="export_csv()"),
    )
    current = bundle_with(
        evidence("EV-new-1", sha="new", path="src/c.py", line=4, excerpt="export_csv()"),
        evidence("EV-new-2", sha="new", path="src/d.py", line=4, excerpt="export_csv()"),
    )

    kinds = [item.kind for item in compare_reviews(previous, current).evidence_changes]

    assert kinds.count(EvidenceChangeKind.REMOVED) == 2
    assert kinds.count(EvidenceChangeKind.ADDED) == 2
    assert EvidenceChangeKind.RELOCATED not in kinds
```

Add validation tests for invalid previous/current combinations, criterion mismatch, blank reason,
one-to-one consumption, and identical serialized output after reversing input evidence order.

- [ ] **Step 2: Run the focused tests and verify RED**

Run `uv run pytest -q tests/reviews/test_comparison.py`.

Expected: duplicate candidates are paired by incidental order or model invariants are not enforced.

- [ ] **Step 3: Implement unique-signature grouping, validators, and stable output ordering**

Use signature-to-index-list maps. Pair only signatures with exactly one unmatched index on each
side. Track consumed indices in sets. Sort the final change list by criterion ID, explicit kind
rank (`modified`, `relocated`, `added`, `removed`, `unchanged`), reference path, line range, and
evidence ID.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run `uv run pytest -q tests/reviews/test_comparison.py`.

Expected: all tests pass with no order-dependent output.

- [ ] **Step 5: Commit deterministic fail-closed behavior**

```bash
git add scopeproof_core/reviews/comparison.py tests/reviews/test_comparison.py
git commit -m "test: harden evidence comparison ambiguity"
```

---

### Task 3: Validated JSON and Markdown comparison exports

**Files:**
- Create: `tests/reporting/test_comparison_exports.py`
- Modify: `scopeproof_core/reporting/exporters.py`
- Modify: `scopeproof_core/reporting/__init__.py`

**Interfaces:**
- Consumes: `ReviewComparison` from Tasks 1-2.
- Produces: `export_comparison_json(comparison: ReviewComparison) -> str`.
- Produces: `export_comparison_markdown(comparison: ReviewComparison) -> str`.

- [ ] **Step 1: Write failing export contract tests**

Build a comparison containing all five kinds and assert:

```python
payload = json.loads(export_comparison_json(comparison))
assert payload["previous_head_sha"] == "old"
assert payload["current_head_sha"] == "new"
assert payload["evidence_change_counts"]["modified"] == 1
assert payload["evidence_changes"][0]["previous"]["permalink"].startswith("https://github.com/")
```

Markdown tests require both head SHAs, per-kind counts, previous/current immutable references,
reason text, and the statement that candidate comparison does not prove satisfaction. Inject
Markdown/HTML metacharacters through path, excerpt, and relevance text and assert inert rendering.
Mutate a comparison into an invalid previous/current shape and assert both exporters reject it.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest -q tests/reporting/test_comparison_exports.py
```

Expected: import failures because the two comparison exporters do not exist.

- [ ] **Step 3: Implement revalidation and deterministic renderers**

Add `_validated_comparison()` using `ReviewComparison.model_validate()` over a Python dump. JSON
uses sorted, indented serialization and a trailing newline. Markdown reuses `_escape_markdown_text`
and `_render_markdown_code`; it renders changed kinds before unchanged and never uses correctness
claims.

- [ ] **Step 4: Run focused exporter and existing exporter suites**

Run:

```bash
uv run pytest -q tests/reporting/test_comparison_exports.py tests/reporting/test_exporters.py tests/reporting/test_lifecycle_exports.py
```

Expected: all tests pass and single-review exports remain unchanged.

- [ ] **Step 5: Commit comparison exports**

```bash
git add scopeproof_core/reporting/exporters.py scopeproof_core/reporting/__init__.py tests/reporting/test_comparison_exports.py
git commit -m "feat: export re-review evidence comparisons"
```

---

### Task 4: Re-review workbench clarity

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py`

**Interfaces:**
- Consumes: `ReviewComparison.evidence_change_counts` and `evidence_changes`.
- Produces: UI-only rendering; no matching or classification logic.

- [ ] **Step 1: Extend the existing reanalysis AppTest with failing evidence-delta assertions**

Patch the current snapshot so one candidate excerpt and line change while retaining the same
positional ID after analysis. Assert the rendered content includes:

```python
assert "Modified" in rendered
assert "Previous candidate" in rendered
assert "Current candidate" in rendered
assert previous_head in rendered
assert changed_snapshot.head_sha in rendered
assert "review the current evidence" in rendered.lower()
assert "does not prove criterion satisfaction" in rendered.lower()
```

Add a separate same-content moved-line case and require `Relocated` rather than `Modified`.

- [ ] **Step 2: Run the two focused AppTests and verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k "reanalysis_shows_previous_and_current_head_sha or rereview_evidence"
```

Expected: the current UI only reports added/removed ID counts and lacks two-sided change detail.

- [ ] **Step 3: Render counts and two-sided change details from the core model**

Replace the added/removed-only summary with five labelled counts. Render non-unchanged changes
first. For each record, show criterion/kind, previous reference when present, current reference when
present, and `change.reason`. Add one bounded caption:

```text
Candidate comparison does not prove criterion satisfaction. Review changed or current-head
evidence before recording a new decision.
```

Do not calculate signatures or kinds in `apps/web/app.py`.

- [ ] **Step 4: Run focused and full AppTests**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py
```

Expected: all AppTests pass.

- [ ] **Step 5: Commit the workbench rendering**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "feat: explain re-review evidence changes"
```

---

### Task 5: Dedicated constructed comparison benchmark and CLI

**Files:**
- Create: `scopeproof_core/evals/comparison_runner.py`
- Create: `tests/evals/test_comparison_runner.py`
- Create: `evals/comparisons/previous_pr.json`
- Create: `evals/comparisons/previous_labels.json`
- Create: `evals/comparisons/current_pr.json`
- Create: `evals/comparisons/current_labels.json`
- Create: `evals/comparisons/rereview_evidence_integrity.json`
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Produces: `ComparisonBenchmarkCaseResult(BaseModel)`.
- Produces: `ComparisonBenchmarkResult(BaseModel)`.
- Produces: `run_comparison_benchmark(root: Path) -> ComparisonBenchmarkResult`.
- Produces: `run_bundled_comparison_benchmark() -> ComparisonBenchmarkResult`.
- Produces: `scopeproof comparison-benchmark`.

- [ ] **Step 1: Write failing runner tests before adding the runner or fixtures**

Tests require one executed case, exact expected/actual counts, no mismatches, the deliberately
constructed boundary, missing-manifest failure, and a changed expected count producing a bounded
case mismatch. Add a CLI test:

```python
def test_comparison_benchmark_command_reports_constructed_boundary(capsys) -> None:
    assert main(["comparison-benchmark"]) == 0
    payload = json.loads(capsys.readouterr().out)
assert payload["executed_case_count"] == 1
assert payload["mismatches"] == []
assert payload["evidence_boundary"] == "deliberately constructed engineering evidence"
```

- [ ] **Step 2: Run runner and CLI tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_comparison_runner.py tests/cli/test_cli.py -k comparison_benchmark
```

Expected: module/command import failures.

- [ ] **Step 3: Add the paired fixture-label corpus and expected manifest**

Use public-PR-shaped local snapshots with no real user or repository claim. Include criteria that
produce one relocated candidate, one modified candidate, one removed candidate, one added
candidate, and duplicate ambiguous candidates that must remain removed plus added. Give previous
and current candidates the same positional evidence IDs where possible. The manifest records exact
kind counts and `does_not_advance_stage_1: true`.

- [ ] **Step 4: Implement the validated runner and CLI command**

The runner loads the manifest, builds previous/current bundles with `build_review_from_paths()`,
calls `compare_reviews()`, compares exact counts, and returns Pydantic results. It never executes
fixture code. The command prints sorted JSON and exits nonzero on mismatches or zero executed cases.

- [ ] **Step 5: Run focused tests, both benchmarks, and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_comparison_runner.py tests/cli/test_cli.py -k comparison_benchmark
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Expected: existing benchmark remains 12 cases with zero mismatches and the comparison benchmark
reports one constructed case with exact counts and zero mismatches.

- [ ] **Step 6: Commit the constructed benchmark**

```bash
git add scopeproof_core/evals/comparison_runner.py scopeproof_core/cli.py tests/evals/test_comparison_runner.py tests/cli/test_cli.py evals/comparisons
git commit -m "test: add re-review comparison benchmark"
```

---

### Task 6: Documentation, repository contracts, and complete verification

**Files:**
- Modify: `README.md`
- Modify: `docs/development-environment.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: the completed core, UI, exports, and comparison benchmark.
- Produces: truthful public engineering documentation and packaging contracts.

- [ ] **Step 1: Write failing repository contract tests**

Require:

- `evals/comparisons` exists and contains the five expected JSON files;
- the wheel already force-includes the complete `evals` directory;
- README names `scopeproof comparison-benchmark`;
- README says the paired case is deliberately constructed engineering evidence and does not
  advance Stage 1;
- development-environment instructions run both benchmark commands;
- neither document claims correctness, customer validation, or external use.

- [ ] **Step 2: Run repository contracts and verify RED**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py
```

Expected: documentation/corpus assertions fail.

- [ ] **Step 3: Update README and development instructions with separate benchmark meanings**

Document:

```bash
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

State that the first tests deterministic acceptance coverage and the second tests deterministic
re-review evidence classification. Both are constructed engineering evidence and neither advances
Stage 1.

- [ ] **Step 4: Run focused contracts and all targeted suites**

Run:

```bash
uv run pytest -q tests/test_repository_contracts.py
uv run pytest -q tests/reviews/test_comparison.py tests/reporting/test_comparison_exports.py tests/evals/test_comparison_runner.py tests/cli/test_cli.py tests/apps/test_streamlit_app.py
uv run ruff check .
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Expected: zero failures, zero benchmark mismatches, zero must-have False Ready, and zero false
blockers.

- [ ] **Step 5: Run the complete offline suite with coverage**

Run:

```bash
uv run pytest -q --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95
```

Expected: all offline tests pass, the intentional live GitHub test is skipped, and total coverage
is at least 95 percent.

- [ ] **Step 6: Build and verify a clean installed wheel outside the source tree**

Run:

```bash
rm -rf /tmp/scopeproof-rereview-dist /tmp/scopeproof-rereview-venv
uv build --out-dir /tmp/scopeproof-rereview-dist
python3 -m venv /tmp/scopeproof-rereview-venv
/tmp/scopeproof-rereview-venv/bin/python -m pip install /tmp/scopeproof-rereview-dist/*.whl
cd /tmp
/tmp/scopeproof-rereview-venv/bin/scopeproof benchmark
/tmp/scopeproof-rereview-venv/bin/scopeproof comparison-benchmark
/tmp/scopeproof-rereview-venv/bin/scopeproof --version
```

Expected: install succeeds outside the checkout, both bundled benchmarks report zero mismatches,
and version identity is available. Remove only the two `/tmp/scopeproof-rereview-*` paths after
verification.

- [ ] **Step 7: Run final diff, boundary, status, and preserved-artifact checks**

Run:

```bash
git diff --check origin/main...HEAD
git status --short
shasum -a 256 "/Users/yjian070/Documents/New project 2/.coverage 2"
```

Expected: no diff whitespace errors; only the pre-existing `.coverage 2` is untracked in the
primary checkout; its hash remains
`b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`.

- [ ] **Step 8: Commit documentation and contracts**

```bash
git add README.md docs/development-environment.md tests/test_repository_contracts.py
git commit -m "docs: document comparison research benchmark"
```

---

## Completion boundary

Implementation is ready for publication only after every task commit exists; all focused and full
verification passes; the installed wheel runs both bundled benchmarks outside the checkout; the UI
shows two-sided evidence changes without correctness language; the public documentation preserves
the constructed-versus-participant boundary; and `.coverage 2` retains its baseline hash.
