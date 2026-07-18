# ScopeProof Reviewer-First v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reviewer-first, five-minute acceptance-coverage workflow without paid models,
correctness claims, notification noise, or fabricated validation.

**Architecture:** Preserve the validated deterministic schemas and add a UI-independent
presentation layer for honest human-facing terminology. Extend lifecycle, retrieval, GitHub, alpha,
and comparison services through small validated interfaces, then make Streamlit and exporters
consume those interfaces. Keep alpha research optional and keep every persisted transition
Pydantic-validated.

**Tech Stack:** Python 3.11+, Pydantic 2, Streamlit 1.59, httpx, pytest 9, Ruff, uv, static HTML/CSS,
GitHub Actions.

## Global Constraints

- No paid OpenAI, LLM, or other model APIs.
- Public repositories only; never execute pull-request code.
- Preserve the evaluation-only use policy and the unrelated `.coverage 2` file.
- Keep the core independent from Streamlit and GitHub UI layers.
- Candidate implementation evidence is never test or runtime verification.
- Criteria confirmation remains mandatory before analysis.
- Every changed evidence or gate rule receives regression coverage.
- Use one `codex/scopeproof-v0-2-product-reset` branch and one pull request without progress comments.
- JSON backward compatibility is required; human-facing terminology may change.

---

### Task 1: Shared acceptance-coverage presentation

**Files:**
- Create: `scopeproof_core/presentation.py`
- Modify: `scopeproof_core/reporting/exporters.py` (`export_markdown`, `export_csv`, `export_html`)
- Modify: `apps/web/app.py`
- Test: `tests/test_presentation.py`
- Test: `tests/reporting/test_exporters.py`
- Test: `tests/reporting/test_html_export.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `ReviewBundle`, `Criterion`, `Finding`, `HumanResolution`.
- Produces: `EvidenceStatus`, `ReviewStatus`, `CriterionCoverageRow`,
  `criterion_coverage_rows(bundle)`, `evidence_status_label(finding, resolution)`, and
  `review_status_label(verdict)`.

- [ ] **Step 1: Write failing presentation tests**

```python
def test_presentation_separates_candidate_status_from_human_decision(bundle):
    row = criterion_coverage_rows(bundle)[0]
    assert row.evidence_status is EvidenceStatus.STRONG_CANDIDATE
    assert row.reviewer_decision == "Unresolved"
    assert row.evidence_types == ["Implementation"]

def test_review_status_does_not_claim_release_readiness():
    assert review_status_label(GateVerdict.READY) == "Review complete"
    assert review_status_label(GateVerdict.BLOCKED) == "Action required"
```

- [ ] **Step 2: Run the focused tests and verify the missing-module failure**

Run: `uv run pytest -q tests/test_presentation.py`

Expected: collection fails because `scopeproof_core.presentation` does not exist.

- [ ] **Step 3: Implement the validated presentation mapping**

```python
class EvidenceStatus(StrEnum):
    STRONG_CANDIDATE = "strong_candidate"
    WEAK_CANDIDATE = "weak_candidate"
    NO_CANDIDATE = "no_candidate"
    ANALYSIS_INCOMPLETE = "analysis_incomplete"
    REVIEWER_VERIFIED = "reviewer_verified"
    REJECTED = "rejected"

class CriterionCoverageRow(BaseModel):
    criterion_id: str
    criterion_text: str
    priority: str
    evidence_status: EvidenceStatus
    evidence_types: list[str]
    reviewer_decision: str
    candidate_count: int
    concern: str
