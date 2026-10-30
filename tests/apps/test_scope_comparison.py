"""Visible re-review scope context is derived from the core comparison."""

from streamlit.testing.v1 import AppTest

from scopeproof_core.reviews.comparison import compare_reviews
from scopeproof_core.schemas.models import IngestionState
from tests.reviews.test_comparison import bundle_with
from tests.reviews.test_scope_comparison import NEW, OLD, decide, revalidated, scoped_bundle


def render_scope(scope) -> AppTest:
    app = AppTest.from_string('''
import streamlit as st
from apps.web.scope_comparison import render_file_scope_comparison
render_file_scope_comparison(st.session_state["scope"])
''')
    app.session_state["scope"] = scope
    return app.run()


def rendered_text(app: AppTest) -> str:
    return "\n".join(item.value for collection in (
        app.markdown, app.caption, app.text, app.code, app.warning,
    ) for item in collection)


def test_scope_comparison_ui_exposes_added_uncited_path_and_current_review_action() -> None:
    scope = compare_reviews(scoped_bundle(OLD), scoped_bundle(NEW, "src/unrelated.py")).file_scope
    app = render_scope(scope)
    assert not app.exception
    text = rendered_text(app)
    assert "src/unrelated.py" in text
    assert "Added to inventory" in text
    assert "1 unresolved" in text
    assert "#changed-file-scope" in text
    assert "content" in text and "acceptance" in text


def test_scope_comparison_ui_keeps_unknown_and_partial_ingestion_visible() -> None:
    previous, current = scoped_bundle(OLD), scoped_bundle(NEW)
    previous.review.changed_file_inventory = None
    current.review.ingestion_state = IngestionState.PARTIAL
    current.review.skipped_files = ["large.bin"]
    current.review.ingestion_warnings = ["<img src=x> File skipped"]
    app = render_scope(compare_reviews(revalidated(previous), revalidated(current)).file_scope)
    assert not app.exception
    text = rendered_text(app)
    assert "unknown" in text.lower()
    assert any("src/export.py" in item.value and "modified" in item.value for item in app.text)
    assert "Partial" in text and "large.bin" in text
    assert any("Current ingestion: Partial" in item.value for item in app.warning)
    assert any("<img src=x>" in item.value for item in app.text)
    assert not any("<img src=x>" in item.value for item in app.markdown)


def test_scope_comparison_ui_displays_attribution_and_does_not_transfer_scope_decisions() -> None:
    previous = decide(scoped_bundle(OLD, "notes.md"), "notes.md", "outside_confirmed_criteria")
    scope = compare_reviews(previous, scoped_bundle(NEW, "notes.md")).file_scope
    app = render_scope(scope)
    assert not app.exception
    text = rendered_text(app)
    assert "Constructed reviewer" in text
    assert OLD in text and "Previously decided" in text
    assert "1 unresolved" in text
    assert scope.current.latest_decisions == []


def test_scope_comparison_ui_legacy_context_is_unknown() -> None:
    app = render_scope(None)
    assert not app.exception
    assert "unknown" in rendered_text(app).lower()


def test_scope_comparison_ui_current_unknown_and_known_empty_are_distinct() -> None:
    previous, current = scoped_bundle(OLD), scoped_bundle(NEW)
    current.review.changed_file_inventory = None
    app = render_scope(compare_reviews(previous, revalidated(current)).file_scope)
    assert not app.exception
    assert any("Current changed-file inventory is unknown" in item.value for item in app.warning)
    app = render_scope(compare_reviews(previous, scoped_bundle(NEW)).file_scope)
    assert not app.exception
    assert "No recorded inventory metadata differences" in rendered_text(app)
    assert "No unresolved inspected paths" in rendered_text(app)
    app = render_scope(compare_reviews(bundle_with(head_sha=OLD),
                                       bundle_with(head_sha=NEW)).file_scope)
    assert not app.exception
    assert "Known empty inventory" in rendered_text(app)
