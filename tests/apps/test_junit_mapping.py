"""Explicit staged choices, never inferred criterion coverage or target execution."""

import pytest
from streamlit.testing.v1 import AppTest


def _render():
    import streamlit as st

    from apps.web.junit_mapping import render_junit_mapping_draft
    from scopeproof_core.importers.junit import parse_junit_artifact
    from tests.importers.test_junit import exact_head_state

    if "review" not in st.session_state:
        st.session_state.review = exact_head_state()
        st.session_state.artifact = (
            b'<testsuites><testsuite name="one"><testcase name="first"/></testsuite>'
            b'<testsuite name="two"><testcase name="second"/></testsuite></testsuites>'
        )
    artifact = st.session_state.artifact
    parsed = parse_junit_artifact(artifact) if artifact is not None else None
    st.text_input("Importer", key="junit_importer", value="CONSTRUCTED actor")
    scopes = [] if parsed is None else [item.suite_id for item in parsed.suites]
    candidate = render_junit_mapping_draft(
        st.session_state.review, artifact, parsed, scope_ids=scopes,
        scope_labels={scope: scope for scope in scopes},
        importer=st.session_state.junit_importer, limitations=[],
    )
    st.session_state.candidate = candidate
    st.button("Save candidate", disabled=candidate is None)


def _stage(app, criterion, scope):
    app.selectbox(key="junit_mapping_target").select(criterion).run()
    app.multiselect(key="junit_mapping_scopes").set_value([scope]).run()
    return app.button(key="stage_junit_mapping").click().run()


def test_two_explicit_targets_stage_before_one_candidate_and_clear_unsubmitted_controls():
    app = AppTest.from_function(_render).run()
    assert not app.exception
    before = app.session_state.review.model_dump_json()
    assert app.selectbox(key="junit_mapping_target").value is None
    assert app.session_state.candidate is None
    app = _stage(app, "AC-01", "suite-0001")
    assert not app.exception
    assert app.selectbox(key="junit_mapping_target").value is None
    assert app.multiselect(key="junit_mapping_scopes").value == []
    assert app.session_state.candidate is not None
    app = _stage(app, "AC-02", "suite-0002")
    assert not app.exception
    mappings = app.session_state.candidate.criterion_mappings
    assert [(m.criterion_id, m.test_case_ids) for m in mappings] == [
        ("AC-01", ["suite-0001-case-0001"]), ("AC-02", ["suite-0002-case-0001"]),
    ]
    assert app.session_state.review.model_dump_json() == before
    assert "Staged JUnit mappings (not imported)" in [item.value for item in app.caption]


def test_unstaged_choices_block_save_and_overlapping_stage_leaves_prior_draft_intact():
    app = _stage(AppTest.from_function(_render).run(), "AC-01", "suite-0001")
    before = app.session_state.junit_mapping_draft.model_dump_json()
    app.selectbox(key="junit_mapping_target").select("AC-02").run()
    app.multiselect(key="junit_mapping_scopes").set_value(["suite-0001"]).run()
    assert app.session_state.candidate is None
    app.button(key="stage_junit_mapping").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.junit_mapping_draft.model_dump_json() == before


def test_remove_group_and_clear_all_are_draft_only():
    app = _stage(AppTest.from_function(_render).run(), "AC-01", "suite-0001")
    app = _stage(app, "AC-02", "suite-0002")
    before = app.session_state.review.model_dump_json()
    app.selectbox(key="junit_mapping_remove_criterion").select("AC-01").run()
    app.button(key="remove_junit_mapping").click().run()
    assert not app.exception
    assert [m.criterion_id for m in app.session_state.candidate.criterion_mappings] == ["AC-02"]
    app.button(key="clear_junit_mappings").click().run()
    assert not app.exception and app.session_state.candidate is None
    assert app.session_state.junit_mapping_draft.selections == ()
    assert app.session_state.review.model_dump_json() == before


def test_replacing_or_removing_artifact_expires_all_mapping_choices():
    replacements = (None, b'<testsuite name="replacement"><testcase name="third"/></testsuite>')
    for replacement in replacements:
        app = _stage(AppTest.from_function(_render).run(), "AC-01", "suite-0001")
        app.session_state.artifact = replacement
        app.run()
        assert not app.exception and app.session_state.candidate is None
        draft = app.session_state.junit_mapping_draft
        assert draft is None or draft.selections == ()
        assert app.selectbox(key="junit_mapping_target").value is None
        assert app.multiselect(key="junit_mapping_scopes").value == []


