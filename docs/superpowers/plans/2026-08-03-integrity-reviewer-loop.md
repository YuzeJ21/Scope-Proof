# ScopeProof Integrity and Reviewer-Loop Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fail closed when GitHub omits changed-file patch content and make saved-review, evidence-matrix, and changed-head review actions direct and inspectable.

**Architecture:** Repair ingestion once in `GitHubClient`, allowing the existing Pydantic, gate, lifecycle, CLI, persistence, and UI boundaries to inherit `partial` truth. Keep reviewer-loop changes in Streamlit session/presentation code and consume existing core comparison/export services without duplicating their logic.

**Tech Stack:** Python 3.11+, HTTPX, Pydantic v2, Streamlit AppTest, pytest, Ruff, uv.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Never execute untrusted repository code.
- Treat False Ready as more harmful than False Blocked.
- Do not change retrieval thresholds, evidence levels, gate precedence, or persisted review schemas.
- Do not add paid APIs, LLM verdicts, accounts, billing, private repositories, comments, outreach, or Figma dependencies.
- All new production behavior must complete a witnessed RED-GREEN-REFACTOR cycle.
- Stage 1 and public release state remain unchanged.

---

### Task 1: Fail-closed missing and malformed GitHub patches

**Files:**
- Modify: `tests/github/test_client.py`
- Modify: `scopeproof_core/github/client.py:492-531`

**Interfaces:**
- Consumes: GitHub pull-request file objects from `_get_all(.../files)`.
- Produces: `PullRequestSnapshot` with truthful `files`, `warnings`, `skipped_files`, and `ingestion_state`.

- [ ] **Step 1: Add controllable file payloads to the existing transport fixture**

Extend `fixture_transport()` with `files_override: list[dict] | None = None` and return the override from the `/files` endpoint when provided. Keep the complete GitHub-shaped file fields in every fixture.

```python
def fixture_transport(
    *,
    file_count: int = 1,
    files_override: list[dict] | None = None,
    pull_status: int = 200,
    pull_headers: dict[str, str] | None = None,
    check_data: dict | None = None,
    check_status: int = 200,
    status_data: dict | None = None,
    status_status: int = 200,
    requested_urls: list[httpx.URL] | None = None,
) -> httpx.MockTransport:
    default_files = [
        {
            "filename": f"src/export_{index}.py",
            "status": "modified",
            "additions": 2,
            "deletions": 1,
            "changes": 3,
            "patch": (
                "@@ -10,2 +10,3 @@\n-old_export()\n+def export_csv():"
                "\n+    return filtered_rows\n context()"
            ),
        }
        for index in range(file_count)
    ]
    files = files_override if files_override is not None else default_files
```

- [ ] **Step 2: Write failing absent/null/empty-patch tests**

```python
@pytest.mark.parametrize("patch_value", [pytest.param(None, id="null"), pytest.param("", id="empty")])
def test_unavailable_patch_marks_snapshot_partial_and_names_path(patch_value: str | None) -> None:
    file_payload = {
        "filename": "assets/logo.bin",
        "status": "modified",
        "additions": 0,
        "deletions": 0,
        "changes": 0,
    }
    if patch_value is not None:
        file_payload["patch"] = patch_value
    snapshot = GitHubClient(
        transport=fixture_transport(files_override=[file_payload])
    ).fetch_pull_request("https://github.com/acme/widget/pull/42")

    assert snapshot.ingestion_state is IngestionState.PARTIAL
    assert snapshot.files == []
    assert snapshot.skipped_files == ["assets/logo.bin"]
    assert snapshot.warnings == [
        "Patch unavailable for assets/logo.bin; file excluded from analysis."
    ]
```

- [ ] **Step 3: Run the new test and verify RED**

Run: `uv run pytest tests/github/test_client.py::test_unavailable_patch_marks_snapshot_partial_and_names_path -q`

Expected: FAIL because current code returns `ingestion_state=complete`, includes an empty `ChangedFile`, and records no limitation.

- [ ] **Step 4: Add mixed-file and malformed-type failing tests**

Add one test proving an available text patch remains in `files` while an unavailable binary path is skipped, and one test proving `patch=[]` raises `GitHubIngestionError` with bounded `malformed patch data` copy. Assert the unavailable-patch case does not contain `Total diff limit reached`.

- [ ] **Step 5: Implement the minimal adapter fix**

In the file loop, validate `filename`, then branch before encoding:

