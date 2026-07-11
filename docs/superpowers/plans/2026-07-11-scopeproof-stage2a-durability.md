# ScopeProof Stage 2A Durability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ScopeProof benchmark claims executable and make local reviews auditable across criterion revisions, human decisions, persistence, and bounded retrieval.

**Architecture:** Extend the UI-independent core first. Fixture bundles drive the exact same snapshot, retrieval, verification, and gate path as product reviews. Lifecycle and persistence services own audit state; Streamlit and all exporters consume their validated results.

**Tech Stack:** Python 3.12, Pydantic 2, httpx, Streamlit, pytest, Ruff

## Global Constraints

- No paid or hosted LLM API.
- No execution of pull-request code.
- Never persist a GitHub token.
- Every Ready requires confirmed criteria, complete analysis, required checks, resolved findings, and explicit final acceptance.
- Candidate implementation and test evidence cannot be presented as runtime evidence.
- Benchmark coverage is execution-derived; static category lists are not coverage.
- All changed behavior follows red-green-refactor testing.

---

### Task 1: Executable Benchmark Case Bundles

**Files:**

- Modify: `scopeproof_core/evals/runner.py`
- Modify: `scopeproof_core/demo.py`
- Modify: `scopeproof_core/schemas/models.py`
- Create: `evals/fixtures/*.json`
- Create: `evals/labels/*.json`
- Modify: `tests/evals/test_demo_regression.py`
- Create: `tests/evals/test_runner_cases.py`

**Interfaces:**

- Produces `BenchmarkCaseResult(case_id, category, criterion_count, expected_gate, actual_gate, mismatches, evidence_link_errors)`.
- Produces `run_benchmark(fixtures_dir: Path, labels_dir: Path) -> BenchmarkResult` which loads every matching label file.
- Produces `BenchmarkResult.executed_case_count`, `executed_criterion_count`, `unexecuted_declared_categories`, `case_results`, `must_have_false_ready`, and `false_blocker`.

- [ ] **Step 1: Write failing multi-case runner tests**

```python
def test_runner_executes_each_labelled_case(tmp_path: Path) -> None:
    result = run_bundled_benchmark()
    assert result.executed_case_count == 12
    assert {case.category for case in result.case_results} == REQUIRED_CATEGORIES
    assert result.unexecuted_declared_categories == []

def test_runner_reports_a_bad_permalink_with_case_and_criterion(tmp_path: Path) -> None:
    result = run_benchmark(corrupt_fixture_dir, label_dir)
    assert result.case_results[0].evidence_link_errors == ["AC-01: invalid immutable permalink"]
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/evals/test_runner_cases.py -q`

Expected: FAIL because the runner only executes one demo fixture and has no case-level result model.

- [ ] **Step 3: Add one real fixture and label per required category**

Create fixture-label pairs for `complete_implementation`, `implementation_without_tests`, `happy_path_only`, `missing_error_state`, `active_filter_omitted`, `analytics_omitted`, `permission_without_authorization_test`, `description_claim_not_in_code`, `test_checks_wrong_behavior`, `scope_expansion`, `ambiguous_criterion`, and `unchanged_file_evidence`. Every label contains `case_id`, `category`, `criteria`, `expected_evidence_ids`, `expected_statuses`, `expected_gate`, `acceptable_alternative_evidence`, and `human_review_required`.

- [ ] **Step 4: Implement execution-derived metrics**

Load every label JSON, load the referenced fixture, execute retrieval/verification/gate, compare expected status and gate, validate immutable permalinks against fixture repository/head SHA/file/line, and derive coverage only from `case_results`.

