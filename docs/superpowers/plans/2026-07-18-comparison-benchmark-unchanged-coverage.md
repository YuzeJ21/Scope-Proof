# Comparison Benchmark Unchanged Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the packaged constructed comparison benchmark from one case to two so its aggregate runtime output covers all five evidence-change classifications, including exactly one `unchanged` candidate.

**Architecture:** Keep `compare_reviews` and all product rules unchanged. Upgrade only the evaluation manifest and runner to validate and execute an ordered nonempty case list, aggregate exact counts, and add one same-snapshot constructed case whose single immutable candidate must classify as `unchanged`.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, Ruff, uv.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Do not modify `scopeproof_core/reviews/comparison.py` or any core classification rule.
- Constructed benchmark output is engineering evidence only and does not advance Stage 1.
- Do not execute fixture repository code.
- Preserve deterministic, Pydantic-validated manifest and result objects.
- Treat unexpected classifications and ambiguous inputs as failures; do not weaken expected counts.
- Do not add paid APIs, LLM calls, generic review, security scanning, automatic fixes, or outreach.
- Preserve `/Users/yjian070/Documents/New project 2/.coverage 2` byte-for-byte.
- Preserve the unrelated `scopeproof_core/reviews/comparison 2.py` file in the existing re-review worktree byte-for-byte.

---

## File map

- `tests/evals/test_comparison_runner.py`: corpus aggregation, per-case results, mismatch attribution, empty-corpus, and duplicate-ID behavior.
- `tests/test_repository_contracts.py`: exact packaged comparison files and positive expected coverage for every `EvidenceChangeKind`.
- `scopeproof_core/evals/comparison_runner.py`: case-list manifest validation, ordered execution, and deterministic count aggregation.
- `evals/comparisons/rereview_evidence_integrity.json`: two-case manifest and exact per-case expectations.
- `evals/comparisons/unchanged_pr.json`: one deliberately constructed immutable PR-shaped snapshot.
- `evals/comparisons/unchanged_labels.json`: one confirmed constructed criterion matching exactly one line.

### Task 1: Specify the two-case corpus in failing tests

**Files:**
- Modify: `tests/evals/test_comparison_runner.py`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `run_bundled_comparison_benchmark()` and `run_comparison_benchmark(root: Path)`.
- Produces: executable expectations for two cases, aggregate counts, and invalid manifest rejection.

- [ ] **Step 1: Update the bundled benchmark expectation**

Replace the one-case assertion with:

```python
assert result.executed_case_count == 2
assert result.expected_counts.model_dump() == {
    "unchanged": 1,
    "relocated": 1,
    "modified": 1,
    "added": 3,
    "removed": 3,
}
assert result.actual_counts == result.expected_counts
assert result.mismatches == []
assert [case.case_id for case in result.case_results] == [
    "rereview-evidence-integrity",
    "unchanged-reference",
]
assert result.case_results[1].actual_counts.model_dump() == {
    "unchanged": 1,
    "relocated": 0,
    "modified": 0,
    "added": 0,
    "removed": 0,
}
```

Keep the existing exact evidence-boundary and `does_not_advance_stage_1` assertions.

- [ ] **Step 2: Update mismatch attribution and add manifest-integrity tests**

Mutate the first case by ID rather than the old top-level count:

```python
manifest["cases"][0]["expected_counts"]["modified"] = 2
```

Require the existing bounded mismatch:

```python
assert result.mismatches == [
    "rereview-evidence-integrity: modified: expected 2, got 1"
]
```

Add two tests that copy the corpus, set `cases` to `[]` or duplicate the first case, and assert
Pydantic `ValidationError` messages contain `at least 1 item` and `case IDs must be unique`,
respectively.

- [ ] **Step 3: Strengthen the packaged-corpus contract**

Update `expected_files` to add `unchanged_pr.json` and `unchanged_labels.json`. Parse the manifest
and sum each case's `expected_counts`; require the aggregate key set to equal:

```python
{kind.value for kind in EvidenceChangeKind}
```

and require every aggregate value to be greater than zero. Import `json` and
`EvidenceChangeKind` explicitly.

- [ ] **Step 4: Run tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_comparison_runner.py \
  tests/test_repository_contracts.py::test_comparison_benchmark_corpus_and_docs_preserve_research_boundary
