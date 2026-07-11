# ScopeProof Public Repository MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Streamlit MVP that reviews public GitHub pull requests against user-confirmed criteria using deterministic, auditable evidence rules and no paid LLM API.

**Architecture:** A UI-independent `scopeproof_core` owns validated domain models, GitHub ingestion, deterministic retrieval, gate evaluation, reporting, and evaluation. `apps/web/app.py` is a thin Streamlit workflow over those interfaces. Bundled fixtures make the complete product demonstrable offline.

**Tech Stack:** Python 3.11+, Pydantic 2, httpx, Streamlit, pytest, Streamlit AppTest, Ruff

## Global Constraints

- Do not call OpenAI, hosted LLM, or other paid model APIs.
- Support public repositories only; never execute pull-request code.
- Anonymous GitHub access must work; an optional token stays in session memory and never enters logs or exports.
- Users must confirm criteria before analysis.
- Candidate code is E1, reviewer-confirmed tests are E2, manual runtime evidence is E3, and explicit acceptance is E4.
- Weak, conflicting, failed, or partial analysis cannot produce Ready.
- Gate precedence is Blocked, Needs Review, Conditional, Ready.
- Core modules must not import Streamlit.
- Every exported result includes head SHA and ruleset version and excludes secrets.
- The product copy must say ScopeProof is an evidence assistant and does not replace QA.

---

## File Map

- `pyproject.toml`: package metadata, runtime and development dependencies, pytest and Ruff settings.
- `AGENTS.md`: repository-wide product trust and implementation rules.
- `scopeproof_core/schemas/models.py`: all Pydantic domain models and enums.
- `scopeproof_core/gates/evaluator.py`: deterministic verdict truth table.
- `scopeproof_core/github/client.py`: URL parsing, public GitHub REST ingestion, error taxonomy, and patch line mapping.
- `scopeproof_core/criteria/service.py`: manual criterion parsing and validation warnings.
- `scopeproof_core/retrieval/engine.py`: explainable keyword and file-pattern evidence retrieval.
- `scopeproof_core/verification/service.py`: provisional finding calculation.
- `scopeproof_core/reporting/exporters.py`: Markdown, JSON, and CSV serialization.
- `scopeproof_core/demo.py`: bundled offline review loader and analysis orchestration.
- `scopeproof_core/evals/runner.py`: labeled benchmark evaluation and False Ready metrics.
- `apps/web/app.py`: five-step Streamlit workflow.
- `evals/fixtures/csv_export_pr.json`: deliberately constructed PR fixture.
- `evals/labels/csv_export_expected.json`: fixture criteria and expected findings.
- `tests/`: focused unit, regression, export, AppTest, and smoke tests.
- `README.md`: setup, product walkthrough, architecture, limits, and demo disclosure.

### Task 1: Project Contracts and Domain Schemas

**Files:**
- Create: `pyproject.toml`
- Create: `AGENTS.md`
- Create: `scopeproof_core/__init__.py`
- Create: `scopeproof_core/schemas/__init__.py`
- Create: `scopeproof_core/schemas/models.py`
- Test: `tests/schemas/test_models.py`

**Interfaces:**
- Produces: `Review`, `Criterion`, `EvidenceItem`, `Finding`, `HumanResolution`, `GateDecision`, `PullRequestSnapshot`, and their enums.
- Produces: `RULESET_VERSION: str = "1.0.0"`.

- [ ] **Step 1: Write schema tests first**

```python
def test_evidence_rejects_line_range_without_sha():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="EV-1", criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            file_path="src/export.py", line_start=2, line_end=4,
            commit_sha="", permalink="https://github.com/acme/repo/blob/sha/src/export.py#L2-L4",
            excerpt="def export_csv():", matching_rule="identifier",
            relevance_reason="Matched export_csv", relevance_score=0.9,
        )

def test_review_requires_confirmed_criteria_before_analysis():
    review = Review(repository="acme/repo", pr_number=7, base_sha="base", head_sha="head")
    assert review.criteria_confirmed is False
    assert review.can_analyze is False
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/schemas/test_models.py -q`
Expected: FAIL because `scopeproof_core.schemas.models` does not exist.

- [ ] **Step 3: Implement validated models and repository contracts**