def test_full_review_note_change_expires_staged_mapping():
    app = _stage(AppTest.from_function(_render).run(), "AC-01", "suite-0001")
    app.session_state.review.bundle.evidence[0].limitations.append("CONSTRUCTED new limitation")
    app.run()
    assert not app.exception and app.session_state.candidate is None
    assert app.session_state.junit_mapping_draft.selections == ()


def test_actual_workbench_saves_both_mappings_once_and_exports_without_gate_changes():
    from scopeproof_core.reporting.exporters import export_json, export_markdown
    from scopeproof_core.schemas.models import ReviewState
    from tests.apps.test_streamlit_app import analyzed_exact_head_standard_demo, new_app

    app = analyzed_exact_head_standard_demo(new_app())
    before = app.session_state["review_state"].model_copy(deep=True)
    xml = (
        b'<testsuites><testsuite name="one"><testcase name="first"/></testsuite>'
        b'<testsuite name="two"><testcase name="second"/></testsuite></testsuites>'
    )
    app.file_uploader(key="junit_artifact_upload").upload("two.xml", xml, "application/xml").run()
    app.text_input(key="junit_importer").set_value("CONSTRUCTED workbench actor").run()
    app = _stage(app, "AC-01", "suite-0001")
    app = _stage(app, "AC-02", "suite-0002")
    app.button(key="save_junit_import").click().run()
    assert not app.exception
    saved = ReviewState.model_validate(app.session_state["review_state"].model_dump(mode="python"))
    assert len(saved.bundle.junit_evidence_imports) == 1
    mappings = saved.bundle.junit_evidence_imports[0].criterion_mappings
    assert [mapping.criterion_id for mapping in mappings] == ["AC-01", "AC-02"]
    assert saved.bundle.gate == before.bundle.gate
    assert saved.bundle.runtime_evidence == before.bundle.runtime_evidence
    assert saved.resolution_events == before.resolution_events
    assert saved.review.final_acceptance is before.review.final_acceptance
    assert app.session_state["junit_mapping_draft"] is None
    for rendered in (export_json(saved), export_markdown(saved)):
        assert "suite-0001-case-0001" in rendered and "suite-0002-case-0001" in rendered
        assert "AC-01" in rendered and "AC-02" in rendered


@pytest.mark.parametrize("external_change", ["note", "provenance"])
def test_detected_saved_review_change_expires_mapping_even_with_queued_save(
    tmp_path, external_change,
):
    from unittest.mock import patch

    from scopeproof_core.schemas.models import ReviewState
    from scopeproof_core.storage.json_store import JsonReviewStore
    from tests.apps.test_streamlit_app import analyzed_exact_head_standard_demo, new_app

    directory = tmp_path.resolve()
    with patch("scopeproof_core.storage.json_store.default_local_review_directory",
               return_value=directory):
        app = analyzed_exact_head_standard_demo(new_app())
        xml = b'<testsuite name="one"><testcase name="first"/></testsuite>'
        app.file_uploader(key="junit_artifact_upload").upload(
            "one.xml", xml, "application/xml",
        ).run()
        app.text_input(key="junit_importer").set_value("CONSTRUCTED stale draft actor").run()
        app = _stage(app, "AC-01", "suite-0001")
        assert not app.button(key="save_junit_import").disabled
        app.button(key="save_junit_import").click()  # An event from the still-valid old screen.
        store = JsonReviewStore(directory)
        changed = store.load(app.session_state["review_state"].review.review_id)
        if external_change == "note":
            changed.bundle.evidence[0].limitations.append("CONSTRUCTED external note change")
        else:
            provenance = changed.review.criteria_source_provenance.model_copy(
                update={"source_revision": "CONSTRUCTED externally changed source revision"},
            )
            changed.review.criteria_source_provenance = provenance
            changed.bundle.review.criteria_source_provenance = provenance
            changed.criteria_revision.source_provenance = provenance
        changed = ReviewState.model_validate(changed.model_dump(mode="python"))
        path = store.save(changed)
        external_bytes = path.read_bytes()
        app.run()
        assert not app.exception
        assert app.session_state["review_save_conflict"] is True
        assert app.session_state["junit_mapping_draft"] is None
        assert app.button(key="save_junit_import").disabled
        assert app.button(key="stage_junit_mapping").disabled
        assert app.selectbox(key="junit_mapping_target").value is None
        assert app.session_state["review_state"].bundle.junit_evidence_imports == []
        assert store.load(changed.review.review_id).bundle.junit_evidence_imports == []
        assert path.read_bytes() == external_bytes
