from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from scopeproof_core.demo import load_demo_snapshot
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    IngestionState,
    Priority,
)

APP_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "app.py"


def new_app() -> AppTest:
    return AppTest.from_file(APP_PATH).run()


def load_demo(app: AppTest) -> AppTest:
    return app.button(key="load_demo").click().run()


def analyzed_demo(app: AppTest) -> AppTest:
    app = load_demo(app)
    app = app.button(key="confirm_criteria").click().run()
    return app.button(key="run_analysis").click().run()


def saved_demo_review(app: AppTest) -> tuple[AppTest, str]:
    app = analyzed_demo(app)
    review_id = app.session_state["review_state"].review.review_id
    app = app.button(key="save_review").click().run()
    return app, review_id


def select_saved_review(app: AppTest, review_id: str) -> AppTest:
    return app.selectbox(key="saved_reopen_review_id").set_value(review_id).run()


def evidence_matrix_table(app: AppTest) -> str:
    return next(
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith("| Criterion | Requirement | Priority |")
    )


def test_analysis_is_disabled_before_criteria_confirmation() -> None:
    app = new_app()
    assert app.button(key="run_analysis").disabled is True


def test_product_disclaimer_is_visible() -> None:
    app = new_app()
    markdown_text = [markdown.value for markdown in app.markdown]
    caption_text = [caption.value for caption in app.caption]
    visible_text = "\n".join(
        [*markdown_text, *caption_text]
    )
    assert "does not replace QA" in visible_text
    assert "No paid LLM API" in visible_text


def test_partial_public_pr_fetch_shows_bounded_analysis_and_skipped_paths() -> None:
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ingestion_state": IngestionState.PARTIAL,
            "warnings": [
                "File limit reached; skipped 2 changed files.",
                "![remote image](https://example.invalid/pixel.png)",
            ],
            "skipped_files": ["src/one.py", "src/two.py"],
        }
    )
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/repo/pull/7"
    ).run()
    with patch(
        "scopeproof_core.github.client.GitHubClient.fetch_pull_request",
        return_value=snapshot,
    ):
        app = app.button(key="fetch_pr").click().run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Partial PR ingestion" in warning_text
    assert "gate cannot be Ready" in warning_text
    assert "File limit reached; skipped 2 changed files." not in warning_text
    code_text = "\n".join(item.value for item in app.code)
    assert "File limit reached; skipped 2 changed files." in code_text
    assert "![remote image](https://example.invalid/pixel.png)" in code_text
    assert [item.label for item in app.expander if "Skipped changed files" in item.label] == [
        "Skipped changed files (2)"
    ]
    assert "src/one.py" in code_text