Define string enums for criterion priority/type, evidence type/level, finding status, human decision, gate verdict, check state, and ingestion state. Use Pydantic validators to require non-empty SHAs, valid line ordering, relevance scores in `[0, 1]`, and confirmed criteria before `Review.can_analyze` becomes true. Add the ten trust rules from the design to `AGENTS.md`.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/schemas/test_models.py -q`
Expected: all schema tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml AGENTS.md scopeproof_core tests/schemas
git commit -m "feat: define ScopeProof product contracts"
```

### Task 2: Deterministic Gate Evaluation

**Files:**
- Create: `scopeproof_core/gates/__init__.py`
- Create: `scopeproof_core/gates/evaluator.py`
- Test: `tests/gates/test_evaluator.py`

**Interfaces:**
- Consumes: `Review`, `Criterion`, `Finding`, `HumanResolution`, `CheckState`.
- Produces: `evaluate_gate(review: Review, criteria: list[Criterion], findings: list[Finding], resolutions: list[HumanResolution]) -> GateDecision`.

- [ ] **Step 1: Write gate truth-table tests**

```python
@pytest.mark.parametrize(
    ("confirmed", "check_state", "priority", "status", "expected"),
    [
        (False, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND, GateVerdict.NEEDS_REVIEW),
        (True, CheckState.FAILING, Priority.MUST_HAVE, FindingStatus.EVIDENCE_FOUND, GateVerdict.BLOCKED),
        (True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.MISSING, GateVerdict.BLOCKED),
        (True, CheckState.PASSING, Priority.MUST_HAVE, FindingStatus.NEEDS_REVIEW, GateVerdict.NEEDS_REVIEW),
        (True, CheckState.PASSING, Priority.SHOULD_HAVE, FindingStatus.MISSING, GateVerdict.CONDITIONAL),
    ],
)
def test_gate_truth_table(confirmed, check_state, priority, status, expected):
    review, criterion, finding = gate_case(confirmed, check_state, priority, status)
    assert evaluate_gate(review, [criterion], [finding], []).verdict is expected
```

Add a Ready test requiring final human acceptance and a partial-ingestion test that forces Needs Review.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/gates/test_evaluator.py -q`
Expected: FAIL because `evaluate_gate` is unavailable.

- [ ] **Step 3: Implement explicit precedence**

Evaluate reason codes in this order: failed required checks, change-required or unresolved must-have gaps → Blocked; unconfirmed criteria, incomplete ingestion, unavailable required checks, ambiguity, or missing final acceptance → Needs Review; resolved must-haves with should-have gaps or accepted exceptions → Conditional; otherwise Ready.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/gates/test_evaluator.py -q`
Expected: all truth-table tests pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/gates tests/gates
git commit -m "feat: add deterministic release gates"
```

### Task 3: Public GitHub PR Ingestion

**Files:**
- Create: `scopeproof_core/github/__init__.py`
- Create: `scopeproof_core/github/client.py`
- Test: `tests/github/test_client.py`
- Test: `tests/github/test_live_public_pr.py`

**Interfaces:**
- Produces: `parse_pr_url(url: str) -> tuple[str, str, int]`.
- Produces: `GitHubClient(token: str | None = None, transport: httpx.BaseTransport | None = None)`.
- Produces: `GitHubClient.fetch_pull_request(url: str) -> PullRequestSnapshot`.
- Raises: `InvalidPullRequestUrl`, `PullRequestNotFound`, `PrivateOrInaccessibleRepository`, `GitHubRateLimited`, `GitHubNetworkError`, `DiffLimitExceeded`.

- [ ] **Step 1: Write URL, response, token, and truncation tests**

```python
def test_parse_pr_url_accepts_only_github_pull_urls():
    assert parse_pr_url("https://github.com/acme/widget/pull/42") == ("acme", "widget", 42)
    with pytest.raises(InvalidPullRequestUrl):
        parse_pr_url("https://example.com/acme/widget/pull/42")

def test_client_uses_optional_token_without_placing_it_in_snapshot():
    client = GitHubClient(token="secret", transport=fixture_transport())
    snapshot = client.fetch_pull_request("https://github.com/acme/widget/pull/42")
    assert snapshot.repository == "acme/widget"
    assert "secret" not in snapshot.model_dump_json()
