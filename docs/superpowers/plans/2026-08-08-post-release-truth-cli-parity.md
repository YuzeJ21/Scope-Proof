# Post-release Truth, CLI Lifecycle Parity, and Packaged Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align ScopeProof with its published v0.2.3 release, expose the existing reviewer lifecycle through the CLI, and add an installed-wheel real-browser regression without weakening evidence boundaries.

**Architecture:** Keep lifecycle decisions in the Python core, make the CLI a thin validated adapter over existing lifecycle/storage/export services, and keep browser automation development-only. Current-state documentation and repository contracts bind release claims to PR #184 and exact-main evidence, while historical audits remain immutable.

**Tech Stack:** Python 3.11+, Pydantic 2, argparse, Streamlit, pytest, Playwright for Python, uv, GitHub Actions.

## Global Constraints

- ScopeProof remains an evidence assistant, not a correctness oracle.
- Candidate implementation evidence, reviewer-confirmed test evidence, runtime evidence, and human acceptance remain distinct.
- Never execute target-repository code.
- Every persisted or exported object is Pydantic-validated.
- Gate decisions remain deterministic and reproducible; False Ready is more harmful than False Blocked.
- The core engine remains independent from Streamlit and GitHub UI layers.
- Playwright is development-only and must not appear in wheel runtime requirements.
- Stage 1 remains 0/5 reviews, 0/3 practitioners, 0/3 repositories, 0/3 independently observed under-ten-minute completions, and 0/2 reuse-intent signals.
- Do not push, open or merge a PR, publish, modify GitHub issues, or contact participants in this plan.
- Preserve `.coverage 2`, unrelated user changes, unmerged worktrees, and standalone nested repositories.

---

### Task 1: Bind Current Surfaces to the Published v0.2.3 Release

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `site/index.html`

**Interfaces:**
- Consumes: GitHub release tag `v0.2.3`, release/main SHA `448c42758ea139bf9203cbf1bb04b02b02ae412c`, PR #184, CI run `30854382641`, CodeQL run `30854382413`, Pages run `30854382659`.
- Produces: current-state documentation and a public-site CTA that identify the published release without rewriting historical audits.

- [x] **Step 1: Replace stale current-state contract expectations with release-bound expectations**

Add constants and assertions equivalent to:

```python
PR184_RELEASE_MERGE_SHA = "448c42758ea139bf9203cbf1bb04b02b02ae412c"
PR184_EXACT_MAIN_RUN_IDS = ("30854382641", "30854382413", "30854382659")

assert "PR #184" in active_status
assert PR184_RELEASE_MERGE_SHA in active_status
assert all(run_id in active_status for run_id in PR184_EXACT_MAIN_RUN_IDS)
assert "v0.2.3 is published" in active_status
assert "Stage 1 remains at zero" in active_status
```

Keep separate assertions that historical PR #183 evidence remains described as historical source evidence.

- [x] **Step 2: Run the current-state contracts and verify RED**

Run: `uv run pytest -q tests/test_repository_contracts.py`

Expected: FAIL because active surfaces still identify PR #183 as current and the site CTA still says `Check for release v0.2.3`.

- [x] **Step 3: Align current-state documentation and site CTA**

Update active surfaces so they state:

```text
ScopeProof v0.2.3 is published. PR #184 merged the release integration at
448c42758ea139bf9203cbf1bb04b02b02ae412c; the peeled v0.2.3 tag and current
main resolve to the same commit. Exact-main CI 30854382641, CodeQL 30854382413,
and Pages 30854382659 succeeded. This is engineering evidence and does not
advance Stage 1, which remains at zero.
```

Use this exact CTA in `site/index.html`:

```html
<a class="button button-primary" href="https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.3">Download v0.2.3</a>
```

- [x] **Step 4: Run focused contracts and verify GREEN**

Run: `uv run pytest -q tests/test_repository_contracts.py`

Expected: PASS.

