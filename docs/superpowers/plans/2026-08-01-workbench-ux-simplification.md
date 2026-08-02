# ScopeProof Workbench UX Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the seven approved workbench hierarchy and workflow problems while preserving
ScopeProof's deterministic, fail-closed evidence and review boundaries.

**Architecture:** Keep lifecycle, gate, retrieval, persistence, and export behavior in
`scopeproof_core`. Add one pure web-layer evidence-grouping view model, then restructure the
existing Streamlit page in bounded slices. Autosave orchestrates the existing validated
`JsonReviewStore` from the web layer and never copies widget drafts into authoritative state.

**Tech Stack:** Python 3.11+, Streamlit 1.37–1.x, Pydantic 2, Pytest AppTest, Ruff, uv.

## Global Constraints

- Start from `origin/main` merge `f4d5da8353087541f3b16e32e25ba2b4add7f6d6` on
  `codex/workbench-ux-simplification`; do not modify the stale root checkout or `.coverage 2`.
- Preserve every evidence level, retrieval rule, gate threshold, gate precedence, lifecycle
  transition, widget key, and export draft guard unless a task explicitly changes presentation.
- False Ready is more harmful than False Blocked. Partial ingestion and insufficient evidence must
  remain fail-closed.
- Do not execute target-repository code or add generic review, security, semantic-model, or auto-fix
  behavior.
- Do not add paid APIs, billing, accounts, private repositories, dependencies, or persisted tokens.
- Keep repository- and human-controlled strings out of raw Markdown and HTML. Use `st.text`,
  `st.code`, or `render_artifact_reference_markdown()` as specified.
- Keep all persisted and exported data in the existing Pydantic-validated models. New view state is
  session-only and never exported.
- Use only Streamlit APIs supported by the declared `streamlit>=1.37,<2` floor.
- Preserve the existing high-contrast `:focus-visible` treatment and visible partial-ingestion
  warnings.
- Engineering tests, constructed demos, browser rehearsals, R-002/R-003, and owner review remain
  engineering evidence with zero Stage 1 credit.
- Do not push, merge, publish a tag or Release, contact anyone, or create GitHub notifications while
  implementing this plan.
- Use TDD for every behavior change: focused RED, minimal GREEN, focused regression, then commit only
  named files.

## File Structure

- Create `apps/web/view_models.py`: pure, deterministic grouping of validated evidence items for
  presentation only.
- Create `tests/apps/test_view_models.py`: isolated order, grouping, and no-mutation contracts.
- Modify `apps/web/app.py`: layout, safe rendering, CI compaction, decision ordering, autosave
  orchestration, and export hierarchy.
- Modify `tests/apps/test_streamlit_app.py`: AppTest workflow, ordering, persistence, error, and draft
  regressions.
- Modify `tests/apps/test_web_app.py`: source-level guards for stable keys and safe rendering.
- Create `docs/audits/workbench-ux-simplification/verification.md`: exact current-run browser and
  verification evidence with explicit environment limits.
- Create current-run PNGs under `docs/audits/workbench-ux-simplification/` only after the verified
  browser flow succeeds.

---

### Task 1: Add deterministic evidence presentation groups

**Files:**
- Create: `apps/web/view_models.py`
- Create: `tests/apps/test_view_models.py`

**Interfaces:**
- Consumes: validated `scopeproof_core.schemas.models.EvidenceItem` objects in current finding order.
- Produces: `EvidenceGroup(file_path: str, evidence_type: EvidenceType,
  items: tuple[EvidenceItem, ...])` and
  `group_candidate_evidence(items: list[EvidenceItem]) -> list[EvidenceGroup]`.

- [ ] **Step 1: Write the failing grouping tests**

```python
from apps.web.view_models import group_candidate_evidence
from scopeproof_core.demo import build_demo_review


def test_candidate_evidence_groups_preserve_first_occurrence_and_item_order() -> None:
    bundle = build_demo_review()
    items = [item for item in bundle.evidence if item.criterion_id == "AC-01"]

    groups = group_candidate_evidence(items)

    assert [(group.file_path, group.evidence_type.value) for group in groups] == [
        ("src/export.py", "implementation"),
        ("tests/test_export.py", "test"),
    ]
    assert [[item.evidence_id for item in group.items] for group in groups] == [
        ["EV-AC-01-01", "EV-AC-01-04"],
        ["EV-AC-01-02", "EV-AC-01-03"],
    ]


def test_candidate_evidence_grouping_keeps_every_validated_item_once() -> None:
    items = list(build_demo_review().evidence)

    grouped = group_candidate_evidence(items)

    flattened = [item for group in grouped for item in group.items]
    assert len(flattened) == len(items)
    assert sorted(item.evidence_id for item in flattened) == sorted(
        item.evidence_id for item in items
    )
    assert {id(item) for item in flattened} == {id(item) for item in items}
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
uv run pytest tests/apps/test_view_models.py -q
```

Expected: collection fails because `apps.web.view_models` does not exist.

- [ ] **Step 3: Implement the pure view model**

```python
"""Pure presentation models for the local ScopeProof workbench."""

from __future__ import annotations

from dataclasses import dataclass

from scopeproof_core.schemas.models import EvidenceItem, EvidenceType


@dataclass(frozen=True)
class EvidenceGroup:
    """One display-only group that preserves validated evidence item order."""

    file_path: str
    evidence_type: EvidenceType
    items: tuple[EvidenceItem, ...]


def group_candidate_evidence(items: list[EvidenceItem]) -> list[EvidenceGroup]:
    """Group by path and type without sorting, deduplicating, or rewriting items."""
    grouped: dict[tuple[str, EvidenceType], list[EvidenceItem]] = {}
    for item in items:
        grouped.setdefault((item.file_path, item.evidence_type), []).append(item)
    return [
        EvidenceGroup(file_path=path, evidence_type=evidence_type, items=tuple(group_items))
        for (path, evidence_type), group_items in grouped.items()
    ]
```

- [ ] **Step 4: Run focused and import tests to verify GREEN**

Run:

```bash
uv run pytest tests/apps/test_view_models.py tests/apps/test_web_app.py -q
```

Expected: all tests pass; no Streamlit app is imported by `test_view_models.py`.

- [ ] **Step 5: Commit the view model**

```bash
git add apps/web/view_models.py tests/apps/test_view_models.py
git commit -m "refactor: add deterministic evidence view groups"
```

---

### Task 2: Put the real public-PR entry before optional controls

**Files:**
- Modify: `apps/web/app.py:462-832`
- Modify: `tests/apps/test_streamlit_app.py:432-456`

**Interfaces:**
- Consumes: current replacement guards, store availability, alpha qualification, token, and bounded
  candidate paths.
- Produces: the same `fetch_pr`, `load_demo`, alpha, advanced, reopen, and delete events with a new
  document order and unchanged widget keys.

- [ ] **Step 1: Replace the old demo-first tests with public-PR-first tests**

```python
def test_public_pr_entry_precedes_optional_start_review_controls() -> None:
    app = new_app()
    keys = _main_widget_keys(app)

    assert keys.count("pr_url") == 1
    assert keys.count("fetch_pr") == 1
    assert keys.index("pr_url") < keys.index("fetch_pr")
    assert keys.index("fetch_pr") < keys.index("load_demo")
    assert keys.index("fetch_pr") < keys.index("alpha_feedback_mode")
    assert keys.index("fetch_pr") < keys.index("github_token")
    assert keys.index("fetch_pr") < keys.index("candidate_paths")
    assert keys.index("fetch_pr") < keys.index("reopen_review_id")
    assert keys.index("fetch_pr") < keys.index("requirements_input")


def test_start_review_secondary_paths_are_collapsed_after_public_pr_entry() -> None:
    app = new_app()

    assert [item.label for item in app.expander[:4]] == [
        "Try ScopeProof",
        "Alpha feedback session (optional)",
        "Advanced source options",
        "Resume a saved review",
    ]
    assert all(item.proto.expanded is False for item in app.expander[:4])
    assert app.button(key="load_demo").label == "Load deliberately constructed demo"
    assert app.button(key="reopen_review").disabled is True
```

