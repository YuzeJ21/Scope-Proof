"""CONSTRUCTED explicit mappings, never runtime or practitioner evidence."""

from importlib import import_module

import pytest

from scopeproof_core.importers.junit import JUnitMappingSelection
from scopeproof_core.reviews.lifecycle import append_junit_evidence_import, append_resolution
from scopeproof_core.schemas.models import HumanDecision, ResolutionEvent
from tests.importers.test_junit import exact_head_state

XML = (
    b'<testsuites><testsuite name="one"><testcase name="first"/></testsuite>'
    b'<testsuite name="two"><testcase name="second"><failure>DISCARD ME</failure>'
    b'</testcase></testsuite></testsuites>'
)


def api():
    return import_module("scopeproof_core.importers.junit_draft")


def choice(scope, criterion):
    return JUnitMappingSelection(scope_id=scope, criterion_id=criterion)


def test_one_artifact_can_explicitly_map_two_distinct_suites_then_import_once():
    module = api()
    state = exact_head_state()
    before = state.model_dump_json()
    draft = module.new_junit_mapping_draft(state, XML)
    assert draft.selections == ()
    for scope, criterion in [("suite-0001", "AC-01"), ("suite-0002", "AC-02")]:
        draft = module.extend_junit_mapping_draft(
            state, XML, draft, [choice(scope, criterion)], importer="CONSTRUCTED draft actor",
        )
    imported = module.build_drafted_junit_import(
        state, XML, draft, importer="CONSTRUCTED draft actor",
    )
    assert [(m.criterion_id, m.test_case_ids) for m in imported.criterion_mappings] == [
        ("AC-01", ["suite-0001-case-0001"]), ("AC-02", ["suite-0002-case-0001"]),
    ]
    assert "DISCARD ME" not in imported.model_dump_json()
    assert state.model_dump_json() == before
    saved = append_junit_evidence_import(state, imported)
    assert len(saved.bundle.junit_evidence_imports) == 1
    assert saved.bundle.gate == state.bundle.gate
    assert saved.bundle.runtime_evidence == state.bundle.runtime_evidence
    assert saved.resolution_events == state.resolution_events


def test_overlapping_addition_is_transactional_and_does_not_retire_valid_draft():
    module = api()
    state = exact_head_state()
    draft = module.extend_junit_mapping_draft(
        state, XML, module.new_junit_mapping_draft(state, XML),
        [choice("suite-0001", "AC-01")], importer="CONSTRUCTED actor",
    )
    before = draft.model_dump_json(), state.model_dump_json()
    with pytest.raises(ValueError):
        module.extend_junit_mapping_draft(
            state, XML, draft, [choice("suite-0001-case-0001", "AC-02")],
            importer="CONSTRUCTED actor",
        )
    assert (draft.model_dump_json(), state.model_dump_json()) == before


def test_same_target_union_is_canonical_and_group_removal_only_removes_that_target():
    module = api()
    state = exact_head_state()
    draft = module.extend_junit_mapping_draft(
        state, XML, module.new_junit_mapping_draft(state, XML), [
            choice("suite-0002", "AC-02"), choice("suite-0001-case-0001", "AC-01"),
            choice("suite-0001", "AC-01"), choice("suite-0001", "AC-01"),
        ], importer="CONSTRUCTED actor",
    )
    assert len(draft.selections) == 3
    revised = module.remove_junit_mapping_criterion(state, XML, draft, "AC-01")
    assert [(item.criterion_id, item.scope_id) for item in revised.selections] == [
        ("AC-02", "suite-0002"),
    ]
    assert len(draft.selections) == 3
    revised = module.remove_junit_mapping_criterion(state, XML, revised, "AC-02")
    assert revised.selections == ()
    with pytest.raises(ValueError):
        module.build_drafted_junit_import(state, XML, revised, importer="CONSTRUCTED actor")


def test_draft_rejects_replacement_bytes_even_when_scope_ids_are_identical():
    module = api()
    state = exact_head_state()
    draft = module.new_junit_mapping_draft(state, XML)
    with pytest.raises(ValueError):
        module.extend_junit_mapping_draft(
            state, XML + b" ", draft, [choice("suite-0001", "AC-01")],
            importer="CONSTRUCTED actor",
        )


def test_criterion_decision_only_change_expires_the_entire_draft():
    module = api()
    state = exact_head_state()
    draft = module.new_junit_mapping_draft(state, XML)
    changed = append_resolution(state, ResolutionEvent(
        criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
        comment="CONSTRUCTED changed saved decision", reviewer="CONSTRUCTED actor",
    ))
    with pytest.raises(ValueError):
        module.extend_junit_mapping_draft(
            changed, XML, draft, [choice("suite-0001", "AC-01")], importer="CONSTRUCTED actor",
        )


def test_revalidated_typed_draft_cannot_smuggle_malformed_selector():
    module = api()
    state = exact_head_state()
    draft = module.new_junit_mapping_draft(state, XML)
    forged = draft.model_copy(update={"selections": (
        choice("suite-0001", "AC-01").model_copy(update={"scope_id": "not-a-scope"}),
    )})
    with pytest.raises(ValueError):
        module.JUnitMappingDraft.model_validate(forged)
    with pytest.raises(ValueError):
        module.build_drafted_junit_import(state, XML, forged, importer="CONSTRUCTED actor")
