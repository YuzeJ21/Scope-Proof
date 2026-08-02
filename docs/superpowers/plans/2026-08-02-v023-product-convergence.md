# ScopeProof v0.2.3 Product Convergence Implementation Plan

> **Execution contract:** Implement each task with strict red-green-refactor cycles.
> Do not weaken evidence rules to make tests pass. Commit each completed task separately,
> review it against the design, and run the named verification before proceeding.

**Goal:** Deliver a cleaner, coherent ScopeProof experience, bind every new criteria
confirmation to deterministic source-snapshot provenance, align the v0.2.3 operational
documents and Action example, and merge the verified result to protected `main` without
publishing a release or creating Stage 1 claims.

**Architecture:** Keep evidence and lifecycle logic in `scopeproof_core`. Streamlit remains
an orchestration/presentation layer. Put source-provenance hashing and validation in the
criteria package, carry the immutable record through `Review` and `CriteriaRevision`, and
enforce equality at model/lifecycle/storage/export boundaries. Presentation cleanup uses
supported Streamlit theme settings plus bounded CSS and progressive disclosure; it never
changes gate behavior.

**Tech stack:** Python 3.12, Pydantic v2, Streamlit, pytest/AppTest, Ruff, uv, static HTML/CSS,
GitHub Actions.

**Design:**
`docs/superpowers/specs/2026-08-02-v023-product-convergence-design.md`

---

### Task 1: Modernize and simplify the product surfaces

**Files:**

- Create: `.streamlit/config.toml`
- Modify: `apps/web/launcher.py`
- Modify: `apps/web/app.py`
- Modify: `site/index.html`
- Modify: `site/styles.css`
- Modify: `tests/apps/test_web_launcher.py`
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `tests/test_repository_contracts.py`

**Step 1: Add failing launcher and static visual-system contracts**

Extend `tests/apps/test_web_launcher.py` to require the supported theme arguments after
the existing server arguments and before the app path. Extend repository contracts to
require matching source-run theme values, preserved focus-visible treatment, the public
alpha primary/secondary/tertiary hierarchy, all existing URLs, and the safety boundary.

Run:

```bash
uv run pytest -q tests/apps/test_web_launcher.py tests/test_repository_contracts.py
```

Expected: FAIL because theme configuration and the new public-page hierarchy are absent.

**Step 2: Add a failing AppTest for progressive matrix filtering**

Add an AppTest that reaches the evidence matrix, finds a collapsed expander labelled
`Filter evidence matrix (optional)`, and proves it owns the existing keys
`status_filter`, `priority_filter`, `blocking_only`, and `evidence_level_filter` with
unchanged defaults and options.

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k "matrix_filter"
```

Expected: FAIL because the four controls are still top-level.

**Step 3: Implement the supported theme and bounded presentation layer**

Add the matching dark/lime/cyan theme to `.streamlit/config.toml` and the packaged launcher.
Expand the existing focus CSS in `apps/web/app.py` only with stable Streamlit test IDs and
semantic HTML selectors for content width, rhythm, headings, buttons, expanders, surfaces,
and reduced motion. Do not hide built-in navigation, warnings, labels, controls, or evidence.

**Step 4: Implement hierarchy cleanup**

Wrap the four matrix filters in one collapsed expander without changing widget keys or
filter logic. Rework only the public-alpha action markup and CSS so the case form is primary,
quickstart is secondary, and the remaining three links are inline resources with the outcome
form explicitly post-review. Preserve all URLs and safety copy.

**Step 5: Verify and commit**

Run:

```bash
uv run pytest -q tests/apps/test_web_launcher.py tests/apps/test_streamlit_app.py \
  tests/test_repository_contracts.py
uv run ruff check apps/web/launcher.py apps/web/app.py tests/apps/test_web_launcher.py \
  tests/apps/test_streamlit_app.py tests/test_repository_contracts.py
git diff --check
```

Commit:

```bash
git add .streamlit/config.toml apps/web/launcher.py apps/web/app.py site/index.html \
  site/styles.css tests/apps/test_web_launcher.py tests/apps/test_streamlit_app.py \
  tests/test_repository_contracts.py
