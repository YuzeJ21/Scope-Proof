import pytest

from scopeproof_core.demo import build_demo_review
from scopeproof_core.reporting.exporters import export_csv, export_json, export_markdown
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import GateVerdict, HumanDecision, ResolutionEvent


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
