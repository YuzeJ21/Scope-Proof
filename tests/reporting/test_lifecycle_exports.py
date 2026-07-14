import json

import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
)


def state_with_history():
    state = new_review_state(build_demo_review())
    return append_resolution(
        state,
        ResolutionEvent(
            event_id="history-1",
            criterion_id="AC-01",
            decision=HumanDecision.ACCEPTED,
            comment="Reviewed implementation candidate",
        ),
    )


def attached_review_state():
    state = new_review_state(build_demo_review())
    updated_criteria = [
        item.model_copy(deep=True) for item in state.criteria_revision.criteria
    ]
    updated_criteria[0] = updated_criteria[0].model_copy(
        update={"text": "Updated AC-01 requirement"}
    )
    revised = confirm_criteria(
        revise_criteria(
            state,
            updated_criteria,
            "Updated requirements",
        )
    )
    incoming = build_demo_review()
    incoming.review = incoming.review.model_copy(
        update={
            "repository": revised.review.repository,
            "pr_number": revised.review.pr_number,
            "base_sha": revised.review.base_sha,
            "head_sha": revised.review.head_sha,
            "check_state": revised.review.check_state,
            "criteria_confirmed": True,
            "ingestion_state": revised.review.ingestion_state,
            "ingestion_warnings": revised.review.ingestion_warnings,
            "skipped_files": revised.review.skipped_files,
            "tool_version": revised.review.tool_version,
            "ruleset_version": revised.review.ruleset_version,
        }
    )
    incoming.source_text = revised.criteria_revision.source_text
    incoming.criteria = [
        item.model_copy(deep=True) for item in revised.criteria_revision.criteria
    ]
    return attach_analysis(revised, incoming)


def test_lifecycle_markdown_exposes_revision_and_resolution_history() -> None:
    markdown = export_markdown(state_with_history())

    assert "Criteria revision: 1" in markdown
    assert "Resolution History" in markdown
    assert "Reviewed implementation candidate" in markdown


def test_lifecycle_json_and_csv_preserve_review_state_without_secret() -> None:
    state = state_with_history()
    json_text = export_json(state)
    csv_text = export_csv(state)

    assert '"criteria_revision"' in json_text
    assert '"resolution_events"' in json_text
    assert "AC-01" in csv_text
    assert "ghp_" not in json_text


def test_lifecycle_json_preserves_attached_reanalysis_lineage() -> None:
    attached = attached_review_state()
    original = build_demo_review()
    stable_review_id = attached.review.review_id

    payload = json.loads(export_json(attached))

    assert payload == attached.model_dump(mode="json")
    assert payload["criteria_revision"]["number"] == 2
    assert len(payload["analysis_history"]) == 1
    assert payload["review"]["review_id"] == stable_review_id
    assert payload["bundle"]["review"]["review_id"] == stable_review_id
    assert payload["bundle"]["source_text"] == "Updated requirements"
    assert payload["bundle"]["criteria"] == payload["criteria_revision"]["criteria"]
    historical = payload["analysis_history"][0]
    assert historical["source_text"] == original.source_text
    assert historical["criteria"] == [
        item.model_dump(mode="json") for item in original.criteria
    ]
    assert historical["source_text"] != payload["bundle"]["source_text"]
    assert historical["criteria"] != payload["bundle"]["criteria"]


@pytest.mark.parametrize("exporter", [export_json, export_markdown])
def test_lifecycle_exports_reject_a_non_deterministic_active_gate(exporter) -> None:
    state = state_with_history()
    assert state.bundle is not None
    state.bundle.gate = state.bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        exporter(state)


@pytest.mark.parametrize("exporter", [export_json, export_markdown])
def test_bundle_exports_reject_a_non_deterministic_gate(exporter) -> None:
    state = state_with_history()
    assert state.bundle is not None
    state.bundle.gate = state.bundle.gate.model_copy(update={"verdict": GateVerdict.READY})

    with pytest.raises(
        ValueError, match="analysis bundle gate must match deterministic evaluation"
    ):
        exporter(state.bundle)


@pytest.mark.parametrize("exporter", [export_json, export_markdown])
def test_lifecycle_exports_reject_forged_ready_without_resolution_events(exporter) -> None:
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    state.review.final_acceptance = True
    state.bundle.review.final_acceptance = True
    state.bundle.resolutions = [
        HumanResolution(
            criterion_id=criterion.criterion_id,
            decision=HumanDecision.ACCEPTED,
            comment="Forged acceptance",
        )
        for criterion in state.bundle.criteria
    ]
    state.bundle.gate = evaluate_gate(
        state.bundle.review,
        state.bundle.criteria,
        state.bundle.findings,
        state.bundle.resolutions,
    )
    assert state.bundle.gate.verdict is GateVerdict.READY
    assert state.resolution_events == []

    with pytest.raises(
        ValueError, match="active bundle resolutions must match active resolution events"
    ):
        exporter(state)


def test_lifecycle_json_rejects_foreign_historical_review_lineage() -> None:
    state = new_review_state(build_demo_review())
    revised = revise_criteria(
        state,
        state.criteria_revision.criteria,
        "Updated requirements",
    )
    revised.analysis_history[0].review.review_id = "foreign-review"

    with pytest.raises(
        ValueError,
        match="historical bundle review lineage must match lifecycle review",
    ):
        export_json(revised)
