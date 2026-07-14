from __future__ import annotations

import pytest

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
        ("https://@", False),
        ("https://.", False),
        ("https://example.test:invalid/run", False),
        ("https://example.test/run\x00", False),
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

    assert fragment == r"artifact\-&amp;copy;\_\[run\]\*\`result\`\\path"


def test_non_link_artifact_reference_cannot_activate_formatting_or_autolinks() -> None:
    reference = "~~strike~~ https://example.test/plain with space"

    fragment = render_artifact_reference_markdown(reference)

    assert "~~strike~~" not in fragment
    assert "https://example.test/plain" not in fragment


def test_non_link_artifact_reference_cannot_break_markdown_with_newlines() -> None:
    reference = "artifact\r\n\r\n    injected code block"

    fragment = render_artifact_reference_markdown(reference)

    assert "\r" not in fragment
    assert "\n" not in fragment
    assert " ".join(fragment.replace("\\", "").split()) == "artifact injected code block"


def test_escaped_https_markdown_preserves_label_and_navigation_semantics() -> None:
    reference = "https://example.test/path\\*name?label=&copy;"

    fragment = render_artifact_reference_markdown(reference)

    assert fragment == (
        r"[https\:\/\/example\.test\/path\\\*name\?label\=&amp;copy;]"
        r"(<https://example.test/path%5C*name?label=&amp;copy;>)"
    )