def test_reopened_partial_review_keeps_ingestion_recovery_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    snapshot = load_demo_snapshot().model_copy(
        update={
            "ingestion_state": IngestionState.PARTIAL,
            "warnings": ["File limit reached; skipped 1 changed files."],
            "skipped_files": ["src/reopen-skipped.py"],
        }
    )
    app = new_app()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=snapshot):
        app = app.button(key="load_demo").click().run()
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    review_id = app.session_state["review_state"].review.review_id
    app = app.button(key="save_review").click().run()

    fresh = select_saved_review(new_app(), review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    warning_text = "\n".join(item.value for item in fresh.warning)
    assert "Partial PR ingestion" in warning_text
    code_text = "\n".join(item.value for item in fresh.code)
    assert "File limit reached; skipped 1 changed files." in code_text
    assert "src/reopen-skipped.py" in code_text


def test_reopen_review_is_a_collapsed_secondary_path_before_start_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()

    assert [item.label for item in app.expander] == ["Reopen saved review"]
    assert app.text_input(key="reopen_review_id").value == ""
    assert app.button(key="reopen_review").disabled is True
    assert "No saved local reviews found." in [item.value for item in app.caption]
    assert "### Reopen saved review" not in [item.value for item in app.markdown]


def test_saved_review_is_discoverable_and_selectable_in_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    saved_ids = fresh.selectbox(key="saved_reopen_review_id")
    assert saved_ids.options == [review_id]
    assert saved_ids.value is None
    assert fresh.button(key="reopen_review").disabled is True
    caption_text = "\n".join(item.value for item in fresh.caption)
    assert "1 saved local review found" in caption_text
    assert "validated when opened" in caption_text

    fresh = saved_ids.set_value(review_id).run()
    fresh = fresh.button(key="reopen_review").click().run()

    assert fresh.session_state["review_state"] == saved_state
    assert "Review reopened from local storage" in "\n".join(
        message.value for message in fresh.success
    )


def test_delete_saved_review_requires_selection_and_confirmation_and_deletes_only_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, first_review_id = saved_demo_review(new_app())
    _, second_review_id = saved_demo_review(new_app())

    app = new_app()
    assert not [item for item in app.button if item.key == "delete_saved_review"]
    assert not [
        item
        for item in app.checkbox
        if item.key == "delete_saved_review_confirmed"
    ]

    app = select_saved_review(app, first_review_id)
    assert app.checkbox(key="delete_saved_review_confirmed").value is False
    assert app.button(key="delete_saved_review").disabled is True

    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    assert app.button(key="delete_saved_review").disabled is False
    app = app.button(key="delete_saved_review").click().run()

    assert app.selectbox(key="saved_reopen_review_id").options == [second_review_id]
    assert app.selectbox(key="saved_reopen_review_id").value is None
    assert app.session_state["delete_saved_review_confirmed"] is False


def test_delete_saved_review_controls_stay_hidden_for_manually_typed_missing_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()

    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()

    assert not [
        item
        for item in app.checkbox
        if item.key == "delete_saved_review_confirmed"
    ]
    assert not [item for item in app.button if item.key == "delete_saved_review"]


def test_delete_saved_open_review_preserves_exact_state_as_unsaved_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.button(key="reopen_review").click().run()
    open_state = app.session_state["review_state"]

    app = select_saved_review(app, review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()
    app = app.button(key="delete_saved_review").click().run()

    assert app.session_state["review_state"] == open_state
    assert app.session_state["saved_review_fingerprint"] is None
    assert (
        "Saved review deleted. The open review remains available as unsaved work."
        in [message.value for message in app.success]
    )


def test_delete_saved_review_race_uses_fixed_recovery_without_raw_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    app = select_saved_review(new_app(), review_id)
    app = app.checkbox(key="delete_saved_review_confirmed").check().run()

    with patch(
        "scopeproof_core.storage.json_store.JsonReviewStore.delete",
        side_effect=FileNotFoundError(review_id),
    ):
        app = app.button(key="delete_saved_review").click().run()

    recovery = (
        "The selected saved review was already removed. Refresh the saved review list."
    )
    assert recovery in [message.value for message in app.warning]
    assert not app.exception
    rendered_recovery = "\n".join(
        message.value for message in [*app.warning, *app.error]
    )
    assert str(tmp_path) not in rendered_recovery


def test_symlinked_review_store_has_safe_recovery_and_disables_storage_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    outside = tmp_path / "outside"
    outside.mkdir()
    store_parent = tmp_path / ".scopeproof"
    store_parent.mkdir()
    (store_parent / "reviews").symlink_to(outside, target_is_directory=True)

    app = new_app()

    assert [item.value for item in app.error] == [
        "Local review storage is unavailable. Verify that the ScopeProof review directory "
        "is a regular local directory."
    ]
    assert not [item for item in app.text_input if item.key == "reopen_review_id"]
    assert not [item for item in app.selectbox if item.key == "saved_reopen_review_id"]
    assert app.button(key="reopen_review").disabled is True

    app = analyzed_demo(app)
    assert app.button(key="save_review").disabled is True
    assert list(outside.iterdir()) == []


def test_regular_file_review_store_has_safe_recovery_and_disables_storage_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    store_parent = tmp_path / ".scopeproof"
    store_parent.mkdir()
    store_root = store_parent / "reviews"
    store_root.write_text("not a directory", encoding="utf-8")

    app = new_app()

    assert [item.value for item in app.error] == [
        "Local review storage is unavailable. Verify that the ScopeProof review directory "
        "is a regular local directory."
    ]
    assert not [item for item in app.text_input if item.key == "reopen_review_id"]
    assert not [item for item in app.selectbox if item.key == "saved_reopen_review_id"]
    assert app.button(key="reopen_review").disabled is True

    app = analyzed_demo(app)
    assert app.button(key="save_review").disabled is True
    assert store_root.read_text(encoding="utf-8") == "not a directory"


def test_blank_public_pr_url_remains_neutral_and_disables_fetch() -> None:
    app = new_app()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Enter a public GitHub pull request URL" not in warning_text
    assert app.button(key="fetch_pr").disabled is True


def test_malformed_public_pr_url_shows_format_guidance_and_disables_fetch() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/not-a-number"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert (
        "Enter a public GitHub pull request URL in this format: "
        "`https://github.com/OWNER/REPO/pull/NUMBER`."
    ) in warning_text
    assert app.button(key="fetch_pr").disabled is True


def test_canonical_public_pr_url_enables_fetch_without_format_warning() -> None:
    app = new_app()
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/widget/pull/42"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Enter a public GitHub pull request URL" not in warning_text
    assert app.button(key="fetch_pr").disabled is False


def test_demo_loads_confirmable_criteria() -> None:
    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    assert app.session_state["criteria_confirmed"] is False
    assert len(app.text_input) >= 4
    assert app.button(key="confirm_criteria").disabled is False


def test_demo_marks_requirements_prepared_and_exposes_confirmation_link() -> None:
    app = load_demo(new_app())

    assert app.button(key="prepare_criteria").disabled is True
    assert "Criteria prepared. Review the set before explicitly confirming it." in [
        item.value for item in app.success
    ]
    assert "[Continue to 2 · Confirm Criteria](#2-confirm-criteria)" in [
        item.value for item in app.markdown
    ]
    assert app.session_state["criteria_confirmed"] is False
    assert app.button(key="run_analysis").disabled is True


def test_editing_prepared_requirements_reenables_preparation() -> None:
    app = load_demo(new_app())
    app = app.text_area(key="requirements_input").set_value(
        "Users can export the currently filtered list as CSV."
    ).run()

    assert app.button(key="prepare_criteria").disabled is False
    assert "Criteria prepared. Review the set before explicitly confirming it." not in [
        item.value for item in app.success
    ]
    assert "[Continue to 2 · Confirm Criteria](#2-confirm-criteria)" not in [
        item.value for item in app.markdown
    ]


def test_criteria_confirmation_explains_required_evidence_levels() -> None:
    app = load_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence levels set the minimum proof needed for each criterion: "
        "E1 = implementation or contract candidate; E2 = test candidate; "
        "E3 = manually recorded runtime verification. Static PR analysis can produce "
        "only E1 or E2."
    ) in caption_text