```python
diff_limit_skipped_count = 0
for item in raw_files:
    filename = item.get("filename")
    if not isinstance(filename, str) or not filename:
        raise GitHubIngestionError("GitHub returned malformed file metadata.")
    raw_patch = item.get("patch")
    if raw_patch is None or raw_patch == "":
        skipped_files.append(filename)
        warnings.append(
            f"Patch unavailable for {filename}; file excluded from analysis."
        )
        ingestion_state = IngestionState.PARTIAL
        continue
    if not isinstance(raw_patch, str):
        raise GitHubIngestionError("GitHub returned malformed patch data.")
    patch = raw_patch
```

Increment `diff_limit_skipped_count` only in the total-byte-limit branch and emit the total-limit warning only when that count is nonzero.

- [ ] **Step 6: Verify GREEN and focused compatibility**

Run:

```bash
uv run pytest tests/github/test_client.py -q
uv run pytest tests/schemas/test_models.py tests/gates tests/reviews/test_lifecycle.py -q
```

Expected: all selected tests pass with no warnings.

- [ ] **Step 7: Commit the ingestion repair**

```bash
git add tests/github/test_client.py scopeproof_core/github/client.py
git commit -m "fix: fail closed on unavailable patches"
```

---

### Task 2: Prove partial ingestion cannot become accepted

**Files:**
- Modify: `tests/reviews/test_lifecycle.py`
- Modify if a projection defect is exposed: the narrow owning core module only

**Interfaces:**
- Consumes: a validated `ReviewState` whose review and bundle carry partial ingestion, warning, and skipped path.
- Produces: unchanged deterministic refusal from `can_record_final_acceptance()` and `append_resolution(...final_acceptance=True)`.

- [ ] **Step 1: Write a lifecycle regression using real state**

Create a partial-ingestion state from the existing lifecycle fixture, record accepted decisions for every active criterion, and assert:

```python
assert can_record_final_acceptance(state) is False
with pytest.raises(ValueError, match="prerequisites"):
    append_resolution(
        state,
        ResolutionEvent(final_acceptance=True, reviewer="QA"),
    )
assert state.bundle is not None
assert state.bundle.gate.verdict is not GateVerdict.READY
assert "partial_ingestion" in state.bundle.gate.reason_codes
```

- [ ] **Step 2: Verify the regression tests existing behavior or exposes a projection defect**

Run the single test. If it passes immediately, retain no change-detector test: instead add the assertion at the first real ingestion-to-review consumer boundary where removing the partial projection would fail it. If it fails, implement only the missing projection.

- [ ] **Step 3: Run lifecycle, CLI, and Streamlit partial-ingestion tests**

Run:

```bash
uv run pytest tests/reviews/test_lifecycle.py tests/cli/test_cli.py -q
uv run pytest tests/apps/test_streamlit_app.py -q -k "partial or ingestion"
```

- [ ] **Step 4: Commit only if this task produces a real regression or production fix**

Stage named files and commit `test: protect partial ingestion acceptance` only when the test catches a realistic production mutation. Otherwise record the existing coverage in the verification report and do not add redundant code.

---

### Task 3: Prepare one-click saved-review current-head checks

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py:175-500,930-1135`

**Interfaces:**
- Consumes: validated `ReviewState` from `JsonReviewStore`.
- Produces: pending source-widget synchronization with canonical PR URL and saved unchanged-candidate paths; dynamic fetch label `Check current head`.

- [ ] **Step 1: Write failing reopened-source preparation tests**

Use the existing saved-review helpers and assert after `reopen_review`:

```python
assert app.text_input(key="pr_url").value == (
    f"https://github.com/{state.review.repository}/pull/{state.review.pr_number}"
)
assert app.text_area(key="candidate_paths").value == "src/unchanged.py"
assert app.button(key="fetch_pr").label == "Check current head"
```

Include two duplicated unchanged-candidate evidence items and assert the path appears once. Include a changed-file-only review and assert the candidate-path input is empty.

- [ ] **Step 2: Verify RED**

Run the two new tests. Expected: reopened review leaves PR URL and candidate paths empty and the button label remains `Fetch public PR`.

- [ ] **Step 3: Implement pre-widget synchronization**

Add `_source_widget_sync_pending` to `_STATE_DEFAULTS`, apply it before widget creation like the criteria-source sync, and set it in `_hydrate_reopened_review()`:

```python
candidate_paths = sorted(
    {
        item.file_path
        for item in state.bundle.evidence
        if item.source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE
    }
) if state.bundle is not None else []
st.session_state["source_widget_sync_pending"] = {
    "pr_url": (
        f"https://github.com/{state.review.repository}/pull/{state.review.pr_number}"
    ),
    "candidate_paths": "\n".join(candidate_paths),
}
```

Populate the existing placeholder with `Check current head` only while the reopened review remains active; keep its key, guards, and handler unchanged.

- [ ] **Step 4: Verify current-head behavior**

Run saved-review, same-head, changed-head, different-PR, and replacement-guard tests. Confirm failed fetches preserve the reopened state and comparison base.

- [ ] **Step 5: Commit**

```bash
git add tests/apps/test_streamlit_app.py apps/web/app.py
git commit -m "feat: streamline saved review refresh"
```

---

### Task 4: Connect matrix findings to the decision workspace

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py:1840-2150`