- [x] **Step 5: Run diff hygiene for Task 1**

Run: `git diff --check -- README.md ROADMAP.md docs/releases/v0.2.3-status-and-next-stages.md site/index.html tests/test_repository_contracts.py`

Expected: no output and exit 0.

---

### Task 2: Centralize the Low-evidence Acceptance-note Rule

**Files:**
- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `apps/web/app.py`
- Modify: `tests/reviews/test_lifecycle.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: `HumanDecision`, a criterion's `required_evidence_level`, and its finding's observed `evidence_level`.
- Produces: `acceptance_requires_comment(decision: HumanDecision, observed_level: EvidenceLevel, required_level: EvidenceLevel) -> bool`.

- [x] **Step 1: Write focused core tests**

Add parameterized tests equivalent to:

```python
@pytest.mark.parametrize(
    ("decision", "observed", "required", "expected"),
    [
        (HumanDecision.ACCEPTED, EvidenceLevel.E1, EvidenceLevel.E2, True),
        (HumanDecision.ACCEPTED, EvidenceLevel.E2, EvidenceLevel.E2, False),
        (HumanDecision.CHANGE_REQUIRED, EvidenceLevel.E1, EvidenceLevel.E2, False),
    ],
)
def test_acceptance_comment_policy(decision, observed, required, expected):
    assert acceptance_requires_comment(decision, observed, required) is expected
```

- [x] **Step 2: Run the core test and verify RED**

Run: `uv run pytest -q tests/reviews/test_lifecycle.py -k acceptance_comment_policy`

Expected: collection/import failure because `acceptance_requires_comment` does not exist.

- [x] **Step 3: Add the minimal pure helper**

```python
def acceptance_requires_comment(
    decision: HumanDecision,
    observed_level: EvidenceLevel,
    required_level: EvidenceLevel,
) -> bool:
    return (
        decision is HumanDecision.ACCEPTED
        and observed_level.rank < required_level.rank
    )
```

- [x] **Step 4: Replace the Streamlit-local expression with the helper**

Import the helper and set:

```python
acceptance_below_required = (
    decision is not None
    and acceptance_requires_comment(
        decision,
        selected_finding.evidence_level,
        selected_criterion.required_evidence_level,
    )
)
```

- [x] **Step 5: Run core and Streamlit acceptance-note regressions**

Run: `uv run pytest -q tests/reviews/test_lifecycle.py -k acceptance_comment_policy tests/apps/test_streamlit_app.py -k 'below_required_evidence'`

Expected: PASS.

---

### Task 3: Add Validated CLI Mutation Helpers and Resolution Command

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `JsonReviewStore.load`, `append_resolution`, `acceptance_requires_comment`, `ResolutionEvent`, `HumanDecision`.
- Produces: `scopeproof resolve REVIEW_ID --criterion-id ID --decision DECISION --reviewer NAME [--comment-file PATH] [--evidence-url URL]`.

- [x] **Step 1: Add failing success and rejection tests**

Create a saved `ReviewState` from `build_demo_review()`, then assert:

```python
assert main([
    "resolve", review_id,
    "--criterion-id", "AC-01",
    "--decision", "accepted",
    "--reviewer", "Reviewer",
    "--comment-file", str(comment_file),
    "--storage-dir", str(store),
]) == 0
payload = json.loads(capsys.readouterr().out)
assert payload["review_id"] == review_id
assert payload["event_id"]
assert JsonReviewStore(store).load(review_id).bundle.resolutions[0].reviewer == "Reviewer"
```

Also assert `manually_verified` is rejected before persistence and low-evidence `accepted` requires a nonblank comment.

- [x] **Step 2: Run focused CLI tests and verify RED**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'resolve_command'`

Expected: argparse rejects unknown command `resolve`.

- [x] **Step 3: Add shared CLI helpers and parser**

Implement private helpers with these signatures:

```python
def _read_optional_comment(path: str | None) -> str: ...
def _mutation_metadata(state: ReviewState, path: Path, event_id: str) -> dict[str, object]: ...
def _resolve(args: argparse.Namespace) -> int: ...
```

The handler must load one validated state, validate the requested criterion and low-evidence note policy, construct `ResolutionEvent`, call `append_resolution`, save only the returned state, and print sorted JSON containing `review_id`, `record`, `head_sha`, `event_id`, `verdict`, and `gate_reason_codes`.

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'resolve_command'`

Expected: PASS.

- [x] **Step 5: Run lifecycle and storage regressions**

Run: `uv run pytest -q tests/cli/test_cli.py tests/reviews/test_lifecycle.py tests/storage/test_json_store.py`

Expected: PASS.

---

### Task 4: Add Atomic Runtime Verification CLI Command

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `append_external_verification`, `RuntimeEvidence`, `ResolutionEvent`, `EvidenceLevel`, active review identity.
- Produces: `scopeproof verify-runtime REVIEW_ID` with required E3/E4 runtime fields and repeatable limitations.

- [x] **Step 1: Write failing atomic success and failure tests**

Test that one command creates a shared UUID-backed runtime record and manual-resolution event. Capture the record bytes before invalid E2, blank comment, unknown criterion, and malformed input attempts; assert the bytes remain identical afterward.

- [x] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'verify_runtime_command'`

Expected: argparse rejects unknown command `verify-runtime`.

- [x] **Step 3: Implement the minimal handler**

Use one generated UUID:

```python
runtime_id = str(uuid4())
evidence = RuntimeEvidence(
    runtime_evidence_id=runtime_id,
    repository=state.review.repository,
    pr_number=state.review.pr_number,
    head_sha=state.review.head_sha,
    criterion_id=args.criterion_id,
    artifact_reference=args.artifact_reference,
    scenario=args.scenario,
    environment=args.environment,
    result=args.result,
    reviewer=args.reviewer.strip(),
    evidence_level=EvidenceLevel(args.level),
    limitations=args.limitation,
)
event = ResolutionEvent(
    criterion_id=args.criterion_id,
    decision=HumanDecision.MANUALLY_VERIFIED,
    comment=_read_required_comment(args.comment_file),
    claimed_evidence_level=evidence.evidence_level,
    runtime_evidence_id=runtime_id,
    reviewer=evidence.reviewer,
)
updated = append_external_verification(state, evidence, event)
```

Save only after every constructor and lifecycle validation succeeds.

- [x] **Step 4: Run focused and lifecycle tests**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'verify_runtime_command' tests/reviews/test_lifecycle.py -k 'external_verification'`

Expected: PASS.

---

### Task 5: Add Final Acceptance and Revocation CLI Command

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: `append_resolution`, `can_record_final_acceptance`, final `ResolutionEvent`.
- Produces: `scopeproof final-acceptance REVIEW_ID (--accept | --revoke) --reviewer NAME [--comment-file PATH]`.

- [x] **Step 1: Write failing tests for acceptance, revocation, and atomic prerequisite failure**

Assert acceptance completes only a fully resolved eligible state; revoke appends a false final event; premature acceptance produces argparse error code 2 and leaves the saved record byte-for-byte unchanged.

- [x] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'final_acceptance_command'`

Expected: argparse rejects unknown command `final-acceptance`.

- [x] **Step 3: Implement the handler and mutually exclusive parser flags**

Construct:

```python
event = ResolutionEvent(
    final_acceptance=args.accept,
    reviewer=args.reviewer.strip(),
    comment=_read_optional_comment(args.comment_file),
)
updated = append_resolution(state, event)
```

Do not pre-mutate the loaded state; rely on core lifecycle validation before saving.

