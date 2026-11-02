"""Comparison replays correction history and retains its complete owning context."""

import copy
import html
import json
import re
import string
from uuid import uuid4

import pytest
from pydantic import ValidationError

from scopeproof_core.importers.junit import JUnitMappingSelection, build_junit_evidence_import
from scopeproof_core.reporting.exporters import (
    export_comparison_json,
    export_comparison_markdown,
)
from scopeproof_core.reviews.comparison import (
    JUnitImportReference,
    ReviewComparison,
    compare_reviews,
)
from scopeproof_core.reviews.junit_correction import correct_junit_mappings
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import, append_resolution
from scopeproof_core.schemas.models import (
    HumanDecision,
    JUnitCriterionMapping,
    ResolutionEvent,
    junit_mapping_sha256,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from tests.junit_audit_fixture import JUNIT_AUDIT_XML, junit_audit_state
from tests.reporting.test_junit_correction import (
    CASE1,
    CASE2,
    CASE3,
    IMPORT_ID,
    REASON,
    REVIEWER,
    correct,
    correction_state,
    mappings,
    moved,
)


def _comparison_payload():
    previous = correction_state()
    current = moved(previous)
    return compare_reviews(previous.bundle, current.bundle).model_dump(mode="json")


def _two_import_histories(rounds=1):
    original = correction_state()
    second = build_junit_evidence_import(
        original,
        JUNIT_AUDIT_XML.replace(b"audit suite", b"second suite"),
        [JUnitMappingSelection(scope_id=CASE1, criterion_id="AC-01")],
        importer="CONSTRUCTED second actor",
        import_id="constructed-second-import",
        imported_at=original.review.created_at,
    )
    original = append_junit_evidence_import(original, second)
    current = original
    for index in range(rounds):
        first_mapping = (
            mappings(("AC-02", [CASE2, CASE3]), ("AC-03", [CASE1]))
            if index % 2 == 0
            else original.bundle.junit_evidence_imports[0].criterion_mappings
        )
        current = correct(current, first_mapping)
        second_mapping = (
            mappings(("AC-02", [CASE1, CASE2])) if index % 2 == 0 else second.criterion_mappings
        )
        current = correct_junit_mappings(
            current,
            import_id=second.import_id,
            criterion_mappings=second_mapping,
            reviewer="CONSTRUCTED second actor",
            reason="CONSTRUCTED second mapping correction",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(current),
            confirm_whole_import=True,
        )
    return original, current


def test_changed_mapping_and_audit_are_both_projected_without_rewriting_originals():
    previous = correction_state()
    current = moved(previous)
    before = current.model_dump(mode="json")
    comparison = compare_reviews(previous.bundle, current.bundle)
    payload = json.loads(export_comparison_json(comparison))
    change = payload["junit_import_changes"][0]
    assert change["kind"] == "mapping_and_context_modified"
    left, right = change["previous"], change["current"]
    original = [
        item.model_dump(mode="json")
        for item in previous.bundle.junit_evidence_imports[0].criterion_mappings
    ]
    assert left["mappings"] == right["original_mappings"] == original
    assert left["mapping_correction_events"] == []
    assert (
        right["mappings"]
        == current.bundle.model_dump(mode="json")["effective_junit_mappings"][IMPORT_ID]
    )
    assert right["mapping_correction_events"] == [
        item.model_dump(mode="json") for item in current.bundle.junit_import_events
    ]
    assert right["retained_test_case_ids"] == [CASE1, CASE2, CASE3]
    assert right["confirmed_criterion_ids"] == ["AC-01", "AC-02", "AC-03"]
    assert left["context_sha256"] != right["context_sha256"]
    assert payload["previous_gate"] == payload["current_gate"]
    markdown = export_comparison_markdown(comparison)
    assert "original" in markdown.lower() and "effective" in markdown.lower()
    displayed = html.unescape(
        re.sub(r"\\([" + re.escape(string.punctuation) + r"])", r"\1", markdown)
    )
    assert current.bundle.junit_import_events[0].event_id in displayed
    assert REVIEWER in displayed and REASON in displayed
    for event in current.bundle.junit_import_events:
        for value in (
            event.previous_mapping_sha256,
            event.confirmed_criteria_sha256,
            event.criteria_source_provenance.source_text_sha256,
            event.criteria_source_provenance.source_uri,
            event.criteria_source_provenance.confirmed_by,
        ):
            assert value in displayed
    assert "<script>" not in markdown and "<img src=x" not in markdown
    assert "[actor](" not in markdown and "[details](" not in markdown
    assert current.model_dump(mode="json") == before


def test_cycle_back_to_original_is_context_modified_with_both_ordered_events():
    original = correction_state()
    first = moved(original)
    current = correct(first, original.bundle.junit_evidence_imports[0].criterion_mappings)
    comparison = compare_reviews(original.bundle, current.bundle)
    change = comparison.junit_import_changes[0]
    assert change.kind.value == "context_modified"
    assert change.previous.mappings == change.current.mappings
    assert len(change.current.mapping_correction_events) == 2
    assert change.current.mapping_correction_events[1].previous_correction_event_id == (
        change.current.mapping_correction_events[0].event_id
    )
    assert change.current.context_sha256 != change.previous.context_sha256
    assert compare_reviews(current.bundle, current.bundle).junit_import_changes[0].kind.value == (
        "unchanged"
    )


def test_removed_intermediate_group_requires_decision_review_without_changing_any_decision():
    original = correction_state()
    for criterion in ("AC-01", "AC-02", "AC-03"):
        original = append_resolution(
            original,
            ResolutionEvent(
                criterion_id=criterion,
                decision=HumanDecision.ACCEPTED,
                reviewer="CONSTRUCTED decision actor",
                comment="CONSTRUCTED recorded decision",
            ),
        )
    first = moved(original)
    current = correct(first, original.bundle.junit_evidence_imports[0].criterion_mappings)
    comparison = compare_reviews(original.bundle, current.bundle)
    assert comparison.criteria_requiring_decision_review == ["AC-01", "AC-02", "AC-03"]
    assert comparison.changed_human_resolutions == []
    assert current.bundle.resolutions == original.bundle.resolutions
    assert current.resolution_events == original.resolution_events
    assert current.bundle.gate == original.bundle.gate
    assert current.review.final_acceptance == original.review.final_acceptance


def test_uncorrected_import_context_hash_is_compatible_with_old_standalone_reference():
    state = junit_audit_state()
    legacy = JUnitImportReference.from_import(state.bundle.junit_evidence_imports[0])
    compared = compare_reviews(state.bundle, state.bundle).junit_import_changes[0].current
    assert legacy.context_sha256 == compared.context_sha256
    assert legacy.context_sha256 == (
        "3a3f316e7bcebe7ce6e8ede90290d2f2f728362587c37e1a61dc4d45df79ff15"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("import_id", "constructed-foreign-import"),
        ("artifact_sha256", "c" * 64),
        ("head_sha", "b" * 40),
        ("review_id", "constructed-foreign-review"),
        ("repository", "foreign/repository"),
        ("pr_number", 99),
        ("criteria_revision_number", 2),
        ("confirmed_criteria_sha256", "d" * 64),
        ("previous_mapping_sha256", "e" * 64),
        ("previous_correction_event_id", "constructed-absent-event"),
    ],
)
def test_comparison_rejects_forged_correction_owner_or_previous_state(field, value):
    payload = _comparison_payload()
    payload["junit_import_changes"][0]["current"]["mapping_correction_events"][0][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_revision", "constructed-foreign-source"),
        ("source_text_sha256", "e" * 64),
        ("confirmed_by", "CONSTRUCTED foreign actor"),
    ],
)
def test_comparison_rejects_forged_complete_correction_provenance(field, value):
    payload = _comparison_payload()
    event = payload["junit_import_changes"][0]["current"]["mapping_correction_events"][0]
    event["criteria_source_provenance"][field] = value
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