def test_evidence_matrix_explains_observed_evidence_levels() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)

    assert (
        "Evidence levels: E0 = no candidate found; E1 = implementation or contract candidate; "
        "E2 = test candidate; E3 = manually recorded runtime verification; "
        "E4 = explicit human acceptance. Levels describe evidence type, not correctness."
    ) in caption_text


def test_sidebar_reports_confirmation_and_next_action_in_same_run() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert "active_step" not in app.session_state.filtered_state


def test_criteria_confirmation_shows_one_durable_success_message() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()

    assert [item.value for item in app.success] == [
        "Criteria confirmed by the reviewer."
    ]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text
    assert app.button(key="run_analysis").disabled is False


def test_sidebar_reports_analysis_and_review_availability() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    sidebar_text = "\n".join(markdown.value for markdown in app.sidebar.markdown)
    assert "Complete — Analysis generated" in sidebar_text
    assert "Complete — Review and export available" in sidebar_text


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_blank_criterion_edit_stays_recoverable_and_cannot_be_confirmed(text: str) -> None:
    app = analyzed_demo(new_app())
    confirmed_text = app.session_state["criteria"][0].text

    app = app.text_input(key="criterion_text_AC-01").set_value(text).run()

    assert not app.exception
    assert app.session_state["criteria"][0].text == confirmed_text
    assert app.button(key="confirm_criteria").disabled is True
    assert app.button(key="run_analysis").disabled is True
    assert "AC-01: Criterion text cannot be blank." in [
        item.value for item in app.warning
    ]


def test_pending_criterion_text_edit_requires_reconfirmation_before_analysis() -> None:
    app = analyzed_demo(new_app())
    confirmed_text = app.session_state["criteria"][0].text

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "Changed visible criterion"
    ).run()

    assert app.text_input(key="criterion_text_AC-01").value == "Changed visible criterion"
    assert app.session_state["criteria"][0].text == confirmed_text
    assert app.session_state["bundle"].criteria[0].text == confirmed_text
    assert app.button(key="run_analysis").disabled is True
    assert (
        "Criteria edits are pending confirmation. Visible evidence and verdict still use "
        "the last confirmed criteria. Confirm the updated set before rerunning analysis."
    ) in [item.value for item in app.warning]
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Confirm updated criteria" in sidebar_text
    assert "Complete — Criteria confirmed" not in sidebar_text

    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["criteria"][0].text == "Changed visible criterion"
    assert app.session_state["criteria_confirmed"] is True
    assert app.session_state["review_state"].bundle is None
    assert app.session_state["bundle"] is None
    assert app.button(key="run_analysis").disabled is False
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Complete — Criteria confirmed" in sidebar_text
    assert "Next — Run deterministic analysis" in sidebar_text


def test_pending_criterion_priority_edit_uses_same_confirmation_boundary() -> None:
    app = analyzed_demo(new_app())

    app = app.selectbox(key="criterion_priority_AC-01").set_value(
        Priority.SHOULD_HAVE
    ).run()

    assert app.session_state["criteria"][0].priority is Priority.MUST_HAVE
    assert app.session_state["bundle"].criteria[0].priority is Priority.MUST_HAVE
    assert app.button(key="run_analysis").disabled is True
    assert "Next — Confirm updated criteria" in "\n".join(
        item.value for item in app.sidebar.markdown
    )


def test_demo_flow_reaches_blocked_summary() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["criteria_confirmed"] is True
    app = app.button(key="run_analysis").click().run()
    visible_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "Blocked" in visible_text
    assert "Partial" in visible_text
    assert "Missing" in visible_text
    assert app.session_state["bundle"] is not None


def test_demo_summary_explains_non_prescriptive_next_actions() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    visible_text = "\n".join(markdown.value for markdown in app.markdown)
    assert "What to do next" in visible_text
    assert "unresolved criteria: AC-01" in visible_text
    assert "ScopeProof does not decide them" in visible_text
    assert "Gate reasons: Blocking Criteria" in visible_text


def test_demo_summary_humanizes_gate_reasons_without_mutating_codes() -> None:
    app = analyzed_demo(new_app())
    markdown_text = "\n".join(item.value for item in app.markdown)

    assert (
        "Gate reasons: Blocking Criteria · Conditional Criteria · Unresolved Criteria"
    ) in markdown_text
    assert "blocking_criteria, conditional_criteria, unresolved_criteria" not in markdown_text
    assert app.session_state["bundle"].gate.reason_codes == [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
    ]


def test_demo_summary_requires_explicit_resolution_decision() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    assert len(app.download_button) == 3
    assert app.selectbox(key="resolution_decision").value is None
    assert app.button(key="save_resolution").disabled is True


def test_human_decision_explains_selected_gate_impact() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Select a decision to see its deterministic gate impact." in caption_text

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.REJECTED_FINDING
    ).run()
    caption_text = "\n".join(item.value for item in app.caption)
    assert (
        "Decision impact: Rejects the provisional finding but does not resolve this criterion; "
        "its finding status continues to control the gate."
    ) in caption_text


def test_optional_token_uses_password_input() -> None:
    app = new_app()
    token = app.text_input(key="github_token")
    assert token.proto.type == token.proto.PASSWORD


