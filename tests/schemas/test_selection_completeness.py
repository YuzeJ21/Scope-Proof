import pytest
from pydantic import ValidationError

from scopeproof_core.schemas.models import CriterionRetrievalDiagnostic, ReviewBundle
from tests.candidate_selection_fixture import selection_bundle

_SELECTION_FIELDS = (
    "eligible_candidate_count",
    "candidate_limit",
    "omitted_candidate_count",
)


def legacy_diagnostic_payload() -> dict:
    """A historical result whose pre-selection population was never recorded."""
    return {
        "criterion_id": "AC-01",
        "outcome": "candidates_found",
        "searched_terms": ["csv", "export"],
        "exact_identifiers": [],
        "searched_paths": ["src/export.py"],
        "searched_evidence_types": ["implementation"],
        "changed_file_count": 1,
        "unchanged_candidate_file_count": 0,
        "inspectable_line_count": 12,
        "exact_identifier_match_line_count": 0,
        "term_overlap_line_count": 12,
        "below_threshold_line_count": 0,
        "accepted_candidate_count": 8,
    }


@pytest.mark.parametrize(
    ("eligible", "limit", "accepted", "omitted"),
    [
        (0, 8, 0, 0),
        (1, 8, 1, 0),
        (7, 8, 7, 0),
        (8, 8, 8, 0),
        (9, 8, 8, 1),
        (12, 8, 8, 4),
        (12, 20, 12, 0),
        (12, 1, 1, 11),
        (2, 8, 1, 1),
        (7, 8, 6, 1),
        (12, 20, 8, 4),
    ],
)
def test_complete_selection_tuple_roundtrips(
    eligible: int, limit: int, accepted: int, omitted: int
) -> None:
    payload = {
        **legacy_diagnostic_payload(),
        "eligible_candidate_count": eligible,
        "candidate_limit": limit,
        "accepted_candidate_count": accepted,
        "omitted_candidate_count": omitted,
    }

    diagnostic = CriterionRetrievalDiagnostic.model_validate(payload)

    assert diagnostic.eligible_candidate_count == eligible
    assert diagnostic.candidate_limit == limit
    assert diagnostic.accepted_candidate_count == accepted
    assert diagnostic.omitted_candidate_count == omitted
    assert (
        CriterionRetrievalDiagnostic.model_validate_json(diagnostic.model_dump_json()) == diagnostic
    )


@pytest.mark.parametrize("explicit_nulls", [False, True])
def test_legacy_selection_completeness_remains_unknown_after_roundtrip(
    explicit_nulls: bool,
) -> None:
    payload = legacy_diagnostic_payload()
    if explicit_nulls:
        payload.update(dict.fromkeys(_SELECTION_FIELDS))

    diagnostic = CriterionRetrievalDiagnostic.model_validate(payload)

    assert diagnostic.accepted_candidate_count == 8
    assert [getattr(diagnostic, field) for field in _SELECTION_FIELDS] == [None, None, None]
    restored = CriterionRetrievalDiagnostic.model_validate_json(diagnostic.model_dump_json())
    assert [getattr(restored, field) for field in _SELECTION_FIELDS] == [None, None, None]


@pytest.mark.parametrize(
    "partial",
    [
        {"eligible_candidate_count": 12},
        {"candidate_limit": 8},
        {"omitted_candidate_count": 4},
        {"eligible_candidate_count": 12, "candidate_limit": 8},
        {"eligible_candidate_count": 12, "omitted_candidate_count": 4},
        {"candidate_limit": 8, "omitted_candidate_count": 4},
        {"eligible_candidate_count": 12, "candidate_limit": 8, "omitted_candidate_count": None},
        {"eligible_candidate_count": 12, "candidate_limit": None, "omitted_candidate_count": 4},
        {"eligible_candidate_count": None, "candidate_limit": 8, "omitted_candidate_count": 4},
    ],
)
def test_selection_completeness_requires_all_or_none(partial: dict) -> None:
    with pytest.raises(ValidationError):
        CriterionRetrievalDiagnostic.model_validate({**legacy_diagnostic_payload(), **partial})


@pytest.mark.parametrize("field", _SELECTION_FIELDS)
@pytest.mark.parametrize("malformed", [True, False, "8", "12", "4", 8.0, 12.0, 4.0])
def test_selection_metadata_requires_strict_integers(field: str, malformed: object) -> None:
    # Keep the arithmetic consistent with a coercing parser so rejection must be
    # due to strict integer validation, rather than an unrelated count mismatch.
    coerced = int(malformed)
    eligible = coerced if field == "eligible_candidate_count" else 12
    limit = coerced if field == "candidate_limit" else 8
    if field == "omitted_candidate_count":
        eligible = 8 + coerced
    accepted = min(eligible, limit)
    payload = {
        **legacy_diagnostic_payload(),
        "inspectable_line_count": max(12, eligible),
        "accepted_candidate_count": accepted,
        "eligible_candidate_count": eligible,
        "candidate_limit": limit,
        "omitted_candidate_count": eligible - accepted,
        field: malformed,
    }

    with pytest.raises(ValidationError):
        CriterionRetrievalDiagnostic.model_validate(payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"eligible_candidate_count": -1},
        {"candidate_limit": 0},
        {"candidate_limit": -1},
        {"omitted_candidate_count": -1},
        {"accepted_candidate_count": 7},
        {"accepted_candidate_count": 9},
        {"omitted_candidate_count": 3},
        {"omitted_candidate_count": 5},
        {"inspectable_line_count": 11},
    ],
)
def test_selection_tuple_rejects_inconsistent_counts(changes: dict) -> None:
    payload = {
        **legacy_diagnostic_payload(),
        "eligible_candidate_count": 12,
        "candidate_limit": 8,
        "omitted_candidate_count": 4,
        **changes,
    }

    with pytest.raises(ValidationError):
        CriterionRetrievalDiagnostic.model_validate(payload)


def test_historical_bundle_does_not_infer_selection_population_from_evidence() -> None:
    payload = selection_bundle().model_dump(mode="json")
    for diagnostic in payload["retrieval_diagnostics"]:
        for field in _SELECTION_FIELDS:
            diagnostic.pop(field, None)

    historical = ReviewBundle.model_validate(payload)
    restored = ReviewBundle.model_validate_json(historical.model_dump_json())

    assert len(restored.evidence) == 8
    assert restored.retrieval_diagnostics[0].accepted_candidate_count == 8
    assert [getattr(restored.retrieval_diagnostics[0], field) for field in _SELECTION_FIELDS] == [
        None,
        None,
        None,
    ]
