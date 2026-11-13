from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from apps.web import deferred_exports
from scopeproof_core.reporting.exporters import export_html
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    can_record_final_acceptance,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    ChangedFile,
    CheckState,
    CIObservation,
    CIReasonCode,
    HumanDecision,
    ResolutionEvent,
)
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import (
    analyzed_demo,
    analyzed_standard_demo,
    load_demo,
    new_app,
    resolve_all_criteria,
    select_saved_review,
)


def test_overview_excludes_unsubmitted_file_scope_draft_from_save_status() -> None:
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(
        ChangedFile(path="src/unrelated.py", status="modified")
    )
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    state = app.session_state["review_state"]
    assert state.bundle.gate.blocking_criteria
    assert "uncited_changed_files" not in state.bundle.gate.reason_codes
    assert "Unresolved inspected changed files: 1" in [item.value for item in app.text]
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    app = app.selectbox(key="scope_file_path").set_value("src/unrelated.py").run()
    assert "Local save: Saved locally" in [item.value for item in app.text]
    assert not app.button(key="open_next_overview_blocker").disabled
    assert app.button(key="save_scope_decision").disabled
    app = app.text_area(key="scope_note").set_value("Unsubmitted scope explanation").run()
    assert "Local save: Pending inputs excluded" in [item.value for item in app.text]
    assert app.button(key="open_next_overview_blocker").disabled
    assert app.text_area(key="scope_note").value == "Unsubmitted scope explanation"
    assert "[Go to changed-file scope](#changed-file-scope)" in [
        item.value for item in app.markdown
    ]

    app.session_state["source_authority_guard"].block(state)
    app = app.run()
    assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
    assert "Unresolved inspected changed files: 1" not in [item.value for item in app.text]
    assert "[Go to changed-file scope](#changed-file-scope)" not in [
        item.value for item in app.markdown
    ]
    assert "Clear pending review inputs before refreshing the review." in [
        item.value for item in app.caption
    ]
    assert app.text_area(key="scope_note").value == "Unsubmitted scope explanation"


def test_file_scope_draft_pauses_current_downloads_until_discarded_or_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    file_path = "src/unrelated.py"
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(ChangedFile(path=file_path, status="modified"))
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    before = app.session_state["review_state"].model_copy(deep=True)
    store = JsonReviewStore(storage)
    record = storage / f"{before.review.review_id}.json"
    saved_bytes = record.read_bytes()

    app = app.selectbox(key="scope_file_path").set_value(file_path).run()
    assert {button.key for button in app.download_button} == {
        "download_markdown", "download_json", "download_csv", "download_html",
    }
    assert all(not button.disabled for button in app.download_button)
    assert "Saved locally — current review matches local storage." in [
        item.value for item in app.caption
    ]

    app = app.selectbox(key="scope_disposition").set_value("outside_confirmed_criteria").run()
    assert all(button.disabled for button in app.download_button)
    assert app.button(key="save_review").disabled
    assert "Saved locally — current review matches local storage." not in [
        item.value for item in app.caption
    ]
    assert "Local save: Pending inputs excluded" in [item.value for item in app.text]
    assert (
        "Save or discard the pending file-scope decision before saving or downloading the "
        "current review."
    ) in [item.value for item in app.caption]
    assert app.session_state["review_state"] == store.load(before.review.review_id) == before
    assert record.read_bytes() == saved_bytes

    app = app.button(key="discard_scope_decision_draft").click().run()
    assert all(not button.disabled for button in app.download_button)
    assert "Saved locally — current review matches local storage." in [
        item.value for item in app.caption
    ]
    assert record.read_bytes() == saved_bytes

    app = app.selectbox(key="scope_file_path").set_value(file_path).run()
    app = app.text_area(key="scope_note").set_value("Reviewed file against the criteria.").run()
    assert all(button.disabled for button in app.download_button)
    app = app.selectbox(key="scope_disposition").set_value("outside_confirmed_criteria").run()
    assert all(button.disabled for button in app.download_button)
    assert app.button(key="save_review").disabled
    assert record.read_bytes() == saved_bytes
    app = app.button(key="save_scope_decision").click().run()

    assert not app.exception
    assert all(not button.disabled for button in app.download_button)
    after = store.load(before.review.review_id)
    assert after == app.session_state["review_state"]
    assert after.resolution_events == before.resolution_events
    decision, = after.bundle.file_scope_decisions
    assert decision.path == file_path
    assert decision.disposition == "outside_confirmed_criteria"
    assert decision.note == "Reviewed file against the criteria."