def test_demo_can_save_and_reopen_durable_review_state() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    review_id = app.session_state["review_state"].review.review_id

    app = app.button(key="save_review").click().run()
    assert "Review saved locally" in "\n".join(message.value for message in app.success)
    app = select_saved_review(app, review_id)
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["review_state"].review.review_id == review_id
    success_text = "\n".join(message.value for message in app.success)
    assert "Review reopened from local storage" in success_text


def test_current_review_id_is_copyable_and_used_in_save_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = analyzed_demo(new_app())
    review_id = app.session_state["review_state"].review.review_id

    assert review_id in [item.value for item in app.code]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Current review ID" in caption_text
    assert "save this review before using the ID in a future session" in caption_text
    assert "Unsaved changes — save locally before relying on this review ID." in caption_text
    assert app.button(key="save_review").disabled is False

    app = app.button(key="save_review").click().run()
    assert f"Review saved locally. ID: {review_id}." in [item.value for item in app.success]
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Saved locally — current review matches the last local save." in caption_text
    assert app.button(key="save_review").disabled is True


def test_post_save_resolution_marks_review_unsaved_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app, _ = saved_demo_review(new_app())
    assert app.button(key="save_review").disabled is True

    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.ACCEPTED
    ).run()
    app = app.button(key="save_resolution").click().run()

    caption_text = "\n".join(item.value for item in app.caption)
    assert "Unsaved changes — save locally before relying on this review ID." in caption_text
    assert app.button(key="save_review").disabled is False


def test_unsaved_review_requires_explicit_approval_before_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, saved_review_id = saved_demo_review(new_app())
    app = analyzed_demo(new_app())
    app = select_saved_review(app, saved_review_id)
    app = app.text_input(key="pr_url").set_value(
        "https://github.com/acme/example/pull/7"
    ).run()
    app = app.text_input(key="new_criterion_text").set_value("A new behavior").run()
    app = app.text_area(key="split_criterion_text").set_value(
        "First behavior\nSecond behavior"
    ).run()

    warning_text = "\n".join(item.value for item in app.warning)
    assert "Replacing it will discard unsaved changes." in warning_text
    assert app.checkbox(key="replace_unsaved_review_confirmed").value is False
    assert app.button(key="reopen_review").disabled is True
    assert app.button(key="load_demo").disabled is True
    assert app.button(key="fetch_pr").disabled is True
    assert app.button(key="prepare_criteria").disabled is True
    assert app.button(key="add_criterion_ui").disabled is True
    assert app.button(key="split_criterion_ui").disabled is True
    assert all(
        button.disabled
        for button in app.button
        if button.key.startswith(("remove_", "move_up_"))
    )

    app = app.checkbox(key="replace_unsaved_review_confirmed").check().run()

    assert app.button(key="reopen_review").disabled is False
    assert app.button(key="load_demo").disabled is False
    assert app.button(key="fetch_pr").disabled is False
    assert app.button(key="prepare_criteria").disabled is False
    assert app.button(key="add_criterion_ui").disabled is False
    assert app.button(key="split_criterion_ui").disabled is False
    assert all(
        not button.disabled
        for button in app.button
        if button.key.startswith(("remove_", "move_up_"))
    )


def test_replacing_unsaved_review_consumes_replacement_approval() -> None:
    app = analyzed_demo(new_app())
    app = app.checkbox(key="replace_unsaved_review_confirmed").check().run()
    app = app.button(key="load_demo").click().run()

    assert app.session_state["review_state"] is None
    assert app.session_state["replace_unsaved_review_confirmed"] is False
    assert not [
        item
        for item in app.checkbox
        if item.key == "replace_unsaved_review_confirmed"
    ]


def test_saved_review_can_be_reopened_from_a_fresh_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_state = saved.session_state["review_state"]

    fresh = new_app()
    assert fresh.selectbox(key="saved_reopen_review_id").value is None
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()

    reopened = fresh.session_state["review_state"]
    assert reopened == saved_state
    assert fresh.session_state["bundle"] == saved_state.bundle
    assert fresh.session_state["criteria"] == saved_state.criteria_revision.criteria
    assert fresh.session_state["criteria_confirmed"] is True
    assert fresh.session_state["source_text"] == saved_state.criteria_revision.source_text
    assert (
        fresh.text_area(key="requirements_input").value
        == saved_state.criteria_revision.source_text
    )
    assert fresh.session_state["snapshot"] is None
    assert fresh.button(key="run_analysis").disabled is True
    assert len(fresh.download_button) == 3
    assert review_id in [item.value for item in fresh.code]
    caption_text = "\n".join(item.value for item in fresh.caption)
    assert "Saved locally — current review matches the last local save." in caption_text
    assert fresh.button(key="save_review").disabled is True


def test_reopening_clears_an_unrelated_loaded_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())

    app = load_demo(new_app())
    assert app.session_state["snapshot"] is not None
    app = select_saved_review(app, review_id)
    app = app.button(key="reopen_review").click().run()

    assert app.session_state["snapshot"] is None
    assert app.button(key="run_analysis").disabled is True
    sidebar_text = "\n".join(item.value for item in app.sidebar.markdown)
    assert "Next — Reload source to rerun analysis" in sidebar_text


