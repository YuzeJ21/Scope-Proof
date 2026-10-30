"""Git source coordinates use LF boundaries even when source contains other separators."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scopeproof_core.github.client import _parse_patch
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.schemas.models import (
    ChangedFile,
    Criterion,
    EvidenceLevel,
    EvidenceSourceScope,
    EvidenceType,
    LineChangeType,
    PullRequestSnapshot,
    RetrievedFile,
)

_SEPARATORS = (
    ("CR", "\r"),
    ("VT", "\v"),
    ("FF", "\f"),
    ("FS", "\x1c"),
    ("GS", "\x1d"),
    ("RS", "\x1e"),
    ("NEL", "\x85"),
    ("LS", "\u2028"),
    ("PS", "\u2029"),
)
_HEAD = "2222222222222222222222222222222222222222"
_BASE = "1111111111111111111111111111111111111111"
_CRITERION = Criterion(criterion_id="AC-01", text="Find target_identifier")


def _snapshot(
    files: list[ChangedFile], *, head_sha: str = _HEAD, base_sha: str = _BASE
) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repository="acme/widget",
        pr_number=7,
        title="Source-coordinate regression fixture",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha=base_sha,
        head_sha=head_sha,
        fetched_at=datetime(2026, 10, 30, tzinfo=UTC),
        files=files,
    )


@pytest.mark.parametrize(
    "separator", [item[1] for item in _SEPARATORS], ids=[item[0] for item in _SEPARATORS]
)
@pytest.mark.parametrize(
    "embedded_prefix",
    ["@@ -1,2 +900,2 @@", "+forged_added()", "-forged_removed()"],
    ids=["fake-hunk", "fake-addition", "fake-deletion"],
)
def test_embedded_non_lf_separator_cannot_inject_patch_protocol(
    separator: str, embedded_prefix: str
) -> None:
    first_line = f"prefix{separator}{embedded_prefix} suffix"
    patch = f"@@ -1,2 +1,2 @@\n-before\n+{first_line}\n target_identifier()\n"

    parsed = _parse_patch(patch)

    assert [(line.change_type, line.line_number, line.content) for line in parsed] == [
        (LineChangeType.REMOVED, 1, "before"),
        (LineChangeType.ADDED, 1, first_line),
        (LineChangeType.CONTEXT, 2, "target_identifier()"),
    ]


@pytest.mark.parametrize(
    "separator", [item[1] for item in _SEPARATORS], ids=[item[0] for item in _SEPARATORS]
)
def test_removed_source_cannot_inject_nonexistent_added_evidence(separator: str) -> None:
    removed_content = f"old{separator}+target_identifier()"
    patch = f"@@ -1 +1 @@\n-{removed_content}\n+unrelated()\n"
    snapshot = _snapshot(
        [
            ChangedFile(
                path="src/coordinates.txt",
                status="modified",
                patch=patch,
                lines=_parse_patch(patch),
            )
        ]
    )

    result = retrieve_evidence_with_diagnostics(snapshot, [_CRITERION])

    assert result.evidence == []
    assert result.diagnostics[0].inspectable_line_count == 1
    assert result.diagnostics[0].exact_identifier_match_line_count == 0


@pytest.mark.parametrize(
    "separator", [item[1] for item in _SEPARATORS], ids=[item[0] for item in _SEPARATORS]
)
@pytest.mark.parametrize("path", ["src/coordinates.txt", "tests/coordinates.txt"])
@pytest.mark.parametrize("route", ["changed", "unchanged"])
def test_retrieval_keeps_literal_lf_line_two_and_complete_neighbor(
    separator: str, path: str, route: str
) -> None:
    first_line = f"prefix{separator}suffix"
    source = f"{first_line}\ntarget_identifier()\n"
    if route == "changed":
        patch = f"@@ -0,0 +1,2 @@\n+{first_line}\n+target_identifier()\n"
        snapshot = _snapshot(
            [ChangedFile(path=path, status="added", patch=patch, lines=_parse_patch(patch))]
        )
        unchanged_files = []
    else:
        snapshot = _snapshot([])
        unchanged_files = [
            RetrievedFile(
                path=path,
                content=source,
                commit_sha=_HEAD,
                retrieval_reason="Matched target_identifier at immutable review head",
            )
        ]

    result = retrieve_evidence_with_diagnostics(snapshot, [_CRITERION], unchanged_files)

    assert len(result.evidence) == 1
    candidate = result.evidence[0]
    assert candidate.line_start == candidate.line_end == 2
    assert candidate.permalink == f"https://github.com/acme/widget/blob/{_HEAD}/{path}#L2-L2"
    assert candidate.commit_sha == _HEAD
    assert candidate.excerpt == "target_identifier()"
    assert candidate.context_excerpt == f"{first_line}\ntarget_identifier()"
    assert result.diagnostics[0].inspectable_line_count == 2
    assert result.diagnostics[0].eligible_candidate_count == 1
    assert candidate.source_scope is (
        EvidenceSourceScope.CHANGED_FILE
        if route == "changed"
        else EvidenceSourceScope.UNCHANGED_CANDIDATE
    )
    assert candidate.evidence_type is (
        EvidenceType.TEST if path.startswith("tests/") else EvidenceType.IMPLEMENTATION
    )
    assert candidate.evidence_level is (
        EvidenceLevel.E2 if path.startswith("tests/") else EvidenceLevel.E1
    )
    assert "Candidate evidence does not prove the criterion is satisfied" in candidate.limitations
    if path.startswith("tests/"):
        assert (
            "Candidate test/eval definition shows test intent, not execution"
            in candidate.limitations
        )


@dataclass(frozen=True)
class _GitSources:
    base_sha: str
    head_sha: str
    blobs: dict[str, bytes]
    patches: dict[str, bytes]


@pytest.fixture(scope="module")
def git_sources(tmp_path_factory: pytest.TempPathFactory) -> _GitSources:
    """Create inert source bytes; Git reads them, and no fixture source is executed."""
    git_binary = shutil.which("git")
    if git_binary is None:
        pytest.skip("Git binary is unavailable; pure coordinate regressions still run")
    root = tmp_path_factory.mktemp("git-source-coordinates")
    repository = root / "repository"
    repository.mkdir()
    hooks = root / "empty-hooks"
    hooks.mkdir()
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_AUTHOR_NAME": "ScopeProof fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "ScopeProof fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )

    def git(*arguments: str) -> bytes:
        return subprocess.run(
            [
                git_binary,
                "-c",
                f"core.hooksPath={hooks.as_posix()}",
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.safecrlf=false",
                "-c",
                "core.eol=lf",
                "-c",
                f"core.attributesFile={os.devnull}",
                "-c",
                "commit.gpgsign=false",
                *arguments,
            ],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
        ).stdout

    git("init", "--quiet")
    sources: dict[str, bytes] = {}
    for name, separator in _SEPARATORS:
        for directory in ("src", "tests"):
            for route in ("changed", "unchanged"):
                path = f"{directory}/{route}_{name}.txt"
                content = f"prefix{separator}suffix\ntarget_identifier()\n".encode()
                sources[path] = content
                destination = repository / Path(path)
                destination.parent.mkdir(exist_ok=True)
                destination.write_bytes(
                    b"before\ntarget_identifier()\n" if route == "changed" else content
                )
    for path, content in (
        ("src/changed_EOF_CR.txt", b"target_identifier()\r"),
        ("src/changed_CRLF.txt", b"target_identifier()\r\n"),
    ):
        sources[path] = content
        (repository / Path(path)).write_bytes(b"before\n")
    git("add", "--", ".")
    git("commit", "--quiet", "-m", "Base fixture")
    base_sha = git("rev-parse", "HEAD").decode("ascii").strip()
    for path, content in sources.items():
        if "/changed_" in path:
            (repository / Path(path)).write_bytes(content)
    git("add", "--", ".")
    git("commit", "--quiet", "-m", "Head fixture")
    head_sha = git("rev-parse", "HEAD").decode("ascii").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", head_sha)
    blobs = {path: git("cat-file", "blob", f"{head_sha}:{path}") for path in sources}
    patches = {
        path: git(
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--unified=1",
            base_sha,
            head_sha,
            "--",
            path,
        )
        for path in sources
    }
    return _GitSources(base_sha=base_sha, head_sha=head_sha, blobs=blobs, patches=patches)


@pytest.mark.parametrize(("name", "separator"), _SEPARATORS, ids=[item[0] for item in _SEPARATORS])
@pytest.mark.parametrize("directory", ["src", "tests"])
@pytest.mark.parametrize("route", ["changed", "unchanged"])
def test_actual_git_blob_and_diff_agree_on_literal_source_line_two(
    git_sources: _GitSources, name: str, separator: str, directory: str, route: str
) -> None:
    path = f"{directory}/{route}_{name}.txt"
    first_line = f"prefix{separator}suffix"
    blob = git_sources.blobs[path]
    assert blob == f"{first_line}\ntarget_identifier()\n".encode()
    assert blob.count(b"\n") == 2
    raw_diff = git_sources.patches[path]
    if route == "changed":
        hunk_start = raw_diff.index(b"\n@@ ") + 1
        raw_patch = raw_diff[hunk_start:]
        assert raw_patch == (
            f"@@ -1,2 +1,2 @@\n-before\n+{first_line}\n target_identifier()\n".encode()
        )
        patch = raw_patch.decode("utf-8")
        files = [ChangedFile(path=path, status="modified", patch=patch, lines=_parse_patch(patch))]
        unchanged_files = []
    else:
        assert raw_diff == b""
        files = []
        unchanged_files = [
            RetrievedFile(
                path=path,
                content=blob.decode("utf-8"),
                commit_sha=git_sources.head_sha,
                retrieval_reason="Matched target_identifier at immutable review head",
            )
        ]
    snapshot = _snapshot(files, head_sha=git_sources.head_sha, base_sha=git_sources.base_sha)

    result = retrieve_evidence_with_diagnostics(snapshot, [_CRITERION], unchanged_files)

    assert len(result.evidence) == 1
    candidate = result.evidence[0]
    assert candidate.line_start == candidate.line_end == 2
    assert candidate.permalink == (
        f"https://github.com/acme/widget/blob/{git_sources.head_sha}/{path}#L2-L2"
    )
    assert candidate.commit_sha == git_sources.head_sha
    assert candidate.excerpt == "target_identifier()"
    assert candidate.context_excerpt == f"{first_line}\ntarget_identifier()"
    assert result.diagnostics[0].inspectable_line_count == 2
    assert candidate.evidence_type is (
        EvidenceType.TEST if directory == "tests" else EvidenceType.IMPLEMENTATION
    )
    assert candidate.evidence_level is (
        EvidenceLevel.E2 if directory == "tests" else EvidenceLevel.E1
    )
    assert "Candidate evidence does not prove the criterion is satisfied" in candidate.limitations


@pytest.mark.parametrize(
    ("path", "expected_blob", "expected_content", "expected_marker"),
    [
        (
            "src/changed_EOF_CR.txt",
            b"target_identifier()\r",
            "target_identifier()\r",
            b"\\ No newline at end of file\n",
        ),
        (
            "src/changed_CRLF.txt",
            b"target_identifier()\r\n",
            "target_identifier()",
            b"",
        ),
    ],
    ids=["unterminated-source-CR", "ordinary-CRLF"],
)
def test_actual_git_distinguishes_unterminated_source_cr_from_crlf_terminator(
    git_sources: _GitSources,
    path: str,
    expected_blob: bytes,
    expected_content: str,
    expected_marker: bytes,
) -> None:
    assert git_sources.blobs[path] == expected_blob
    raw_diff = git_sources.patches[path]
    raw_patch = raw_diff[raw_diff.index(b"\n@@ ") + 1 :]
    assert raw_patch == (b"@@ -1 +1 @@\n-before\n+target_identifier()\r\n" + expected_marker)

    patch = raw_patch.decode("utf-8")
    parsed = _parse_patch(patch)

    assert [(line.change_type, line.line_number, line.content) for line in parsed] == [
        (LineChangeType.REMOVED, 1, "before"),
        (LineChangeType.ADDED, 1, expected_content),
    ]
    snapshot = _snapshot(
        [ChangedFile(path=path, status="modified", patch=patch, lines=parsed)],
        head_sha=git_sources.head_sha,
        base_sha=git_sources.base_sha,
    )

    result = retrieve_evidence_with_diagnostics(snapshot, [_CRITERION])

    assert len(result.evidence) == 1
    candidate = result.evidence[0]
    assert candidate.context_excerpt == expected_content
    assert candidate.line_start == candidate.line_end == 1
    assert candidate.permalink == (
        f"https://github.com/acme/widget/blob/{git_sources.head_sha}/{path}#L1-L1"
    )