git commit -m "feat: refresh ScopeProof product surfaces"
```

### Task 2: Add typed criteria-source provenance and deterministic gates

**Files:**

- Modify: `scopeproof_core/schemas/models.py`
- Modify: `scopeproof_core/criteria/confirmation.py`
- Modify: `scopeproof_core/gates/evaluator.py`
- Modify: `scopeproof_core/gates/validation.py`
- Modify: `tests/criteria/test_confirmation.py`
- Modify: `tests/schemas/test_models.py`
- Modify: `tests/schemas/test_review_state_integrity.py`
- Modify: `tests/gates/test_evaluator.py`
- Modify: `tests/gates/test_validation.py`

**Step 1: Add failing provenance-model and digest tests**

Specify `CriteriaSourceProvenance` as frozen and extra-forbid. Test valid HTTPS and the
single constructed-demo URI, field normalization, blank/invalid values, lowercase 64-character
digests, timezone-aware UTC confirmation, deterministic source-text digest, deterministic
canonical-criteria digest, and rejection when either observed payload no longer matches.

Run:

```bash
uv run pytest -q tests/criteria/test_confirmation.py tests/schemas/test_models.py
```

Expected: FAIL because the model and helpers do not exist.

**Step 2: Implement the pure provenance model and helpers**

Implement canonical hashing without network access. The helper must accept validated
`Criterion` objects, canonicalize all criterion fields deterministically, and return one
immutable record. Validation must use stable messages and never mutate inputs.

Add optional `criteria_source_provenance` to `Review` for legacy decode and optional
`source_provenance` to `CriteriaRevision`. Reject confirmed revisions whose supplied
provenance does not match their source text and criteria. Add `ReviewState` equality checks
between the active revision and active bundle review.

**Step 3: Add failing gate tests**

Prove a formerly Ready-shaped review without provenance returns `Needs Review` and
`criteria_source_provenance_missing`; a valid provenance preserves existing outcomes; and
typed contradictions are rejected before deterministic evaluation. Update explicit Ready
fixtures to supply real provenance rather than weakening assertions.

**Step 4: Implement gate enforcement**

Make the evaluator fail closed on missing provenance. Keep reason-code ordering deterministic
and preserve higher-severity failing-check/blocking-criterion precedence. Revalidation must
recompute and compare the same gate.

**Step 5: Verify and commit**

Run:

```bash
uv run pytest -q tests/criteria/test_confirmation.py tests/schemas/test_models.py \
  tests/schemas/test_review_state_integrity.py tests/gates/test_evaluator.py \
  tests/gates/test_validation.py
uv run ruff check scopeproof_core/schemas/models.py \
  scopeproof_core/criteria/confirmation.py scopeproof_core/gates/evaluator.py \
  scopeproof_core/gates/validation.py tests/criteria/test_confirmation.py \
  tests/schemas/test_models.py tests/schemas/test_review_state_integrity.py \
  tests/gates/test_evaluator.py tests/gates/test_validation.py
