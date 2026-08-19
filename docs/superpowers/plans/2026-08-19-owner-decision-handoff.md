# Owner Decision Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put unresolved blockers first and render the selected criterion evidence and decision controls before the optional global evidence matrix.

**Architecture:** Add a pure stable-partition presentation helper, use it in the Streamlit workbench, and move the existing matrix block without changing its widgets or business logic. Keep all review lifecycle, gate, schema, storage, export, and GitHub integration code unchanged; align only the authoritative current-state documents with merged PR #197 evidence.

**Tech Stack:** Python 3.11+, Streamlit AppTest, Playwright 1.62.0, Pytest, Pydantic, Ruff, uv

**Spec:** `docs/superpowers/specs/2026-08-19-owner-decision-handoff-design.md`

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Users confirm normalized acceptance criteria before analysis.
- Never execute target-repository code.
- Static implementation or test candidates are not runtime verification.
- Every persisted or exported object remains Pydantic-validated.
- Gate decisions remain deterministic and fail closed; False Ready is more harmful than False Blocked.
- Do not change core gate, evidence-level, decision, final-acceptance, schema, storage, export, comparison, or GitHub Action behavior.
- Reviewer identity remains asserted, not authenticated; the GitHub Action remains opt-in and informational.
- Preserve `.coverage 2` exactly and never stage, modify, delete, rename, or package it.
- Stage 1 remains `closed_not_pursued_by_owner` at 0/5, 0/3, 0/3, 0/3, and 0/2.
- This branch is Stage 2 engineering evidence only and does not authorize merge, release, tag, publication, deployment, outreach, R-002 retuning, R-003 generation, or Stage 3.

---

### Task 1: Stable unresolved-criterion priority

**Files:**
- Modify: `apps/web/view_models.py:30-53`
- Test: `tests/apps/test_streamlit_app.py:1-15,3998-4013`

**Interfaces:**
- Consumes: ordered unresolved criterion IDs and the deterministic gate's blocking-ID set.
- Produces: `prioritize_unresolved_criterion_ids(*, unresolved_ids: list[str], blocking_ids: set[str]) -> list[str]` and blocker-first fallback behavior from `default_criterion_detail_id(...)`.

- [ ] **Step 1: Add failing presentation-model tests**

Import the new helper beside `default_criterion_detail_id`, then add:

```python
def test_unresolved_criterion_priority_stably_places_blockers_first() -> None:
    assert prioritize_unresolved_criterion_ids(
        unresolved_ids=["AC-01", "AC-02", "AC-03", "AC-04"],
        blocking_ids={"AC-02", "AC-03"},
    ) == ["AC-02", "AC-03", "AC-01", "AC-04"]
```

Rename `test_empty_detail_target_defaults_to_first_criterion` to
`test_empty_detail_target_defaults_to_first_unresolved_blocker` and change its
literal expected value from `"AC-01"` to `"AC-02"`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_unresolved_criterion_priority_stably_places_blockers_first \
  tests/apps/test_streamlit_app.py::test_empty_detail_target_defaults_to_first_unresolved_blocker \
  -q
```

Expected: collection fails because `prioritize_unresolved_criterion_ids` does not
exist, or the new default assertion fails with `AC-01 != AC-02`. Both failures name
the missing presentation behavior.

- [ ] **Step 3: Implement the minimal pure presentation behavior**

Add to `apps/web/view_models.py`:

```python
def prioritize_unresolved_criterion_ids(
    *, unresolved_ids: list[str], blocking_ids: set[str]
) -> list[str]:
    """Return blockers first while preserving order within both groups."""

    return [
        *(criterion_id for criterion_id in unresolved_ids if criterion_id in blocking_ids),
        *(criterion_id for criterion_id in unresolved_ids if criterion_id not in blocking_ids),
    ]
```

In `default_criterion_detail_id`, preserve a valid `selected_id`, then use the
existing blocker → unresolved → criterion fallback for both absent and invalid
selections by removing the special `selected_id is None` return.

- [ ] **Step 4: Run focused tests and presentation-model coverage**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_unresolved_criterion_priority_stably_places_blockers_first \
  tests/apps/test_streamlit_app.py::test_empty_detail_target_defaults_to_first_unresolved_blocker \
  tests/apps/test_streamlit_app.py::test_invalid_detail_target_defaults_to_first_unresolved_blocker \
  -q
uv run ruff check apps/web/view_models.py tests/apps/test_streamlit_app.py
```