@pytest.mark.parametrize(
    "alteration",
    [
        "unknown_effective_case",
        "unknown_original_case",
        "unknown_effective_criterion",
        "unknown_original_criterion",
        "event_case",
        "event_criterion",
        "mismatched_effective",
        "missing_original",
        "missing_case_catalog",
        "missing_criterion_catalog",
        "missing_owner",
        "duplicate_event",
        "reordered_events",
    ],
)
def test_comparison_rejects_inconsistent_original_current_and_replay_projections(alteration):
    original = correction_state()
    first = moved(original)
    current = correct(first, mappings(("AC-01", [CASE1]), ("AC-02", [CASE2, CASE3])))
    payload = compare_reviews(original.bundle, current.bundle).model_dump(mode="json")
    reference = payload["junit_import_changes"][0]["current"]
    if alteration == "unknown_effective_case":
        reference["mappings"][0]["test_case_ids"] = ["suite-9999-case-9999"]
    elif alteration == "unknown_original_case":
        reference["original_mappings"][0]["test_case_ids"] = ["suite-9999-case-9999"]
    elif alteration == "unknown_effective_criterion":
        reference["mappings"][0]["criterion_id"] = "AC-UNKNOWN"
    elif alteration == "unknown_original_criterion":
        reference["original_mappings"][0]["criterion_id"] = "AC-UNKNOWN"
    elif alteration == "event_case":
        reference["mapping_correction_events"][0]["criterion_mappings"][0]["test_case_ids"] = [
            "suite-9999-case-9999"
        ]
    elif alteration == "event_criterion":
        reference["mapping_correction_events"][0]["criterion_mappings"][0]["criterion_id"] = (
            "AC-UNKNOWN"
        )
    elif alteration == "mismatched_effective":
        reference["mappings"] = copy.deepcopy(reference["original_mappings"])
    elif alteration.startswith("missing_"):
        field = {
            "missing_original": "original_mappings",
            "missing_case_catalog": "retained_test_case_ids",
            "missing_criterion_catalog": "confirmed_criterion_ids",
        }.get(alteration)
        if field:
            reference.pop(field)
        else:
            payload.pop("decision_context_comparison")
    elif alteration == "duplicate_event":
        reference["mapping_correction_events"].append(
            copy.deepcopy(reference["mapping_correction_events"][0]),
        )
    else:
        reference["mapping_correction_events"].reverse()
    if alteration != "missing_owner":
        with pytest.raises(ValidationError):
            JUnitImportReference.model_validate(reference)
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