- [x] **Step 4: Run focused and full CLI lifecycle tests**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'final_acceptance_command' tests/reviews/test_lifecycle.py -k 'final_acceptance'`

Expected: PASS.

---

### Task 6: Add Validated Review Comparison CLI Command

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: two validated `ReviewState` records, active `ReviewBundle` objects, `compare_reviews`, `export_comparison_json`, `export_comparison_markdown`.
- Produces: `scopeproof compare PREVIOUS_REVIEW_ID CURRENT_REVIEW_ID [--format json|markdown] [--output PATH] [--storage-dir PATH]`.

- [x] **Step 1: Write failing stdout, output, no-overwrite, and missing-bundle tests**

Assert JSON is Pydantic-valid and deterministic, Markdown includes both immutable heads and the evidence boundary, an existing output path is never overwritten, and neither source review is mutated.

- [x] **Step 2: Run focused tests and verify RED**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'compare_command'`

Expected: argparse rejects unknown command `compare`.

- [x] **Step 3: Implement renderer selection and no-overwrite output**

```python
COMPARISON_RENDERERS = {
    "json": export_comparison_json,
    "markdown": export_comparison_markdown,
}
comparison = compare_reviews(previous.bundle, current.bundle)
rendered = COMPARISON_RENDERERS[args.format](comparison)
if args.output:
    with Path(args.output).open("x", encoding="utf-8") as handle:
        handle.write(rendered)
else:
    print(rendered, end="")
```

Reject states without an active bundle before attempting comparison.

- [x] **Step 4: Run focused CLI and comparison tests**

Run: `uv run pytest -q tests/cli/test_cli.py -k 'compare_command' tests/reviews/test_comparison.py tests/reporting/test_comparison_exports.py`

Expected: PASS.

---

### Task 7: Add an Installed-wheel Playwright Browser Contract

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/browser/test_packaged_workbench.py`
- Modify: `tests/test_repository_contracts.py`
- Create: `docs/audits/post-release-cli-browser/verification.md`

**Interfaces:**
- Consumes: installed `scopeproof-web`, bundled constructed demo, Chromium installed from the locked Playwright version.
- Produces: pytest marker `browser` and a real-browser installed-wheel primary-path regression at desktop and narrow viewports.

- [x] **Step 1: Add failing dependency and CI contract tests**

Assert that:

```python
assert 'playwright' in pyproject["project"]["optional-dependencies"]["dev"]
assert 'playwright' not in pyproject["project"]["dependencies"]
assert "browser: installed-wheel real-browser regression" in pytest_markers
assert "python -m playwright install --with-deps chromium" in ci
assert "pytest -q -m browser" in ci
```

Also require CI to execute the browser marker only after the installed-wheel smoke.

- [x] **Step 2: Run repository contracts and verify RED**

Run: `uv run pytest -q tests/test_repository_contracts.py`

Expected: FAIL because Playwright, the browser marker, and CI browser step are absent.

- [x] **Step 3: Add locked development dependency and marker**

Add a bounded Playwright dependency under `project.optional-dependencies.dev`, add the `browser` marker, and refresh `uv.lock` with `uv lock`.

- [x] **Step 4: Add the installed-wheel browser fixture and path**

The test must build a wheel into `tmp_path`, create an isolated virtual environment, install the wheel plus the locked Playwright package, start `scopeproof-web` with temporary `HOME` and storage, and drive Chromium over loopback. It must collect console errors and page errors, use the constructed demo without GitHub networking, confirm criteria, run analysis, inspect evidence/missing-evidence/status, and confirm Markdown/JSON/CSV export controls.

For each viewport:

```python
for viewport in ({"width": 1280, "height": 720}, {"width": 390, "height": 844}):
    page.set_viewport_size(viewport)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