Expected: all three tests pass and Ruff exits zero.

- [ ] **Step 5: Commit the presentation model intentionally**

```bash
git add -- apps/web/view_models.py tests/apps/test_streamlit_app.py
git commit -m "feat: prioritize unresolved blocker decisions"
```

---

### Task 2: Direct queue-to-decision layout

**Files:**
- Modify: `apps/web/app.py:55-75,1925-2840`
- Test: `tests/apps/test_streamlit_app.py:576-586,2262-2291`
- Test: `tests/browser/test_packaged_workbench.py:226-275`

**Interfaces:**
- Consumes: `prioritize_unresolved_criterion_ids(...)` from Task 1, existing session key `selected_criterion`, existing matrix filter keys, and existing review lifecycle functions.
- Produces: numbered section order `Start Review`, `Confirm Criteria`, `Decision Progress`, `Criterion Review`, `Evidence Matrix`, `Summary & Export`; queue/detail widgets preceding matrix widgets in rendered order.

- [ ] **Step 1: Add failing Streamlit behavior regressions**

Update `test_workbench_heading_order_uses_one_h1_and_numbered_h2_sections` to
expect these literal headers:

```python
[
    "1 · Start Review",
    "2 · Confirm Criteria",
    "3 · Decision Progress",
    "4 · Criterion Review",
    "5 · Evidence Matrix",
    "6 · Summary & Export",
]
```

In `test_evidence_matrix_has_compact_strength_summary_and_unresolved_queue`, add:

```python
queue_keys = [
    button.key
    for button in app.button
    if button.key is not None and button.key.startswith("inspect_queue_")
]
assert queue_keys == [
    "inspect_queue_AC-02",
    "inspect_queue_AC-03",
    "inspect_queue_AC-01",
    "inspect_queue_AC-04",
]

main_nodes = list(app.main)
node_positions = {
    node.key: index
    for index, node in enumerate(main_nodes)
    if node.key in {
        "inspect_queue_AC-02",
        "selected_criterion",
        "resolution_decision",
        "status_filter",
    }
}
assert node_positions["inspect_queue_AC-02"] < node_positions["selected_criterion"]
assert node_positions["selected_criterion"] < node_positions["resolution_decision"]
assert node_positions["resolution_decision"] < node_positions["status_filter"]
```

Keep the existing click and `selected_criterion == "AC-02"` assertion.

- [ ] **Step 2: Run the focused AppTests and verify RED**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_workbench_heading_order_uses_one_h1_and_numbered_h2_sections \
  tests/apps/test_streamlit_app.py::test_evidence_matrix_has_compact_strength_summary_and_unresolved_queue \
  -q
```

Expected: the header expectation fails at `3 · Evidence Matrix`, queue ordering
starts with `inspect_queue_AC-01`, and `status_filter` occurs before the decision
widgets.

- [ ] **Step 3: Apply the blocker-first queue and section labels**

Import `prioritize_unresolved_criterion_ids` from `apps.web.view_models`. Keep the
existing source-order unresolved derivation, then replace `unresolved_ids` with:

```python
unresolved_ids = prioritize_unresolved_criterion_ids(
    unresolved_ids=unresolved_ids,
    blocking_ids=blocking_criteria,
)
```

Rename the numbered headers exactly:

```python
st.header("3 · Decision Progress")
st.header("4 · Criterion Review")
st.header("5 · Evidence Matrix")
st.header("6 · Summary & Export")
```

- [ ] **Step 4: Move the existing global matrix block without rewriting it**

Move the current block beginning with the caption
`Evidence status describes deterministic candidates` and ending with the
`inspect_matrix_<criterion>` button handling so it renders after the selected
criterion two-column block and recorded runtime-evidence expander, immediately
before final review acceptance. Prepend `st.header("5 · Evidence Matrix")` at the
new location.

Do not rename or duplicate matrix filter keys, card-selection keys, the resolution
form, runtime-evidence form, lifecycle calls, or save/rerun ordering. The selected
criterion block remains one copy and executes before the moved matrix.

- [ ] **Step 5: Run focused AppTests and the affected app slice**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_workbench_heading_order_uses_one_h1_and_numbered_h2_sections \
  tests/apps/test_streamlit_app.py::test_evidence_matrix_has_compact_strength_summary_and_unresolved_queue \
  tests/apps/test_streamlit_app.py::test_summary_offers_direct_next_unresolved_action \
  tests/apps/test_streamlit_app.py::test_evidence_matrix_cards_explain_and_open_each_criterion \
  tests/apps/test_streamlit_app.py::test_criterion_resolution_context_identifies_target_and_boundary \
  tests/apps/test_streamlit_app.py::test_manual_verification_is_only_available_through_external_verification \
  -q
```

