from scopeproof_core.criteria.service import parse_criteria, validate_criteria
from scopeproof_core.schemas.models import Criterion


def test_parse_criteria_preserves_user_language_and_assigns_ids() -> None:
    drafts = parse_criteria("Export CSV\nFailed export shows an error")
    assert [(draft.criterion_id, draft.text) for draft in drafts] == [
        ("AC-01", "Export CSV"),
        ("AC-02", "Failed export shows an error"),
    ]


def test_parse_criteria_removes_only_list_markers() -> None:
    drafts = parse_criteria("- Keep user's active filter\n2. Record research_exported")
    assert [draft.text for draft in drafts] == [
        "Keep user's active filter",
        "Record research_exported",
    ]


def test_compound_criterion_warns_but_is_not_silently_split() -> None:
    criterion = Criterion(criterion_id="AC-01", text="Export CSV and record analytics")
    warnings = validate_criteria([criterion])
    assert warnings[0].code == "compound_criterion"
    assert criterion.text == "Export CSV and record analytics"


def test_duplicate_criteria_are_reported() -> None:
    criteria = [
        Criterion(criterion_id="AC-01", text="Export CSV"),
        Criterion(criterion_id="AC-02", text=" export csv "),
    ]
    warnings = validate_criteria(criteria)
    assert any(warning.code == "duplicate_criterion" for warning in warnings)
