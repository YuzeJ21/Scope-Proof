"""Independent safety regressions for session-only JUnit mapping drafts."""

from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError

import scopeproof_core.importers.junit as junit_module
from scopeproof_core.importers.junit import (
    JUnitMappingSelection,
    build_junit_evidence_import,
    parse_junit_artifact,
)
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import
from scopeproof_core.schemas.models import ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.importers.test_junit import SIMPLE_XML, TWO_CASE_XML, exact_head_state


def load_draft_api() -> ModuleType:
    try:
        return import_module("scopeproof_core.importers.junit_draft")
    except ModuleNotFoundError as error:
        if error.name != "scopeproof_core.importers.junit_draft":
            raise
        pytest.fail("JUnit mapping draft feature is not implemented yet", pytrace=False)


def staged_draft(api: ModuleType, state: ReviewState, xml: bytes = TWO_CASE_XML):
    return api.extend_junit_mapping_draft(
        state,
        xml,
        api.new_junit_mapping_draft(state, xml),
        [JUnitMappingSelection(scope_id="suite-0001-case-0001", criterion_id="AC-01")],
        importer="Constructed QA actor",
    )


@pytest.mark.parametrize("operation", ["extend", "remove", "build"])
def test_replacement_bytes_with_same_scope_ids_expire_every_draft_operation(operation: str) -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    replacement = TWO_CASE_XML.replace(b"test_export", b"test_replacement")
    old = parse_junit_artifact(TWO_CASE_XML)
    new = parse_junit_artifact(replacement)
    assert [case.test_case_id for case in old.suites[0].test_cases] == [
        case.test_case_id for case in new.suites[0].test_cases
    ]
    original = draft.model_dump(mode="python")

    with pytest.raises(ValueError):
        if operation == "extend":
            draft_api.extend_junit_mapping_draft(
                state,
                replacement,
                draft,
                [JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02")],
                importer="Constructed QA actor",
            )
        elif operation == "remove":
            draft_api.remove_junit_mapping_criterion(state, replacement, draft, "AC-01")
        else:
            draft_api.build_drafted_junit_import(
                state, replacement, draft, importer="Constructed QA actor"
            )

    assert draft.model_dump(mode="python") == original


@pytest.mark.parametrize("operation", ["extend", "remove", "build"])
@pytest.mark.parametrize("change", ["evidence_limitation", "source_provenance"])
def test_full_state_change_expires_draft_without_changing_criterion_or_head_ids(
    operation: str, change: str
) -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    changed = state.model_copy(deep=True)
    assert changed.bundle is not None
    if change == "evidence_limitation":
        changed.bundle.evidence[0].limitations.append("Additional constructed source limitation.")
    else:
        assert changed.review.criteria_source_provenance is not None
        provenance = changed.review.criteria_source_provenance.model_copy(
            update={"source_revision": "replacement-source-revision"}
        )
        changed.review.criteria_source_provenance = provenance
        changed.criteria_revision.source_provenance = provenance
        changed.bundle.review.criteria_source_provenance = provenance
    changed = ReviewState.model_validate(changed.model_dump(mode="python"))
    assert changed.review.head_sha == state.review.head_sha
    assert [item.criterion_id for item in changed.criteria_revision.criteria] == [
        item.criterion_id for item in state.criteria_revision.criteria
    ]

    with pytest.raises(ValueError):
        if operation == "extend":
            draft_api.extend_junit_mapping_draft(
                changed,
                TWO_CASE_XML,
                draft,
                [JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02")],
                importer="Constructed QA actor",
            )
        elif operation == "remove":
            draft_api.remove_junit_mapping_criterion(changed, TWO_CASE_XML, draft, "AC-01")
        else:
            draft_api.build_drafted_junit_import(
                changed, TWO_CASE_XML, draft, importer="Constructed QA actor"
            )


def test_rejected_overlap_does_not_partly_apply_a_valid_addition() -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    before = draft.model_dump(mode="python")

    with pytest.raises(ValueError, match="multiple criteria"):
        draft_api.extend_junit_mapping_draft(
            state,
            TWO_CASE_XML,
            draft,
            [
                JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02"),
                JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-02"),
            ],
            importer="Constructed QA actor",
        )

    assert draft.model_dump(mode="python") == before
    record = draft_api.build_drafted_junit_import(
        state, TWO_CASE_XML, draft, importer="Constructed QA actor"
    )
    assert [(item.criterion_id, item.test_case_ids) for item in record.criterion_mappings] == [
        ("AC-01", ["suite-0001-case-0001"])
    ]


def test_draft_schema_rejects_unknown_fields_at_both_levels() -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    payload = draft.model_dump(mode="python")

    with pytest.raises(ValidationError):
        draft_api.JUnitMappingDraft.model_validate({**payload, "verified": True})
    payload["selections"] = [{"scope_id": "suite-0001", "criterion_id": "AC-01", "verified": True}]
    with pytest.raises(ValidationError):
        draft_api.JUnitMappingDraft.model_validate(payload)


@pytest.mark.parametrize("operation", ["extend", "remove", "build"])
def test_forged_typed_nested_selection_is_revalidated(operation: str) -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    forged = draft.model_copy(
        update={
            "selections": (
                JUnitMappingSelection.model_construct(scope_id=" ", criterion_id="AC-01"),
            )
        }
    )

    with pytest.raises(ValueError):
        if operation == "extend":
            draft_api.extend_junit_mapping_draft(
                state,
                TWO_CASE_XML,
                forged,
                [JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02")],
                importer="Constructed QA actor",
            )
        elif operation == "remove":
            draft_api.remove_junit_mapping_criterion(state, TWO_CASE_XML, forged, "AC-01")
        else:
            draft_api.build_drafted_junit_import(
                state, TWO_CASE_XML, forged, importer="Constructed QA actor"
            )


def test_forged_added_selection_cannot_enter_a_draft() -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    draft = staged_draft(draft_api, state)
    forged = JUnitMappingSelection.model_construct(scope_id="suite-0001", criterion_id=" ")

    with pytest.raises(ValueError):
        draft_api.extend_junit_mapping_draft(
            state, TWO_CASE_XML, draft, [forged], importer="Constructed QA actor"
        )
    assert len(draft.selections) == 1


def test_draft_cannot_reimport_an_already_recorded_artifact() -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    record = build_junit_evidence_import(
        state,
        SIMPLE_XML,
        [JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-01")],
        importer="Constructed QA actor",
    )
    saved = append_junit_evidence_import(state, record)
    before = saved.model_dump(mode="python")

    with pytest.raises(ValueError, match=r"[Dd]uplicate|already imported"):
        draft = draft_api.new_junit_mapping_draft(saved, SIMPLE_XML)
        draft = draft_api.extend_junit_mapping_draft(
            saved,
            SIMPLE_XML,
            draft,
            [JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-02")],
            importer="Constructed QA actor",
        )
        draft_api.build_drafted_junit_import(
            saved, SIMPLE_XML, draft, importer="Constructed QA actor"
        )

    assert saved.model_dump(mode="python") == before


def test_new_draft_preserves_the_existing_parser_byte_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft_api = load_draft_api()
    monkeypatch.setattr(junit_module, "MAX_JUNIT_BYTES", len(SIMPLE_XML) - 1)
    with pytest.raises(ValueError, match="byte limit"):
        draft_api.new_junit_mapping_draft(exact_head_state(), SIMPLE_XML)


def test_new_draft_rejects_a_typed_state_with_removed_provenance() -> None:
    draft_api = load_draft_api()
    state = exact_head_state().model_copy(deep=True)
    assert state.bundle is not None
    state.review.criteria_source_provenance = None
    state.bundle.review.criteria_source_provenance = None
    state.criteria_revision.source_provenance = None

    with pytest.raises(ValueError):
        draft_api.new_junit_mapping_draft(state, SIMPLE_XML)


def test_draft_operations_leave_saved_review_and_gate_truth_unchanged(tmp_path: Path) -> None:
    draft_api = load_draft_api()
    state = exact_head_state()
    store = JsonReviewStore(tmp_path / "reviews")
    saved_path = store.save(state)
    saved_bytes = saved_path.read_bytes()
    original = state.model_dump(mode="python")
    draft = staged_draft(draft_api, state)
    draft = draft_api.extend_junit_mapping_draft(
        state,
        TWO_CASE_XML,
        draft,
        [JUnitMappingSelection(scope_id="suite-0001-case-0002", criterion_id="AC-02")],
        importer="Constructed QA actor",
    )
    record = draft_api.build_drafted_junit_import(
        state, TWO_CASE_XML, draft, importer="Constructed QA actor"
    )
    assert [(item.criterion_id, item.test_case_ids) for item in record.criterion_mappings] == [
        ("AC-01", ["suite-0001-case-0001"]),
        ("AC-02", ["suite-0001-case-0002"]),
    ]
    draft = draft_api.remove_junit_mapping_criterion(state, TWO_CASE_XML, draft, "AC-01")
    draft = draft_api.remove_junit_mapping_criterion(state, TWO_CASE_XML, draft, "AC-02")

    assert draft.selections == ()
    assert state.model_dump(mode="python") == original
    assert saved_path.read_bytes() == saved_bytes
    assert store.load(state.review.review_id).model_dump(mode="python") == original
    with pytest.raises(ValueError):
        draft_api.build_drafted_junit_import(
            state, TWO_CASE_XML, draft, importer="Constructed QA actor"
        )