**Interfaces:**
- Consumes: existing coverage, finding, criterion, and resolution maps.
- Produces: richer deterministic card rows and direct selection of the existing criterion-detail workspace.

- [ ] **Step 1: Write failing card-content and navigation tests**

Assert every card renders `Candidate count`, the finding reason, missing evidence when present,
recommended action, and one stable `inspect_matrix_<criterion_id>` button. Click AC-03 and assert
`selected_criterion == "AC-03"` and the selected requirement is AC-03.

- [ ] **Step 2: Write a failing default-target test**

Construct or reuse an analyzed bundle where the first criterion is resolved and AC-02 is an
unresolved blocker. Clear `selected_criterion` before the run and assert the selector defaults to
AC-02 rather than list position zero.

- [ ] **Step 3: Verify RED**

Run the new tests. Expected: cards omit the added context/buttons and selection defaults to AC-01.

- [ ] **Step 4: Implement the minimal view-model additions**

Add finding-derived fields to each matrix row, render inert text, and add:

```python
if st.button(
    "Inspect this criterion",
    key=f"inspect_matrix_{row['Criterion']}",
):
    st.session_state["selected_criterion"] = row["Criterion"]
    st.rerun()
```

Before the selector is created, initialize its state only when absent or invalid using blocking
and unresolved IDs in confirmed criterion order. Do not reorder the selector's option list.

- [ ] **Step 5: Verify draft and selection safety**

Run matrix-filter, criterion-target-change, pending-draft, resolution-history, narrow-card, and
repository-controlled-text tests. Confirm direct navigation uses the existing draft-clear notice.

- [ ] **Step 6: Commit**

```bash
git add tests/apps/test_streamlit_app.py apps/web/app.py
git commit -m "feat: connect matrix to criterion review"
```

---

### Task 5: Require context for insufficient-evidence acceptance

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py:2090-2160`

**Interfaces:**
- Consumes: selected criterion required level, selected finding observed level, selected human decision, reviewer note.
- Produces: a presentation-level save guard; lifecycle and gate semantics remain unchanged.

- [ ] **Step 1: Write failing guard tests**

Select AC-03 (`required=E1`, `observed=E0`), choose `HumanDecision.ACCEPTED`, and assert:

```python
assert "Accept despite insufficient candidate evidence" in warning_text
assert "Required E1 · observed E0" in caption_text
assert app.button(key="save_resolution").disabled is True
```

Enter a nonblank note and assert the button becomes enabled. Also prove `CHANGE_REQUIRED`,
`REJECTED_FINDING`, and an accepted criterion whose observed rank meets the requirement do not
require the new note.

- [ ] **Step 2: Verify RED**

Expected: current UI enables accepted resolution with an empty note.

- [ ] **Step 3: Implement the minimal rank-aware UI guard**

```python
acceptance_below_required = bool(
    decision is HumanDecision.ACCEPTED
    and selected_finding.evidence_level.rank
    < selected_criterion.required_evidence_level.rank
)
if acceptance_below_required:
    st.warning("Accept despite insufficient candidate evidence only with an explicit reviewer explanation.")
    st.caption(
        "Required "
        f"{selected_criterion.required_evidence_level.value} · observed "
        f"{selected_finding.evidence_level.value}"
    )