def test_reopened_review_reports_changed_head_before_invalidating_analysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha
    changed_head = "changed-head-for-regression"
    changed_snapshot = load_demo_snapshot().model_copy(update={"head_sha": changed_head})

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=changed_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    warning_text = "\n".join(item.value for item in fresh.warning)
    assert saved_head in warning_text
    assert changed_head in warning_text
    assert "saved evidence remains anchored" in warning_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["bundle"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reopened_review_reports_same_head_before_reanalysis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    saved, review_id = saved_demo_review(new_app())
    saved_head = saved.session_state["review_state"].review.head_sha

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    fresh = fresh.button(key="load_demo").click().run()

    info_text = "\n".join(item.value for item in fresh.info)
    assert f"same head SHA: {saved_head}" in info_text
    assert fresh.session_state["review_state"] is None
    assert fresh.session_state["criteria_confirmed"] is False
    assert fresh.button(key="run_analysis").disabled is True


def test_reopened_review_does_not_compare_a_different_pull_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _, review_id = saved_demo_review(new_app())
    unrelated_snapshot = load_demo_snapshot().model_copy(update={"pr_number": 999})

    fresh = new_app()
    fresh = select_saved_review(fresh, review_id)
    fresh = fresh.button(key="reopen_review").click().run()
    with patch("scopeproof_core.demo.load_demo_snapshot", return_value=unrelated_snapshot):
        fresh = fresh.button(key="load_demo").click().run()

    assert fresh.session_state.filtered_state.get("source_reload_notice", "missing") is None
    assert not any("PR head changed" in item.value for item in fresh.warning)


def test_missing_saved_review_has_safe_recovery_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    app = new_app()
    app = app.text_input(key="reopen_review_id").set_value("missing-review").run()
    app = app.button(key="reopen_review").click().run()

    assert [item.value for item in app.error] == [
        "No saved review was found for that review ID."
    ]
    assert app.session_state["review_state"] is None
    assert app.session_state["bundle"] is None


def test_final_acceptance_control_is_visible_only_after_analysis() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert app.button(key="record_final_acceptance").disabled is False


def test_final_acceptance_is_labeled_as_review_level_without_overriding_gate() -> None:
    app = analyzed_demo(new_app())
    state_before = app.session_state["review_state"]
    gate_before = state_before.bundle.gate

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Final review acceptance" in markdown_text
    assert "records a review-level acceptance event" in caption_text
    assert "does not resolve individual criteria or override the deterministic gate" in caption_text
    assert "Review every criterion and its evidence before recording" in caption_text

    app = app.button(key="record_final_acceptance").click().run()
    state_after = app.session_state["review_state"]

    assert state_after.review.final_acceptance is True
    assert state_after.bundle.gate.verdict is GateVerdict.BLOCKED
    assert state_after.bundle.gate.blocking_criteria == gate_before.blocking_criteria
    assert state_after.bundle.gate.unresolved_criteria == gate_before.unresolved_criteria
    assert len(state_after.resolution_events) == 1
    assert app.button(key="record_final_acceptance").disabled is True
    assert "Final acceptance appended to the local review history." in [
        item.value for item in app.success
    ]
    history = [item.value for item in app.markdown if "Final acceptance:" in item.value]
    assert history == [
        "- **Current · revision 1** — Final acceptance: Recorded — "
        "Reviewer recorded final acceptance"
    ]


def test_criteria_revision_reenables_final_acceptance_after_invalidation() -> None:
    app = analyzed_demo(new_app())
    app = app.button(key="record_final_acceptance").click().run()
    assert app.button(key="record_final_acceptance").disabled is True

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "User can export the research list as a downloadable CSV"
    ).run()

    app = app.button(key="confirm_criteria").click().run()
    assert app.session_state["review_state"].review.final_acceptance is False
    assert app.session_state["review_state"].bundle is None
    app = app.button(key="run_analysis").click().run()
    assert app.button(key="record_final_acceptance").disabled is False


def test_analysis_is_disabled_with_active_bundle_and_enabled_for_pending_revision() -> None:
    app = analyzed_demo(new_app())

    assert app.button(key="run_analysis").disabled is True

    app = app.text_input(key="criterion_text_AC-01").set_value(
        "User can export the revised research list as a downloadable CSV"
    ).run()
    app = app.button(key="confirm_criteria").click().run()

    assert app.session_state["review_state"].bundle is None
    assert app.button(key="run_analysis").disabled is False


def test_reanalysis_preserves_review_lineage_and_prior_events() -> None:
    app = analyzed_demo(new_app())
    original_review_id = app.session_state["review_state"].review.review_id
    app = app.button(key="record_final_acceptance").click().run()
    original_bundle = app.session_state["review_state"].bundle.model_copy(deep=True)
    original_event = app.session_state["review_state"].resolution_events[0].model_copy(
        deep=True
    )
    edited_criterion = "User can export the edited research list as a downloadable CSV"

    app = app.text_input(key="criterion_text_AC-01").set_value(edited_criterion).run()
    app = app.button(key="confirm_criteria").click().run()

    pending_state = app.session_state["review_state"]
    assert pending_state.review.review_id == original_review_id
    assert pending_state.criteria_revision.number == 2
    assert len(pending_state.analysis_history) == 1
    assert len(pending_state.resolution_events) == 1

    app = app.button(key="run_analysis").click().run()
    state = app.session_state["review_state"]

    assert (
        state.review.review_id,
        state.criteria_revision.number,
        len(state.analysis_history),
        len(state.resolution_events),
    ) == (original_review_id, 2, 1, 1)
    assert state.analysis_history == [original_bundle]
    assert state.resolution_events == [original_event]
    assert state.resolution_events[0].criteria_revision_number == 1
    assert state.bundle.criteria[0].text == edited_criterion
    assert state.review.final_acceptance is False
    assert state.bundle.review.final_acceptance is False
    assert app.session_state["bundle"] == state.bundle
    assert app.session_state["bundle"].review.review_id == original_review_id