def test_file_scope_draft_expires_an_already_rendered_current_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(tmp_path / "reviews"))
    html_callbacks = []
    real_deferred = deferred_exports.deferred_review_export

    def capture_html(source, renderer, **kwargs):
        callback = real_deferred(source, renderer, **kwargs)
        if renderer is export_html:
            html_callbacks.append(callback)
        return callback

    monkeypatch.setattr(deferred_exports, "deferred_review_export", capture_html)
    file_path = "src/unrelated.py"
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(ChangedFile(path=file_path, status="modified"))
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    old_download = html_callbacks[-1]

    app = app.selectbox(key="scope_file_path").set_value(file_path).run()
    assert "ScopeProof Acceptance Review" in old_download()
    app = app.text_area(key="scope_note").set_value("Unsubmitted scope explanation").run()

    with pytest.raises(deferred_exports.DeferredExportUnavailable, match="file-scope decision"):
        old_download()

    app = app.button(key="discard_scope_decision_draft").click().run()
    with pytest.raises(deferred_exports.DeferredExportUnavailable, match="file-scope decision"):
        old_download()
    assert "ScopeProof Acceptance Review" in html_callbacks[-1]()


def test_file_scope_draft_pauses_saving_an_otherwise_writable_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = tmp_path / "reviews"
    monkeypatch.setenv("SCOPEPROOF_WORKBENCH_STORAGE_DIR", str(storage))
    file_path = "src/unrelated.py"
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(ChangedFile(path=file_path, status="modified"))
    app = app.run().button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    original = app.session_state["review_state"].model_copy(deep=True)
    review_id = original.review.review_id
    store = JsonReviewStore(storage)
    record = storage / f"{review_id}.json"
    original_bytes = record.read_bytes()

    app = app.selectbox(key="scope_file_path").set_value(file_path).run()
    app = app.text_area(key="scope_note").set_value("Unsubmitted scope explanation").run()
    unsaved = append_resolution(
        original,
        ResolutionEvent(
            criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
            comment="Earlier in-memory criterion decision", reviewer="Fixture reviewer",
        ),
    )
    app.session_state["review_state"] = unsaved
    app.session_state["bundle"] = unsaved.bundle
    app = app.run()

    assert not app.exception
    save_button = app.button(key="save_review")
    assert save_button.label == "Save now"
    assert save_button.disabled
    assert app.session_state["review_state"] == unsaved
    assert store.load(review_id) == original
    assert record.read_bytes() == original_bytes

    app = app.button(key="discard_scope_decision_draft").click().run()

    assert not app.exception
    assert app.session_state["review_state"] == store.load(review_id) == unsaved
    assert "Saved locally — current review matches local storage." in [
        item.value for item in app.caption
    ]
    assert not store.load(review_id).bundle.file_scope_decisions


def test_overview_scope_preview_is_bounded_and_reopens_with_failing_checks() -> None:
    app = load_demo(new_app())
    snapshot = app.session_state["snapshot"]
    snapshot.files.extend(
        ChangedFile(path=path, status="modified")
        for path in ("z-last.py", "b\tfile.py", "a<img>.py", "c\nfile.py")
    )
    snapshot.check_state = CheckState.FAILING
    snapshot.ci_observation = CIObservation(
        state=CheckState.FAILING,
        reason="Constructed failing check",
        reason_code=CIReasonCode.FAILING_CHECK_RUNS,
        total_check_runs=1,
        failing_check_runs=1,
    )
    app = app.run().button(key="confirm_criteria").click().run()
    app = resolve_all_criteria(app.button(key="run_analysis").click().run())
    state = app.session_state["review_state"]
    assert state.bundle.gate.reason_codes == ["required_checks_failing"]
    record = JsonReviewStore(default_local_review_directory()).directory / (
        f"{state.review.review_id}.json"
    )
    saved_bytes = record.read_bytes()
    reopened = select_saved_review(new_app(), state.review.review_id)
    reopened = reopened.button(key="reopen_review").click().run()

    assert not reopened.exception
    assert reopened.session_state["snapshot"] is None
    assert "Unresolved inspected changed files: 4" in [item.value for item in reopened.text]
    assert r"a<img>.py" + "\n" + r"b\tfile.py" + "\n" + r"c\u000afile.py" in [
        item.value for item in reopened.text
    ]
    assert "1 more in changed-file scope." in [item.value for item in reopened.caption]
    assert not any("a<img>.py" in item.value for item in reopened.markdown)
    assert record.read_bytes() == saved_bytes


