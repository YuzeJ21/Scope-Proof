"""Explicit source selections stay separate from automatic and human review truth."""

from unittest.mock import patch

import pytest

from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
from scopeproof_core.storage.json_store import JsonReviewStore, default_local_review_directory
from tests.apps.test_streamlit_app import load_demo, new_app


def reference_app():
    app = load_demo(new_app())
    app.session_state["snapshot"].files.append(
        ChangedFile(
            path="src/reference_only.py",
            status="modified",
            lines=[
                ChangedLine(
                    change_type=LineChangeType.ADDED, line_number=7, content="    return 17"
                )
            ],
        )
    )
    app = app.run()
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert not app.exception
    return app


def choose_reference(app):
    app = (
        app.selectbox(key="selected_reference_source")
        .set_value("changed_file:src/reference_only.py")
        .run()
    )
    return app.selectbox(key="selected_reference_line").set_value(7).run()


def complete_reference(app):
    app = choose_reference(app)
    app = (
        app.text_input(key="selected_reference_reviewer")
        .set_value("Constructed automated reviewer")
        .run()
    )
    return (
        app.text_area(key="selected_reference_rationale")
        .set_value("Constructed omitted-line reference for explicit inspection.")
        .run()
    )


def test_omitted_line_requires_explicit_choice_then_saves_without_upgrading_review() -> None:
    app = reference_app()
    before = app.session_state["review_state"].model_dump(mode="json")
    assert not any(e["file_path"] == "src/reference_only.py" for e in before["bundle"]["evidence"])
    assert app.selectbox(key="selected_reference_source").value is None
    assert app.button(key="save_selected_reference").disabled
    app = complete_reference(app)
    assert not app.button(key="save_selected_reference").disabled
    with (
        patch(
            "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
            side_effect=AssertionError("M3 must not fetch"),
        ),
        patch("subprocess.run", side_effect=AssertionError("M3 must not execute target code")),
    ):
        app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    state = app.session_state["review_state"]
    refs = state.bundle.reviewer_selected_references
    assert len(refs) == 1
    assert refs[0].file_path == "src/reference_only.py"
    assert refs[0].line_number == 7 and refs[0].excerpt == "    return 17"
    assert refs[0].criterion_id == app.selectbox(key="selected_criterion").value
    assert refs[0].reviewer == "Constructed automated reviewer"
    after = state.model_dump(mode="json")
    for field in (
        "evidence",
        "findings",
        "gate",
        "retrieval_diagnostics",
        "resolutions",
        "runtime_evidence",
        "junit_evidence_imports",
        "file_scope_decisions",
    ):
        assert after["bundle"][field] == before["bundle"][field]
    assert after["resolution_events"] == before["resolution_events"]
    assert after["review"] == before["review"]
    assert after["analysis_history"] == before["analysis_history"]
    assert app.selectbox(key="selected_reference_source").value is None
    assert app.text_area(key="selected_reference_rationale").value == ""
    saved = JsonReviewStore(default_local_review_directory()).load(state.review.review_id)
    assert saved.bundle.reviewer_selected_references == refs


@pytest.mark.parametrize("field", ["source", "reviewer", "rationale"])
def test_any_selection_draft_blocks_authoritative_exports_until_cleared(field: str) -> None:
    app = reference_app()
    if field == "source":
        app = choose_reference(app)
    elif field == "reviewer":
        app = app.text_input(key="selected_reference_reviewer").set_value("Draft actor").run()
    else:
        app = app.text_area(key="selected_reference_rationale").set_value("Unsaved draft").run()
    assert not app.exception
    assert all(b.disabled for b in app.download_button if b.key.startswith("download_"))
    assert app.button(key="record_final_acceptance").disabled
    app = app.button(key="clear_criterion_detail_drafts").click().run()
    assert not app.exception
    assert all(
        not b.disabled
        for b in app.download_button
        if b.key in {"download_markdown", "download_json", "download_csv"}
    )