```

Map `EVIDENCE_FOUND` to strong candidate, `PARTIAL` to weak candidate, complete-ingestion `MISSING`
to no candidate, and `NEEDS_REVIEW` to analysis incomplete. A current manual verification or
rejected finding changes only the presentation status; it does not rewrite static findings.

- [ ] **Step 4: Replace human-facing matrix and report labels**

Use `criterion_coverage_rows()` in Streamlit, Markdown, CSV, and HTML. Retain canonical legacy enum
values in JSON. Replace `Verdict` with `Review status`, `Level` with `Evidence types`, and
`Evidence Found` with `Strong candidate` on user-facing surfaces.

- [ ] **Step 5: Run focused presentation, reporting, and AppTests**

Run: `uv run pytest -q tests/test_presentation.py tests/reporting tests/apps/test_streamlit_app.py`

Expected: all focused tests pass.

- [ ] **Step 6: Commit the slice**

```bash
git add scopeproof_core/presentation.py scopeproof_core/reporting apps/web/app.py \
  tests/test_presentation.py tests/reporting tests/apps/test_streamlit_app.py
git commit -m "feat: present acceptance coverage honestly"
```

### Task 2: Evidence context and observed CI accuracy

**Files:**
- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/retrieval/engine.py`
- Modify: `scopeproof_core/github/client.py`
- Modify: `apps/web/app.py`
- Test: `tests/retrieval/test_engine.py`
- Test: `tests/schemas/test_models.py`
- Test: `tests/github/test_client.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Adds backward-compatible `EvidenceItem.context_excerpt: str | None = None`.
- Keeps `PullRequestSnapshot.check_state` but presents it as observed CI state.

- [ ] **Step 1: Write failing context and CI tests**

```python
def test_retrieval_adds_one_neighbor_on_each_side(snapshot, criteria):
    item = retrieve_evidence(snapshot, criteria)[0]
    assert item.context_excerpt == "before line\nmatched line\nafter line"

def test_neutral_or_skipped_checks_do_not_prove_passing():
    assert GitHubClient._check_state(
        {"check_runs": [{"status": "completed", "conclusion": "skipped"}]},
        {"state": None},
    ) is CheckState.UNAVAILABLE
```

- [ ] **Step 2: Verify both tests fail for the intended reasons**

Run: `uv run pytest -q tests/retrieval/test_engine.py tests/github/test_client.py`

Expected: missing context field assertion and skipped-check aggregation assertion fail.

- [ ] **Step 3: Implement deterministic bounded context**

Build context only from inspectable non-removed lines in the same `ChangedFile`; include at most one
line before and after the matched line. Keep `line_start`, `line_end`, and permalink bound to the
matched line. Validate nonblank optional context.

- [ ] **Step 4: Tighten observed CI aggregation**

Only explicit `success` is passing. Failure conclusions take precedence, then queued/in-progress,
then explicit success, otherwise unavailable. Rename human-facing labels and limitations to
`Observed CI state`; do not rename the stored field.

- [ ] **Step 5: Run schema, retrieval, GitHub, and AppTests**

Run: `uv run pytest -q tests/schemas tests/retrieval tests/github tests/apps/test_streamlit_app.py`

Expected: all focused tests pass.

- [ ] **Step 6: Commit the slice**

```bash
git add scopeproof_core/schemas/models.py scopeproof_core/retrieval/engine.py \
  scopeproof_core/github/client.py apps/web/app.py tests/schemas tests/retrieval tests/github \
  tests/apps/test_streamlit_app.py
git commit -m "feat: add bounded evidence context"
```

### Task 3: Atomic external verification and final-acceptance prerequisites

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/reviews/__init__.py`
- Modify: `apps/web/app.py`
- Test: `tests/reviews/test_lifecycle.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Produces: `append_external_verification(state, evidence, event) -> ReviewState`.
- Produces: `can_record_final_acceptance(state) -> bool`.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_external_verification_atomically_appends_evidence_and_resolution():
    updated = append_external_verification(state, runtime_evidence, manual_event)
    assert updated.bundle.runtime_evidence == [runtime_evidence]
    assert updated.bundle.resolutions[0].decision is HumanDecision.MANUALLY_VERIFIED

def test_final_acceptance_requires_all_current_criteria_resolved():
    assert can_record_final_acceptance(initial_state()) is False
    assert can_record_final_acceptance(accepted_state) is True
```

