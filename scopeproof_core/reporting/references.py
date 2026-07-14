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
    escaped = value.replace("&", "&amp;").replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "<", ">"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _escape_markdown_destination(value: str) -> str:
    return value.replace("\\", "%5C").replace("&", "&amp;")


def render_artifact_reference_markdown(value: str) -> str:
    """Return a Markdown link for HTTP(S), otherwise escaped plain text."""
    label = _escape_markdown_text(value)
    if not is_linkable_artifact_reference(value):
        return label
    destination = _escape_markdown_destination(value)
    return f"[{label}](<{destination}>)"