Keep `test_blank_public_pr_url_remains_neutral_and_disables_fetch`, canonical URL, alpha
qualification, token secrecy, candidate path, replacement, reopen, and delete tests unchanged.

- [ ] **Step 2: Run the two tests to verify RED**

Run:

```bash
uv run pytest \
  tests/apps/test_streamlit_app.py::test_public_pr_entry_precedes_optional_start_review_controls \
  tests/apps/test_streamlit_app.py::test_start_review_secondary_paths_are_collapsed_after_public_pr_entry \
  -q
```

Expected: the order and expander labels fail against the demo-first layout.

- [ ] **Step 3: Reorder Start Review with an early Fetch placeholder**

Move the exact existing reopen/delete block at current lines 522–599 below the primary entry. Use
this concrete structure for the new and relocated Start Review controls:

```python
st.header("1 · Start Review")
st.markdown("**Public PR → Confirm criteria → Review coverage → Record decisions → Export**")
st.caption(
    "Five bounded stages keep source loading, human confirmation, candidate analysis, "
    "reviewer decisions, and exports separate."
)
pr_url = st.text_input(
    "Public GitHub pull request URL",
    placeholder="https://github.com/owner/repository/pull/123",
    key="pr_url",
)
pr_url_is_valid = False
if pr_url.strip():
    try:
        parse_pr_url(pr_url)
    except InvalidPullRequestUrl:
        st.warning(
            "Enter a public GitHub pull request URL in this format: "
            "`https://github.com/OWNER/REPO/pull/NUMBER`."
        )
    else:
        pr_url_is_valid = True
fetch_action_placeholder = st.empty()
alpha_feedback_mode = bool(st.session_state.get("alpha_feedback_mode", False))

with st.expander("Try ScopeProof", expanded=False):
    if st.button(
        "Load deliberately constructed demo",
        key="load_demo",
        disabled=replacement_blocked or alpha_feedback_mode,
    ):
        labels = load_demo_labels()
        snapshot = load_demo_snapshot()
        _record_reopened_source_reload(snapshot)
        st.session_state["snapshot"] = snapshot
        st.session_state["source_text"] = labels["source_text"]
        st.session_state["requirements_input"] = labels["source_text"]
        st.session_state["criteria"] = [
            Criterion.model_validate(item) for item in labels["criteria"]
        ]
        st.session_state["candidate_files"] = []
        st.session_state["comparison_base_bundle"] = None
        _reset_analysis()
        st.rerun()

with st.expander("Alpha feedback session (optional)", expanded=False):
    alpha_feedback_mode = st.checkbox(
        "Collect local alpha feedback for this review",
        value=False,
        key="alpha_feedback_mode",
    )
    if alpha_feedback_mode:
        st.caption(
            "Qualification is session-only. Confirm a genuine public case before fetching; "
            "ScopeProof does not store these preflight fields here."
        )
        requirements_source_url = st.text_input(
            "Public requirements source URL",
            placeholder="https://github.com/owner/repository/issues/123",
            key="requirements_source_url",
        )
        participant_role = st.selectbox(
            "Participant role",
            options=[role.value for role in ParticipantRole],
            key="participant_role",
        )
        source_owner_confirmed = st.checkbox(
            "I am the source owner or directly authorized to confirm these requirements",
            key="source_owner_confirmed",
        )
        no_confidential_information = st.checkbox(
            "This review contains no confidential information, secrets, or private links",
            key="no_confidential_information",
        )

alpha_qualification_ready = True
alpha_qualification: AlphaQualification | None = None
if alpha_feedback_mode:
    alpha_qualification_ready = False
    if (
        pr_url_is_valid
        and requirements_source_url.strip()
        and source_owner_confirmed
        and no_confidential_information
    ):
        try:
            alpha_qualification = AlphaQualification(
                public_pr_url=pr_url,
                requirements_source_url=requirements_source_url,
                participant_role=ParticipantRole(participant_role),
                source_owner_confirmed=True,
                no_confidential_information=True,
            )
        except ValueError:
            st.warning("Use a public HTTPS requirements source and a canonical public PR URL.")
        else:
            alpha_qualification_ready = True
else:
    st.caption("Standard review mode does not create participant research records.")

with st.expander("Advanced source options", expanded=False):
    github_token = st.text_input(
        "Optional GitHub token",
        type="password",
        help=(
            "Used only in this session to increase free GitHub rate limits. "
            "Never exported or saved."
        ),
        key="github_token",
    )
    candidate_paths_text = st.text_area(
        "Bounded unchanged candidate paths (optional)",
        key="candidate_paths",
        help=(
            "One explicit repository-relative file path per line. ScopeProof does not "
            "infer paths or scan the repository."
        ),
    )
    candidate_paths = list(
        dict.fromkeys(
            line.strip()
            for line in candidate_paths_text.splitlines()
            if line.strip()
        )
    )

if fetch_action_placeholder.button(
    "Fetch public PR",
    key="fetch_pr",
    disabled=(
        not pr_url_is_valid
        or not alpha_qualification_ready
        or replacement_blocked
    ),
    use_container_width=True,
):
    try:
        client = GitHubClient(token=github_token or None)
        snapshot = client.fetch_pull_request(pr_url)
        candidate_files = client.fetch_candidate_files(
            snapshot.repository, snapshot.head_sha, candidate_paths
        )
        _record_reopened_source_reload(snapshot)
        st.session_state["snapshot"] = snapshot
        st.session_state["candidate_files"] = candidate_files
        st.session_state["alpha_case_id"] = None
        _reset_analysis()
        st.session_state["source_load_notice"] = (
            "Public PR loaded. Add and confirm criteria before analysis."
        )
        st.rerun()
    except (GitHubIngestionError, ValueError) as error:
        st.error(
            f"{error} No review data was changed. Verify that the PR is public and "
            "try again. Use the optional token only if GitHub reports a rate limit."
        )
```

Wrap the exact current reopen/delete rendering at lines 522–599 in
`with st.expander("Resume a saved review", expanded=False):`. Keep store initialization
outside that expander so Task 6 can call autosave before rendering. Show reopen/delete success or
warning notices immediately afterward.

- [ ] **Step 4: Run Start Review and storage regressions**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "public_pr or start_review or alpha or candidate_paths or reopen or delete_saved or review_store"
```

Expected: all selected tests pass and the existing widget keys remain discoverable while collapsed.

