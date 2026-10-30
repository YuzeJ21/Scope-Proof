"""Reference context stays informational and uses safe literal UI rendering."""

from streamlit.testing.v1 import AppTest


def _legacy_projection():
    from apps.web.selected_reference_comparison import render_selected_reference_comparison

    render_selected_reference_comparison(None)


def _identical_projection():
    from apps.web.selected_reference_comparison import render_selected_reference_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.reporting.test_selected_references import selected_state

    state = selected_state()
    render_selected_reference_comparison(
        compare_reviews(state.bundle, state.bundle).selected_reference_comparison
    )


def _literal_source_projection():
    from apps.web.selected_reference_comparison import render_selected_reference_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from scopeproof_core.schemas.models import ChangedFile, ChangedLine, LineChangeType
    from tests.reviews.test_selected_references import append, source_state

    state, snapshot = source_state(
        files=[
            ChangedFile(
                path="src/**accepted**.py",
                status="modified",
                lines=[
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        line_number=1,
                        content="unfamiliar_symbol = 42",
                    )
                ],
            )
        ]
    )
    state = append(state, snapshot)
    render_selected_reference_comparison(
        compare_reviews(state.bundle, state.bundle).selected_reference_comparison
    )


def _confirmation_metadata_projection():
    from datetime import UTC, datetime

    from apps.web.selected_reference_comparison import render_selected_reference_comparison
    from scopeproof_core.reviews.comparison import compare_reviews
    from tests.reviews.test_selected_reference_comparison import constructed_pair

    _, previous = constructed_pair()
    current = previous.model_copy(deep=True)
    current.review.criteria_source_provenance = (
        current.review.criteria_source_provenance.model_copy(
            update={
                "confirmed_by": "Constructed distinct criteria confirmer",
                "confirmed_at": datetime(2026, 10, 30, 11, 22, 33, tzinfo=UTC),
            }
        )
    )
    reference = current.reviewer_selected_references[0]
    current.reviewer_selected_references[0] = reference.model_copy(
        update={
            "criteria_source_provenance": current.review.criteria_source_provenance.model_copy(
                deep=True
            ),
        }
    )
    render_selected_reference_comparison(
        compare_reviews(previous, current).selected_reference_comparison
    )


def test_legacy_unknown_context_does_not_render_an_invented_empty_comparison():
    app = AppTest.from_function(_legacy_projection).run()
    assert not app.exception
    assert any("not included" in item.value for item in app.info)
    assert not any("Only current" in item.value for item in app.markdown)


def test_identical_context_keeps_both_literal_records_and_non_gating_boundary():
    app = AppTest.from_function(_identical_projection).run()
    assert not app.exception
    markdown = "\n".join(item.value for item in app.markdown)
    captions = "\n".join(item.value for item in app.caption)
    text = "\n".join(item.value for item in app.text)
    assert "Identical record: 1" in markdown
    assert "Previous selected reference" in markdown and "Current selected reference" in markdown
    assert "=Actor <script>bad</script>" in text
    assert "=SUM(1,1) <img src=x>" in text
    assert "<script>" not in markdown and "<img" not in markdown
    assert sum("<script>bad</script>" in item.value for item in app.code) == 2
    assert "non-gating static context" in captions and "not execution" in captions


def test_markdown_bearing_source_path_has_literal_location_and_neutral_disclosure():
    app = AppTest.from_function(_literal_source_projection).run()
    assert not app.exception
    assert "AC-01 · src/**accepted**.py:1" in [item.value for item in app.text]
    assert all("**accepted**" not in item.label for item in app.expander)


def test_confirmation_only_difference_is_visible_in_both_record_details():
    app = AppTest.from_function(_confirmation_metadata_projection).run()
    assert not app.exception
    assert "Only previous: 1" in "\n".join(item.value for item in app.markdown)
    text = "\n".join(item.value for item in app.text)
    assert "Constructed distinct criteria confirmer" in text
    assert "2026-10-30T11:22:33+00:00" in text