```

Keyboard activation is required only for stable accessible controls exposed by the installed Streamlit version. Native browser zoom, screen-reader operation, Windows, Linux desktop, and Python 3.13 remain explicitly unverified.

- [x] **Step 5: Update CI without renaming the protected `verify` job**

Install the locked Chromium owned by Playwright and run `pytest -q -m browser` after existing wheel smoke. Keep every third-party Action SHA-pinned.

- [x] **Step 6: Run contracts and browser test locally**

Run: `uv run pytest -q tests/test_repository_contracts.py`

Run: `uv run playwright install chromium`

Run: `uv run pytest -q -m browser`

Expected: both PASS, with zero console/page errors and clean process teardown.

- [x] **Step 7: Record bounded browser evidence**

Document exact commit/tree under test, environment, commands, viewport results, accessible-control coverage, and unsupported rows. State that browser automation is engineering runtime evidence for ScopeProof itself, not target-repository runtime verification or Stage 1 validation.

---

### Task 8: Perform Provably Safe Worktree Hygiene

**Files:**
- No product files.

**Interfaces:**
- Consumes: registered worktree path, clean status, branch merge ancestry, and remote-branch absence.
- Produces: removal only of worktrees satisfying every guard, using normal worktree removal and non-force branch deletion.

- [x] **Step 1: Inventory every registered worktree read-only**

For each worktree, record path, branch, `git status --porcelain`, `git merge-base --is-ancestor <branch> main`, and `git ls-remote --heads origin <branch>`.

- [x] **Step 2: Exclude every protected or ambiguous target**

Always preserve the root worktree, R-002 worktree, re-review worktree, `codex/evidence-integrity-hotfix`, dirty worktrees, unmerged branches, and standalone nested repositories.

- [x] **Step 3: Remove only exact eligible paths**

For each proven eligible path, run `git worktree remove <exact-path>`, then `git branch -d <exact-branch>`. Do not use force flags or broad globs.

- [x] **Step 4: Re-list worktrees and report preserved/removed targets**

Run: `git worktree list --porcelain`

Expected: all protected and ambiguous targets remain registered and unchanged.

---

### Task 9: Full Verification and Evidence-bound Handoff

**Files:**
- Modify: `docs/audits/post-release-cli-browser/verification.md`

**Interfaces:**
- Consumes: complete branch diff.
- Produces: PR-ready local branch evidence without commit, push, PR, release, issue mutation, or outreach.

- [x] **Step 1: Run lint and full coverage gate**

Run: `uv run ruff check .`

Run: `uv run pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q`

Expected: PASS with coverage at least 95% and only the intentional live-GitHub skip.

- [x] **Step 2: Run deterministic benchmarks and contracts**

Run: `uv run scopeproof benchmark`

Run: `uv run scopeproof comparison-benchmark`

Run: `uv run pytest -q tests/test_repository_contracts.py`

Expected: zero mismatches, zero must-have False Ready cases, contracts PASS.

- [x] **Step 3: Build and inspect packages**

Run: `uv build`

Inspect wheel and sdist inventories; reject `.git`, `.scopeproof`, coverage files, credentials, private data, or Playwright as a runtime dependency.

- [x] **Step 4: Run isolated installed-product smokes**

Install the wheel into a fresh Python environment and run version checks, both benchmarks, CLI resolution/runtime/final/comparison smoke using constructed local data, workbench health, packaged browser regression, and process-group cleanup.

- [x] **Step 5: Run diff and secret/path hygiene**

Run: `git diff --check`

Run bounded scans over changed files for credential patterns, private paths, generated caches, `.coverage 2`, and accidental target-repository content.

- [x] **Step 6: Obtain an independent complete-diff review**

The reviewer must inspect spec compliance, core/CLI separation, atomic persistence, False Ready risk, browser evidence boundaries, packaging, CI ordering, and documentation truth. Fix every confirmed Critical or Important finding and rerun affected plus full verification.

- [x] **Step 7: Finalize the verification record and handoff**

Record exact branch, HEAD/tree, changed files, commands/results, evidence boundaries, unsupported environments, Stage 1 zero counts, external gates, and the single next safe action. Provide a recommended commit message and PR description, but do not publish.
