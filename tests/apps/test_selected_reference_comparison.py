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
