from datetime import UTC, datetime

from scopeproof_core.retrieval.engine import retrieve_evidence
from scopeproof_core.schemas.models import CheckState, Criterion, PullRequestSnapshot, RetrievedFile


def test_unchanged_candidate_evidence_is_labeled_and_immutable() -> None:
    snapshot = PullRequestSnapshot(
        repository="acme/widget",
        pr_number=1,
        title="Export",
        html_url="https://github.com/acme/widget/pull/1",
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        fetched_at=datetime.now(UTC),
    )
    candidate = RetrievedFile(
        path="src/export.py",
        content="def export_csv(rows):\n    return rows\n",
        commit_sha="head",
        retrieval_reason="Matched criterion identifier export_csv",
    )
    evidence = retrieve_evidence(
        snapshot,
        [Criterion(criterion_id="AC-01", text="Export CSV")],
        unchanged_files=[candidate],
    )
    assert evidence[0].source_scope == "unchanged_candidate"
    assert evidence[0].commit_sha == "head"
    assert "unchanged candidate" in evidence[0].limitations[0].lower()