def test_comparison_export_revalidates_mutable_nested_correction_attribution():
    original = correction_state()
    current = moved(original)
    comparison = compare_reviews(original.bundle, current.bundle)
    event = comparison.junit_import_changes[0].current.mapping_correction_events[0]
    assert event.reviewer == REVIEWER and event.reason == REASON
    comparison.junit_import_changes[0].current.mapping_correction_events[0] = event.model_copy(
        update={"review_id": "constructed-foreign-review"},
    )
    for exporter in (export_comparison_json, export_comparison_markdown):
        with pytest.raises(ValueError):
            exporter(comparison)


@pytest.mark.parametrize("map_to_forged_criterion", [False, True])
def test_correction_criterion_catalog_must_match_full_owning_confirmed_criteria(
    map_to_forged_criterion,
):
    payload = _comparison_payload()
    reference = payload["junit_import_changes"][0]["current"]
    reference["confirmed_criterion_ids"].append("AC-UNKNOWN")
    if map_to_forged_criterion:
        # A self-consistent forged catalog/snapshot must still fail the authoritative owner.
        for group in reference["mappings"]:
            if group["criterion_id"] == "AC-03":
                group["criterion_id"] = "AC-UNKNOWN"
        for group in reference["mapping_correction_events"][0]["criterion_mappings"]:
            if group["criterion_id"] == "AC-03":
                group["criterion_id"] = "AC-UNKNOWN"
    assert payload["decision_context_comparison"]["current"]["criterion_ids"] == [
        "AC-01",
        "AC-02",
        "AC-03",
    ]
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


@pytest.mark.parametrize("side", ["previous", "current"])
def test_comparison_rejects_duplicate_audit_ids_across_imports_on_one_side(side):
    _original, state = _two_import_histories()
    payload = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    references = [item[side] for item in payload["junit_import_changes"]]
    references[1]["mapping_correction_events"][0]["event_id"] = references[0][
        "mapping_correction_events"
    ][0]["event_id"]
    # Each import is internally valid; the duplicate exists only across this owning side.
    for reference in references:
        JUnitImportReference.model_validate(reference)
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)


def test_identical_audit_ids_on_both_sides_are_valid_shared_history():
    _original, state = _two_import_histories()
    payload = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    validated = ReviewComparison.model_validate(payload)
    assert len(validated.junit_import_changes) == 2
    for change in validated.junit_import_changes:
        assert change.kind.value == "unchanged"
        assert change.previous.mapping_correction_events == change.current.mapping_correction_events


@pytest.mark.parametrize("side", ["previous", "current"])
def test_comparison_bounds_total_corrections_across_imports_per_owning_side(side):
    original, state = _two_import_histories(rounds=10)
    payload = compare_reviews(original.bundle, state.bundle).model_dump(mode="json")
    if side == "previous":
        # Both sides are valid before adding one event to the selected owning side.
        payload = compare_reviews(state.bundle, state.bundle).model_dump(mode="json")
    reference = next(
        item[side]
        for item in payload["junit_import_changes"]
        if item[side]["import_id"] == IMPORT_ID
    )
    extra = copy.deepcopy(reference["mapping_correction_events"][-1])
    extra["event_id"] = str(uuid4())
    extra["previous_correction_event_id"] = reference["mapping_correction_events"][-1]["event_id"]
    extra["previous_mapping_sha256"] = junit_mapping_sha256(
        [JUnitCriterionMapping.model_validate(group) for group in reference["mappings"]]
    )
    extra["criterion_mappings"] = [
        group.model_dump(mode="json")
        for group in mappings(
            ("AC-02", [CASE2, CASE3]),
            ("AC-03", [CASE1]),
        )
    ]
    reference["mapping_correction_events"].append(extra)
    reference["mappings"] = copy.deepcopy(extra["criterion_mappings"])
    # Keep classification consistent so the rejected condition is the global history bound.
    change = next(
        item for item in payload["junit_import_changes"] if item[side]["import_id"] == IMPORT_ID
    )
    change["kind"] = "mapping_and_context_modified" if side == "current" else "mapping_modified"
    assert (
        sum(
            len(item[side]["mapping_correction_events"]) for item in payload["junit_import_changes"]
        )
        == 21
    )
    JUnitImportReference.model_validate(reference)
    with pytest.raises(ValidationError):
        ReviewComparison.model_validate(payload)