- [ ] **Step 5: Commit the entry redesign**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "feat: prioritize public PR entry"
```

---

### Task 3: Compact criteria editing and keep confirmation early

**Files:**
- Modify: `apps/web/app.py:834-1091`
- Modify: `tests/apps/test_streamlit_app.py:864-1320`
- Modify: `tests/apps/test_web_app.py`

**Interfaces:**
- Consumes: current criteria list, per-criterion session keys, draft detection, authoring guards,
  `revise_criteria()`, and `confirm_criteria()`.
- Produces: one early `confirm_criteria` action, collapsed criterion editors, and one collapsed
  add/split editor with unchanged authoritative transitions.

- [ ] **Step 1: Add RED tests for the compact criteria hierarchy**

```python
def test_criteria_summary_and_confirmation_precede_long_editor_list() -> None:
    app = load_demo(new_app())
    keys = _main_widget_keys(app)
    visible = "\n".join(item.value for item in [*app.caption, *app.markdown])

    assert keys.count("confirm_criteria") == 1
    assert keys.index("confirm_criteria") < keys.index("criterion_text_AC-01")
    assert keys.index("confirm_criteria") < keys.index("new_criterion_text")
    assert "Criteria: 4" in visible
    assert "Confirmation: Required" in visible
    assert "Pending edits: None" in visible


def test_criterion_editors_are_collapsed_and_keep_requirement_text_inert() -> None:
    app = load_demo(new_app())
    criterion_expanders = [item for item in app.expander if item.label.startswith("AC-")]

    assert [item.label for item in criterion_expanders] == [
        "AC-01 · Must Have · E1",
        "AC-02 · Must Have · E1",
        "AC-03 · Must Have · E1",
        "AC-04 · Should Have · E1",
    ]
    assert all(item.proto.expanded is False for item in criterion_expanders)
    for criterion, expander in zip(app.session_state["criteria"], criterion_expanders, strict=True):
        assert criterion.text in [item.value for item in expander.text]
        assert criterion.text not in expander.label


def test_add_and_split_controls_are_one_collapsed_secondary_group() -> None:
    app = load_demo(new_app())
    editor = next(item for item in app.expander if item.label == "Add or split criteria")
    child_keys = _main_widget_keys(editor)

    assert editor.proto.expanded is False
    assert child_keys == [
        "new_criterion_text",
        "add_criterion_ui",
        "split_criterion_id",
        "split_criterion_text",
        "split_criterion_ui",
    ]


def test_markdown_shaped_confirmed_requirement_remains_inert() -> None:
    unsafe_text = "![criterion](https://example.invalid/criterion.png)"
    app = load_demo(new_app())
    app = app.text_input(key="criterion_text_AC-01").set_value(unsafe_text).run()
    app = app.button(key="confirm_criteria").click().run()

    assert unsafe_text in [item.value for item in app.text]
    assert all(unsafe_text not in item.label for item in app.expander)
    assert all(unsafe_text not in item.value for item in app.markdown)
```

Add a source guard to `tests/apps/test_web_app.py` that requires `st.text(criterion.text)` and rejects
interpolating `selected_criterion.text` or `criterion.text` into Markdown-capable heading strings.

- [ ] **Step 2: Run the new tests to verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "criteria_summary or criterion_editors_are_collapsed or add_and_split_controls"
```

Expected: confirmation follows the full editor list and the new expanders are absent.

- [ ] **Step 3: Implement the early placeholder and collapsed editors**

At the top of the non-empty criteria branch, reserve these locations:

```python
criteria_summary_placeholder = st.empty()
criteria_validation_placeholder = st.container()
confirm_action_placeholder = st.empty()
analysis_continuation_placeholder = st.empty()
criterion_validation_placeholders = {}
```

Indent the exact current add/split block at lines 851–883 under this expander without changing its
five widget keys, enablement expressions, `_apply_criteria_update()` calls, or consumed-input keys:

```python
with st.expander("Add or split criteria", expanded=False):
    new_criterion_text = st.text_input("Add criterion", key="new_criterion_text")
    if st.button(
        "Add criterion",
        key="add_criterion_ui",
        disabled=not new_criterion_text.strip() or authoring_submission_blocked,
    ):
        _apply_criteria_update(
            partial(add_criterion, criteria, new_criterion_text),
            "Criterion added. Confirm the updated set before analysis.",
            consumed_input_keys=("new_criterion_text",),
        )
    split_target = st.selectbox(
        "Split criterion",
        options=[item.criterion_id for item in criteria],
        key="split_criterion_id",
    )
    split_text = st.text_area(
        "Split criterion into one behavior per line",
        key="split_criterion_text",
    )
    if st.button(
        "Split criterion",
        key="split_criterion_ui",
        disabled=(
            len([line for line in split_text.splitlines() if line.strip()]) < 2
            or authoring_submission_blocked
        ),
    ):
        split_texts = [line.strip() for line in split_text.splitlines() if line.strip()]
        _apply_criteria_update(
            partial(split_criterion, criteria, split_target, split_texts),
            "Criterion split. Confirm the updated set before analysis.",
            consumed_input_keys=("split_criterion_text",),
        )
```

Render each criterion without repository text in the label:

```python
for position, criterion in enumerate(criteria):
    displayed_priority = st.session_state.get(
        f"criterion_priority_{criterion.criterion_id}", criterion.priority
    )
    displayed_level = st.session_state.get(
        f"criterion_level_{criterion.criterion_id}", criterion.required_evidence_level
    )
    editor_label = (
        f"{criterion.criterion_id} · {_status_label(displayed_priority.value)} · "
        f"{displayed_level.value}"
    )
    with st.expander(editor_label, expanded=False):
        st.caption("Confirmed requirement")
        st.text(criterion.text)
```

Immediately after `st.text(criterion.text)`, indent the exact current per-criterion widget and action
block at lines 891–959. Do not change `criterion_text_*`, `criterion_priority_*`,
`criterion_level_*`, `remove_*`, or `move_up_*` keys, and keep the existing reconstruction of
`edited_criteria` after the expander closes. At the end of each expander body, add:

```python
criterion_validation_placeholders[criterion.criterion_id] = st.empty()
```

After building `edited_criteria`, `blank_criterion_ids`, and `warnings`, populate the reserved
locations and call the existing confirmation handler through the early placeholder:

```python
criteria_summary_placeholder.caption(
    f"Criteria: {len(criteria)} · "
    f"Confirmation: {'Confirmed' if st.session_state['criteria_confirmed'] else 'Required'} · "
    f"Pending edits: {'Present' if criteria_edits_pending else 'None'}"
)
with criteria_validation_placeholder:
    for criterion_id in blank_criterion_ids:
        st.warning(f"{criterion_id}: Criterion text cannot be blank.")
    for warning in warnings:
        st.warning(f"{warning.criterion_id}: {warning.message}")

warnings_by_criterion: dict[str, list[str]] = {
    criterion.criterion_id: [] for criterion in criteria
}
for criterion_id in blank_criterion_ids:
    warnings_by_criterion[criterion_id].append("Criterion text cannot be blank.")
for warning in warnings:
    warnings_by_criterion[warning.criterion_id].append(warning.message)
for criterion_id, placeholder in criterion_validation_placeholders.items():
    with placeholder.container():
        for message in warnings_by_criterion[criterion_id]:
            st.warning(message)

confirm_clicked = confirm_action_placeholder.button(
    "Confirm criteria",
    key="confirm_criteria",
    disabled=bool(blank_criterion_ids)
    or (st.session_state["criteria_confirmed"] and not criteria_edits_pending),
    use_container_width=True,
)
```

Replace the current `if st.button(...):` with `if confirm_clicked:` and indent the exact current
confirmation body at lines 990–1045 under it. Keep its
`revise_criteria()`, `confirm_criteria()`, alpha-case qualification, state replacement, and rerun
operations byte-for-byte. Leave the discard controls, analysis lock, and continuation link outside
the editor expanders with their current keys and conditions.

Extend the existing parameterized blank-criterion test to assert that `Criterion text cannot be
blank.` appears both in the top validation container and inside AC-01's matching editor, while the
authoritative criterion remains unchanged and `confirm_criteria` is disabled.