Expected: all tests pass with the same selected criterion, gate, and persistence
behavior.

- [ ] **Step 6: Add the failing installed-browser handoff regression**

In `_exercise_primary_path`, replace the queue summary-link-only check with a
keyboard activation of the `Open AC-02 decision controls` button. Assert the
criterion selectbox has `AC-02`, the Human decision combobox is visible, and it
precedes the matrix filter in DOM order:

```python
open_ac_02 = page.get_by_role(
    "button", name="Open AC-02 decision controls", exact=True
)
_activate_with_keyboard(
    page,
    open_ac_02,
    label="Open AC-02 decision controls",
    key="Enter",
)
criterion_selector = page.get_by_role("combobox", name="Inspect criterion", exact=True)
expect(criterion_selector).to_have_value("AC-02")
decision_selector = page.get_by_role("combobox", name="Human decision", exact=True)
expect(decision_selector).to_be_visible()
matrix_filter = page.get_by_role("heading", name="5 · Evidence Matrix", exact=True)
matrix_handle = matrix_filter.element_handle()
assert matrix_handle is not None
assert decision_selector.evaluate(
    "(decision, matrix) => Boolean("
    "decision.compareDocumentPosition(matrix) & Node.DOCUMENT_POSITION_FOLLOWING)",
    matrix_handle,
)
```

Before implementation, running this regression against the old layout would fail
because the matrix precedes the decision control. After the implementation, run it
through both configured viewports.

- [ ] **Step 7: Run browser, lint, and diff checks**

Run:

```bash
uv run pytest tests/browser/test_packaged_workbench.py -m browser -q
uv run ruff check apps/web/app.py apps/web/view_models.py \
  tests/apps/test_streamlit_app.py tests/browser/test_packaged_workbench.py
git diff --check
```

Expected: installed-wheel Chromium passes at 1280×720 and 390×844, Ruff exits zero,
and the diff check is clean.

- [ ] **Step 8: Commit the workflow handoff intentionally**

```bash
git add -- apps/web/app.py apps/web/view_models.py \
  tests/apps/test_streamlit_app.py tests/browser/test_packaged_workbench.py
git commit -m "feat: put criterion decisions before matrix detail"
```

---

### Task 3: Authoritative post-PR #197 truth

**Files:**
- Modify: `ROADMAP.md:18-58,283-304`
- Modify: `docs/releases/v0.2.3-status-and-next-stages.md:3-68,307-326`
- Modify: `CHANGELOG.md:22-30`
- Test: `tests/test_repository_contracts.py:28-50,1754-1771`

**Interfaces:**
- Consumes: immutable GitHub evidence for PR #197 and resulting `main`.
- Produces: dated current-state records for PR #197 head `5a69af4e92e2720adc524a32ea8c4eb94d013cb8`, base `8387156fd6f6e90eef7caf58881b0cc5bb62b111`, merge `789950dc63d80ec24d8bca5974a3ae52955b1c4f`, CI `32194734107`, CodeQL `32194733033`, Pages `32194734125`, and base advance `32194734440`.

- [ ] **Step 1: Add the failing authoritative-document contract**

Add exact PR #197 constants beside the PR #196 constants. Rename
`test_authoritative_status_records_dated_post_pr196_main_evidence` to
`test_authoritative_status_records_dated_post_pr197_main_evidence` and require both
documents to include:

```python
assert "Post-PR #197 resulting-main snapshot (2026-08-18)" in normalized
assert f"PR #197 head `{PR197_EXACT_HEAD_SHA}`" in normalized
assert f"base `{PR197_EXACT_BASE_SHA}`" in normalized
assert f"merge `{PR197_MERGE_SHA}`" in normalized
for run_id in PR197_RESULTING_MAIN_RUN_IDS:
    assert f"{GITHUB_ACTIONS_RUN_ROOT}/{run_id}" in normalized
assert "succeeded" in normalized
assert "owner workflow consolidation is complete" in normalized.lower()
assert "does not claim customer validation" in normalized
```

Use:

```python
PR197_EXACT_HEAD_SHA = "5a69af4e92e2720adc524a32ea8c4eb94d013cb8"
PR197_EXACT_BASE_SHA = "8387156fd6f6e90eef7caf58881b0cc5bb62b111"
PR197_MERGE_SHA = "789950dc63d80ec24d8bca5974a3ae52955b1c4f"
PR197_RESULTING_MAIN_RUN_IDS = (
    "32194734107",
    "32194733033",
    "32194734125",
    "32194734440",
)
```

- [ ] **Step 2: Run the contract and verify RED**

Run:

```bash
uv run pytest \
  tests/test_repository_contracts.py::test_authoritative_status_records_dated_post_pr197_main_evidence \
  -q
```

Expected: failure because the authoritative documents end at PR #196 and describe
the owner workflow consolidation as future work.

- [ ] **Step 3: Align the authoritative documents**

In both documents:

- update current development alignment to 2026-08-19 where present;
- add the dated post-PR #197 row/header using the exact immutable values above;
- state that PR #197 owner workflow consolidation is complete and that this
  decision-handoff ordering completes a bounded Stage 2 follow-up;
- replace future-tense owner-workflow priority prose with current baseline truth;
- retain v0.2.3 as the published release and `0.2.4.dev0` as unreleased development;
- retain every Stage 1 zero, customer-validation boundary, unsupported-environment
  caveat, and separate Stage 3 owner gate.

Add one Unreleased changelog bullet describing blocker-first unresolved decisions
and the direct pre-matrix criterion handoff without claiming correctness or runtime
verification.

- [ ] **Step 4: Run repository contracts and lint**

Run:

```bash
uv run pytest tests/test_repository_contracts.py -q
uv run ruff check tests/test_repository_contracts.py
git diff --check
```

Expected: all repository contracts pass, Ruff exits zero, and the diff is clean.

- [ ] **Step 5: Commit the current-state alignment intentionally**

```bash
git add -- ROADMAP.md CHANGELOG.md \
  docs/releases/v0.2.3-status-and-next-stages.md \
  tests/test_repository_contracts.py
git commit -m "docs: record completed owner workflow baseline"
```

---

### Task 4: Final branch verification and review

**Files:**
- Verify all changed files from Tasks 1-3.
- Do not modify product behavior unless a confirmed Critical or Important review finding requires a test-first repair.

**Interfaces:**
- Consumes: the complete branch diff from `origin/main` through the final task commit.
- Produces: a verified, independently reviewed, ready-for-review pull request candidate.

- [ ] **Step 1: Run the complete source verification**

```bash
uv run ruff check .
uv run python -m pytest --cov=scopeproof_core --cov=apps \
  --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run pytest tests/test_repository_contracts.py -q
uv run scopeproof benchmark
uv run python -m scopeproof_core.evals.comparison_runner
git diff --check origin/main...HEAD
```

Expected: Ruff and every test command exit zero, coverage is at least 95%, both
benchmarks report zero mismatches, must-have False Ready remains zero, and the diff
check is clean.

- [ ] **Step 2: Run package and installed-browser verification**

```bash
uv build --wheel --out-dir dist-owner-decision-handoff
uv run pytest tests/browser/test_packaged_workbench.py -m browser -q
uv run scopeproof --version
uv run scopeproof-web --version
```

Expected: the wheel builds, the installed-wheel browser regression passes at both
viewports with loopback-only networking and no console/page errors, and CLI/web
versions both report `0.2.4.dev0`.

- [ ] **Step 3: Audit exact branch scope and protected local state**

```bash
git status --short
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
```

Expected: only planned branch files plus generated ignored build state are present;
no `.coverage 2` is staged or modified; the parent checkout's protected file retains
SHA-256 `b392e4579f77b2dfd1ca904f1569e01dc887f79af9573e66534c85d7cb0e97fb`, inode
`184803784`, and size `53248`.

- [ ] **Step 4: Obtain independent whole-branch review**

Provide the approved spec, this plan, the complete `origin/main...HEAD` diff, test
evidence, and exact head to an independent reviewer. Resolve every actionable
Critical or Important finding test-first and re-run affected verification. Record
Minor findings without expanding into unrelated refactoring.

- [ ] **Step 5: Prepare the ready pull request**

After fresh verification and review, push `codex/owner-decision-handoff` and open one
ready-for-review pull request against `main`. Summarize the direct owner decision
handoff, blocker-first stable ordering, current-document alignment, engineering-only
evidence boundary, exact verification, and Stage 1 zero state. Do not merge it.
