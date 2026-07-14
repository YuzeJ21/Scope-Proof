import json
from pathlib import Path

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
from scopeproof_core.storage.json_store import JsonReviewStore


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
    return attach_analysis(revised, analysis_for(revised))


def analysis_for(state):
    incoming = build_demo_review()
    incoming.review = incoming.review.model_copy(
        update={
            "repository": state.review.repository,
            "pr_number": state.review.pr_number,
            "base_sha": state.review.base_sha,
            "head_sha": state.review.head_sha,
            "check_state": state.review.check_state,
            "criteria_confirmed": True,
            "ingestion_state": state.review.ingestion_state,
            "ingestion_warnings": state.review.ingestion_warnings,
            "skipped_files": state.review.skipped_files,
            "tool_version": state.review.tool_version,
            "ruleset_version": state.review.ruleset_version,
        }
    )
    incoming.source_text = state.criteria_revision.source_text
    incoming.criteria = [
        item.model_copy(deep=True) for item in state.criteria_revision.criteria
    ]
    return incoming


def state_with_skipped_analysis_revision():
    revision_one = new_review_state(build_demo_review())
    revision_two = confirm_criteria(
        revise_criteria(
            revision_one,
            revision_one.criteria_revision.criteria,
            "Confirmed revision two without analysis",
        )
    )
    revision_three = confirm_criteria(
        revise_criteria(
            revision_two,
            revision_two.criteria_revision.criteria,
            "Confirmed revision three",
        )
    )
    analyzed_revision_three = attach_analysis(
        revision_three,
        analysis_for(revision_three),
    )
    revision_four = confirm_criteria(
        revise_criteria(
            analyzed_revision_three,
            analyzed_revision_three.criteria_revision.criteria,
            "Confirmed revision four",
        )
    )
    return attach_analysis(revision_four, analysis_for(revision_four))


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


def test_lifecycle_json_exposes_active_and_skipped_known_revision_lineage() -> None:
    state = state_with_skipped_analysis_revision()

    payload = json.loads(export_json(state))

    assert payload == state.model_dump(mode="json")
    assert payload["bundle"]["criteria_revision_number"] == 4
    assert [
        bundle["criteria_revision_number"] for bundle in payload["analysis_history"]
    ] == [1, 3]


def test_lifecycle_json_preserves_migrated_unknown_revision_lineage(
    tmp_path: Path,
) -> None:
    store = JsonReviewStore(tmp_path)
    state = attached_review_state()
    path = store.save(state)
    legacy_record = json.loads(path.read_text(encoding="utf-8"))
    legacy_record["record_version"] = 1
    legacy_record["state"]["bundle"].pop("criteria_revision_number")
    for historical_bundle in legacy_record["state"]["analysis_history"]:
        historical_bundle.pop("criteria_revision_number")
    path.write_text(json.dumps(legacy_record), encoding="utf-8")

    migrated = store.load(state.review.review_id)
    payload = json.loads(export_json(migrated))

    assert payload == migrated.model_dump(mode="json")
    assert payload["bundle"]["criteria_revision_number"] == 2
    assert [
        bundle["criteria_revision_number"] for bundle in payload["analysis_history"]
    ] == ["unknown"]


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
