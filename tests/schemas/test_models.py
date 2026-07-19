from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import (
    CheckState,
    CIObservation,
    Criterion,
    EvidenceItem,
    EvidenceLevel,
    EvidenceType,
    Finding,
    FindingStatus,
    IngestionState,
    Priority,
    PullRequestSnapshot,
    Review,
    SavedReviewListing,
)
from scopeproof_core.version import __version__


def candidate_evidence_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "evidence_id": "EV-1",
        "criterion_id": "AC-01",
        "evidence_type": EvidenceType.IMPLEMENTATION,
        "evidence_level": EvidenceLevel.E1,
        "file_path": "src/export.py",
        "line_start": 2,
        "line_end": 4,
        "commit_sha": "head123",
        "permalink": "https://github.com/acme/repo/blob/head123/src/export.py#L2-L4",
        "excerpt": "def export_csv():",
        "matching_rule": "identifier",
        "relevance_reason": "Matched export_csv",
        "relevance_score": 0.9,
        "limitations": ["Candidate evidence does not prove runtime behavior"],
    }
    payload.update(overrides)
    return payload


def finding_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "criterion_id": "AC-01",
        "status": FindingStatus.MISSING,
        "reason": "No candidate evidence was found.",
        "missing_evidence": ["Required evidence level E1"],
        "contradictions": [],
        "recommended_action": "Add or identify candidate evidence.",
    }
    payload.update(overrides)
    return payload


def review_identity_payload(model, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "repository": "acme/widgets",
        "pr_number": 7,
        "base_sha": "base123",
        "head_sha": "head123",
    }
    if model is PullRequestSnapshot:
        payload.update(
            {
                "title": "Example",
                "html_url": "https://github.com/acme/widgets/pull/7",
            }
        )
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    "review_ids",
    [["z-review", "a-review"], ["duplicate", "duplicate"], ["../unsafe"]],
)
def test_saved_review_listing_rejects_unsorted_duplicate_or_unsafe_ids(
    review_ids: list[str],
) -> None:
    with pytest.raises(ValidationError):
        SavedReviewListing(review_ids=review_ids, storage_dir=".scopeproof/reviews")


def test_evidence_rejects_line_range_without_sha() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="EV-1",
            criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            evidence_level=EvidenceLevel.E1,
            file_path="src/export.py",
            line_start=2,
            line_end=4,
            commit_sha="",
            permalink="https://github.com/acme/repo/blob/sha/src/export.py#L2-L4",
            excerpt="def export_csv():",
            matching_rule="identifier",
            relevance_reason="Matched export_csv",
            relevance_score=0.9,
        )


def test_evidence_rejects_reversed_line_range() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="EV-1",
            criterion_id="AC-01",
            evidence_type=EvidenceType.IMPLEMENTATION,
            evidence_level=EvidenceLevel.E1,
            file_path="src/export.py",
            line_start=8,
            line_end=4,
            commit_sha="head123",
            permalink="https://github.com/acme/repo/blob/head123/src/export.py#L8-L4",
            excerpt="def export_csv():",
            matching_rule="identifier",
            relevance_reason="Matched export_csv",
            relevance_score=0.9,
        )


@pytest.mark.parametrize(
    "field",
    [
        "evidence_id",
        "criterion_id",
        "file_path",
        "commit_sha",
        "permalink",
        "excerpt",
        "matching_rule",
        "relevance_reason",
    ],
)
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_candidate_evidence_context_rejects_blank_required_text(
    field: str, blank: str
) -> None:
    with pytest.raises(ValidationError, match="must contain non-whitespace text"):
        EvidenceItem.model_validate(candidate_evidence_payload(**{field: blank}))


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_candidate_evidence_context_rejects_blank_limitation(blank: str) -> None:
    with pytest.raises(ValidationError, match="limitations must contain non-whitespace text"):
        EvidenceItem.model_validate(candidate_evidence_payload(limitations=[blank]))


def test_candidate_evidence_context_preserves_valid_text_exactly() -> None:
    item = EvidenceItem.model_validate(
        candidate_evidence_payload(
            excerpt="  def export_csv():  ",
            relevance_reason="  Matched export_csv  ",
            limitations=["  Requires reviewer confirmation  "],
        )
    )

    assert item.excerpt == "  def export_csv():  "
    assert item.relevance_reason == "  Matched export_csv  "
    assert item.limitations == ["  Requires reviewer confirmation  "]