def _final_acceptance_panel_text(app: AppTest) -> list[str]:
    nodes = list(app.main)
    headings = {
        node.value: index for index, node in enumerate(nodes) if node.type == "markdown"
    }
    start = headings["### Final review acceptance"]
    end = headings["### Resolution history"]
    return [
        node.value for node in nodes[start + 1:end]
        if node.type in {"caption", "info", "markdown", "text", "warning"}
    ]


@pytest.mark.parametrize(
    ("checks_failing", "scope_unresolved"),
    [
        pytest.param(True, True, id="checks-and-scope"),
        pytest.param(True, False, id="checks-only"),
        pytest.param(False, True, id="scope-only"),
        pytest.param(False, False, id="eligible"),
    ],
)
def test_final_acceptance_panel_explains_blockers_after_every_criterion_decision(
    checks_failing: bool, scope_unresolved: bool,
) -> None:
    app = load_demo(new_app())
    snapshot = app.session_state["snapshot"]
    if scope_unresolved:
        snapshot.files.append(ChangedFile(path="src/unrelated.py", status="modified"))
    if checks_failing:
        snapshot.check_state = CheckState.FAILING
        snapshot.ci_observation = CIObservation(
            state=CheckState.FAILING,
            reason="Constructed failing check",
            reason_code=CIReasonCode.FAILING_CHECK_RUNS,
            total_check_runs=1,
            failing_check_runs=1,
        )
    app = app.run().button(key="confirm_criteria").click().run()
    app = resolve_all_criteria(app.button(key="run_analysis").click().run())
    state = app.session_state["review_state"]
    assert len(state.bundle.resolutions) == len(state.bundle.criteria)
    store = JsonReviewStore(default_local_review_directory())
    record = store.directory / f"{state.review.review_id}.json"
    saved_bytes = record.read_bytes()

    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()

    assert not app.exception
    assert app.session_state["review_state"] == store.load(state.review.review_id) == state
    assert record.read_bytes() == saved_bytes
    eligible = not (checks_failing or scope_unresolved)
    assert can_record_final_acceptance(state) == eligible
    assert app.button(key="record_final_acceptance").disabled == (not eligible)
    panel = _final_acceptance_panel_text(app)
    assert not any(item.startswith("Review criteria without a decision") for item in panel)
    checks_message = (
        "Observed GitHub checks are failing. Review them on the pull request, "
        "then check the current head."
    )
    scope_message = (
        "Changed-file scope is unresolved. Review the uncited files and record "
        "their scope or obtain criterion evidence."
    )
    assert (checks_message in panel) == checks_failing
    assert (scope_message in panel) == scope_unresolved
    scope_link = "[Review changed-file scope before acceptance](#changed-file-scope)"
    assert (scope_link in panel) == scope_unresolved
    assert [item.value for item in app.markdown].count(
        "[Go to changed-file scope](#changed-file-scope)"
    ) == int(scope_unresolved)

    markdown = [item.value for item in app.markdown]
    assert "### Changed-file scope" in markdown
    acceptance_link = (
        "[Record final acceptance after reviewing every criterion](#final-review-acceptance)"
    )
    assert (acceptance_link in markdown) == eligible


def test_overview_opens_next_blocker_without_writing_or_discarding_inputs() -> None:
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
    assert "### Decision overview" in [item.value for item in app.markdown]
    assert "**Recorded verdict: Action required**" in [item.value for item in app.markdown]
    assert f"Reviewed head: {state.review.head_sha}" in [item.value for item in app.text]
    assert "Blocking criteria (2): AC-02, AC-03" in [item.value for item in app.text]
    assert "Recorded final acceptance: No" in [item.value for item in app.text]
    assert "Local save: Saved locally" in [item.value for item in app.text]
    assert any("Constructed demo" in item.value for item in app.caption)

    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    app = app.text_input(key="runtime_artifact_reference").set_value("pending-reference").run()
    assert app.button(key="open_next_overview_blocker").disabled
    assert app.selectbox(key="selected_criterion").value == "AC-01"
    assert app.text_input(key="runtime_artifact_reference").value == "pending-reference"
    assert "Local save: Pending inputs excluded" in [item.value for item in app.text]
    assert all(button.disabled for button in app.download_button)

    app = app.text_input(key="runtime_artifact_reference").set_value("").run()
    app = app.button(key="open_next_overview_blocker").click().run()
    assert not app.exception
    assert app.selectbox(key="selected_criterion").value == "AC-02"
    assert "[Go to AC-02 decision controls](#4-criterion-review)" in [
        item.value for item in app.markdown
    ]
    assert app.session_state["review_state"] == store.load(state.review.review_id) == state


