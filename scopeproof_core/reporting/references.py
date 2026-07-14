"""Render human-supplied artifact references without inventing unsafe links."""

from __future__ import annotations

import html
import string
from urllib.parse import urlsplit

_MARKDOWN_PUNCTUATION = frozenset(set(string.punctuation) - {"&", ";"})


def is_linkable_artifact_reference(value: str) -> bool:
    """Return whether an artifact reference is a safe absolute web URL."""
    if (
        not value.isprintable()
        or any(character.isspace() for character in value)
        or "<" in value
        or ">" in value
    ):
        return False
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed_port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() in {"http", "https"}
        and bool(hostname)
        and bool(hostname.strip("."))
        and (parsed_port is None or parsed_port > 0)
    )


def _escape_markdown_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return "".join(
        f"\\{character}" if character in _MARKDOWN_PUNCTUATION else character
        for character in escaped
    )


def _escape_markdown_destination(value: str) -> str:
    return value.replace("\\", "%5C").replace("&", "&amp;")


def render_artifact_reference_markdown(value: str) -> str:
    """Return a Markdown link for HTTP(S), otherwise escaped plain text."""
    label = _escape_markdown_text(value)
    if not is_linkable_artifact_reference(value):
        return label
    destination = _escape_markdown_destination(value)
    return f"[{label}](<{destination}>)"