- [ ] **Step 2: Verify the tests fail because the interfaces are absent**

Run: `uv run pytest -q tests/reviews/test_lifecycle.py -k 'external_verification or final_acceptance_requires'`

- [ ] **Step 3: Implement atomic verification**

Validate both inputs before mutation. Require the same criterion, `MANUALLY_VERIFIED`, E3 or E4,
matching reviewer, and a nonblank note. Append runtime evidence to a deep bundle copy, bind the event
to the active revision, then recalculate once.

- [ ] **Step 4: Implement final-acceptance eligibility**

Require complete ingestion, passing observed CI, an active bundle, and a current decision in
`ACCEPTED`, `ACCEPTED_EXCEPTION`, `MANUALLY_VERIFIED`, or `NOT_IN_SCOPE` for every active criterion.

- [ ] **Step 5: Replace the duplicate workbench forms**

Use one `Record external verification` form and one atomic save button. Disable final acceptance
until the helper returns true and explain the exact missing prerequisite.

- [ ] **Step 6: Run lifecycle and AppTests**

Run: `uv run pytest -q tests/reviews tests/apps/test_streamlit_app.py`

- [ ] **Step 7: Commit the slice**

```bash
git add scopeproof_core/reviews apps/web/app.py tests/reviews tests/apps/test_streamlit_app.py
git commit -m "feat: unify external verification decisions"
```

### Task 4: Optional end-to-end alpha feedback session

**Files:**
- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/alpha/service.py`
- Modify: `scopeproof_core/alpha/__init__.py`
- Test: `tests/alpha/test_service.py`
- Test: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Reuses: `initialize_alpha_case`, `record_alpha_outcome`, `JsonAlphaCaseStore`.
- Produces: `ensure_alpha_case(...) -> AlphaCaseRecord`, an idempotent service transition that
  returns the existing matching case or creates one supplied by the caller's store boundary.

- [ ] **Step 1: Write failing AppTests for the default and optional flows**

```python
def test_standard_review_hides_alpha_research_fields():
    app = new_app()
    assert app.checkbox(key="alpha_feedback_mode").value is False
    assert not [item for item in app.text_input if item.key == "requirements_source_url"]