- [ ] **Step 4: Run the complete criteria lifecycle regression set**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "criteria or criterion or analysis_is_disabled or analysis_continuation"
uv run pytest tests/apps/test_web_app.py -q
```

Expected: blank, add, split, remove, move, priority, evidence-level, confirmation, invalidation, and
analysis-lock tests all pass.

- [ ] **Step 5: Commit criteria compaction**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py tests/apps/test_web_app.py
git commit -m "feat: compact criteria confirmation"
```

---

### Task 4: Replace repeated CI diagnostics with one compact truthful summary

**Files:**
- Modify: `apps/web/app.py:387-407,1093-1320`
- Modify: `tests/apps/test_streamlit_app.py:208-353,913-920`

**Interfaces:**
- Consumes: `ReviewBundle.review.ci_observation`, `runtime_verification_state`, and optional
  `research_context`.
- Produces: `_render_ci_observation_summary(bundle: ReviewBundle) -> None`; presentation only.

- [ ] **Step 1: Write RED tests for non-duplicated compact CI rendering**

```python
def test_loaded_source_identity_does_not_repeat_ci_diagnostics() -> None:
    app = load_demo(new_app())
    captions = "\n".join(item.value for item in app.caption)

    assert "Loaded source" in "\n".join(item.value for item in app.markdown)
    assert "head-demo-002" in [item.value for item in app.code]
    assert "Observed CI state:" not in captions
    assert "Observed CI reason:" not in captions


def test_evidence_matrix_ci_summary_is_compact_complete_and_deterministic() -> None:
    app = analyzed_demo(new_app())
    details = next(
        item for item in app.expander if item.label == "CI details and evidence boundary"
    )
    visible = "\n".join(item.value for item in [*app.caption, *app.text, *app.warning])

    assert details.proto.expanded is False
    assert "Observed CI: Passing" in visible
    assert "Collection: Complete" in visible
    assert "1 total · 1 successful · 0 pending · 0 failing" in visible
    assert "0 neutral · 0 skipped · 0 concrete legacy statuses" in visible
    assert "Runtime verification: Not recorded" in visible
```

Convert the existing skipped-check test so the static limiting warning remains outside the details
expander while `integration` and diagnostic notes appear only in `details.text`.

- [ ] **Step 2: Run CI tests to verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "loaded_source_identity_does_not_repeat_ci or evidence_matrix_ci_summary or limiting_ci"
```

Expected: loaded source still repeats CI and no compact details expander exists.

- [ ] **Step 3: Implement the compact CI renderer**

Add `CheckState` to the schema imports and add this web-layer helper near
`_render_loaded_source_identity`:

```python
def _render_ci_observation_summary(bundle: ReviewBundle) -> None:
    observation = bundle.review.ci_observation
    with st.container(border=True):
        st.markdown("**Observed CI and verification boundary**")
        st.caption(f"Observed CI: {_status_label(observation.state.value)}")
        st.caption(
            f"Collection: {'Complete' if observation.collection_complete else 'Incomplete'}"
        )
        st.caption(
            f"{observation.total_check_runs} total · "
            f"{observation.successful_check_runs} successful · "
            f"{observation.pending_check_runs} pending · "
            f"{observation.failing_check_runs} failing · "
            f"{observation.neutral_check_runs} neutral · "
            f"{observation.skipped_check_runs} skipped · "
            f"{observation.concrete_legacy_status_count} concrete legacy statuses"
        )
        st.caption("Deterministic reason")
        st.text(observation.reason)
        st.caption(
            "Runtime verification: "
            f"{bundle.runtime_verification_state.value.replace('_', ' ').capitalize()}"
        )
        if observation.state is not CheckState.PASSING or not observation.collection_complete:
            st.warning(
                "Observed CI has a limiting state. Review its deterministic reason before "
                "relying on the gate."
            )

    with st.expander("CI details and evidence boundary", expanded=False):
        if observation.skipped_check_names:
            st.caption("Skipped CI checks (unexecuted)")
            for name in observation.skipped_check_names:
                st.text(name)
        if observation.collection_notes:
            st.caption("CI collection diagnostics")
            for note in observation.collection_notes:
                st.text(note)
        st.caption(
            "Static candidates and observed CI do not establish runtime verification. "
            "Runtime evidence and reviewer decisions remain separate."
        )
        if bundle.research_context is not None:
            st.caption("Public engineering research · Stage 1 credit: 0")
            st.caption("Case ID")
            st.code(bundle.research_context.case_id, language=None)
            st.text(bundle.research_context.boundary_note)
```

Remove CI state, reason, skipped names, and collection notes from `_render_loaded_source_identity`.
Call `_render_ci_observation_summary(bundle)` once at the matrix entry. Keep
`_render_ingestion_limitations()` outside collapsed content.

- [ ] **Step 4: Run CI, gate, partial-ingestion, and reopen regressions**

Run:

```bash
uv run pytest -q \
  tests/apps/test_streamlit_app.py \
  tests/gates \
  tests/reviews/test_lifecycle.py
```

Expected: all tests pass and no gate or lifecycle file changed.

- [ ] **Step 5: Commit CI compaction**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "feat: compact CI evidence boundary"
```

---

### Task 5: Build one evidence-and-decision criterion workspace

**Files:**
- Modify: `apps/web/app.py:1321-1768`
- Modify: `tests/apps/test_streamlit_app.py:2399-3100`
- Modify: `tests/apps/test_web_app.py`

**Interfaces:**
- Consumes: `group_candidate_evidence()` from Task 1, existing selected criterion, finding,
  diagnostic, resolution, runtime records, and lifecycle handlers.
- Produces: responsive evidence and decision columns; ordinary resolution before optional E3/E4;
  the same authoritative resolution, final-acceptance, and external-verification events.

- [ ] **Step 1: Add RED tests for grouping, source order, and inert values**

```python
def test_ordinary_resolution_precedes_optional_external_verification() -> None:
    app = analyzed_demo(new_app())
    keys = _main_widget_keys(app)
    optional = next(
        item
        for item in app.expander
        if item.label == "Record optional external verification (E3/E4)"
    )

    assert keys.index("decision_reviewer") < keys.index("resolution_decision")
    assert keys.index("save_resolution") < keys.index("runtime_artifact_reference")
    assert keys.index("runtime_artifact_reference") < keys.index("save_runtime_evidence")
    assert optional.proto.expanded is False


def test_candidate_evidence_groups_by_path_and_type_without_losing_items() -> None:
    app = analyzed_demo(new_app())
    groups = [item for item in app.expander if item.label.startswith("Evidence group ")]

    assert [item.label for item in groups] == [
        "Evidence group 1 · Implementation · 2 items",
        "Evidence group 2 · Test · 2 items",
    ]
    assert [groups[0].code[0].value, groups[1].code[0].value] == [
        "src/export.py",
        "tests/test_export.py",
    ]
    rendered_ids = [
        value
        for group in groups
        for value in [item.value for item in group.code]
        if value.startswith("EV-")
    ]
    assert rendered_ids == [
        "EV-AC-01-01",
        "EV-AC-01-04",
        "EV-AC-01-02",
        "EV-AC-01-03",
    ]


def test_selected_requirement_and_candidate_values_are_not_raw_markdown() -> None:
    app = analyzed_demo(new_app())
    selected_text = app.session_state["criteria"][0].text
    markdown_values = [item.value for item in app.markdown]

    assert selected_text in [item.value for item in app.text]
    assert all(selected_text not in value for value in markdown_values)
```

