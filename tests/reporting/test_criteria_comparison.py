"""Requirements-only exports retain explicit missing provenance and inert text."""

import json
from importlib import import_module

import pytest

from tests.reviews.test_criteria_comparison import report_for


def test_json_contains_only_validated_requirements_context(tmp_path):
    _, _, _, _, report = report_for(tmp_path)
    exporter = import_module("scopeproof_core.reporting.criteria_comparison")
    text = exporter.export_criteria_comparison_json(report)
    data = json.loads(text)
    assert data["report_kind"] == "scopeproof_criteria_revision_comparison"
    assert data["current"]["confirmed"] is False
    assert data["current"]["source_provenance"] is None
    assert data["previous"]["revision_number"] == 1
    assert "gate" not in data and "evidence" not in data and "resolutions" not in data
    assert text == exporter.export_criteria_comparison_json(report)


def test_markdown_preserves_unknown_history_and_complete_escaped_values(tmp_path):
    from tests.reviews.test_historical_analysis import history_only_state

    state = history_only_state()
    state.analysis_history[0].criteria_revision_number = "unknown"
    state.analysis_history[0].file_scope_decisions = []
    state.analysis_history[0].review.criteria_source_provenance = None
    from scopeproof_core.gates.evaluator import evaluate_gate
    old = state.analysis_history[0]
    old.gate = evaluate_gate(old.review, old.criteria, old.findings, old.resolutions, old.evidence)
    state.criteria_revision.source_text = "<img src=x onerror=bad> **CONSTRUCTED**\nsource|`value`"
    _, _, _, _, report = report_for(tmp_path, state)
    exporter = import_module("scopeproof_core.reporting.criteria_comparison")
    text = exporter.export_criteria_comparison_markdown(report)
    assert "# ScopeProof Criteria Revision Changes" in text
    assert "unknown" in text and "Not recorded" in text
    assert "Unconfirmed" in text
    assert "not semantic equivalence" in text
    assert "<img src=" not in text and "&lt;img" in text
    for field in ("priority", "criterion_type", "criterion_source", "source_span",
                  "required_evidence_level"):
        assert field in text
    assert state.review.head_sha in text


@pytest.mark.parametrize("format", ["json", "markdown"])
def test_export_revalidates_tampered_requirements(tmp_path, format):
    _, _, _, _, report = report_for(tmp_path)
    report.current.criteria[0].text = "Tampered later input"
    exporter = import_module("scopeproof_core.reporting.criteria_comparison")
    with pytest.raises(ValueError):
        getattr(exporter, f"export_criteria_comparison_{format}")(report)