git diff --check
```

Commit the named files with `feat: bind criteria to source snapshots`.

### Task 3: Enforce provenance through lifecycle and local record migration

**Files:**

- Modify: `scopeproof_core/reviews/lifecycle.py`
- Modify: `scopeproof_core/storage/json_store.py`
- Modify: `tests/reviews/test_lifecycle.py`
- Modify: `tests/storage/test_json_store.py`
- Modify: `tests/schemas/test_review_state_integrity.py`

**Step 1: Add failing lifecycle tests**

Cover new-state creation, criteria revision, reconfirmation with a newly validated snapshot,
analysis attachment, final-acceptance eligibility, and tampered source/criteria digest
rejection. Prove revising criteria clears provenance and retains prior bundle provenance only
as immutable history.

Run the focused tests and capture the expected failures.

**Step 2: Implement lifecycle propagation**

Change `confirm_criteria` to require a `CriteriaSourceProvenance`. Ensure `new_review_state`
requires and copies bundle review provenance, `revise_criteria` clears it, `attach_analysis`
requires exact equality, and `can_record_final_acceptance` returns false without it. Update
all core callers with explicit validated values.

**Step 3: Add failing v4 migration tests**

Prove v4 save/load round trips exact provenance. For v1–v3 fixtures, prove migration invents
nothing, recomputes active and historical gates as missing-provenance `Needs Review`, and
is deterministic/idempotent. Preserve historical evidence, events, source text, and attribution.

**Step 4: Implement v4 persistence**

Bump `RECORD_VERSION` and supported versions. Add one conservative migration path that inserts
no provenance and recomputes affected gates. Do not silently delete evidence or fabricate an
owner, URL, digest, revision, or time.

**Step 5: Verify and commit**

Run focused lifecycle/storage/schema tests, Ruff on changed files, and `git diff --check`.
Commit the named files with `feat: enforce criteria provenance lifecycle`.

### Task 4: Carry provenance through CLI and trusted-base Action flows

**Files:**

- Modify: `scopeproof_core/cli.py`
- Modify: `.github/workflows/scopeproof.yml`
- Modify: `examples/github-actions/scopeproof.yml`
- Modify: `.scopeproof/requirements-confirmation.json`
- Modify: `tests/cli/test_cli.py`
- Modify: `tests/github_action/test_workflow_files.py`
- Modify: `tests/github_action/test_contract.py`
- Modify: `tests/github_action/test_runner.py`

**Step 1: Add failing CLI tests**

Require `scopeproof review --confirmation FILE`. Prove a missing, changed, or malformed
confirmation fails before GitHub fetch or fixture analysis; a valid confirmation is persisted
and emitted in metadata; and the validation command prints the new typed shape. Retain the
no-network confirmation validator.

**Step 2: Implement CLI propagation**

Validate requirements text, parsed criteria, and the confirmation artifact before source
ingestion. Pass the immutable provenance into `_build_bundle` and the review. Never infer a
confirmation from the presence of a requirements file.

**Step 3: Add failing workflow contracts**

Prove both workflows pass `--confirmation` into `review`, keep trusted-base checkout,
never execute PR-head code, and remain informational. Update the repository's own confirmation
record with real computed digests and source identity.

**Step 4: Implement Action flow**

Propagate the already validated confirmation file to the review command. Preserve current
permissions, SHA-pinned third-party actions, fork-safe publication boundary, and non-required
status.

**Step 5: Verify and commit**

Run CLI and GitHub Action suites plus Ruff and diff checks. Commit the named files with
`feat: require provenance in automated reviews`.

### Task 5: Expose provenance in reports and alpha evidence

**Files:**

- Modify: `scopeproof_core/reporting/exporters.py`
- Modify: `scopeproof_core/alpha/models.py`
- Modify: `scopeproof_core/alpha/service.py`
- Modify: `scopeproof_core/alpha/storage.py`
- Modify: `tests/reporting/test_exporters.py`
- Modify: `tests/reporting/test_lifecycle_exports.py`
- Modify: `tests/alpha/test_models.py`
- Modify: `tests/alpha/test_service.py`
- Modify: `tests/alpha/test_storage.py`
- Modify: `tests/cli/test_cli.py`

**Step 1: Add failing export tests**

Require exact source reference, optional revision, both digests, confirmer, and timestamp in
JSON, Markdown, HTML, and CSV. Prove tampering or current missing provenance is rejected with
a stable message; no token or untrusted HTML is introduced.

**Step 2: Implement report rendering**

Render one compact Criteria Source section in Markdown/HTML and deterministic columns in CSV.
Continue validating every export input at the trust boundary.

**Step 3: Add failing alpha tests**

Require new alpha cases to retain the same provenance and require its HTTPS source URI to
match `requirements_source_url`. Prove old records remain readable as legacy but cannot be
newly completed without reconfirmed provenance. Cover storage round trip and public summary
non-disclosure.

**Step 4: Implement alpha compatibility**

Carry the shared object through initialize/ensure/outcome transitions. Do not invent fields
when loading old records. Update CLI alpha initialization to use the validated confirmation
artifact rather than a separate unbound criteria path.

**Step 5: Verify and commit**

Run reporting, lifecycle-export, alpha, and affected CLI tests; run Ruff and diff checks.
Commit the named files with `feat: export criteria source provenance`.

### Task 6: Integrate compact provenance confirmation into the workbench

**Files:**

- Modify: `apps/web/app.py`
- Modify: `scopeproof_core/demo.py`
- Modify: `tests/apps/test_streamlit_app.py`
- Modify: `tests/demo/test_demo.py`

**Step 1: Add failing workbench tests**

Cover:

- standard review requires source reference and confirmer before confirmation;
- optional revision normalization;
- demo preloads its explicit constructed-source URI;
- alpha mode reuses the already-entered public requirements URL;
- confirming computes/persists both digests and UTC time;
- changing source text, normalized criteria, source reference, revision, or confirmer requires
  reconfirmation and disables analysis;
- invalid input causes no review mutation;
- reopened legacy records explain missing provenance and cannot export or final-accept; and
- confirmed provenance is visible in a compact, collapsed details panel.

Run the focused tests and record the expected failures.

**Step 2: Implement session and form state**

Add only the necessary source reference, optional revision, and confirmer controls. Reuse the
alpha qualification URL and demo source URI; never ask twice for the same fact. Build the
typed snapshot only inside the explicit confirmation action. Clear it through existing draft
and revision reset paths when any bound input changes.

**Step 3: Propagate to analysis, persistence, export, and alpha**

Pass the snapshot into lifecycle and alpha services, expose the immutable confirmation summary,
and ensure existing autosave/pending-input guards continue to protect authoritative state.
Keep all existing keys stable unless a new key is required for a genuinely new field.

**Step 4: Verify and commit**

Run the full Streamlit AppTest file, demo tests, relevant lifecycle/export/alpha focused tests,
Ruff, and diff checks. Commit the named files with `feat: capture criteria provenance in workbench`.

### Task 7: Align Action pin, v0.2.3 status, and roadmap truth

**Files:**

- Modify: `examples/github-actions/scopeproof.yml`
- Modify: `docs/github-action.md`
- Modify: `tests/test_repository_contracts.py`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md`
- Modify: `docs/releases/v0.2.3-internal-candidate.md`
- Modify: `docs/releases/v0.2.3-post-merge-release-readiness.md`
- Modify: `docs/releases/v0.2.3-pr-review-map.md`