```

Expected: failures because the current manifest has no `cases`, the runner executes one case, the
new files are absent, and aggregate `unchanged` remains zero. Validation failures must be caused by
missing multi-case behavior rather than test syntax or imports.

### Task 2: Implement validated multi-case execution and data

**Files:**
- Modify: `scopeproof_core/evals/comparison_runner.py`
- Modify: `evals/comparisons/rereview_evidence_integrity.json`
- Create: `evals/comparisons/unchanged_pr.json`
- Create: `evals/comparisons/unchanged_labels.json`

**Interfaces:**
- Produces: `_ComparisonBenchmarkCaseManifest` and a `_ComparisonBenchmarkManifest.cases` list.
- Preserves: `run_comparison_benchmark(root: Path) -> ComparisonBenchmarkResult` and the public result models.

- [ ] **Step 1: Define the validated case-list manifest**

Move case fields into:

```python
class _ComparisonBenchmarkCaseManifest(BaseModel):
    case_id: str = Field(min_length=1)
    previous_fixture: str = Field(min_length=1)
    previous_labels: str = Field(min_length=1)
    current_fixture: str = Field(min_length=1)
    current_labels: str = Field(min_length=1)
    expected_counts: EvidenceChangeCounts
```

Define the top-level model with `cases: list[_ComparisonBenchmarkCaseManifest] = Field(min_length=1)`
and retain both literal evidence-boundary fields. Add an `after` model validator that raises
`ValueError("comparison benchmark case IDs must be unique")` when IDs repeat.

- [ ] **Step 2: Add deterministic count aggregation**

Add:

```python
def _sum_counts(counts: list[EvidenceChangeCounts]) -> EvidenceChangeCounts:
    return EvidenceChangeCounts(
        **{
            kind.value: sum(getattr(item, kind.value) for item in counts)
            for kind in EvidenceChangeKind
        }
    )
```

Iterate `manifest.cases` in order. For each case, build previous/current reviews, compare them,
create `ComparisonBenchmarkCaseResult`, and append case-prefixed mismatch messages. Return aggregate
expected and actual counts, `len(case_results)`, and the unchanged boundary literals.

- [ ] **Step 3: Add the immutable constructed case**

Create `unchanged_pr.json` with repository
`scopeproof/constructed-rereview-benchmark`, a positive PR number, matching base/head identity fields,
complete ingestion, and one changed-file line at `src/unchanged.py` containing the unique identifier
`unchangedproof`.

Create `unchanged_labels.json` with `criteria_confirmed: true`, no resolutions, no final acceptance,
and one `AC-01` criterion whose text is `unchangedproof`, priority is `must_have`, and required
evidence level is `E1`.

Reference the same two new files as both the previous and current inputs of case
`unchanged-reference`. Migrate the original case without changing its file paths or expected counts.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command. Expected: all focused tests pass, including empty-corpus and duplicate-ID
validation.

- [ ] **Step 5: Run the installed-facing benchmark command**

Run:

```bash
uv run scopeproof comparison-benchmark
```

Expected: exit zero, `executed_case_count: 2`, no mismatches, exact aggregate counts of 1 unchanged,
1 relocated, 1 modified, 3 added, and 3 removed, plus the engineering boundary and
`does_not_advance_stage_1: true`.

- [ ] **Step 6: Commit the behavior slice**

```bash
git add scopeproof_core/evals/comparison_runner.py \
  evals/comparisons/rereview_evidence_integrity.json \
  evals/comparisons/unchanged_pr.json \
  evals/comparisons/unchanged_labels.json \
  tests/evals/test_comparison_runner.py \
  tests/test_repository_contracts.py
git commit -m "test: cover Unchanged comparison benchmark"
```

### Task 3: Verify boundaries and repository health

**Files:**
- Verify only: all changed files from Tasks 1-2.

**Interfaces:**
- Consumes: the two-case constructed benchmark.
- Produces: current verification evidence and a clean focused commit.

- [ ] **Step 1: Run formatting and lint checks**

```bash
uv run ruff check scopeproof_core/evals/comparison_runner.py \
  tests/evals/test_comparison_runner.py tests/test_repository_contracts.py
git diff --check main...HEAD
```

Expected: both commands exit zero with no findings.

- [ ] **Step 2: Run repository contracts**

```bash
uv run pytest -q tests/test_repository_contracts.py
```

Expected: all repository contracts pass.

- [ ] **Step 3: Run the complete test suite**

```bash
uv run pytest -q
```

Expected: at least the baseline 834 tests pass, with only the pre-existing skip, plus the new tests.

- [ ] **Step 4: Audit scope and protected files**

Confirm `git diff --name-only main...HEAD` contains only the design, plan, runner, comparison corpus,
and the two intended test files. Confirm the SHA-256 of `.coverage 2` remains
`b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`. Confirm the unrelated re-review
worktree still reports only its pre-existing untracked `scopeproof_core/reviews/comparison 2.py`.

- [ ] **Step 5: Record plan completion**

Mark every checkbox complete after its command succeeds. Commit the completed plan together with
any verification-only checkbox updates:

```bash
git add docs/superpowers/plans/2026-07-18-comparison-benchmark-unchanged-coverage.md
git commit -m "docs: record Unchanged benchmark verification"
```