def test_alpha_mode_creates_case_after_confirming_criteria(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    app = qualified_alpha_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["alpha_case_id"].startswith("alpha-")
    assert JsonAlphaCaseStore(default_alpha_case_directory()).list_case_ids()
```

- [ ] **Step 2: Verify the new AppTests fail on the current review-path radio**

Run: `uv run pytest -q tests/apps/test_streamlit_app.py -k 'standard_review_hides or alpha_mode_creates'`

- [ ] **Step 3: Make standard review the default**

Replace the path radio with an unchecked `Alpha feedback session` checkbox. Standard public PR
review requires only the PR URL. Show source-owner, role, source URL, and confidentiality fields
only in alpha mode. Keep the demo explicitly constructed.

- [ ] **Step 4: Create and display one validated case**

After criteria confirmation, create and save the case exactly once. Store only its generated case
ID in session. Any invalid or unsafe store error leaves review state unchanged and shows a safe
message.

- [ ] **Step 5: Record the alpha outcome inline**

After analysis, require a saved review ID and exact head SHA. Show outcome, conditional friction
stage, optional notes, and separate report/quote consent. Update the existing record atomically and
display its completion state. Do not show these controls in standard review.

- [ ] **Step 6: Run alpha and AppTests**

Run: `uv run pytest -q tests/alpha tests/apps/test_streamlit_app.py`

- [ ] **Step 7: Commit the slice**

```bash
git add scopeproof_core/alpha apps/web/app.py tests/alpha tests/apps/test_streamlit_app.py
git commit -m "feat: connect optional alpha feedback flow"
```

### Task 5: Bounded candidate paths and visible re-review comparison

**Files:**
- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/reviews/comparison.py`
- Test: `tests/apps/test_streamlit_app.py`
- Test: `tests/reviews/test_comparison.py`
- Test: `tests/github/test_pagination_and_candidates.py`

**Interfaces:**
- Reuses: `GitHubClient.fetch_candidate_files(repository, head_sha, paths)`.
- Reuses: `compare_reviews(previous, current) -> ReviewComparison`.

- [ ] **Step 1: Write failing AppTests for explicit paths and comparison**

```python
def test_explicit_candidate_paths_are_fetched_and_passed_to_analysis():
    assert app.text_area(key="candidate_paths").value == ""
    # Patch the public fetch and assert normalized explicit paths only.

def test_reanalysis_shows_previous_and_current_head_sha():
    assert "Previous head" in rendered_comparison
    assert "Current head" in rendered_comparison
```

- [ ] **Step 2: Verify focused failures**

Run: `uv run pytest -q tests/apps/test_streamlit_app.py -k 'candidate_paths or reanalysis_shows'`

- [ ] **Step 3: Add explicit advanced candidate-path input**

Normalize one repository-relative path per line, reject absolute or traversal paths through the
existing client validation, fetch at most the configured bound, and pass returned files to
`retrieve_evidence`. Persist no token and do not infer paths.

- [ ] **Step 4: Preserve the previous bundle for re-review**

When a reopened review fetches the same PR at a new head, preserve its active validated bundle in
`comparison_base_bundle`. After new analysis, compute and display the immutable comparison. Clear
the comparison base when a different PR or constructed demo is loaded.

- [ ] **Step 5: Run comparison, candidate, and AppTests**

Run: `uv run pytest -q tests/reviews/test_comparison.py tests/github/test_pagination_and_candidates.py tests/apps/test_streamlit_app.py`

- [ ] **Step 6: Commit the slice**

```bash
git add apps/web/app.py scopeproof_core/reviews/comparison.py tests/apps/test_streamlit_app.py \
  tests/reviews/test_comparison.py tests/github/test_pagination_and_candidates.py
git commit -m "feat: show bounded re-review changes"
```

### Task 6: Product cleanup, responsive public site, and roadmap

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `site/index.html`
- Modify: `site/styles.css`
- Modify: `docs/launch/demo-script.md`
- Modify: `docs/launch/evidence-matrix.md`
- Modify: `docs/alpha/participant-quickstart.md`
- Modify: `docs/github-action.md`
- Modify: `tests/test_repository_contracts.py`
- Modify: `scopeproof_core/version.py`

**Interfaces:**
- Human-facing contract only; canonical JSON values remain backward compatible.

- [ ] **Step 1: Write failing repository-contract assertions**

```python
assert "See which acceptance criteria have credible PR evidence" in readme
assert "Prove the PR matches the product intent" not in public_surfaces
assert "Five completed reviews" in roadmap
assert "Alpha feedback session" in readme
assert "GitHub Action advanced preview" in readme
```

- [ ] **Step 2: Verify contract tests fail on stale product language**

Run: `uv run pytest -q tests/test_repository_contracts.py`

- [ ] **Step 3: Rewrite product and research documentation**

Define the primary reviewer, under-five-minute outcome, honest candidate vocabulary, optional alpha
mode, observed CI limitation, comparison workflow, and advanced Action boundary. Remove Action
comments and alpha operating details from first-use documentation while retaining linked advanced
runbooks.

- [ ] **Step 4: Rewrite the roadmap gates**

Add product-reset completion, genuine public alpha with five reviews/three practitioners/three
repositories, beta eligibility based on repeat behavior, and evidence-guided expansion. Keep
`waiting_for_external_participant_evidence` honest until qualifying records exist.

- [ ] **Step 5: Fix mobile CSS and update static copy**

At `max-width: 600px`, bound the hero to `clamp(2.35rem, 12vw, 3.5rem)`, set
`overflow-wrap: anywhere`, constrain media to `max-width: 100%`, and keep full-width buttons inside
the viewport. Update the static matrix and workflow copy to the shared product terms.

- [ ] **Step 6: Set source version to `0.2.0` and update changelog**

Only perform this after all behavior tests pass. Document the reset without claiming external
validation.

- [ ] **Step 7: Run repository contracts and full AppTests**

Run: `uv run pytest -q tests/test_repository_contracts.py tests/apps`

- [ ] **Step 8: Commit the slice**

```bash
git add README.md ROADMAP.md CHANGELOG.md site docs/launch docs/alpha \
  docs/github-action.md tests/test_repository_contracts.py scopeproof_core/version.py
git commit -m "docs: align public alpha with reviewer workflow"
```

### Task 7: Full verification and release artifact proof

**Files:**
- Modify only files implicated by verified failures.
- Create temporary artifacts outside the repository.

- [ ] **Step 1: Run formatting, lint, complete tests, coverage, and benchmark**

```bash
uv run ruff check .
uv run pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 -q
uv run scopeproof benchmark
```

- [ ] **Step 2: Build and validate wheel metadata**

```bash
dist_dir="$(mktemp -d /tmp/scopeproof-v0.2.0-dist.XXXXXX)"
venv_dir="$(mktemp -d /tmp/scopeproof-v0.2.0-venv.XXXXXX)"
uv build --out-dir "$dist_dir"
python -m venv "$venv_dir"
"$venv_dir/bin/pip" install "$dist_dir/scopeproof-0.2.0-py3-none-any.whl"
"$venv_dir/bin/scopeproof" --version
"$venv_dir/bin/scopeproof" benchmark
```

- [ ] **Step 3: Verify CLI, exporters, and installed workbench health**

Run every supported export on the constructed fixture, validate JSON, inspect Markdown/CSV/HTML,
start the installed workbench on a temporary port, and require `/_stcore/health` to return `ok`.

- [ ] **Step 4: Inspect desktop and 390px browser captures**

Start the local site and workbench without untrusted code. Capture desktop and 390px views, inspect
the images, and verify no page-level horizontal overflow, clipped hero, hidden primary action, or
unlabelled constructed evidence.

- [ ] **Step 5: Audit the complete goal against the diff**

Re-read the design and this plan, map every completion condition to code, test, documentation, or
an explicit external waiting condition. Run `git diff --check`, `git status -sb`, and a sensitive
data scan before publishing.

### Task 8: Publish one pull request, merge, release, and record honest alpha status

**Files:**
- No product file changes unless a protected check exposes a verified defect.

- [ ] **Step 1: Push the verified branch**

Run: `git push -u origin codex/scopeproof-v0-2-product-reset`

- [ ] **Step 2: Open one ready pull request without comments**

The PR body states what changed, why, user impact, verification evidence, and the remaining external
alpha limitation. Do not add progress comments.

- [ ] **Step 3: Wait for protected checks and repair genuine failures test-first**

Require the protected `verify` check and any configured CodeQL check to pass. Do not bypass branch
protection and do not merge failures.

- [ ] **Step 4: Merge and synchronize main**

Merge the PR, fetch origin, switch the primary checkout to `main`, fast-forward it, and verify local
and remote SHAs match while `.coverage 2` remains unchanged.

- [ ] **Step 5: Publish and verify v0.2.0 only when eligible**

Tag the exact merged commit, create one GitHub release with the wheel, source distribution, and
checksums, then verify the public release assets, install the downloaded wheel in a new environment,
and verify Pages deployment. Do not publish if any release prerequisite failed.

- [ ] **Step 6: Audit genuine external alpha evidence once**

Inspect validated local alpha records and genuine non-owner public submissions. If the required
five-review threshold is unmet, record exactly `waiting_for_external_participant_evidence` in the
final report. Do not poll, comment, contact users, or invent evidence.

- [ ] **Step 7: Report completion evidence**

Report branch, commits, PR, merge SHA, release URL and checksums when published, verification counts,
browser artifacts, working-tree state, and every external item still open.
