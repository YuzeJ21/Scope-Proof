"""Git source records use LF boundaries rather than Unicode text separators."""

from __future__ import annotations


def split_git_source_lines(text: str, *, strip_crlf: bool = True) -> list[str]:
    """Preserve source content and numbering, with explicit CRLF handling.

    Only LF ends a record. A CR immediately before that LF belongs to its
    CRLF terminator; lone/embedded/final CR and other separators remain content.
    The final empty split sentinel is not an additional source record. Patch
    parsing can retain CR until its no-final-newline protocol is inspected.
    """
    records = text.split("\n")
    lines = [record.removesuffix("\r") if strip_crlf else record for record in records[:-1]]
    if records[-1]:
        lines.append(records[-1])
    return lines