- [ ] **Step 5: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/evals -q && .venv/bin/python -m scopeproof_core.evals.runner`

Expected: Every fixture runs; all declared categories are executed; must-have False Ready is zero.

- [ ] **Step 6: Commit**

```bash
git add scopeproof_core/evals scopeproof_core/demo.py scopeproof_core/schemas evals tests/evals
git commit -m "feat: execute truthful benchmark case bundles"
```

### Task 2: Criteria Revision and Resolution History

**Files:**

- Modify: `scopeproof_core/schemas/models.py`
- Create: `scopeproof_core/reviews/lifecycle.py`
- Create: `scopeproof_core/reviews/__init__.py`
- Create: `tests/reviews/test_lifecycle.py`
- Modify: `scopeproof_core/gates/evaluator.py`
- Modify: `tests/gates/test_evaluator.py`

**Interfaces:**

- Produces `CriteriaRevision(revision_id, criteria, confirmed_at, source_text)`.
- Produces `ResolutionEvent(event_id, criterion_id | None, decision, comment, timestamp)`.
- Produces `revise_criteria(review_state, criteria, source_text) -> ReviewState`.
- Produces `append_resolution(review_state, event) -> ReviewState`.
- Produces `current_resolutions(events) -> list[HumanResolution]`.

- [ ] **Step 1: Write lifecycle tests**

```python
def test_editing_confirmed_criteria_creates_new_revision_and_invalidates_analysis() -> None:
    revised = revise_criteria(confirmed_state(), [criterion("AC-01", "Updated behavior")], "Updated")
    assert revised.criteria_revision.number == 2
    assert revised.criteria_confirmed is False
    assert revised.bundle is None

def test_resolution_events_preserve_history_and_last_decision_controls_gate() -> None:
    state = append_resolution(append_resolution(state, rejected_event), accepted_event)
    assert len(state.resolution_events) == 2
    assert current_resolutions(state.resolution_events)[0].decision is HumanDecision.ACCEPTED
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/reviews tests/gates -q`

Expected: FAIL because revisions and events do not exist.

- [ ] **Step 3: Implement append-only lifecycle models and helpers**

Keep provisional analysis tied to a criteria revision ID. A criterion edit creates a new unconfirmed revision and clears active analysis. Final acceptance is a review-level event with no criterion ID. Gate evaluation consumes only the current resolution per criterion plus the latest final-acceptance event.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/reviews tests/gates -q`

Expected: revision invalidation, history, final acceptance, exceptions, and gate recalculation pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/reviews scopeproof_core/schemas scopeproof_core/gates tests/reviews tests/gates
git commit -m "feat: preserve criteria revisions and resolution history"
```

### Task 3: Versioned Local Review Store

**Files:**

- Create: `scopeproof_core/storage/json_store.py`
- Create: `scopeproof_core/storage/__init__.py`
- Create: `tests/storage/test_json_store.py`
- Modify: `scopeproof_core/schemas/models.py`

**Interfaces:**

- Produces `JsonReviewStore(directory: Path)`.
- Produces `save(state: ReviewState) -> Path`.
- Produces `load(review_id: str) -> ReviewState`.
- Produces `detect_head_change(state: ReviewState, snapshot: PullRequestSnapshot) -> HeadChange`.
- Raises `UnsupportedRecordVersion` for unknown record formats.

- [ ] **Step 1: Write persistence tests**

```python
def test_saved_review_round_trips_without_token(tmp_path: Path) -> None:
    path = JsonReviewStore(tmp_path).save(review_state_with_history())
    loaded = JsonReviewStore(tmp_path).load("review-1")
    assert loaded.model_dump(mode="json") == review_state_with_history().model_dump(mode="json")
    assert "ghp_" not in path.read_text()

def test_head_change_is_reported_without_mutating_old_evidence(tmp_path: Path) -> None:
    change = detect_head_change(saved_state, snapshot_with_head("new-head"))
    assert change.changed is True
    assert saved_state.bundle.review.head_sha == "old-head"
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/storage/test_json_store.py -q`

Expected: FAIL because the store does not exist.

- [ ] **Step 3: Implement versioned JSON records**

Write atomically through a sibling temporary file followed by `Path.replace`. Store `record_version`, validated lifecycle state, and a timestamp. Reject unknown versions. Restrict filenames to a generated review ID. Do not accept arbitrary paths from UI input.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/storage/test_json_store.py -q`