Add a source test that rejects the current raw evidence link form
`f"[Open immutable GitHub evidence]({item.permalink})"` and requires
`render_artifact_reference_markdown(item.permalink)`.

- [ ] **Step 2: Run the new tests to verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "ordinary_resolution_precedes or candidate_evidence_groups or values_are_not_raw_markdown"
uv run pytest tests/apps/test_web_app.py -q
```

Expected: the external form precedes resolution, item expanders are ungrouped, and selected text is
interpolated into Markdown.

- [ ] **Step 3: Render the selected criterion inertly and create responsive columns**

Import `group_candidate_evidence` and replace the dynamic selected heading with:

```python
st.markdown("### Selected criterion")
st.caption("Criterion ID")
st.code(selected_id, language=None)
st.caption("Confirmed requirement")
st.text(selected_criterion.text)
evidence_column, decision_column = st.columns([3, 2], gap="large")
```

In `evidence_column`, keep evidence status, required/observed level, missing evidence, recommended
action, retrieval diagnostics, and candidate evidence. Render dynamic missing/action/rationale/rule
and limitation strings with `st.text` or `st.code`, not `st.markdown`.

- [ ] **Step 4: Replace item expanders with deterministic group expanders**

```python
selected_items = [evidence_by_id[evidence_id] for evidence_id in selected_finding.evidence_ids]
for group_number, group in enumerate(group_candidate_evidence(selected_items), start=1):
    group_label = (
        f"Evidence group {group_number} · {_status_label(group.evidence_type.value)} · "
        f"{len(group.items)} {'item' if len(group.items) == 1 else 'items'}"
    )
    with st.expander(group_label, expanded=False):
        st.caption("Repository path")
        st.code(group.file_path, language=None)
        for item in group.items:
            with st.container(border=True):
                st.caption("Evidence ID")
                st.code(item.evidence_id, language=None)
                st.caption(
                    f"Lines {item.line_start}-{item.line_end} · "
                    f"Level {item.evidence_level.value}"
                )
                if item.evidence_type.value == "test":
                    st.caption(
                        "Test/eval definition shows intent, not executed verification."
                    )
                st.code(item.excerpt)
                if item.context_excerpt:
                    st.caption("Bounded context")
                    st.code(item.context_excerpt)
                st.markdown(render_artifact_reference_markdown(item.permalink))
                st.caption("Matching rationale")
                st.text(item.relevance_reason)
                st.caption("Matching rule")
                st.text(item.matching_rule)
                for limitation in item.limitations:
                    st.caption("Limitation")
                    st.text(limitation)
```

The label contains only group number, enum-derived type, and count. The repository path remains
inside `st.code`.

- [ ] **Step 5: Move ordinary resolution before the optional external form**

Inside `decision_column`, render the current ordinary decision block first with its existing
`decision_reviewer`, `resolution_decision`, `resolution_note`, and `save_resolution` keys. Replace
the interpolated target Markdown with static copy referring to the selected criterion above.

Then move the existing E3/E4 widgets and atomic handler unchanged into:

```python
runtime_evidence_save_notice = st.session_state.pop(
    "runtime_evidence_save_notice", None
)
if runtime_evidence_save_notice is not None:
    st.success(runtime_evidence_save_notice)

with st.expander(
    "Record optional external verification (E3/E4)",
    expanded=False,
):
    st.caption(
        "Record a human-supplied observation only. ScopeProof does not run PR code or "
        "infer runtime results. Saving records runtime evidence and its manual-verification "
        "decision atomically."
    )
```

Indent the exact current runtime form and atomic handler at lines 1479–1573 immediately after the
caption inside this expander. Do not change any `runtime_*` key, required-field check,
`RuntimeEvidence` construction, `ResolutionEvent(MANUALLY_VERIFIED)` construction,
`append_external_verification()` call, reset flag, or rerun. Render existing runtime records after
that expander in a sibling `Recorded runtime evidence (N)` expander. Use `st.text`/`st.code` for
scenario, environment, result, reviewer, timestamp, and limitations; keep the artifact reference
clickable only through `render_artifact_reference_markdown()`. Keep final acceptance and resolution
history full-width after both columns; render human comments through `st.text`.

- [ ] **Step 6: Run criterion, resolution, runtime, gate, and safe-rendering regressions**

Run:

```bash
uv run pytest -q \
  tests/apps/test_streamlit_app.py \
  tests/apps/test_view_models.py \
  tests/apps/test_web_app.py \
  tests/reviews/test_lifecycle.py \
  tests/gates
```

Expected: ordinary and manual verification remain separate; external verification still appends
runtime evidence and `MANUALLY_VERIFIED` atomically; final acceptance remains prerequisite-gated.

- [ ] **Step 7: Commit the criterion workspace**

```bash
git add \
  apps/web/app.py \
  tests/apps/test_streamlit_app.py \
  tests/apps/test_web_app.py
git commit -m "feat: unify evidence and reviewer decisions"
```

---

### Task 6: Add one-attempt validated autosave with explicit recovery

**Files:**
- Modify: `apps/web/app.py:84-224,462-608,1770-1844`
- Modify: `tests/apps/test_streamlit_app.py:76-80,459-676,1442-2028`

**Interfaces:**
- Consumes: existing `_review_state_fingerprint()`, `JsonReviewStore.save()`, draft flags, store
  availability, and validated `ReviewState`.
- Produces: `_persist_review_state(state: ReviewState, store: JsonReviewStore) -> bool` and
  `_autosave_review_if_eligible(*, state: ReviewState | None, store: JsonReviewStore,
  store_available: bool, has_pending_review_input: bool) -> bool`; session-only successful, failed,
  and deleted fingerprints.

- [ ] **Step 1: Change the saved-review helper and add RED autosave tests**

Change the existing helper so it relies on autosave:

```python
def saved_demo_review(app: AppTest) -> tuple[AppTest, str]:
    app = analyzed_demo(app)
    review_id = app.session_state["review_state"].review.review_id
    return app, review_id
```

Add these tests:

```python
def test_authoritative_review_autosaves_without_manual_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    stored = JsonReviewStore(default_local_review_directory()).load(state.review.review_id)

    assert stored == state
    assert app.session_state["saved_review_fingerprint"] is not None
    assert app.session_state["failed_review_save_fingerprint"] is None
    assert app.session_state["deleted_review_save_fingerprint"] is None
    assert app.button(key="save_review").disabled is True
    assert "Review saved automatically" in "\n".join(
        item.value for item in app.success
    )


def test_unchanged_authoritative_review_does_not_autosave_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        app = app.run()

    save.assert_not_called()