def test_candidate_evidence_context_allows_no_limitations() -> None:
    item = EvidenceItem.model_validate(candidate_evidence_payload(limitations=[]))

    assert item.limitations == []


def test_candidate_evidence_allows_missing_context_for_legacy_records() -> None:
    item = EvidenceItem.model_validate(candidate_evidence_payload())

    assert item.context_excerpt is None


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_candidate_evidence_rejects_blank_optional_context(blank: str) -> None:
    with pytest.raises(ValidationError, match="context excerpt must contain non-whitespace text"):
        EvidenceItem.model_validate(candidate_evidence_payload(context_excerpt=blank))


def test_candidate_evidence_preserves_legacy_non_http_permalink_for_inert_recovery() -> None:
    permalink = "relative/legacy-evidence"

    item = EvidenceItem.model_validate(candidate_evidence_payload(permalink=permalink))

    assert item.permalink == permalink


@pytest.mark.parametrize("field", ["reason", "recommended_action"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_required_text(field: str, blank: str) -> None:
    with pytest.raises(ValidationError, match="must contain non-whitespace text"):
        Finding.model_validate(finding_payload(**{field: blank}))


@pytest.mark.parametrize("field", ["missing_evidence", "contradictions"])
@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_finding_context_rejects_blank_list_member(field: str, blank: str) -> None:
    with pytest.raises(
        ValidationError, match="finding context must contain non-whitespace text"
    ):
        Finding.model_validate(finding_payload(**{field: [blank]}))


def test_finding_context_preserves_valid_text_exactly() -> None:
    finding = Finding.model_validate(
        finding_payload(
            reason="  No candidate evidence was found.  ",
            recommended_action="  Add candidate evidence.  ",
            missing_evidence=["  Required evidence level E1  "],
            contradictions=["  Conflicting implementation  "],
        )
    )

    assert finding.reason == "  No candidate evidence was found.  "
    assert finding.recommended_action == "  Add candidate evidence.  "
    assert finding.missing_evidence == ["  Required evidence level E1  "]
    assert finding.contradictions == ["  Conflicting implementation  "]


def test_finding_context_allows_empty_optional_lists() -> None:
    finding = Finding.model_validate(finding_payload(missing_evidence=[], contradictions=[]))

    assert finding.missing_evidence == []
    assert finding.contradictions == []


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
@pytest.mark.parametrize("field_name", ["base_sha", "head_sha"])
@pytest.mark.parametrize("blank", ["   ", "\t\n"])
def test_review_identity_rejects_whitespace_only_shas(model, field_name, blank) -> None:
    with pytest.raises(
        ValidationError, match="review identity must contain non-whitespace text"
    ):
        model.model_validate(review_identity_payload(model, **{field_name: blank}))


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
@pytest.mark.parametrize("repository", [" / ", "acme/ ", " acme/widgets", "acme/widgets/extra"])
def test_review_identity_rejects_malformed_repositories(model, repository) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(review_identity_payload(model, repository=repository))


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
def test_review_identity_preserves_valid_nonblank_values(model) -> None:
    payload = review_identity_payload(
        model,
        repository="YuzeJ21/Scope-Proof",
        base_sha="  base123  ",
        head_sha="head-demo-002",
    )

    identity = model.model_validate(payload)

    assert identity.repository == "YuzeJ21/Scope-Proof"
    assert identity.base_sha == "  base123  "
    assert identity.head_sha == "head-demo-002"


def test_review_requires_confirmed_criteria_before_analysis() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
    )
    assert review.criteria_confirmed is False
    assert review.can_analyze is False


def test_confirmed_complete_review_can_analyze() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        criteria_confirmed=True,
        ingestion_state=IngestionState.COMPLETE,
    )
    assert review.can_analyze is True