Expected: round trip, secret exclusion, bad-version rejection, and SHA-change detection pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/storage scopeproof_core/schemas tests/storage
git commit -m "feat: persist local ScopeProof review records"
```

### Task 4: Bounded GitHub and Unchanged-File Retrieval

**Files:**

- Modify: `scopeproof_core/github/client.py`
- Modify: `scopeproof_core/retrieval/engine.py`
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `tests/github/test_client.py`
- Modify: `tests/retrieval/test_engine.py`

**Interfaces:**

- Produces `PullRequestSnapshot.ingestion_reasons: list[str]`.
- Produces `GitHubClient.fetch_candidate_files(repository, head_sha, paths) -> list[RetrievedFile]`.
- Produces `retrieve_evidence(..., unchanged_files: list[RetrievedFile] = []) -> list[EvidenceItem]`.

- [ ] **Step 1: Write bounded-retrieval tests**

```python
def test_second_files_page_is_loaded_until_limit() -> None:
    snapshot = GitHubClient(transport=paged_transport()).fetch_pull_request(PR_URL)
    assert [file.path for file in snapshot.files] == ["src/a.py", "src/b.py"]

def test_unchanged_candidate_requires_reason_and_is_marked_separately() -> None:
    evidence = retrieve_evidence(snapshot, criteria, unchanged_files=[candidate_file])
    assert evidence[0].source_scope == "unchanged_candidate"
    assert "criterion identifier" in evidence[0].relevance_reason
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/github tests/retrieval -q`

Expected: FAIL because pagination and unchanged candidate retrieval are unavailable.

- [ ] **Step 3: Implement safe retrieval**

Follow GitHub pagination links until configured limits. Mark every omitted page/file/patch with a reason. Retrieve only caller-selected paths, cap count and bytes, anchor content to head SHA, classify binary/missing content, and never treat failed candidate retrieval as complete analysis.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/github tests/retrieval -q`

Expected: pagination, limits, binary paths, immutable links, deleted lines, and unchanged-source labels pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/github scopeproof_core/retrieval scopeproof_core/schemas tests/github tests/retrieval
git commit -m "feat: bound GitHub ingestion and unchanged evidence"
```

### Task 5: Durable Reports and Streamlit Workflow

**Files:**

- Modify: `scopeproof_core/reporting/exporters.py`
- Modify: `apps/web/app.py`
- Modify: `tests/reporting/test_exporters.py`
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `README.md`

**Interfaces:**

- Consumes `ReviewState` and derives the current `ReviewBundle`.
- Produces save/reopen controls, status filters, history rendering, and final-acceptance control.
- Produces exports containing criteria revision and resolution history.

- [ ] **Step 1: Write export and AppTest failures**

```python
def test_reopened_export_contains_current_revision_and_full_history() -> None:
    markdown = export_markdown(reopened_state)
    assert "Criteria revision: 2" in markdown
    assert markdown.count("Human resolution") == 2

def test_app_can_save_reopen_and_show_final_acceptance() -> None:
    app = complete_demo(AppTest.from_file(APP_PATH).run())
    app.button(key="save_review").click().run()
    app.button(key="reopen_review").click().run()
    assert "Resolution history" in visible_text(app)
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/reporting tests/apps -q`

Expected: FAIL because reports and UI do not consume lifecycle state.

- [ ] **Step 3: Implement core-backed UX**

Add filters for must-have, should-have, Missing, Partial, and Needs Review. Display ingestion reasons and evidence limitations. Save/reopen local records through JsonReviewStore. Use revision helpers for criterion changes. Append resolution events rather than overwriting history. Add final acceptance and rerun the deterministic gate after every lifecycle change.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/reporting tests/apps -q`

Expected: UI and exports show the same current revision, current decision, history, and gate.

- [ ] **Step 5: Run Stage 2A verification**

Run:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m pytest -q
.venv/bin/python -m scopeproof_core.evals.runner
RUN_LIVE_GITHUB_TESTS=1 .venv/bin/python -m pytest tests/github/test_live_public_pr.py -q
git diff --check
```

Start Streamlit on a free local port and request `/_stcore/health`; expect `ok`.

- [ ] **Step 6: Commit**

```bash
git add apps scopeproof_core/reporting tests/reporting tests/apps README.md
git commit -m "feat: make ScopeProof reviews durable in the workbench"
```