@pytest.mark.parametrize(
    ("widget_collection", "key", "value"),
    [
        ("text_input", "criterion_text_AC-01", "Pending revised requirement"),
        ("text_input", "new_criterion_text", "Pending additional criterion"),
        ("text_area", "requirements_input", "Pending source requirement"),
        ("text_input", "runtime_artifact_reference", "pending-runtime-artifact"),
    ],
)
def test_pending_draft_categories_block_autosave(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    widget_collection: str,
    key: str,
    value: str,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, review_id = saved_demo_review(new_app())
    store = JsonReviewStore(default_local_review_directory())
    persisted_before = store.load(review_id)
    app.session_state["saved_review_fingerprint"] = None

    with patch("scopeproof_core.storage.json_store.JsonReviewStore.save") as save:
        widget = getattr(app, widget_collection)(key=key)
        app = widget.set_value(value).run()

    save.assert_not_called()
    assert store.load(review_id) == persisted_before
    assert all(button.disabled for button in app.download_button)
```

This parameterization explicitly covers criteria edits, add/split authoring, requirements edits,
and criterion-detail drafts. Clearing the successful fingerprint proves the pending-input guard,
rather than a successful-save no-op, prevented the write.

- [ ] **Step 2: Run autosave tests to verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "autosave or authoritative_review_autosaves or unchanged_authoritative_review"
```

Expected: no autosave state or file exists.

- [ ] **Step 3: Add session markers and persistence helpers**

Add these `_STATE_DEFAULTS` entries:

```python
"failed_review_save_fingerprint": None,
"deleted_review_save_fingerprint": None,
```

Add these helpers after `_review_matches_local_save`:

```python
def _persist_review_state(state: ReviewState, store: JsonReviewStore) -> bool:
    fingerprint = _review_state_fingerprint(state)
    try:
        store.save(state)
    except (OSError, ValueError):
        st.session_state["failed_review_save_fingerprint"] = fingerprint
        return False
    st.session_state["saved_review_fingerprint"] = fingerprint
    st.session_state["failed_review_save_fingerprint"] = None
    st.session_state["deleted_review_save_fingerprint"] = None
    return True


def _autosave_review_if_eligible(
    *,
    state: ReviewState | None,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
) -> bool:
    if state is None or not store_available or has_pending_review_input:
        return False
    fingerprint = _review_state_fingerprint(state)
    suppressed = {
        st.session_state["saved_review_fingerprint"],
        st.session_state["failed_review_save_fingerprint"],
        st.session_state["deleted_review_save_fingerprint"],
    }
    if fingerprint in suppressed:
        return False
    if not _persist_review_state(state, store):
        return False
    st.session_state["review_save_notice"] = (
        f"Review saved automatically. ID: {state.review.review_id}."
    )
    return True
```

Clear failed/deleted markers in `_reset_analysis()` and `_hydrate_reopened_review()`. Every
successful explicit save also clears them through `_persist_review_state()`.

- [ ] **Step 4: Move the autosave call before unsaved/replacement derivation**

The exact order after pending-reset processing must be:

```python
storage_directory = default_local_review_directory()
review_store = JsonReviewStore(Path(storage_directory))
try:
    saved_review_ids = review_store.list_review_ids()
except (OSError, UnsafeReviewStore):
    saved_review_ids = []
    review_store_available = False
else:
    review_store_available = True

current_review_state: ReviewState | None = st.session_state["review_state"]
has_pending_criteria_draft = _criteria_draft_pending(st.session_state["criteria"])
has_pending_criteria_authoring_draft = _criteria_authoring_draft_pending()
has_pending_requirements_draft = _requirements_draft_pending()
has_pending_criterion_detail_draft = _criterion_detail_draft_pending()
has_pending_review_input = (
    has_pending_criteria_draft
    or has_pending_criteria_authoring_draft
    or has_pending_requirements_draft
    or has_pending_criterion_detail_draft
)
autosaved = _autosave_review_if_eligible(
    state=current_review_state,
    store=review_store,
    store_available=review_store_available,
    has_pending_review_input=has_pending_review_input,
)
if autosaved and current_review_state is not None:
    saved_review_ids = sorted(
        {*saved_review_ids, current_review_state.review.review_id}
    )
# Only now derive has_unsaved_review and all replacement/authoring guards.
```

This ordering prevents one render from showing both autosaved and stale unsaved warnings and also
saves a valid revised state whose active bundle is temporarily `None`.

- [ ] **Step 5: Add failure, retry, and unavailable-store tests**

Add `from hashlib import sha256` and `ReviewState` to the test module imports, then add this
test-only helper:

```python
def _review_fingerprint_for_test(state: ReviewState) -> str:
    return sha256(state.model_dump_json().encode("utf-8")).hexdigest()
```

Patch `JsonReviewStore.save` around the `run_analysis` click so the first eligible autosave fails:

```python
@pytest.mark.parametrize(
    "save_error",
    [OSError("disk full at /private/secret/path"), ValueError("invalid state")],
)
def test_autosave_failure_attempts_once_and_preserves_explicit_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    save_error: OSError | ValueError,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.save",
        side_effect=save_error,
    ) as save:
        app = app.button(key="run_analysis").click().run()
        assert save.call_count == 1
        app = app.run()
        assert save.call_count == 1

    state = app.session_state["review_state"]
    assert app.session_state["saved_review_fingerprint"] is None
    assert app.session_state["failed_review_save_fingerprint"] == (
        _review_fingerprint_for_test(state)
    )
    assert app.button(key="save_review").label == "Retry local save"
    assert app.button(key="save_review").disabled is False
    assert all(not button.disabled for button in app.download_button)
    assert "/private/secret/path" not in "\n".join(
        item.value for item in [*app.error, *app.warning, *app.caption]
    )
```

Add a follow-on test that clicks `save_review` without the failure patch, loads the validated record,
and proves both suppression markers are cleared. Extend the existing symlink and regular-file tests
to patch `save()` and assert it is never called.

- [ ] **Step 6: Add delete suppression and post-delete mutation tests**

When deleting the current open review, set:

```python
current_fingerprint = _review_state_fingerprint(current)
st.session_state["saved_review_fingerprint"] = None
st.session_state["deleted_review_save_fingerprint"] = current_fingerprint
if st.session_state["failed_review_save_fingerprint"] == current_fingerprint:
    st.session_state["failed_review_save_fingerprint"] = None
```

Add tests proving:

- the delete rerun and a later plain rerun do not recreate the file;
- `Save now` explicitly recreates it and clears deletion suppression;
- a new ordinary resolution changes the fingerprint and may autosave;
- deleting a different review leaves the current saved and deleted fingerprints unchanged; and
- reopening an unchanged review does not call `save()`.

Use `JsonReviewStore(default_local_review_directory()).load()` for positive persistence checks and
`pytest.raises(FileNotFoundError)` for the deleted file checks.

- [ ] **Step 7: Run all storage, lifecycle, draft, and export tests**

Run:

```bash
uv run pytest -q \
  tests/apps/test_streamlit_app.py \
  tests/storage/test_json_store.py \
  tests/reviews/test_lifecycle.py \
  tests/reporting
```

Expected: autosave writes validated authoritative state once, drafts never write, failures do not
loop, and deletion does not silently recreate the same record.

- [ ] **Step 8: Commit autosave**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "feat: autosave validated review state"
```

---

### Task 7: Put status and exports before local storage and alpha feedback

**Files:**
- Modify: `apps/web/app.py:1770-1978`
- Modify: `tests/apps/test_streamlit_app.py:141-187,1321-1936`

**Interfaces:**
- Consumes: Task 6 save markers/helpers, existing gate guidance, export functions, and alpha outcome
  workflow.
- Produces: `_render_local_review_storage(state: ReviewState, *, store: JsonReviewStore,
  store_available: bool, has_pending_review_input: bool, pending_messages: list[str]) -> None` and
  status → reasons/actions → provenance → downloads → local storage → optional alpha outcome, with
  stable download widget keys.

- [ ] **Step 1: Add RED ordering and alpha compatibility tests**

Extract the current qualified-alpha setup into this helper above the tests:

```python
def qualified_alpha_analyzed_app(app: AppTest) -> AppTest:
    app = app.checkbox(key="alpha_feedback_mode").check().run()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/repo/pull/7"
    ).run()
    app = app.text_input(key="requirements_source_url").set_value(
        "https://github.com/acme/repo/issues/6"
    ).run()
    app = app.checkbox(key="source_owner_confirmed").check().run()
    app = app.checkbox(key="no_confidential_information").check().run()
    snapshot = load_demo_snapshot().model_copy(
        update={"repository": "acme/repo", "pr_number": 7, "head_sha": "a" * 40}
    )
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()
    app = app.text_area(key="requirements_input").set_value("Export CSV").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()