```

Add mocked REST tests for 404, 403 private/inaccessible, 403 rate limit, check-state aggregation, deleted-line classification, and partial ingestion when file or patch limits are reached.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/github/test_client.py -q`
Expected: FAIL because the GitHub client does not exist.

- [ ] **Step 3: Implement ingestion**

Use `httpx.Client` with GitHub REST media headers, a short timeout, and optional bearer authorization. Fetch the PR, files, commits, and commit check-runs/status. Map patch hunk headers into new-file line numbers and mark removed lines so retrieval can exclude them. Enforce constants for maximum files, patch bytes, and total diff bytes, recording skipped content and `IngestionState.PARTIAL`.

- [ ] **Step 4: Verify GREEN and optional live smoke**

Run: `python3 -m pytest tests/github/test_client.py -q`
Expected: mocked ingestion tests pass.

Run: `RUN_LIVE_GITHUB_TESTS=1 python3 -m pytest tests/github/test_live_public_pr.py -q`
Expected: a known public PR returns repository, PR number, non-empty head SHA, and at least one changed file; skip with a clear reason if outbound GitHub access is unavailable.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/github tests/github
git commit -m "feat: ingest public GitHub pull requests"
```

### Task 4: Criteria and Deterministic Evidence Analysis

**Files:**
- Create: `scopeproof_core/criteria/__init__.py`
- Create: `scopeproof_core/criteria/service.py`
- Create: `scopeproof_core/retrieval/__init__.py`
- Create: `scopeproof_core/retrieval/engine.py`
- Create: `scopeproof_core/verification/__init__.py`
- Create: `scopeproof_core/verification/service.py`
- Test: `tests/criteria/test_service.py`
- Test: `tests/retrieval/test_engine.py`
- Test: `tests/verification/test_service.py`

**Interfaces:**
- Produces: `parse_criteria(text: str) -> list[CriterionDraft]` using one non-empty line per criterion.
- Produces: `validate_criteria(criteria: list[Criterion]) -> list[CriterionWarning]`.
- Produces: `retrieve_evidence(snapshot: PullRequestSnapshot, criteria: list[Criterion]) -> list[EvidenceItem]`.
- Produces: `build_findings(criteria: list[Criterion], evidence: list[EvidenceItem], ingestion_state: IngestionState) -> list[Finding]`.

- [ ] **Step 1: Write criteria validation tests**

```python
def test_parse_criteria_preserves_user_language_and_assigns_ids():
    drafts = parse_criteria("Export CSV\nFailed export shows an error")
    assert [(d.criterion_id, d.text) for d in drafts] == [
        ("AC-01", "Export CSV"), ("AC-02", "Failed export shows an error")
    ]

def test_compound_criterion_warns_but_is_not_silently_split():
    warnings = validate_criteria([criterion("Export CSV and record analytics")])
    assert warnings[0].code == "compound_criterion"
```

- [ ] **Step 2: Write retrieval and verification tests**

```python
def test_retrieval_links_identifier_and_excludes_deleted_lines():
    evidence = retrieve_evidence(snapshot_with_added_and_deleted_event(), [criterion("Record research_exported")])
    assert [item.excerpt for item in evidence] == ['track("research_exported")']
    assert all(item.commit_sha == "head123" for item in evidence)

def test_test_filename_alone_does_not_create_test_evidence():
    evidence = retrieve_evidence(snapshot_with_unrelated_test(), [criterion("Failed export shows an error")])
    assert not any(item.evidence_type is EvidenceType.TEST for item in evidence)

def test_partial_ingestion_forces_needs_review_when_evidence_is_absent():
    finding = build_findings([criterion("Export CSV")], [], IngestionState.PARTIAL)[0]
    assert finding.status is FindingStatus.NEEDS_REVIEW
