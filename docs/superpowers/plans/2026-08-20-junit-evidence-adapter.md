# Bounded JUnit Evidence Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import bounded local JUnit XML into a validated, exact-head,
non-gating evidence record that is visible in CLI, Streamlit, exports, and
comparison without executing target-repository code.

**Architecture:** A new core importer accepts bytes and produces sanitized
Pydantic data. A lifecycle transition appends a versioned `JUnitEvidenceImport`
to the active `ReviewBundle` while proving all gate and human-decision inputs
are unchanged. CLI and Streamlit call the same importer and lifecycle functions;
storage and exports continue to revalidate complete review state.

**Tech Stack:** Python 3.11+, Pydantic 2, standard-library
`xml.etree.ElementTree`, argparse, Streamlit, pytest, Playwright, Ruff, uv.

**Spec:** `docs/superpowers/specs/2026-08-20-junit-evidence-adapter-design.md`

## Global Constraints

- Accept at most 1,048,576 artifact bytes, 100 suites, 5,000 cases, and 20,000 XML elements.
- Accept UTF-8 only and reject DTD, entity, XInclude, remote, path, or executable processing.
- Persist no raw XML, failure bodies, stdout, stderr, properties, commands, paths, URLs, or attachments from the artifact.
- Require repository, PR, exact 40-character lowercase hexadecimal head, criteria revision, normalized criteria digest, and exact criteria-source provenance binding.
- Imported results are never E1, E2, E3, E4, CI, a human resolution, final acceptance, or a deterministic gate input.
- Every saved or exported object is Pydantic-revalidated; failed imports do not mutate state.
- Preserve `.coverage 2` exactly and never stage, package, modify, rename, or delete it.
- Keep Stage 1 closed at 0/5, 0/3, 0/3, 0/3, and 0/2; keep Stage 2 active; do not begin Stage 3.

---

### Task 1: Persisted import contracts

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/schemas/__init__.py`
- Create: `tests/schemas/test_junit_evidence_import.py`
- Modify: `tests/schemas/test_review_bundle_integrity.py`

**Interfaces:**
- Consumes: `CriteriaSourceProvenance`, `ReviewBundle`, `ReviewState`, `normalized_criteria_sha256`.
- Produces: `JUnitCaseStatus`, `JUnitCaseResult`, `JUnitResultTotals`,
  `JUnitCriterionMapping`, `JUnitEvidenceImport`, and
  `JUnitImportMutationMetadata`.

- [ ] **Step 1: Write the failing contract tests**

Create literal fixtures with exact head `"a" * 40` and assert:

```python
def test_junit_import_requires_exact_review_and_criteria_identity() -> None:
    payload = valid_junit_import_payload()
    record = JUnitEvidenceImport.model_validate(payload)
    assert record.schema_version == "junit-import-v1"
    assert record.totals.total == 2
    assert record.criterion_mappings[0].test_case_ids == [
        "suite-0001-case-0001"
    ]


def test_review_bundle_rejects_junit_import_from_another_head() -> None:
    bundle = exact_head_bundle()
    bundle.junit_evidence_imports = [junit_import(head_sha="b" * 40)]
    with pytest.raises(ValidationError, match="JUnit import identity"):
        ReviewBundle.model_validate(bundle.model_dump(mode="python"))