**Step 1: Add a failing pin-consistency contract**

Parse the exact full source pin from the copyable workflow and require the guide to show the
same pin. Require the pin to include the already-merged exact-head integrity product commit
`2a320df966eff30c05a2b1dce607a247201fa165`, pending a later final-release repin.

**Step 2: Update factual release and roadmap state**

Record PR #181 and merge `eaa66c5979e2a71769d58f0699537da474094d06` as completed docs
alignment with green CI/CodeQL/Pages, while explicitly saying it is not packaged release-tree
evidence. Add the new convergence features to the unreleased v0.2.3 ledger and state that they
create zero Stage 1 credit. Remove stale next-action language only where the action is already
complete.

Keep README, public Pages, and install guidance on v0.2.1. Keep v0.2.3 tagging/publication as
a separate decision after final release-tree assets and checksums.

**Step 3: Verify and commit**

Run repository contracts, relevant workflow tests, Markdown/link/static checks available in
the repository, Ruff if Python tests changed, and `git diff --check`. Commit the named files
with `docs: align v0.2.3 product and release truth`.

### Task 8: Integrated engineering and browser verification

**Files:**

- Create: `docs/audits/v0.2.3-product-convergence/verification.md`
- Modify only if a verified defect is found: files owned by Tasks 1–7 plus their regression
  tests.

**Step 1: Run the complete locked verification matrix**

Run:

```bash
uv sync --extra dev --extra research --locked
uv run ruff check .
uv run pytest -q
uv run coverage run -m pytest -q
uv run coverage report --fail-under=95
uv run scopeproof benchmark --json
uv run scopeproof comparison-benchmark --json
uv build
git diff --check origin/main...HEAD
git status --short
```

Also run the repository's documented clean-install, installed-version, installed benchmark,
package-inventory, workbench-health, Action contract, and source-tree hygiene commands against
the exact branch head. Record exact outputs and evidence limitations.

**Step 2: Perform browser visual and interaction QA**

Launch the packaged workbench from the branch. Capture and inspect current-run screenshots for
start, confirmed criteria, matrix, summary/export, desktop public Pages, and one narrow viewport
where supported. Verify primary path clarity, no clipped controls, visible safety copy, keyboard
focus evidence that the available browser can actually observe, and matching visual tokens.

Screenshots are visual evidence only; do not call them full accessibility or cross-platform
proof.

**Step 3: Fix verified defects test-first**

For any defect, first add a focused failing regression, then make the smallest fix and rerun
the affected focused suite plus the complete required matrix. Do not add unrelated features.

**Step 4: Record and commit evidence**

Write the exact-tree verification report with commands, counts, hashes, browser states, known
unsupported rows, release boundary, and zero-Stage-1 statement. Commit only the report and any
test-first fixes with named staging.

### Task 9: Review, publish PR, and merge protected main

**Files:** None unless review or CI identifies a verified defect.

**Step 1: Run independent branch review**

Request a spec-compliance review and a code-quality/evidence-integrity review across
`origin/main...HEAD`. Address every Critical or Important finding with a failing regression,
small fix, focused verification, and re-review.

**Step 2: Push and create the PR**

Confirm only intended files are committed, push `codex/v023-product-convergence`, and create a
ready PR that summarizes product cleanup, criteria provenance, release alignment, exact
verification, and the explicit no-release/no-Stage-1 boundary. Do not add the ScopeProof Action
label or trigger product-comment workflows.

**Step 3: Wait for required checks and merge**

Wait for protected-main required checks (`verify` and `CodeQL`) plus Pages if triggered. Diagnose
any failure from exact logs, fix test-first on the branch, and repeat until green. Merge using the
repository's normal merge method; do not bypass protection or force push.

**Step 4: Verify merged main**

Fetch and confirm local/remote `main` point to the merge result, no PR remains open, and exact
merged-main checks are green. Confirm public release remains v0.2.1 and v0.2.3 remains untagged
unless the owner separately authorizes publication. Leave the user-owned root `.coverage 2`
untouched and remove only disposable branch preview processes/worktrees created by this task.

Report the merged commit, PR, checks, product changes, exact remaining evidence-gated gaps, and
why Stage 1–4 status did not change.