def test_criteria_can_be_added_and_removed_before_reconfirmation() -> None:
    app = load_demo(new_app())
    app = app.text_input(key="new_criterion_text").set_value("Document export format").run()
    app = app.button(key="add_criterion_ui").click().run()

    assert len(app.session_state["criteria"]) == 5
    assert app.session_state["criteria"][-1].criterion_id == "AC-05"
    assert app.session_state["criteria_confirmed"] is False

    app = app.button(key="remove_AC-05").click().run()
    assert len(app.session_state["criteria"]) == 4


def test_evidence_matrix_exposes_status_and_priority_filters() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    assert app.multiselect(key="status_filter").value == []
    assert app.multiselect(key="priority_filter").value == []


def test_evidence_matrix_exposes_blocker_and_evidence_level_filters() -> None:
    app = analyzed_demo(new_app())

    assert app.checkbox(key="blocking_only").value is False
    assert app.multiselect(key="evidence_level_filter").value == []


def test_evidence_matrix_combines_blocker_and_evidence_level_filters() -> None:
    app = analyzed_demo(new_app())
    app = app.checkbox(key="blocking_only").check().run()
    app = app.multiselect(key="evidence_level_filter").select(EvidenceLevel.E2).run()

    table = evidence_matrix_table(app)
    assert "| AC-02 |" in table
    assert "| AC-01 |" not in table
    assert "| AC-03 |" not in table
    assert "| AC-04 |" not in table


def test_evidence_matrix_reports_empty_filter_results() -> None:
    app = analyzed_demo(new_app())
    app = app.checkbox(key="blocking_only").check().run()
    app = app.multiselect(key="evidence_level_filter").select(EvidenceLevel.E4).run()

    assert "| AC-" not in evidence_matrix_table(app)
    assert "No criteria match the current filters." in [item.value for item in app.info]


def test_evidence_matrix_renders_as_one_markdown_table() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()

    table_blocks = [
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith(
            "| Criterion | Requirement | Priority | Status | Evidence | Human resolution |"
        )
    ]
    assert len(table_blocks) == 1
    assert "|---|---|---|---|---|---|" in table_blocks[0]
    assert "| AC-01 | User can export the research list as CSV |" in table_blocks[0]
    assert "| Must Have | Evidence Found | E2 | Unresolved |" in table_blocks[0]
    assert "| Unresolved |" in table_blocks[0]
    assert "| AC-04 | Successful export records research_exported |" in table_blocks[0]
    assert "Confidence" not in table_blocks[0]
    assert "Count" not in table_blocks[0]
    assert "Concern" not in table_blocks[0]


def test_criterion_detail_preserves_deep_matrix_context_without_duplicate_summary() -> None:
    app = analyzed_demo(new_app())
    markdown_text = [item.value for item in app.markdown]
    visible_markdown = "\n".join(markdown_text)

    assert (
        "**Required evidence:** E1 · **Observed evidence:** E2 · "
        "**Confidence:** High · **Candidates:** 4 · **Human resolution:** Unresolved"
    ) in markdown_text
    assert "Strong candidate evidence was found; a reviewer must still judge sufficiency." in (
        item.value for item in app.markdown
    )
    assert "**AC-01 — Evidence Found** · User can export the research list as CSV" not in (
        visible_markdown
    )


def test_evidence_matrix_shows_current_human_resolution() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = app.run()

    table = next(
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith("| Criterion | Requirement | Priority |")
    )
    ac_01_row = next(line for line in table.splitlines() if line.startswith("| AC-01 |"))
    assert ac_01_row.endswith("| Accepted |")


def test_successful_resolution_save_clears_form_and_prevents_accidental_repeat() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.text_area(key="resolution_note").set_value("Evidence reviewed").run()
    app = app.button(key="save_resolution").click().run()

    state = app.session_state["review_state"]
    assert len(state.resolution_events) == 1
    assert app.selectbox(key="resolution_decision").value is None
    assert app.text_area(key="resolution_note").value == ""
    assert app.button(key="save_resolution").disabled is True
    assert "Human resolution appended to the local review history." in [
        message.value for message in app.success
    ]


@pytest.mark.parametrize("note", ["", "   ", "\t\n"])
def test_manual_verification_requires_nonblank_reviewer_note(note: str) -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.MANUALLY_VERIFIED
    ).run()
    app = app.text_area(key="resolution_note").set_value(note).run()

    assert app.button(key="save_resolution").disabled is True
    assert len(app.session_state["review_state"].resolution_events) == 0
    assert (
        "Reviewer note is required for manual verification. Describe what was verified."
    ) in [item.value for item in app.caption]