```

Add parametrized failures for partial identity, non-exact SHA, unknown criterion,
unknown case ID, duplicate case IDs, inconsistent totals, duplicate import IDs,
duplicate artifact digests, mismatched revision/digest/provenance, blank asserted
importer, naive timestamp, blank warning/limitation, and extra fields.

- [ ] **Step 2: Run tests and confirm the missing-contract failure**

Run:

```bash
uv run pytest tests/schemas/test_junit_evidence_import.py tests/schemas/test_review_bundle_integrity.py -q
```

Expected: collection fails because the new types and bundle field do not exist.

- [ ] **Step 3: Add minimal strict Pydantic models and bundle validation**

Use `ConfigDict(extra="forbid", frozen=True)` on nested import records, exact
digest/SHA patterns, timezone normalization, sorted-unique validators, totals
consistency, and cross-reference checks in `ReviewBundle.validate_cross_references`.
Add:

```python
junit_evidence_imports: list[JUnitEvidenceImport] = Field(default_factory=list)
```

Validate all import identity/provenance fields against the owning bundle and
require unique import IDs and artifact digests.

- [ ] **Step 4: Run the schema tests to green**

Run the Step 2 command. Expected: all selected tests pass.

- [ ] **Step 5: Commit the contracts**

```bash
git add scopeproof_core/schemas/models.py scopeproof_core/schemas/__init__.py tests/schemas/test_junit_evidence_import.py tests/schemas/test_review_bundle_integrity.py
git commit -m "feat: define imported JUnit evidence contracts"
```

### Task 2: Bounded bytes-only parser and explicit mapping builder

**Files:**
- Create: `scopeproof_core/importers/__init__.py`
- Create: `scopeproof_core/importers/junit.py`
- Create: `tests/importers/test_junit.py`

**Interfaces:**
- Consumes: `ReviewState`, `JUnitEvidenceImport`, confirmed criteria and provenance.
- Produces:

```python
def parse_junit_artifact(artifact_bytes: bytes) -> ParsedJUnitArtifact: ...
def build_junit_evidence_import(
    state: ReviewState,
    artifact_bytes: bytes,
    selections: list[JUnitMappingSelection],
    *,
    importer: str,
    limitations: list[str] | None = None,
    imported_at: datetime | None = None,
    import_id: str | None = None,
) -> JUnitEvidenceImport: ...
```

- [ ] **Step 1: Write parser success and safety failures first**

Use literal byte fixtures and assert sanitized output:

```python
def test_parser_returns_sanitized_cases_and_ignores_output_bodies() -> None:
    parsed = parse_junit_artifact(
        b'<testsuite name="unit"><testcase name="safe"/>'
        b'<system-out>secret output</system-out></testsuite>'
    )
    assert parsed.totals.model_dump() == {
        "total": 1, "passed": 1, "failures": 0, "errors": 0, "skipped": 0
    }
    assert parsed.suites[0].cases[0].test_case_id == "suite-0001-case-0001"
    assert "secret output" not in parsed.model_dump_json()