resolution_note_ready = bool(resolution_note.strip()) or not acceptance_below_required
```

Include `not resolution_note_ready` in the existing save-button disablement only.

- [ ] **Step 4: Run focused resolution and gate regressions**

Run all ordinary-resolution, external-verification, final-acceptance, and guidance tests.

- [ ] **Step 5: Commit**

```bash
git add tests/apps/test_streamlit_app.py apps/web/app.py
git commit -m "feat: clarify insufficient evidence acceptance"
```

---

### Task 6: Complete comparison inspection, downloads, and disclosure cleanup

**Files:**
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `apps/web/app.py:40-60,1728-1785,2460-2640`

**Interfaces:**
- Consumes: validated `ReviewComparison`, existing comparison exporters, active review origin.
- Produces: inspectable unchanged records, comparison downloads, conditional demo disclosure, and secondary-field cleanup.

- [ ] **Step 1: Write failing comparison UI tests**

Extend the changed-head comparison fixture so it contains at least one unchanged candidate. Assert:

- `Unchanged candidates (1)` exists as a collapsed expander;
- its immutable previous/current references and limitation copy are rendered;
- download keys `download_comparison_markdown` and `download_comparison_json` exist and are enabled;
- their bytes equal `export_comparison_markdown(comparison)` and
  `export_comparison_json(comparison)`.

- [ ] **Step 2: Write failing disclosure and field-placement tests**

Assert constructed-demo copy is present for the demo, absent for a live public-origin bundle, the
root storage path appears only in `Local review storage`, and `Source revision (optional)` is inside
a collapsed provenance expander.

- [ ] **Step 3: Verify RED**

Run the new tests. Expected: unchanged changes are skipped, no comparison downloads exist, demo
copy is unconditional, and secondary fields are always visible.

- [ ] **Step 4: Implement shared comparison rendering and downloads**

Import the existing exporters. Extract a UI-only helper that renders one validated
`EvidenceChange`. Render non-unchanged changes first and unchanged changes inside a collapsed
expander. Add Markdown and JSON download buttons with filenames containing both head prefixes.

- [ ] **Step 5: Implement origin-aware disclosure and secondary-field placement**

Determine the active origin from `review_state.review` or `bundle.review`. Show demo disclosure
only when no review exists or origin is `ReviewInputOrigin.CONSTRUCTED_DEMO`. Move the storage-path
caption into `_render_local_review_storage()` and wrap only the optional revision input in a
collapsed `Optional source revision` expander.

- [ ] **Step 6: Run the complete Streamlit and exporter suites**

Run:

```bash
uv run pytest tests/apps/test_streamlit_app.py tests/reporting -q
uv run ruff check apps/web/app.py tests/apps/test_streamlit_app.py
```

- [ ] **Step 7: Commit**

```bash
git add tests/apps/test_streamlit_app.py apps/web/app.py
git commit -m "feat: complete rereview inspection"
```

---

### Task 7: Verify the integrated slice and align documentation

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Create: `docs/audits/v0.2.3-integrity-reviewer-loop/verification.md`

**Interfaces:**
- Consumes: exact branch HEAD and fresh command outputs.
- Produces: an evidence-bound engineering report with no release or Stage 1 claim.

- [ ] **Step 1: Run static and focused verification**

```bash
uv run ruff check .
uv run pytest tests/github/test_client.py tests/reviews/test_lifecycle.py tests/apps/test_streamlit_app.py tests/reporting -q
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

- [ ] **Step 2: Prove R-002 remains byte-identical**

Run the repository's existing R-002 result/integrity command or focused tests. Do not regenerate
or rewrite canonical research artifacts.

- [ ] **Step 3: Run full tests and coverage**

```bash
uv run pytest -q
uv run coverage erase
uv run coverage run --source=scopeproof_core,apps -m pytest -q
uv run coverage report --fail-under=95
```

- [ ] **Step 4: Build and install from exact HEAD**

Build wheel and sdist into a temporary directory, verify metadata, install the wheel into a clean
temporary Python 3.12 environment, run `scopeproof --version`, both benchmarks, and loopback
`scopeproof-web` health. Do not create a tag or Release.

- [ ] **Step 5: Perform fresh browser checks**

Exercise the constructed demo and one controlled saved-review comparison at desktop and narrow
viewport. Check keyboard order for changed controls and inspect 200 percent zoom if available.
Record unavailable screen-reader and operating-system evidence honestly.

- [ ] **Step 6: Update roadmap and release truth**

Record the exact merge-candidate SHA only after all source commits exist. Mark this slice as
engineering evidence, keep Stage 1 at zero, keep R-003 separately gated, and keep v0.2.3 untagged.

- [ ] **Step 7: Write verification report and run diff hygiene**

Record exact commands, exit codes, counts, SHA targets, limitations, and artifact paths. Run:

```bash
git diff --check origin/main...HEAD
git status --short
git diff --name-only origin/main...HEAD
```

Exclude coverage, local review records, temporary package artifacts, and generated research data.

- [ ] **Step 8: Commit named documentation files**

```bash
git add ROADMAP.md docs/releases/v0.2.3-status-and-next-stages.md \
  docs/audits/v0.2.3-integrity-reviewer-loop/verification.md
git commit -m "docs: record integrity reviewer loop evidence"
```