```

- [ ] **Step 3: Verify RED**

Run: `python3 -m pytest tests/criteria tests/retrieval tests/verification -q`
Expected: FAIL because the services do not exist.

- [ ] **Step 4: Implement conservative explainable rules**

Tokenize identifiers and meaningful terms without changing criterion text. Rank exact identifiers above multi-token matches. Classify paths as implementation, test, documentation, migration, or contract. Require a meaningful criterion token in the test name or changed test lines before creating TEST evidence. Store matching-rule IDs and limitations. Build Missing only after complete ingestion; otherwise use Needs Review. Use confidence bands `high`, `medium`, and `low`, not unsupported percentage precision.

- [ ] **Step 5: Verify GREEN**

Run: `python3 -m pytest tests/criteria tests/retrieval tests/verification -q`
Expected: all analysis tests pass.

- [ ] **Step 6: Commit**

```bash
git add scopeproof_core/criteria scopeproof_core/retrieval scopeproof_core/verification tests/criteria tests/retrieval tests/verification
git commit -m "feat: map criteria to deterministic evidence"
```

### Task 5: Reports and Review Serialization

**Files:**
- Create: `scopeproof_core/reporting/__init__.py`
- Create: `scopeproof_core/reporting/exporters.py`
- Test: `tests/reporting/test_exporters.py`

**Interfaces:**
- Produces: `export_json(bundle: ReviewBundle) -> str`.
- Produces: `export_markdown(bundle: ReviewBundle) -> str`.
- Produces: `export_csv(bundle: ReviewBundle) -> str`.

- [ ] **Step 1: Write cross-format consistency and secret-exclusion tests**

```python
def test_exports_agree_on_verdict_head_sha_and_criteria():
    bundle = example_bundle()
    json_text = export_json(bundle)
    markdown = export_markdown(bundle)
    csv_text = export_csv(bundle)
    assert '"verdict": "blocked"' in json_text
    assert "Blocked" in markdown
    assert "blocked" in csv_text
    for output in (json_text, markdown, csv_text):
        assert "head123" in output
        assert "AC-01" in output

def test_exports_never_include_token():
    for output in export_all(example_bundle()):
        assert "ghp_" not in output
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/reporting/test_exporters.py -q`
Expected: FAIL because exporters are unavailable.

- [ ] **Step 3: Implement deterministic exporters**

JSON uses sorted keys and ISO timestamps. Markdown contains a summary, evidence matrix, criterion details, human resolutions, limitations, and disclaimer. CSV emits one row per criterion with flattened evidence permalinks and missing-evidence text. All use the same `ReviewBundle` object.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/reporting/test_exporters.py -q`
Expected: all export tests pass.

- [ ] **Step 5: Commit**

```bash
git add scopeproof_core/reporting tests/reporting
git commit -m "feat: export auditable review reports"
```

### Task 6: Offline Demo and Evaluation Harness

**Files:**
- Create: `evals/fixtures/csv_export_pr.json`
- Create: `evals/labels/csv_export_expected.json`
- Create: `scopeproof_core/demo.py`
- Create: `scopeproof_core/evals/__init__.py`
- Create: `scopeproof_core/evals/runner.py`
- Test: `tests/evals/test_demo_regression.py`

**Interfaces:**
- Produces: `load_demo_snapshot() -> PullRequestSnapshot`.
- Produces: `build_demo_review() -> ReviewBundle`.
- Produces: `run_benchmark(fixtures_dir: Path, labels_dir: Path) -> BenchmarkResult`.

- [ ] **Step 1: Write expected demo and False Ready tests**

```python
def test_demo_is_deliberately_blocked_for_missing_must_haves():
    bundle = build_demo_review()
    statuses = {finding.criterion_id: finding.status for finding in bundle.findings}
    assert statuses["AC-01"] is FindingStatus.EVIDENCE_FOUND
    assert statuses["AC-02"] is FindingStatus.PARTIAL
    assert statuses["AC-03"] is FindingStatus.MISSING
    assert statuses["AC-04"] is FindingStatus.MISSING
    assert bundle.gate.verdict is GateVerdict.BLOCKED

def test_benchmark_reports_zero_must_have_false_ready():
    result = run_bundled_benchmark()
    assert result.must_have_false_ready == 0
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/evals/test_demo_regression.py -q`
Expected: FAIL because fixtures and runner do not exist.

- [ ] **Step 3: Implement the controlled fixture and evaluator**