def test_successful_manual_verification_clears_conditional_evidence_level() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.MANUALLY_VERIFIED
    ).run()
    app = app.selectbox(key="manual_evidence_level").set_value(EvidenceLevel.E4).run()
    app = app.text_area(key="resolution_note").set_value(
        "Verified the export in staging."
    ).run()
    assert app.button(key="save_resolution").disabled is False
    app = app.button(key="save_resolution").click().run()

    assert len(app.session_state["review_state"].resolution_events) == 1
    assert app.session_state["review_state"].resolution_events[0].comment == (
        "Verified the export in staging."
    )
    assert app.selectbox(key="resolution_decision").value is None
    assert "manual_evidence_level" not in app.session_state.filtered_state


def test_criterion_resolution_context_identifies_target_and_boundary() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)

    resolution_context = next(
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith("### Criterion resolution")
    )
    assert (
        "This decision will be recorded for AC-01 — User can export the research list as CSV. "
        "It does not record final review acceptance."
    ) in resolution_context
    assert "Select a decision to see its deterministic gate impact." in caption_text

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    resolution_context = next(
        markdown.value
        for markdown in app.markdown
        if markdown.value.startswith("### Criterion resolution")
    )
    assert (
        "This decision will be recorded for AC-03 — Failed export shows an error message. "
        "It does not record final review acceptance."
    ) in resolution_context


def test_criterion_detail_labels_candidate_evidence_and_recovery_guidance() -> None:
    app = analyzed_demo(new_app())
    bundle = app.session_state["review_state"].bundle
    finding = next(item for item in bundle.findings if item.criterion_id == "AC-01")
    evidence = next(item for item in bundle.evidence if item.evidence_id in finding.evidence_ids)

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    info_text = "\n".join(item.value for item in app.info)

    assert "Recommended next action" in markdown_text
    assert finding.recommended_action in info_text
    assert "Candidate evidence" in markdown_text
    assert f"**Matching rationale:** {evidence.relevance_reason}" in markdown_text
    assert f"Matching rule: {evidence.matching_rule}" in caption_text
    assert f"Limitation: {evidence.limitations[0]}" in caption_text
    assert evidence.excerpt in [item.value for item in app.code]
    assert "Open immutable GitHub evidence" in markdown_text


def test_missing_criterion_detail_shows_action_and_no_candidate_state() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    bundle = app.session_state["review_state"].bundle
    finding = next(item for item in bundle.findings if item.criterion_id == "AC-03")

    markdown_text = "\n".join(item.value for item in app.markdown)
    info_text = "\n".join(item.value for item in app.info)
    caption_text = "\n".join(item.value for item in app.caption)

    assert "Recommended next action" in markdown_text
    assert finding.recommended_action in info_text
    assert "Candidate evidence" in markdown_text
    assert "No candidate evidence is linked to this provisional finding." in caption_text


def test_compound_criterion_can_be_split_in_workbench() -> None:
    app = new_app()
    app = app.text_area(key="requirements_input").set_value("Export CSV and record analytics").run()
    app = app.button(key="prepare_criteria").click().run()
    app = app.text_area(key="split_criterion_text").set_value("Export CSV\nRecord analytics").run()
    app = app.button(key="split_criterion_ui").click().run()

    assert [(item.criterion_id, item.text) for item in app.session_state["criteria"]] == [
        ("AC-01", "Export CSV"),
        ("AC-02", "Record analytics"),
    ]


def test_human_decision_and_final_acceptance_append_history() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()
    app = app.button(key="record_final_acceptance").click().run()

    state = app.session_state["review_state"]
    assert len(state.resolution_events) == 2
    assert state.review.final_acceptance is True
    assert "Resolution history" in "\n".join(markdown.value for markdown in app.markdown)


def test_resolution_history_distinguishes_current_and_superseded_decisions() -> None:
    app = analyzed_demo(new_app())
    app = app.selectbox(key="resolution_decision").set_value(
        HumanDecision.REJECTED_FINDING
    ).run()
    app = app.button(key="save_resolution").click().run()
    app = app.selectbox(key="resolution_decision").set_value(HumanDecision.ACCEPTED).run()
    app = app.button(key="save_resolution").click().run()

    markdown_text = "\n".join(item.value for item in app.markdown)
    caption_text = "\n".join(item.value for item in app.caption)
    assert "Superseded · revision 1 — AC-01: Rejected Finding" in markdown_text
    assert "Current · revision 1** — AC-01: Accepted" in markdown_text
    assert (
        "Current events are the latest recorded inputs for the active revision. Superseded and "
        "prior-revision events remain audit history and do not independently control the gate."
    ) in caption_text


def test_runtime_evidence_guidance_lists_only_missing_required_fields() -> None:
    app = analyzed_demo(new_app())

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Artifact or URL, Runtime scenario, "
        "Environment, Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()

    guidance = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("Complete required fields to enable Save:")
    ]
    assert guidance == [
        "Complete required fields to enable Save: Observed result, Runtime reviewer."
    ]
    assert app.button(key="save_runtime_evidence").disabled is True


def test_runtime_evidence_guidance_disappears_when_save_is_ready() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save: Artifact or URL." in guidance
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()

    guidance = "\n".join(caption.value for caption in app.caption)
    assert "Complete required fields to enable Save:" not in guidance
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_save_requires_all_required_fields() -> None:
    app = analyzed_demo(new_app())
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value("   ").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    assert app.button(key="save_runtime_evidence").disabled is True

    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/1"
    ).run()
    assert app.button(key="save_runtime_evidence").disabled is False


