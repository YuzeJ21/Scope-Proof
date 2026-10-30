"""Correct new references without silently rewriting saved historical coordinates."""

import csv
import io
import json

import pytest

from scopeproof_core.build_identity import CoreSourceIdentity
from scopeproof_core.demo import build_review
from scopeproof_core.github.client import _parse_patch
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.reviews.lifecycle import new_review_state, revise_criteria
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    LineChangeType,
    PullRequestSnapshot,
    RetrievedFile,
)
from scopeproof_core.storage.json_store import JsonReviewStore

_HEAD = "2" * 40
_LABELS = {
    "source_text": "- Find target_identifier",
    "criteria_confirmed": True,
    "criteria": [{"criterion_id": "AC-01", "text": "Find target_identifier"}],
}


def test_github_crlf_patch_without_protocol_lf_matches_unchanged_source_context():
    # GitHub's patch field can omit its final protocol LF for a CRLF-terminated blob.
    patch = "@@ -0,0 +1 @@\n+target_identifier()\r"
    lines = _parse_patch(patch)
    assert lines[0].content == "target_identifier()"
    snapshot = PullRequestSnapshot(
        repository="acme/widget",
        pr_number=7,
        title="Constructed API-shaped CRLF patch",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha="1" * 40,
        head_sha=_HEAD,
        files=[ChangedFile(path="src/coordinates.txt", status="added", patch=patch, lines=lines)],
    )
    state = new_review_state(build_review(snapshot, _LABELS))
    changed = state.bundle.evidence[0]
    unchanged = retrieve_evidence(
        snapshot.model_copy(update={"files": []}),
        state.criteria_revision.criteria,
        [
            RetrievedFile(
                path="src/coordinates.txt",
                content="target_identifier()\r\n",
                commit_sha=_HEAD,
                retrieval_reason="Constructed immutable CRLF source",
            )
        ],
    )[0]
    assert changed.excerpt == unchanged.excerpt == "target_identifier()"
    assert changed.context_excerpt == unchanged.context_excerpt == "target_identifier()"
    assert changed.line_start == changed.line_end == unchanged.line_start == unchanged.line_end == 1


def coordinate_state(*, legacy: bool = False):
    patch = "@@ -0,0 +1,2 @@\n+prefix\u2028suffix\n+target_identifier()\n"
    lines = (
        [
            ChangedLine(
                change_type=LineChangeType.ADDED, line_number=3, content="target_identifier()"
            )
        ]
        if legacy
        else _parse_patch(patch)
    )
    snapshot = PullRequestSnapshot(
        repository="acme/widget",
        pr_number=7,
        title="Constructed coordinate export",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha="1" * 40,
        head_sha=_HEAD,
        files=[ChangedFile(path="src/coordinates.txt", status="added", patch=patch, lines=lines)],
    )
    bundle = build_review(snapshot, _LABELS)
    if legacy:
        # An illustrative previously recorded source identity, not a fresh attestation.
        bundle.review.analysis_source_identity = CoreSourceIdentity(sha256="1" * 64)
    return new_review_state(bundle)


def test_new_exports_retain_whole_context_and_literal_git_line_two():
    state = coordinate_state()
    payload = json.loads(export_json(state))
    candidate = payload["bundle"]["evidence"][0]
    assert candidate["line_start"] == candidate["line_end"] == 2
    assert candidate["context_excerpt"] == "prefix\u2028suffix\ntarget_identifier()"
    link = f"https://github.com/acme/widget/blob/{_HEAD}/src/coordinates.txt#L2-L2"
    assert candidate["permalink"] == link
    row = next(csv.DictReader(io.StringIO(export_csv(state))))
    assert json.loads(row["evidence_links"]) == [link]
    assert link in export_markdown(state)
    assert link in export_html(state)
    assert state.bundle.runtime_evidence == []
    assert state.bundle.resolutions == []
    assert not state.review.final_acceptance
    assert state.bundle.gate.verdict.value != "ready"


@pytest.mark.parametrize("archived", [False, True])
def test_loading_and_exporting_old_coordinates_does_not_reparse_or_renumber(tmp_path, archived):
    state = coordinate_state(legacy=True)
    if archived:
        state = revise_criteria(
            state, state.criteria_revision.criteria, state.criteria_revision.source_text
        )
    store = JsonReviewStore(tmp_path / "records")
    store.save(state)
    path = store.directory / f"{state.review.review_id}.json"
    original_bytes = path.read_bytes()

    loaded = store.load(state.review.review_id)
    bundle = loaded.analysis_history[0] if archived else loaded.bundle
    assert bundle.evidence[0].line_start == bundle.evidence[0].line_end == 3
    assert bundle.evidence[0].permalink.endswith("#L3-L3")
    assert bundle.review.analysis_source_identity.sha256 == "1" * 64
    exported = json.loads(export_json(bundle if archived else loaded))
    exported_bundle = exported if archived else exported["bundle"]
    assert exported_bundle["evidence"][0]["line_start"] == 3
    assert path.read_bytes() == original_bytes