def test_overview_distinguishes_recorded_acceptance_from_source_and_conflict() -> None:
    app = resolve_all_criteria(analyzed_standard_demo(new_app()))
    app = app.button(key="record_final_acceptance").click().run()
    state = app.session_state["review_state"]
    assert "Source loaded for the reviewed head." in [item.value for item in app.caption]
    assert "**Recorded verdict: Review complete**" in [item.value for item in app.markdown]
    assert "Recorded final acceptance: Yes" in [item.value for item in app.text]
    assert "[See next steps](#6-summary-and-export)" in [item.value for item in app.markdown]

    app = select_saved_review(new_app(), state.review.review_id)
    app = app.button(key="reopen_review").click().run()
    assert "Saved analysis. Current PR head unverified in this view." in [
        item.value for item in app.caption
    ]
    assert "**Recorded verdict: Review complete**" in [item.value for item in app.markdown]
    assert "Recorded final acceptance: Yes" in [item.value for item in app.text]
    assert "Local save: Saved locally" in [item.value for item in app.text]

    app.session_state["source_authority_guard"].block(state)
    app = app.run()
    assert "**Decision status: Refresh required**" in [item.value for item in app.markdown]
    assert "**Recorded verdict: Review complete**" not in [item.value for item in app.markdown]
    assert "[See refresh guidance](#6-summary-and-export)" in [
        item.value for item in app.markdown
    ]
    assert "Recorded final acceptance: Yes" in [item.value for item in app.text]
    assert all(button.disabled for button in app.download_button)


def test_overview_ignores_click_bound_to_an_earlier_saved_state() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    before = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
    # Keep AC-02 first so a criterion-only callback would appear valid.
    after, _ = store.mutate(
        before.review.review_id,
        lambda state: append_resolution(
            state,
            ResolutionEvent(
                criterion_id="AC-03",
                decision=HumanDecision.CHANGE_REQUIRED,
                comment="Constructed concurrent decision",
            ),
        ),
    )
    app = app.button(key="open_next_overview_blocker").click().run()
    assert not app.exception
    assert app.session_state["review_state"] == after
    assert app.selectbox(key="selected_criterion").value == "AC-01"
    assert app.button(key="open_next_overview_blocker").label == "Open next blocker · AC-02"


def test_overview_and_exports_disappear_after_late_external_revision() -> None:
    app = analyzed_demo(new_app())
    before = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
    revised = revise_criteria(before, before.criteria_revision.criteria, "Revised requirements")
    original_locked_load = JsonReviewStore.locked_load
    locks = 0

    @contextmanager
    def update_between_page_and_status(store, review_id):
        nonlocal locks
        locks += 1
        if locks == 2:
            store.save(revised)
        with original_locked_load(store, review_id) as persisted:
            yield persisted

    with patch.object(JsonReviewStore, "locked_load", update_between_page_and_status):
        app = app.run()

    assert not app.exception
    assert locks >= 2
    assert app.session_state["review_state"] == store.load(before.review.review_id) == revised
    assert "### Decision overview" not in [item.value for item in app.markdown]
    assert not app.download_button


def test_overview_restores_selection_when_late_update_changes_next_blocker() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    before = app.session_state["review_state"]
    original_locked_load = JsonReviewStore.locked_load
    locks = 0

    @contextmanager
    def accept_between_page_and_status(store, review_id):
        nonlocal locks
        locks += 1
        if locks == 2:
            store.mutate(
                review_id,
                lambda state: append_resolution(
                    state,
                    ResolutionEvent(
                        criterion_id="AC-02",
                        decision=HumanDecision.ACCEPTED,
                        comment="Constructed concurrent acceptance",
                    ),
                ),
            )
        with original_locked_load(store, review_id) as persisted:
            yield persisted

    with patch.object(JsonReviewStore, "locked_load", accept_between_page_and_status):
        app = app.button(key="open_next_overview_blocker").click().run()

    assert not app.exception
    assert app.button(key="open_next_overview_blocker").label == "Open next blocker · AC-03"
    assert app.session_state["review_state"] != before
    assert app.selectbox(key="selected_criterion").value == "AC-01"