```

Parametrize exact-boundary acceptance and one-over rejection for bytes, suites,
cases, and elements. Add failures for non-bytes, non-UTF-8, non-UTF-8 XML
declarations, DTD, internal/external entities, non-declaration processing
instructions, XInclude namespace elements, unsupported roots, nested suites,
cases outside suites, missing test names, multiple result markers, and malformed
XML. Assert error messages contain no supplied secret strings.

- [ ] **Step 2: Verify the parser tests fail because the module is absent**

```bash
uv run pytest tests/importers/test_junit.py -q
```

Expected: import/collection failure for `scopeproof_core.importers.junit`.

- [ ] **Step 3: Implement the minimal bounded parser**

Check byte and encoding boundaries before `ElementTree.fromstring`. Reject
forbidden constructs before parsing, then enforce local tag names, direct-child
structure, element/suite/case limits, bounded names, and at most one direct
result marker. Compute totals from cases. Persist only sanitized names/statuses
and deterministic warnings for declared-count mismatches or discarded output.

- [ ] **Step 4: Add failing builder tests**

Assert suite and case selectors expand deterministically and require explicit
valid mappings:

```python
def test_builder_expands_explicit_suite_mapping_and_binds_review() -> None:
    state = exact_head_state()
    record = build_junit_evidence_import(
        state,
        TWO_CASE_XML,
        [JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-01")],
        importer="QA owner",
        imported_at=datetime(2026, 8, 20, tzinfo=UTC),
        import_id="import-001",
    )
    assert record.artifact_sha256 == sha256(TWO_CASE_XML).hexdigest()
    assert record.criterion_mappings[0].test_case_ids == [
        "suite-0001-case-0001", "suite-0001-case-0002"
    ]
    assert record.repository == state.review.repository
    assert record.head_sha == state.review.head_sha
```

Add failures for no active analysis, unconfirmed/missing provenance, non-exact
head, blank importer, no selections, unknown scope, unknown criterion, empty
suite mapping, and blank limitations.

- [ ] **Step 5: Implement the minimal builder and run tests to green**

Build canonical mappings from parsed IDs, copy exact review/criteria identity,
add the three fixed evidence-boundary limitations, append normalized user
limitations, and return a fully revalidated frozen envelope.

Run:

```bash
uv run pytest tests/importers/test_junit.py tests/schemas/test_junit_evidence_import.py -q
uv run ruff check scopeproof_core/importers tests/importers
```

- [ ] **Step 6: Commit the importer**

```bash
git add scopeproof_core/importers scopeproof_core/schemas tests/importers tests/schemas/test_junit_evidence_import.py
git commit -m "feat: parse bounded JUnit evidence bytes"
```

### Task 3: Atomic lifecycle and saved-review behavior

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/reviews/__init__.py`
- Modify: `tests/reviews/test_lifecycle.py`
- Modify: `tests/storage/test_json_store.py`

**Interfaces:**
- Consumes: `build_junit_evidence_import`, `validated_review_state`.
- Produces:

```python
def append_junit_evidence_import(
    state: ReviewState, evidence_import: JUnitEvidenceImport
) -> ReviewState: ...
```

- [ ] **Step 1: Write lifecycle red tests**

Test successful deep-copy append and literal equality of the pre/post gate,
findings, resolutions, runtime evidence, final acceptance, and resolution
history. Add atomic failures for changed repository/PR/head, changed criteria
revision/digest/provenance, unknown criterion/case, duplicate ID/digest, mutated
input models, and missing active bundle.

```python
def test_junit_import_append_is_non_gating_and_does_not_alias_input() -> None:
    state = exact_head_state()
    record = junit_import_for(state)
    updated = append_junit_evidence_import(state, record)
    assert updated.bundle.junit_evidence_imports == [record]
    assert updated.bundle.gate == state.bundle.gate
    assert updated.bundle.resolutions == state.bundle.resolutions
    assert state.bundle.junit_evidence_imports == []
```

- [ ] **Step 2: Run the lifecycle slice and observe the missing transition**

```bash
uv run pytest tests/reviews/test_lifecycle.py -q -k junit
```

Expected: failure because `append_junit_evidence_import` is absent.

- [ ] **Step 3: Implement the transition and run to green**

Revalidate state and record, verify all active relationships, append a deep
copy, revalidate the resulting state, and explicitly compare unchanged gate and
human/runtime fields before returning.

- [ ] **Step 4: Add storage red-green coverage**

Persist and reopen a state containing an import; assert record version 4,
nested `junit-import-v1`, exact equality, no raw XML, and successful exports.
Downgrade a fixture by deleting `junit_evidence_imports`; assert it reopens as
an empty list. Use `JsonReviewStore.mutate` with a failing transition and assert
the file bytes and fingerprint are unchanged.

Run:

```bash
uv run pytest tests/reviews/test_lifecycle.py tests/storage/test_json_store.py -q -k 'junit or imported_test'
```

- [ ] **Step 5: Commit lifecycle and storage behavior**

```bash
git add scopeproof_core/reviews tests/reviews/test_lifecycle.py tests/storage/test_json_store.py
git commit -m "feat: append imported test evidence atomically"
```

### Task 4: Shared CLI inspection and import

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `parse_junit_artifact`, `build_junit_evidence_import`,
  `append_junit_evidence_import`, `JsonReviewStore.mutate`.
- Produces: `inspect-junit` and `import-junit` CLI commands.

- [ ] **Step 1: Write CLI failing tests**

Create a strict `junit-mapping-v1` JSON fixture and assert `inspect-junit`
outputs sanitized JSON with no raw output. Assert `import-junit` appends one
record and emits validated metadata. Test malformed mapping, wrong schema,
extra fields, unsafe XML, stale review identity, duplicate artifact, missing
file, and store failure; each failed command must leave record bytes unchanged.

```python
def test_import_junit_persists_one_non_gating_record(tmp_path: Path, capsys) -> None:
    review_id = save_exact_head_review(tmp_path)
    result = main([
        "import-junit", review_id, str(write_xml(tmp_path)),
        "--mapping", str(write_mapping(tmp_path)),
        "--importer", "QA owner", "--storage-dir", str(tmp_path / "reviews"),
    ])
    assert result == 0
    loaded = JsonReviewStore(tmp_path / "reviews").load(review_id)
    assert len(loaded.bundle.junit_evidence_imports) == 1
    assert loaded.bundle.gate.verdict is GateVerdict.NEEDS_REVIEW
```

- [ ] **Step 2: Run CLI tests and confirm parser rejects the new commands**

```bash
uv run pytest tests/cli/test_cli.py -q -k junit
```

Expected: argparse rejects `inspect-junit` and `import-junit`.

- [ ] **Step 3: Implement strict mapping parsing and command handlers**

Define a strict Pydantic `JUnitMappingDocument` with literal
`junit-mapping-v1`. Read explicit local files only in the CLI adapter. Use
`JsonReviewStore.mutate` for the persisted transition. Print only sanitized
Pydantic JSON metadata; never print raw XML or local paths from XML.

- [ ] **Step 4: Run CLI and adjacent storage tests to green**

```bash
uv run pytest tests/cli/test_cli.py tests/storage/test_json_store.py -q -k 'junit or import_junit or inspect_junit'
uv run ruff check scopeproof_core/cli.py tests/cli/test_cli.py
```

- [ ] **Step 5: Commit CLI parity**

```bash
git add scopeproof_core/cli.py tests/cli/test_cli.py
git commit -m "feat: expose bounded JUnit imports in CLI"
```

### Task 5: Streamlit import, preview, and reopen flow

**Files:**
- Modify: `apps/web/app.py`
- Modify: `apps/web/view_models.py` only if presentation projection is reusable.
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `tests/apps/test_view_models.py` only if `view_models.py` changes.
- Modify: `tests/browser/test_packaged_workbench.py`

**Interfaces:**
- Consumes: shared core parser, builder, lifecycle transition.
- Produces: one separate selected-criterion JUnit import expander and recorded
  import display.

- [ ] **Step 1: Write AppTest failures for the new workflow**

Start from `analyzed_exact_head_standard_demo`. Upload a one-suite fixture,
enter importer, preview sanitized scope IDs, choose `suite-0001`, save to the
selected criterion, and assert the import is separate from E3/E4 controls. Test
disabled save, parser error, invalid scope, oversized upload, failed transition,
form reset, save/reopen display, and unchanged gate/human/runtime state.

Assert hostile suite/test/importer text appears only through inert Streamlit
text/code elements, never Markdown. Assert ignored XML output is absent from all
visible elements and session-state models.

Also add the installed-wheel exact-head import/save/reopen/download browser case
described in Task 7 before changing the UI.

- [ ] **Step 2: Run AppTest and confirm the controls are absent**

```bash
uv run pytest tests/apps/test_streamlit_app.py -q -k junit
uv run pytest -m browser tests/browser/test_packaged_workbench.py::test_installed_wheel_junit_import_round_trip -q
```

Expected: both commands fail because the new uploader/controls are absent.

- [ ] **Step 3: Implement the minimal shared-core UI**

Place `Import external JUnit results` before the E3/E4 expander. Check uploaded
size before reading bytes. Preview with `parse_junit_artifact`; use the stable
scope IDs as multiselect options and the currently selected criterion as the
explicit mapping target. Apply `append_junit_evidence_import` only on Save.
Render saved imports with `st.text`, `st.code`, and existing inert reference
helpers, never raw Markdown from artifact values.

- [ ] **Step 4: Run AppTest and nearby browser-independent UI tests**

```bash
uv run pytest tests/apps/test_streamlit_app.py tests/apps/test_web_app.py tests/apps/test_view_models.py -q
uv run pytest -m browser tests/browser/test_packaged_workbench.py::test_installed_wheel_junit_import_round_trip -q
uv run ruff check apps/web tests/apps
```

- [ ] **Step 5: Commit the workbench flow**

```bash
git add apps/web/app.py apps/web/view_models.py tests/apps/test_streamlit_app.py tests/apps/test_view_models.py tests/browser/test_packaged_workbench.py
git commit -m "feat: add JUnit import review workflow"
```

Stage only files that actually changed.

### Task 6: Safe exports and comparison projection

**Files:**
- Modify: `scopeproof_core/reporting/exporters.py`
- Modify: `scopeproof_core/reviews/comparison.py`
- Modify: `tests/reporting/test_exporters.py`
- Modify: `tests/reporting/test_html_export.py`
- Modify: `tests/reporting/test_comparison_exports.py`
- Modify: `tests/reviews/test_comparison.py`
- Modify: `scopeproof_core/evals/comparison_runner.py` only if the typed output changes require fixture assertions.

**Interfaces:**
- Consumes: validated `JUnitEvidenceImport` lists.
- Produces: safe Markdown/HTML/CSV sections and typed comparison changes keyed
  by artifact digest and mapping signature.

- [ ] **Step 1: Write export red tests**

Assert JSON, Markdown, HTML, and CSV include the artifact digest, exact head,
asserted importer, mapped criterion/case/status, warnings, and limitations.
Assert they exclude a sentinel raw XML string, ignored stdout, failure body, and
local artifact path. Use formula/HTML/Markdown payloads in all imported names
and assert CSV neutralization plus inert Markdown/HTML escaping.

- [ ] **Step 2: Run export tests and observe missing import sections**

```bash
uv run pytest tests/reporting/test_exporters.py tests/reporting/test_html_export.py -q -k junit
```

- [ ] **Step 3: Implement safe export projections and run to green**

Reuse `_render_markdown_code`, `html.escape`, and `_csv_text`. Do not serialize
the source XML or any discarded parser field.

- [ ] **Step 4: Write comparison red tests**

Assert unchanged, added, removed, and same-digest mapping-modified projections.
Tamper imported repository/head/provenance/mapping data and assert comparison
fails before output. Assert changed imported context adds only previously
resolved affected criteria to `criteria_requiring_decision_review`, copies no
resolution, and changes neither gate.

- [ ] **Step 5: Implement typed import comparison and run the full slice**

```bash
uv run pytest tests/reviews/test_comparison.py tests/reporting/test_comparison_exports.py tests/evals/test_comparison_runner.py -q
uv run ruff check scopeproof_core/reporting scopeproof_core/reviews tests/reporting tests/reviews/test_comparison.py
```

- [ ] **Step 6: Commit exports and comparison**

```bash
git add scopeproof_core/reporting/exporters.py scopeproof_core/reviews/comparison.py scopeproof_core/evals/comparison_runner.py tests/reporting tests/reviews/test_comparison.py tests/evals/test_comparison_runner.py
git commit -m "feat: export and compare imported test evidence"
```

Stage only files that actually changed.

### Task 7: Installed-wheel browser completion and product documentation

**Files:**
- Modify: `tests/browser/test_packaged_workbench.py`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/commercialization/stage2-readiness-packet.md`
- Create or modify focused repository contracts in `tests/test_repository_contracts.py` only for authoritative machine-checkable status relationships.

**Interfaces:**
- Consumes: installed wheel, local review store, browser workbench.
- Produces: exact-head import/save/reopen/download browser proof and truthful
  product status.

- [ ] **Step 1: Complete the installed-wheel browser regression started in Task 5**

Confirm the failing test written in Task 5 builds an exact-head synthetic saved
review with installed ScopeProof code in the temporary HOME. It must launch the
installed wheel with loopback-only networking, reopen the review, upload a
one-suite XML file, map `suite-0001`, save, verify the non-gating label,
save/reopen, and download JSON and Markdown. Both downloads must contain the
SHA-256 digest and exclude raw XML/output sentinels.

- [ ] **Step 2: Run the browser regression and observe the absent UI**

```bash
uv run pytest -m browser tests/browser/test_packaged_workbench.py -q
```

Expected after Tasks 1–6: all browser cases pass with zero external requests,
console errors, or page errors.

- [ ] **Step 3: Update product truth documents**

Document the adapter as externally supplied, non-gating engineering context.
Keep version `0.2.4.dev0`, latest release v0.2.3, Stage 1 counts zero, Stage 2
active, Stage 3 gated, reviewer identity asserted, and platform/accessibility
limits unchanged. Move the exact-SHA informational Check lifecycle from the
future-candidate list to delivered Stage 2 work because PR #196 already merged.

- [ ] **Step 4: Add behavior-level documentation contracts only where needed**

If an authoritative status relationship needs a contract, parse the exact
section and assert the state relationship rather than merely searching the
whole document for words. Do not test ordinary explanatory prose.

- [ ] **Step 5: Run documentation, browser, and repository-contract checks**

```bash
uv run pytest tests/test_repository_contracts.py -q
uv run pytest -m browser tests/browser/test_packaged_workbench.py -q
uv run ruff check .
git diff --check
```

- [ ] **Step 6: Commit browser and documentation evidence**

```bash
git add tests/browser/test_packaged_workbench.py README.md ROADMAP.md CHANGELOG.md docs/releases/v0.2.3-status-and-next-stages.md docs/commercialization/stage2-readiness-packet.md tests/test_repository_contracts.py
git commit -m "docs: record bounded external test imports"
```

Stage only files that actually changed.

### Task 8: Complete verification and exact-head review

**Files:**
- Modify only confirmed defects found by verification, each with a failing regression first.

**Interfaces:**
- Consumes: final feature branch.
- Produces: reproducible engineering evidence and a reviewed exact head.

- [ ] **Step 1: Run formatting, complete suite, and coverage**

```bash
uv run ruff check .
uv run python -m pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run pytest tests/test_repository_contracts.py -q
git diff --check
```

- [ ] **Step 2: Run deterministic benchmarks**

```bash
uv run scopeproof-eval
uv run scopeproof-compare-eval
```

Require every mismatch and must-have False Ready count to equal zero.

- [ ] **Step 3: Build and compare two wheels**

Build in two clean temporary output directories with the repository's standard
build command, compare SHA-256 values byte-for-byte, inspect archive entries,
and assert `.coverage`, `.scopeproof`, `.superpowers`, worktrees, raw test
artifacts, and local state are absent.

- [ ] **Step 4: Verify clean installation and runtime lanes**

Install the wheel into a clean environment, run dependency validation, compare
source/installed versions, run both CLIs and installed benchmarks, start exact
loopback health and confirm listener shutdown, and rerun installed-wheel
Chromium. Run the supported local Python lanes available on the host; hosted
Python and Windows conclusions come from the PR checks.

- [ ] **Step 5: Audit the exact diff and commits**

```bash
git status --short
git diff --check origin/main...HEAD
git log --oneline --decorate origin/main..HEAD
git diff --stat origin/main...HEAD
```

Confirm only named in-scope files changed and the original checkout still has
the exact `.coverage 2` SHA-256, size, mtime, and inode.

- [ ] **Step 6: Obtain an independent read-only review**

Review exact range `f586d90b72a14fd19d5a0add01f3d05532a88955..HEAD`
against the approved spec. Require explicit Critical/Important/Minor findings,
read-only diff inspection, and a merge-readiness verdict. For every actionable
Critical or Important issue, write a failing regression, implement the minimal
fix, rerun affected and full checks, commit intentionally, and repeat exact-head
review until none remain.

### Task 9: Publish the ready PR and monitor hosted checks

**Files:**
- No source files unless a hosted check exposes a confirmed in-scope defect.

**Interfaces:**
- Consumes: independently reviewed exact head.
- Produces: ready PR `feat: import bounded external test evidence`.

- [ ] **Step 1: Push the exact branch**

```bash
git push -u origin codex/junit-evidence-adapter
```

- [ ] **Step 2: Open a ready-for-review PR against `main`**

The description must summarize the evidence taxonomy, parser bounds, explicit
mapping, atomic lifecycle, CLI/UI parity, safe exports/comparison, browser proof,
verification, independent review, unsupported environments, preserved
`.coverage 2`, Stage 1 zero counts, and the no-release/no-Stage-3 boundary.

- [ ] **Step 3: Monitor every available check to a terminal conclusion**

Diagnose failures systematically. Fix only confirmed in-scope defects with a
failing regression first, commit and push the repair, repeat independent review
for the changed exact head, and wait for replacement checks.

- [ ] **Step 4: Final handoff without merging**

Report PR URL, exact base/head/tree, commits, complete verification results,
hosted conclusions, review findings, unsupported environments, preserved local
artifact proof, Stage 1 counts, and the owner decision: merge or hold/request
changes. Do not merge, release, tag, publish, conduct outreach, generate R-003,
retune R-002, or start Stage 3/4.