```

```python
def test_summary_places_exports_before_local_storage() -> None:
    app = analyzed_demo(new_app())
    keys = _main_widget_keys(app)

    assert keys.index("download_markdown") < keys.index("save_review")
    assert keys.index("download_json") < keys.index("save_review")
    assert keys.index("download_csv") < keys.index("save_review")


def test_alpha_outcome_is_ready_after_authoritative_review_autosaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = qualified_alpha_analyzed_app(new_app())
    app = app.selectbox(key="alpha_outcome").set_value(
        AlphaOutcome.FOUND_USEFUL_GAP
    ).run()

    assert app.button(key="record_alpha_outcome").disabled is False
    assert _main_widget_keys(app).index("download_csv") < _main_widget_keys(app).index(
        "record_alpha_outcome"
    )
```

Refactor `test_alpha_mode_creates_case_after_confirming_criteria` to call this helper, remove its
manual `save_review` click, and keep the existing stored outcome and consent assertions.

- [ ] **Step 2: Run Summary tests to verify RED**

Run:

```bash
uv run pytest -q tests/apps/test_streamlit_app.py -k \
  "summary_places_exports or alpha_outcome_is_ready"
```

Expected: downloads lack stable keys and render after save/alpha controls.

- [ ] **Step 3: Reorder Summary and add stable download keys**

Render the existing status, reason codes, guidance, head SHA, ruleset, and exports immediately after
the header. Keep the same validated export source and draft-only disablement:

```python
st.header("5 · Summary & Export")
review_status = review_status_label(bundle.gate.verdict)
st.markdown(f"## Review status: **{review_status}**")
if bundle.gate.reason_codes:
    labels = [_status_label(code) for code in bundle.gate.reason_codes]
    st.write("Gate reasons: " + " · ".join(labels))
guidance = gate_guidance(bundle.gate)
if guidance:
    st.markdown("### What to do next")
    for message in guidance:
        st.text(message)
st.caption(
    f"Head SHA {bundle.review.head_sha} · Ruleset {bundle.review.ruleset_version} · "
    "results are reproducible from the exported review"
)
if has_pending_review_input:
    st.warning(
        "Resolve, submit, discard, or clear pending inputs before exporting the "
        "authoritative review."
    )
export_source = review_state if review_state is not None else bundle
markdown_report = export_markdown(export_source)
json_report = export_json(export_source)
csv_report = export_csv(export_source)
markdown_column, json_column, csv_column = st.columns(3)
with markdown_column:
    st.download_button(
        "Download Markdown",
        markdown_report,
        file_name=f"scopeproof-pr-{bundle.review.pr_number}.md",
        mime="text/markdown",
        disabled=has_pending_review_input,
        key="download_markdown",
    )
with json_column:
    st.download_button(
        "Download JSON",
        json_report,
        file_name=f"scopeproof-pr-{bundle.review.pr_number}.json",
        mime="application/json",
        disabled=has_pending_review_input,
        key="download_json",
    )
with csv_column:
    st.download_button(
        "Download CSV",
        csv_report,
        file_name=f"scopeproof-pr-{bundle.review.pr_number}.csv",
        mime="text/csv",
        disabled=has_pending_review_input,
        key="download_csv",
    )
```

Do not make downloads depend on local save success.

- [ ] **Step 4: Add one reusable local-storage recovery surface**

Build the exact pending-draft strings from the four existing flags:

```python
pending_storage_messages: list[str] = []
if has_pending_criteria_draft:
    pending_storage_messages.append(
        "Pending criteria edits are not saved or exported. Confirm or discard them "
        "before relying on this review ID."
    )
if has_pending_criteria_authoring_draft:
    pending_storage_messages.append(
        "Pending add or split criterion inputs are not saved or exported. Submit or "
        "clear them before relying on this review ID."
    )
if has_pending_requirements_draft:
    pending_storage_messages.append(
        "Pending requirements changes are not saved or exported. Prepare or discard "
        "them before relying on this review ID."
    )
if has_pending_criterion_detail_draft:
    pending_storage_messages.append(
        "Pending criterion-detail inputs are not saved or exported. Submit or clear "
        "them before relying on this review ID."
    )
```

Then render the review ID, messages, store warning, save state, and explicit recovery through this
helper:

```python
def _render_local_review_storage(
    state: ReviewState,
    *,
    store: JsonReviewStore,
    store_available: bool,
    has_pending_review_input: bool,
    pending_messages: list[str],
) -> None:
    current_fingerprint = _review_state_fingerprint(state)
    review_matches_local_save = bool(
        _review_matches_local_save(state) and not has_pending_review_input
    )
    save_failed = (
        st.session_state["failed_review_save_fingerprint"] == current_fingerprint
    )
    save_deleted = (
        st.session_state["deleted_review_save_fingerprint"] == current_fingerprint
    )
    with st.expander("Local review storage", expanded=save_failed):
        st.caption("Current review ID")
        st.code(state.review.review_id, language=None)
        for message in pending_messages:
            st.caption(message)
        if not store_available:
            export_availability = (
                "exports remain unavailable until pending review inputs are confirmed, "
                "submitted, discarded, or cleared."
                if has_pending_review_input
                else "exports remain available."
            )
            st.warning(
                "Local saving is unavailable. The current review remains open as unsaved work, "
                f"and {export_availability} Verify that the ScopeProof review directory is a "
                "regular local directory; ScopeProof will recheck it on the next interaction."
            )
        elif review_matches_local_save:
            st.caption("Saved locally — current review matches local storage.")
        elif save_failed:
            st.error(
                "The review could not be saved locally. The current review remains open as "
                "unsaved work. Verify the local review directory and review integrity, then "
                "try again."
            )
        elif save_deleted:
            st.caption("Deleted locally — use Save now to recreate this review.")
        save_label = "Retry local save" if save_failed else "Save now"
        save_clicked = st.button(
            save_label,
            key="save_review",
            disabled=(
                review_matches_local_save
                or has_pending_review_input
                or not store_available
            ),
        )
        if save_clicked:
            if _persist_review_state(state, store):
                st.session_state["review_save_notice"] = (
                    f"Review saved locally. ID: {state.review.review_id}."
                )
                st.rerun()
            else:
                st.error(
                    "The review could not be saved locally. The current review remains open "
                    "as unsaved work. Verify the local review directory and review integrity, "
                    "then try again."
                )
```

For an analyzed review, call the helper after the downloads. If a validated revised/reopened
`ReviewState` exists while `bundle is None`, call the same helper after the locked Evidence Matrix
notice; this gives a failed pre-analysis autosave an immediate retry instead of hiding recovery
until a later analysis. The two branches are mutually exclusive, so `save_review` appears once.
Pop and display `review_save_notice` before either call.

- [ ] **Step 5: Put optional alpha feedback after analyzed local storage**

Render the existing alpha outcome workflow after analyzed local storage, inside
`Alpha feedback outcome (optional)`. Keep consent, attribution, qualification, and
`record_alpha_outcome()` unchanged. Show `review_save_notice` outside collapsed expanders so an
autosave or explicit-save confirmation remains visible.

- [ ] **Step 6: Update old manual-save expectations and pre-analysis recovery**

Replace the old `test_post_save_resolution_marks_review_unsaved_again` with a test that records a
resolution, proves the fingerprint changes, loads the new persisted state, and sees `save_review`
disabled. Keep explicit-save coverage through autosave failure and deleted-record tests. Keep every
pending-draft test asserting all three downloads are disabled and the store's authoritative state
is unchanged.

Add a regression that reopens a saved review, changes and confirms a criterion while `save()` is
patched to fail, then proves `bundle is None`, the `Local review storage` expander is expanded, and
the enabled `Retry local save` button is present without requiring analysis.

- [ ] **Step 7: Run Summary, export, alpha, and full AppTest regressions**

Run:

```bash
uv run pytest -q \
  tests/apps/test_streamlit_app.py \
  tests/apps/test_web_app.py \
  tests/reporting
