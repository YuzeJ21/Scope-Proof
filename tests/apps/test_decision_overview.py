from contextlib import contextmanager
from unittest.mock import patch

from scopeproof_core.reviews.lifecycle import append_resolution, revise_criteria
from scopeproof_core.schemas.models import ChangedFile, HumanDecision, ResolutionEvent
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
    app = app.selectbox(key="selected_criterion").set_value("AC-01").run()
    app = app.selectbox(key="scope_file_path").set_value("src/unrelated.py").run()
    app = app.text_area(key="scope_note").set_value("Unsubmitted scope explanation").run()
    assert "Local save: Pending inputs excluded" in [item.value for item in app.text]
    assert app.button(key="open_next_overview_blocker").disabled
    assert app.text_area(key="scope_note").value == "Unsubmitted scope explanation"


def test_overview_opens_next_blocker_without_writing_or_discarding_inputs() -> None:
    app = analyzed_demo(new_app())
    state = app.session_state["review_state"]
    store = JsonReviewStore(default_local_review_directory())
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
    assert not any(item.value == "Decision overview" for item in app.subheader)
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
