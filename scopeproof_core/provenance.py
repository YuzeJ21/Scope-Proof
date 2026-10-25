"""Network-free checks for GitHub candidate links tied to a review."""

from __future__ import annotations

from urllib.parse import quote, urlsplit


def candidate_permalink_matches(
    permalink: str,
    *,
    repository: str,
    commit_sha: str,
    file_path: str,
    line_start: int,
    line_end: int,
) -> bool:
    """Accept only a GitHub blob URL for this exact candidate and line range."""
    try:
        parsed = urlsplit(permalink)
    except ValueError:
        return False
    expected_path = (
        f"/{quote(repository, safe='/')}/blob/{quote(commit_sha, safe='')}/"
        f"{quote(file_path, safe='/')}"
    )
    fragments = {f"L{line_start}-L{line_end}"}
    if line_start == line_end:
        fragments.add(f"L{line_start}")
    return (
        parsed.scheme == "https"
        and parsed.netloc == "github.com"
        and parsed.path == expected_path
        and not parsed.query
        and parsed.fragment in fragments
    )