```

Expected: all tests pass; valid exports are immediate; alpha outcome sees the successful autosave;
drafts remain excluded.

- [ ] **Step 8: Commit Summary hierarchy**

```bash
git add apps/web/app.py tests/apps/test_streamlit_app.py
git commit -m "feat: surface review status and exports"
```

---

### Task 8: Verify the changed flow in a real browser and record bounded evidence

**Files:**
- Create: `docs/audits/workbench-ux-simplification/verification.md`
- Create: `docs/audits/workbench-ux-simplification/01-start-review.png`
- Create: `docs/audits/workbench-ux-simplification/02-confirm-criteria.png`
- Create: `docs/audits/workbench-ux-simplification/03-evidence-and-decision.png`
- Create: `docs/audits/workbench-ux-simplification/04-summary-and-export.png`
- Create: `docs/audits/workbench-ux-simplification/05-narrow-workspace.png`

**Interfaces:**
- Consumes: the completed local Streamlit workbench and constructed demo.
- Produces: current-run owner-operated browser evidence only; no customer, runtime-correctness,
  cross-platform, Stage 1, or WCAG claim.

- [ ] **Step 1: Run focused automated UI and source gates before browser work**

Run:

```bash
uv run pytest -q \
  tests/apps/test_streamlit_app.py \
  tests/apps/test_view_models.py \
  tests/apps/test_web_app.py \
  tests/test_presentation.py
uv run ruff check apps/web tests/apps
```

Expected: all tests and Ruff pass.

- [ ] **Step 2: Launch the local workbench on loopback**

Run:

```bash
uv run scopeproof-web --host 127.0.0.1 --port 8512
```

In a separate session, verify:

```bash
curl --fail --silent http://127.0.0.1:8512/_stcore/health
```

Expected health body: `ok`.

- [ ] **Step 3: Complete and capture the desktop pointer flow**

At 1280×720, verify and capture exactly these states:

1. PR URL and Fetch appear before all four optional collapsed controls.
2. Load the constructed demo, confirm four criteria using the early action, and verify the four
   criterion editors remain collapsed.
3. Run analysis, verify one compact CI summary, then select AC-01 and inspect the two evidence
   groups beside the ordinary decision.
4. Record one ordinary `Accepted` decision with reviewer `Local reviewer`; verify E3/E4 stays
   optional and collapsed.
5. Verify Summary shows the blocked/action-required gate and three downloads before local storage,
   and that autosave reports a durable local review without a manual click.

Save the first four screenshots at the exact file paths listed above. Check the browser console has
zero errors or warnings caused by ScopeProof.

- [ ] **Step 4: Complete narrow, keyboard, and zoom checks without inference**

At an actual 390×844 viewport, verify no page-level horizontal overflow, evidence precedes decision
when columns stack, every evidence item remains reachable, and downloads remain reachable. Save
`05-narrow-workspace.png`.

Using keyboard input only, attempt PR URL focus, Fetch, demo load, criteria confirmation, analysis,
criterion selection, ordinary resolution, optional external verification expansion, and downloads.
Record each exercised interaction and any unavailable harness behavior. Attempt actual 200% browser
zoom and record the measured result. If the tool cannot prove keyboard activation or zoom, classify
that row as `Not confirmed`; do not infer success from pointer or viewport evidence. Do not claim a
screen-reader, Windows, Linux, or WCAG result.

- [ ] **Step 5: Write the exact verification record and commit it**

The document must include the tested commit SHA, date, macOS/browser environment, automated command
results, the five walkthrough images, pointer outcome, narrow-width outcome, console outcome,
keyboard result, zoom result, and explicit unavailable rows for screen reader, Windows, and Linux.
It must state that the constructed demo and owner operation provide engineering evidence only and
zero Stage 1 credit.

```bash
git add docs/audits/workbench-ux-simplification
git commit -m "docs: record workbench UX verification"
```

---

### Task 9: Run release-quality local verification and finalize branch evidence

**Files:**
- Modify: `docs/audits/workbench-ux-simplification/verification.md`

**Interfaces:**
- Consumes: all completed implementation commits and browser evidence.
- Produces: exact branch-head engineering results and a clean handoff; no release or Stage 1 claim.

- [ ] **Step 1: Recreate the complete locked environment**

Run:

```bash
uv sync --extra dev --extra research --locked
uv lock --check
```

Expected: lock check and sync succeed without modifying `uv.lock`.

- [ ] **Step 2: Run static, full-suite, coverage, and deterministic benchmark gates**

Run:

```bash
uv run ruff check .
uv run pytest -q
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
uv run pytest \
  --cov=scopeproof_core \
  --cov=apps \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=95 \
  -q
```

Expected: Ruff passes; full tests pass with only the intentional live skip; both benchmarks report
zero mismatches and zero must-have False Ready outcomes; combined coverage is at least 95%.

- [ ] **Step 3: Build and smoke-test the package outside the checkout**

Create a unique temporary artifact directory and build:

```bash
artifact_dir="$(mktemp -d /tmp/scopeproof-workbench-ux-dist-XXXXXX)"
uv build --out-dir "$artifact_dir"
python -m venv "$artifact_dir/venv"
"$artifact_dir/venv/bin/python" -m pip install "$artifact_dir"/scopeproof-0.2.3-py3-none-any.whl
"$artifact_dir/venv/bin/scopeproof" benchmark
"$artifact_dir/venv/bin/scopeproof" comparison-benchmark
```

Launch the installed workbench from outside the checkout, verify `/_stcore/health` returns `ok`,
then stop only that process. Inspect wheel and source-distribution inventories and confirm they
contain no `.scopeproof`, coverage, virtual-environment, Git, bytecode, credential, or local-review
artifacts.

- [ ] **Step 4: Record exact final results without rewriting historical evidence**

Append the exact final branch SHA, test count, skip count, coverage percentage, Ruff result,
benchmark counts, artifact filenames, inventory counts, and installed-health result to the new
verification document. Do not alter the historical v0.2.3 post-merge audit or describe this branch
as public `main`.

- [ ] **Step 5: Run diff and artifact hygiene**

Run:

```bash
git diff --check origin/main...HEAD
git status --short --branch
git ls-files | rg '(^|/)(\.coverage|\.scopeproof|\.venv|__pycache__)(/|$)|\.pyc$'
```

Expected: diff check passes; only the intentional verification-document update is uncommitted;
artifact scan returns no tracked generated data.

- [ ] **Step 6: Commit final exact evidence and verify a clean branch**

```bash
git add docs/audits/workbench-ux-simplification/verification.md
git commit -m "docs: finalize workbench UX evidence"
git status --short --branch
```

Expected: the branch is clean and ahead of `origin/main`; it remains local until the owner separately
authorizes push/PR/merge.
