# ScopeProof Stage 4 Evidence Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make evidence-quality metrics, historical review comparisons, and local Definition-of-Done rule packs explicit, reproducible, and unable to masquerade as user-owned requirements.

**Architecture:** Keep the calculation and comparison logic in `scopeproof_core`, operating solely on validated review bundles and executed benchmark labels. Add rule packs as explicit, caller-selected criterion sources; the Streamlit surface may render these later but cannot silently inject them.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, Ruff, existing local JSON review store.

## Global Constraints

- No paid or hosted LLM API.
- Metrics derive from executed labels or persisted review facts; no fabricated validation.
- User-sourced and implicit criteria remain distinct and implicit criteria require explicit inclusion.
- Static evidence never becomes runtime evidence.
- Preserve deterministic gates, Pydantic validation, and token-free persistence.

---

### Task 1: Executed-label evidence-quality metrics

**Files:**
- Create: `scopeproof_core/evals/metrics.py`
- Modify: `scopeproof_core/evals/runner.py`
- Test: `tests/evals/test_metrics.py`

**Interfaces:**
- Produces `EvidenceQualityMetrics.from_benchmark(result: BenchmarkResult) -> EvidenceQualityMetrics`.
- Consumes `BenchmarkCaseResult` and actual executed benchmark output only.

- [ ] **Step 1: Write the failing test**

```python
def test_metrics_are_derived_from_executed_case_results() -> None:
    metrics = EvidenceQualityMetrics.from_benchmark(run_bundled_benchmark())
    assert metrics.executed_case_count == 12
    assert metrics.must_have_false_ready == 0
    assert metrics.evidence_link_precision == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/evals/test_metrics.py -q`

Expected: import failure because `EvidenceQualityMetrics` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class EvidenceQualityMetrics(BaseModel):
    executed_case_count: int
    executed_criterion_count: int
    evidence_link_precision: float
    incorrect_line_citation_rate: float
    criterion_agreement_rate: float
    must_have_false_ready: int
    false_blocker: int
    human_override_rate: float | None = None
    accepted_exception_rate: float | None = None
    unresolved_ambiguity_rate: float | None = None
```

Derive link metrics from `evidence_link_errors`, agreement from case mismatches, and keep human-review rates `None` without persisted human-resolution data.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/evals/test_metrics.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/evals/metrics.py scopeproof_core/evals/runner.py tests/evals/test_metrics.py
git commit -m "feat: add executed evidence quality metrics"
```

### Task 2: Deterministic review comparison

**Files:**
- Create: `scopeproof_core/reviews/comparison.py`
- Test: `tests/reviews/test_comparison.py`

**Interfaces:**
- Produces `compare_reviews(previous: ReviewBundle, current: ReviewBundle) -> ReviewComparison`.
- Compares head SHA, rule version, evidence IDs, finding status, current human resolutions, and gate verdict.

- [ ] **Step 1: Write the failing test**

```python
def test_comparison_reports_evidence_status_resolution_and_gate_changes() -> None:
    comparison = compare_reviews(previous_bundle, current_bundle)
    assert comparison.previous_head_sha == "oldsha"
    assert comparison.current_head_sha == "newsha"
    assert comparison.added_evidence_ids == ["EV-new"]
    assert comparison.changed_finding_statuses[0].criterion_id == "AC-01"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/reviews/test_comparison.py -q`

Expected: import failure because `compare_reviews` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class ReviewComparison(BaseModel):
    previous_head_sha: str
    current_head_sha: str
    added_evidence_ids: list[str]
    removed_evidence_ids: list[str]
    changed_finding_statuses: list[FindingStatusChange]
    changed_human_resolutions: list[ResolutionChange]
    previous_gate: GateVerdict
    current_gate: GateVerdict
    ruleset_version_changed: bool
```

Use stable evidence IDs and criterion IDs, sort every returned list, and do not compare timestamps as semantic changes.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/reviews/test_comparison.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/reviews/comparison.py tests/reviews/test_comparison.py
git commit -m "feat: compare persisted review revisions"
```

### Task 3: Explicit local DoD rule packs

**Files:**
- Create: `scopeproof_core/rule_packs.py`
- Create: `tests/test_rule_packs.py`
- Modify: `README.md`

**Interfaces:**
- Produces `available_rule_packs() -> list[RulePack]` and `criteria_from_rule_packs(names: list[str]) -> list[Criterion]`.
- Packs: error state, loading state, empty state, analytics, authorization, API documentation, migrations.

- [ ] **Step 1: Write the failing test**

```python
def test_rule_pack_criteria_are_explicitly_implicit_and_stably_identified() -> None:
    criteria = criteria_from_rule_packs(["analytics"])
    assert criteria[0].criterion_id.startswith("IM-AN")
    assert "Implicit local rule" in criteria[0].text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rule_packs.py -q`

Expected: import failure because `criteria_from_rule_packs` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class RulePack(BaseModel):
    name: str
    display_name: str
    criteria: list[Criterion]
```

Return only packs named by the caller, reject unknown names, and prefix every generated text with `Implicit local rule —` so it cannot be mistaken for a confirmed source requirement.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rule_packs.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/rule_packs.py tests/test_rule_packs.py README.md
git commit -m "feat: add explicit local definition of done packs"
```

### Task 4: Stage 4 verification

- [ ] **Step 1: Run complete gates**

Run:

```bash
python -m ruff check .
python -m pytest -q
python -m scopeproof_core.evals.runner
git diff --check
```

Expected: no lint errors, all tests pass, benchmark reports zero known must-have False Ready and zero mismatches.

- [ ] **Step 2: Document metric limitations**

Add README text stating that benchmark metrics are fixture-label metrics and human rates are unavailable until local review histories are selected; no metric establishes runtime correctness or market validation.
