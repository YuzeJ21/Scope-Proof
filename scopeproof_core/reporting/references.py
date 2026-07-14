"""Render human-supplied artifact references without inventing unsafe links."""

from __future__ import annotations

from urllib.parse import urlsplit


def is_linkable_artifact_reference(value: str) -> bool:
    """Return whether an artifact reference is a safe absolute web URL."""
    if any(character.isspace() for character in value) or "<" in value or ">" in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _escape_markdown_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def render_artifact_reference_markdown(value: str) -> str:
    """Return a Markdown link for HTTP(S), otherwise escaped plain text."""
    label = _escape_markdown_text(value)
    if not is_linkable_artifact_reference(value):
        return label
    return f"[{label}](<{value}>)"