The fixture changes CSV export code, applies a sector filter, and adds a happy-path test. It omits the date-range filter, failure UI, and `research_exported`. Label metadata states `deliberately_constructed_demo: true`. The runner compares statuses and gates, counts False Ready and False Blocker separately, and returns per-case mismatches.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/evals/test_demo_regression.py -q`
Expected: demo and benchmark tests pass with zero must-have False Ready.

- [ ] **Step 5: Commit**

```bash
git add evals scopeproof_core/demo.py scopeproof_core/evals tests/evals
git commit -m "feat: add offline ScopeProof benchmark demo"
```

### Task 7: Streamlit Review Workflow

**Files:**
- Create: `apps/__init__.py`
- Create: `apps/web/__init__.py`
- Create: `apps/web/app.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes all core services through public interfaces only.
- Produces a five-step Streamlit workflow with session-state keys `snapshot`, `criteria`, `criteria_confirmed`, `bundle`, and `active_step`.

- [ ] **Step 1: Write AppTest flow tests**

```python
def test_demo_flow_reaches_blocked_summary():
    app = AppTest.from_file("apps/web/app.py").run()
    app.button(key="load_demo").click().run()
    assert app.session_state["snapshot"] is not None
    app.button(key="confirm_criteria").click().run()
    app.button(key="run_analysis").click().run()
    assert "Blocked" in [markdown.value for markdown in app.markdown]

def test_analysis_is_disabled_before_criteria_confirmation():
    app = AppTest.from_file("apps/web/app.py").run()
    assert app.button(key="run_analysis").disabled is True
```

Add tests for the disclaimer, Missing/Partial display, resolution controls, and three download buttons.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/apps/test_streamlit_app.py -q`
Expected: FAIL because the Streamlit application does not exist.

- [ ] **Step 3: Implement the thin UI**

Use sidebar progress for Start Review, Confirm Criteria, Evidence Matrix, Criterion Detail, and Summary & Export. Provide public PR URL, optional password-type token, pasted requirements, demo loader, editable criterion rows, explicit confirmation, conservative evidence cards, resolution controls, gate reason codes, and download buttons. Keep provisional findings separate from human decisions. Include the disclaimer and demo disclosure on relevant screens.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/apps/test_streamlit_app.py -q`
Expected: all AppTest workflow tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps tests/apps
git commit -m "feat: add ScopeProof review workbench"
```

### Task 8: Documentation and Full Verification

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml`
- Test: `tests/test_repository_contracts.py`

**Interfaces:**
- Produces documented commands: install, `streamlit run apps/web/app.py`, tests, lint, benchmark, and live GitHub smoke.

- [ ] **Step 1: Write repository-contract tests**

```python
def test_readme_states_product_limits():
    readme = Path("README.md").read_text()
    assert "does not replace QA" in readme
    assert "No paid LLM API" in readme
    assert "deliberately constructed demo" in readme

def test_core_never_imports_streamlit():
    assert not any("import streamlit" in path.read_text() for path in Path("scopeproof_core").rglob("*.py"))
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/test_repository_contracts.py -q`
Expected: FAIL because README and CI contracts are missing.

- [ ] **Step 3: Add operating documentation and CI**

Document the product story, quickstart, anonymous/token behavior, five-step flow, evidence levels, deterministic limitations, privacy boundary, fixture disclosure, architecture, exports, benchmark, and live-smoke command. Configure CI to install the package, run Ruff, run all non-live tests, and execute the bundled benchmark.

- [ ] **Step 4: Run fresh full verification**

Run: `python3 -m ruff check .`
Expected: exit 0 with no lint errors.

Run: `python3 -m pytest -q`
Expected: all tests pass, with only the opt-in live test skipped by default.

Run: `python3 -m scopeproof_core.evals.runner`
Expected: benchmark reports zero must-have False Ready and exits 0.

Run: `streamlit run apps/web/app.py --server.headless true --server.port 8501` and request `http://127.0.0.1:8501/_stcore/health`.
Expected: HTTP 200 and `ok`.

Run: `RUN_LIVE_GITHUB_TESTS=1 python3 -m pytest tests/github/test_live_public_pr.py -q`
Expected: public GitHub ingestion passes or reports a clearly identified environment/network blocker.

- [ ] **Step 5: Commit**

```bash
git add README.md .gitignore .github pyproject.toml tests/test_repository_contracts.py
git commit -m "docs: prepare ScopeProof MVP for public demo"
```
