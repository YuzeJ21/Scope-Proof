from __future__ import annotations

import pytest
from markdown_it import MarkdownIt

from scopeproof_core.reporting.references import (
    is_linkable_artifact_reference,
    render_artifact_reference_markdown,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://example.test/run/42", True),
        ("HTTPS://example.test/run/42", True),
        ("http:///run/42", False),
        ("https://", False),
        ("https://example.test/run 42", False),
        ("https://example.test/run\t42", False),
        ("https://example.test/<run>", False),
        ("artifact-42", False),
        ("relative/run-42", False),
        ("file:///tmp/run-42", False),
        ("javascript:alert(1)", False),
        ("mailto:reviewer@example.test", False),
    ],
)
def test_artifact_reference_classifier_covers_every_link_boundary(
    value: str, expected: bool
) -> None:
    assert is_linkable_artifact_reference(value) is expected


def test_inert_markdown_label_renders_as_the_exact_supplied_text() -> None:
    reference = r"artifact-&copy;_[run]*`result`\path"

    fragment = render_artifact_reference_markdown(reference)
    children = MarkdownIt().parseInline(fragment)[0].children or []

    assert [(token.type, token.content) for token in children] == [("text", reference)]


def test_escaped_https_markdown_preserves_label_and_navigation_semantics() -> None:
    reference = "https://example.test/path\\*name?label=&copy;"

    fragment = render_artifact_reference_markdown(reference)
    children = MarkdownIt().parseInline(fragment)[0].children or []

    assert [token.type for token in children] == ["link_open", "text", "link_close"]
    assert children[1].content == reference
    assert children[0].attrs["href"] == "https://example.test/path%5C*name?label=&copy;"
    assert "&amp;copy;" in fragment
    assert "%5C" in fragment