def test_ci_observation_requires_consistent_counts_and_bounded_skipped_names() -> None:
    with pytest.raises(ValidationError):
        CIObservation(
            state=CheckState.UNAVAILABLE,
            reason=" ",
        )
    with pytest.raises(ValidationError):
        CIObservation(
            state=CheckState.PASSING,
            reason="Observed CI.",
            total_check_runs=1,
            successful_check_runs=2,
        )
    with pytest.raises(ValidationError):
        CIObservation(
            state=CheckState.UNAVAILABLE,
            reason="Skipped checks were observed.",
            total_check_runs=9,
            skipped_check_runs=9,
            skipped_check_names=[f"check-{index}" for index in range(9)],
        )


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
def test_ci_observation_must_agree_with_top_level_check_state(model) -> None:
    payload = review_identity_payload(
        model,
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PENDING,
            reason="Observed 1 pending check run.",
            total_check_runs=1,
            pending_check_runs=1,
        ),
    )

    with pytest.raises(ValidationError, match="check_state must agree"):
        model.model_validate(payload)


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
def test_new_records_default_to_an_unavailable_ci_observation(model) -> None:
    record = model.model_validate(review_identity_payload(model))

    assert record.ci_observation.state is CheckState.UNAVAILABLE
    assert (
        record.ci_observation.reason
        == "No check runs or concrete legacy statuses were observed."
    )


@pytest.mark.parametrize("model", [PullRequestSnapshot, Review])
def test_historical_ci_observation_is_incomplete(model) -> None:
    record = model.model_validate(
        review_identity_payload(model, check_state=CheckState.PASSING)
    )

    assert record.ci_observation.collection_complete is False


def test_review_preserves_ingestion_limitations_with_backward_compatible_defaults() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        ingestion_state=IngestionState.PARTIAL,
        ingestion_warnings=["File limit reached; skipped 2 changed files."],
        skipped_files=["src/one.py", "src/two.py"],
    )

    reopened = Review.model_validate_json(review.model_dump_json())
    historical = Review.model_validate(
        {
            "repository": "acme/repo",
            "pr_number": 7,
            "base_sha": "base",
            "head_sha": "head",
        }
    )

    assert reopened.ingestion_warnings == ["File limit reached; skipped 2 changed files."]
    assert reopened.skipped_files == ["src/one.py", "src/two.py"]
    assert historical.ingestion_warnings == []
    assert historical.skipped_files == []


@pytest.mark.parametrize(
    ("model", "extra"),
    [
        (Review, {"ingestion_warnings": ["unexpected limitation"]}),
        (Review, {"skipped_files": ["src/skipped.py"]}),
        (PullRequestSnapshot, {"warnings": ["unexpected limitation"]}),
        (PullRequestSnapshot, {"skipped_files": ["src/skipped.py"]}),
    ],
)
def test_complete_ingestion_rejects_limitation_provenance(model, extra) -> None:
    base = {
        "repository": "acme/widgets",
        "pr_number": 7,
        "base_sha": "base123",
        "head_sha": "head123",
        "ingestion_state": IngestionState.COMPLETE,
    }
    if model is PullRequestSnapshot:
        base.update(
            {
                "title": "Example",
                "html_url": "https://github.com/acme/widgets/pull/7",
            }
        )

    with pytest.raises(ValueError, match="complete ingestion cannot include limitations"):
        model.model_validate({**base, **extra})


def test_new_review_records_current_package_version() -> None:
    review = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
    )

    assert review.tool_version == __version__


def test_review_round_trip_preserves_historical_tool_version() -> None:
    historical = Review(
        repository="acme/repo",
        pr_number=7,
        base_sha="base",
        head_sha="head",
        tool_version="0.1.0",
    )

    reopened = Review.model_validate_json(historical.model_dump_json())
    assert reopened.tool_version == "0.1.0"


def test_snapshot_round_trip_preserves_changed_lines() -> None:
    snapshot = PullRequestSnapshot(
        repository="acme/repo",
        pr_number=7,
        title="Export CSV",
        description="Adds CSV export",
        html_url="https://github.com/acme/repo/pull/7",
        base_sha="base",
        head_sha="head",
        check_state=CheckState.PASSING,
        fetched_at=datetime.now(UTC),
        files=[],
    )
    assert PullRequestSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot


def test_criterion_defaults_to_must_have_e1() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV")
    assert criterion.priority is Priority.MUST_HAVE
    assert criterion.required_evidence_level is EvidenceLevel.E1


@pytest.mark.parametrize("text", ["", "   ", "\t\n"])
def test_criterion_rejects_blank_normalized_text(text: str) -> None:
    with pytest.raises(ValidationError):
        Criterion(criterion_id="AC-01", text=text)


def test_criterion_normalizes_nonblank_text_before_validation() -> None:
    criterion = Criterion(criterion_id="AC-01", text="  Export CSV  ")

    assert criterion.text == "Export CSV"