def test_runtime_evidence_fields_identify_required_and_optional_status() -> None:
    app = analyzed_demo(new_app())

    assert app.text_input(key="runtime_artifact_reference").label == (
        "Artifact or URL (required)"
    )
    assert app.text_area(key="runtime_scenario").label == "Runtime scenario (required)"
    assert app.text_input(key="runtime_environment").label == "Environment (required)"
    assert app.text_input(key="runtime_result").label == "Observed result (required)"
    assert app.text_input(key="runtime_reviewer").label == "Runtime reviewer (required)"
    assert app.text_area(key="runtime_limitations").label == (
        "Runtime limitations (optional)"
    )
    assert app.button(key="save_runtime_evidence").disabled is True
    assert (
        "This records a review-level acceptance event. It does not resolve individual criteria "
        "or override the deterministic gate. Review every criterion and its evidence before "
        "recording final acceptance."
    ) in [caption.value for caption in app.caption]


def test_runtime_evidence_prerequisite_guidance_is_visible() -> None:
    app = analyzed_demo(new_app())
    caption_text = "\n".join(caption.value for caption in app.caption)
    assert (
        "Artifact, scenario, environment, observed result, and reviewer are required"
        in caption_text
    )
    assert "Limitations are optional" in caption_text


def test_runtime_evidence_context_identifies_criterion_and_explains_levels() -> None:
    app = analyzed_demo(new_app())
    target_context = next(
        caption.value
        for caption in app.caption
        if caption.value.startswith("This record will be attached to")
    )
    assert (
        "This record will be attached to AC-01 — User can export the research list as CSV."
    ) in target_context
    assert "Record a human-supplied observation only." in target_context

    level_context = next(
        caption.value
        for caption in app.caption
        if caption.value.startswith("E3 means manually recorded external runtime verification")
    )
    assert (
        "E3 means manually recorded external runtime verification. "
        "E4 means explicit human acceptance. Saving this record does not resolve the criterion "
        "or record final review acceptance."
    ) in level_context
    assert (
        "Artifact, scenario, environment, observed result, and reviewer are required."
        in level_context
    )
    assert "Limitations are optional." in level_context

    app = app.selectbox(key="selected_criterion").set_value("AC-03").run()
    target_captions = [
        caption.value
        for caption in app.caption
        if caption.value.startswith("This record will be attached to")
    ]
    assert len(target_captions) == 1
    assert (
        "This record will be attached to AC-03 — Failed export shows an error message."
        in target_captions[0]
    )
    assert "Record a human-supplied observation only." in target_captions[0]


def test_manual_runtime_evidence_can_be_recorded_without_changing_static_findings() -> None:
    app = load_demo(new_app())
    app = app.button(key="confirm_criteria").click().run()
    app = app.button(key="run_analysis").click().run()
    finding_status = app.session_state["review_state"].bundle.findings[0].status
    app = app.text_input(key="runtime_artifact_reference").set_value("https://example.test/run/1").run()
    app = app.text_area(key="runtime_scenario").set_value("Export CSV").run()
    app = app.text_input(key="runtime_environment").set_value("staging").run()
    app = app.text_input(key="runtime_result").set_value("passed").run()
    app = app.text_input(key="runtime_reviewer").set_value("QA").run()
    app = app.button(key="save_runtime_evidence").click().run()

    bundle = app.session_state["review_state"].bundle
    assert bundle.findings[0].status is finding_status
    assert bundle.runtime_evidence[0].artifact_reference.endswith("/1")


def test_runtime_artifact_identifier_renders_as_plain_text() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value("artifact-42").run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.button(key="save_runtime_evidence").click().run()

    runtime_rows = [
        item.value.replace("\\", "")
        for item in app.markdown
        if "artifact\\-42" in item.value
    ]
    assert runtime_rows == [
        "- artifact-42 — Fixture scenario (Fixture environment: Fixture result; E3)"
    ]


def test_successful_runtime_evidence_save_clears_form_and_prevents_accidental_repeat() -> None:
    app = analyzed_demo(new_app())
    app = app.text_input(key="runtime_artifact_reference").set_value(
        "https://example.test/run/reset"
    ).run()
    app = app.text_area(key="runtime_scenario").set_value("Fixture scenario").run()
    app = app.text_input(key="runtime_environment").set_value("Fixture environment").run()
    app = app.text_input(key="runtime_result").set_value("Fixture result").run()
    app = app.text_input(key="runtime_reviewer").set_value("Fixture reviewer").run()
    app = app.text_area(key="runtime_limitations").set_value("Fixture limitation").run()
    app = app.selectbox(key="runtime_evidence_level").set_value(EvidenceLevel.E4).run()

    app = app.button(key="save_runtime_evidence").click().run()

    assert len(app.session_state["review_state"].bundle.runtime_evidence) == 1
    assert app.text_input(key="runtime_artifact_reference").value == ""
    assert app.text_area(key="runtime_scenario").value == ""
    assert app.text_input(key="runtime_environment").value == ""
    assert app.text_input(key="runtime_result").value == ""
    assert app.text_input(key="runtime_reviewer").value == ""
    assert app.text_area(key="runtime_limitations").value == ""
    assert app.selectbox(key="runtime_evidence_level").value is EvidenceLevel.E3
    assert app.button(key="save_runtime_evidence").disabled is True
    assert "Manual runtime evidence appended without changing static findings." in [
        item.value for item in app.success
    ]
