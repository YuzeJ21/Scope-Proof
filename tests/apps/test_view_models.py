from apps.web.view_models import group_candidate_evidence
from scopeproof_core.demo import build_demo_review


def test_candidate_evidence_groups_preserve_first_occurrence_and_item_order() -> None:
    bundle = build_demo_review()
    items = [item for item in bundle.evidence if item.criterion_id == "AC-01"]

    groups = group_candidate_evidence(items)

    assert [(group.file_path, group.evidence_type.value) for group in groups] == [
        ("src/export.py", "implementation"),
        ("tests/test_export.py", "test"),
    ]
    assert [[item.evidence_id for item in group.items] for group in groups] == [
        ["EV-AC-01-01", "EV-AC-01-04"],
        ["EV-AC-01-02", "EV-AC-01-03"],
    ]


def test_candidate_evidence_grouping_keeps_every_validated_item_once() -> None:
    items = list(build_demo_review().evidence)

    grouped = group_candidate_evidence(items)

    flattened = [item for group in grouped for item in group.items]
    assert len(flattened) == len(items)
    assert sorted(item.evidence_id for item in flattened) == sorted(
        item.evidence_id for item in items
    )
    assert {id(item) for item in flattened} == {id(item) for item in items}