def test_criterion_change_clears_selection_and_rationale_without_recording() -> None:
    app = complete_reference(reference_app())
    old = app.selectbox(key="selected_criterion").value
    other = next(v for v in app.selectbox(key="selected_criterion").options if v != old)
    app = app.selectbox(key="selected_criterion").set_value(other).run()
    assert not app.exception
    assert app.selectbox(key="selected_reference_source").value is None
    assert app.text_area(key="selected_reference_rationale").value == ""
    assert app.session_state["review_state"].bundle.reviewer_selected_references == []


def test_failed_core_transition_preserves_draft_and_does_not_change_record() -> None:
    app = complete_reference(reference_app())
    before = app.session_state["review_state"].model_dump(mode="json")
    with patch(
        "apps.web.selected_references.append_reviewer_selected_reference",
        side_effect=ValueError("Changed source"),
    ):
        app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert app.session_state["review_state"].model_dump(mode="json") == before
    assert app.text_area(key="selected_reference_rationale").value.startswith("Constructed")
    assert any("could not be recorded" in v.value for v in app.error)


def test_saved_references_reopen_without_source_and_remain_inspectable() -> None:
    app = complete_reference(reference_app())
    app = app.button(key="save_selected_reference").click().run()
    review_id = app.session_state["review_state"].review.review_id
    app = new_app()
    app = app.selectbox(key="saved_reopen_review_id").set_value(review_id).run()
    app = app.button(key="reopen_review").click().run()
    assert not app.exception
    assert app.session_state["snapshot"] is None
    text = "\n".join(
        v.value for group in (app.text, app.caption, app.code, app.markdown) for v in group
    )
    assert "Reviewer-selected references" in text
    assert "src/reference_only.py" in text and "Constructed automated reviewer" in text
    assert "Load matching source" in text
    assert not any(b.key == "save_selected_reference" and not b.disabled for b in app.button)


@pytest.mark.parametrize("changed", ["content", "head"])
def test_changed_loaded_source_clears_staged_reference_before_save(changed: str) -> None:
    app = complete_reference(reference_app())
    snapshot = app.session_state["snapshot"]
    if changed == "content":
        snapshot.files[-1].lines[0].content = "    return 18"
    else:
        snapshot.head_sha = "changed-source-head"
    app = app.run()
    assert not app.exception
    assert app.session_state["review_state"].bundle.reviewer_selected_references == []
    assert app.session_state["selected_reference_rationale"] == ""
    assert app.session_state["selected_reference_source"] is None


def test_externally_changed_saved_record_is_not_overwritten_by_selection() -> None:
    from scopeproof_core.reviews.lifecycle import append_resolution
    from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent

    app = reference_app()
    state = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
    app = complete_reference(app)
    changed = append_resolution(state, ResolutionEvent(
        criterion_id="AC-01", reviewer="Concurrent constructed actor",
        decision=HumanDecision.CHANGE_REQUIRED, comment="Newer decision must survive.",
    ))
    store.save(changed)
    original = (store.directory / f"{state.review.review_id}.json").read_bytes()
    app = app.button(key="save_selected_reference").click().run()
    assert not app.exception
    assert (store.directory / f"{state.review.review_id}.json").read_bytes() == original
    assert app.session_state["review_save_conflict"]
    assert any("changed" in v.value.lower() for v in app.warning)


def test_other_pending_decision_blocks_saving_a_reference() -> None:
    from scopeproof_core.schemas.models import HumanDecision

    app = complete_reference(reference_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.CHANGE_REQUIRED).run()
    assert not app.exception
    assert app.button(key="save_selected_reference").disabled


def test_no_available_source_lines_gives_bounded_feedback() -> None:
    app = reference_app()
    for file in app.session_state["snapshot"].files:
        file.lines.clear()
    app = app.run()
    assert not app.exception
    assert any("No inspectable source lines" in v.value for v in app.caption)
