"""Independent recipient-facing audit safety checks using public exporters only."""

from datetime import datetime
from html.parser import HTMLParser

import pytest

from scopeproof_core.criteria.confirmation import build_criteria_source_provenance
from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.reporting.exporters import (
    export_csv,
    export_html,
    export_json,
    export_markdown,
)
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    attach_analysis,
    confirm_criteria,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    GateVerdict,
    HumanDecision,
    HumanResolution,
    ResolutionEvent,
)


class _ReadableText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _history(report: str) -> str:
    if report.startswith("<!DOCTYPE") or "<html" in report:
        marker = "<h2>Resolution History</h2>"
        assert marker in report, "HTML handoff must include the resolution audit"
        return report.split(marker, 1)[1].split("<h2>", 1)[0]
    marker = "## Resolution History\n"
    assert marker in report, "Markdown handoff must include the resolution audit"
    return report.split(marker, 1)[1].split("\n## ", 1)[0]


def _text(report: str) -> str:
    parser = _ReadableText()
    parser.feed(_history(report))
    # Markdown uses backslash escapes; inspecting readable text must undo those.
    return " ".join(" ".join(parser.parts).replace("\\", "").split())


def _state_with_event(**changes):
    event = ResolutionEvent(
        event_id="independent-safety-event",
        criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED,
        reviewer="Safety reviewer",
        comment="Independent recorded reason",
        timestamp=datetime.fromisoformat("2025-03-02T01:02:03+05:45"),
        **changes,
    )
    return append_resolution(new_review_state(build_demo_review()), event)


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_history_preserves_recorded_metadata_and_offset_without_utc_inference(exporter):
    state = _state_with_event(evidence_url="https://audit.example/explicit?x=1&y=2")

    text = _text(exporter(state))

    for value in (
        "independent-safety-event", "Current", "Criteria revision", "1", "AC-01",
        "change_required", "Safety reviewer", "Independent recorded reason",
        "2025-03-02T01:02:03+05:45", "https://audit.example/explicit?x=1&y=2",
        "Not recorded",
    ):
        assert value in text
    assert "2025-03-01T19:17:03+00:00" not in text


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_history_preserves_naive_legacy_time_with_explicit_uncertainty(exporter):
    state = new_review_state(build_demo_review())
    state = append_resolution(state, ResolutionEvent(
        event_id="naive-recorded-time", final_acceptance=False,
        timestamp=datetime(2024, 2, 3, 4, 5, 6), reviewer="Legacy actor",
    ))

    text = _text(exporter(state))

    assert "2024-02-03T04:05:06" in text
    assert "timezone not recorded" in text.lower()
    assert "2024-02-03T04:05:06+00:00" not in text


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_history_distinguishes_empty_optional_url_from_absence(exporter):
    absent = _text(exporter(_state_with_event(evidence_url=None)))
    empty = _text(exporter(_state_with_event(evidence_url="")))

    assert "Empty value recorded" not in absent
    assert "Empty value recorded" in empty
    assert "Evidence URL" in empty
    assert "Not recorded" in absent


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_history_fields_and_urls_remain_inert_hostile_recorded_text(exporter):
    hostile = '<script>alert("audit")</script><img src=x onerror=alert(1)>'
    malicious_url = 'javascript:alert(1)"><a href="https://audit.invalid">bad</a>'
    state = new_review_state(build_demo_review())
    state = append_resolution(state, ResolutionEvent(
        event_id="hostile-audit-id-" + hostile, final_acceptance=False,
        reviewer=hostile, comment='[click](https://audit.invalid) ' + hostile,
        evidence_url=malicious_url,
    ))

    history = _history(exporter(state))
    text = _text(exporter(state))

    assert hostile in text
    assert malicious_url in text
    assert "<script>" not in history
    assert "<img " not in history
    assert "<a " not in history
    if exporter is export_markdown:
        assert '[click](https://audit.invalid)' not in history


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_explicit_false_is_recorded_value_without_invented_revocation(exporter):
    state = append_resolution(new_review_state(build_demo_review()), ResolutionEvent(
        event_id="initial-false-flag", final_acceptance=False,
        reviewer="Flag recorder", comment="Only a recorded false flag",
    ))

    text = _text(exporter(state))

    assert "final_acceptance=false" in text
    assert "initial-false-flag" in text
    assert "revoked" not in text.lower()
    assert "never accepted" not in text.lower()


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_empty_full_history_differs_from_unavailable_bundle_history(exporter):
    state = new_review_state(build_demo_review())
    assert state.bundle is not None

    empty = _text(exporter(state)).lower()
    unavailable = _text(exporter(state.bundle)).lower()

    assert "no resolution events" in empty
    assert "unavailable" not in empty
    assert "unavailable" in unavailable
    assert "no resolution events" not in unavailable


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_history_authority_follows_append_order_and_revision_instead_of_time(exporter):
    state = append_resolution(new_review_state(build_demo_review()), ResolutionEvent(
        event_id="prior-revision-safety-input", criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED, reviewer="Prior reviewer",
        timestamp=datetime.fromisoformat("2035-01-01T00:00:00+00:00"),
    ))
    state = revise_criteria(state, state.criteria_revision.criteria, "Explicit revision two")
    state = confirm_criteria(state, build_criteria_source_provenance(
        source_uri="https://audit.example/revision-two", source_revision="2",
        source_text=state.criteria_revision.source_text, criteria=state.criteria_revision.criteria,
        confirmed_by="Requirements recorder", confirmed_at=state.criteria_revision.created_at,
    ))
    incoming = build_demo_review()
    incoming.review = state.review.model_copy(deep=True)
    incoming.source_text = state.criteria_revision.source_text
    incoming.criteria = [item.model_copy(deep=True) for item in state.criteria_revision.criteria]
    state = attach_analysis(state, incoming)
    for event_id, timestamp in (
        ("superseded-safety-input", "2030-01-01T00:00:00+00:00"),
        ("current-safety-input", "2020-01-01T00:00:00+00:00"),
    ):
        state = append_resolution(state, ResolutionEvent(
            event_id=event_id, criterion_id="AC-01", decision=HumanDecision.CHANGE_REQUIRED,
            timestamp=datetime.fromisoformat(timestamp), reviewer="Revision two recorder",
        ))

    text = _text(exporter(state))

    first = text.index("prior-revision-safety-input")
    second = text.index("superseded-safety-input")
    third = text.index("current-safety-input")
    assert first < second < third
    assert "Prior revision" in text[first:second]
    assert "Superseded" in text[second:third]
    assert "Current" in text[third:]


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
def test_legacy_manual_claim_retains_unlinked_uncertainty_in_history(exporter):
    state = new_review_state(build_demo_review())
    assert state.bundle is not None
    event = ResolutionEvent(
        event_id="legacy-unlinked-audit-event", criterion_id="AC-01",
        decision=HumanDecision.MANUALLY_VERIFIED, reviewer="Legacy claimant",
        comment="Recorded legacy observation", claimed_evidence_level=EvidenceLevel.E3,
        criteria_revision_number=1,
    )
    state.resolution_events = [event]
    state.bundle.resolutions = [HumanResolution(
        criterion_id="AC-01", decision=HumanDecision.MANUALLY_VERIFIED,
        reviewer=event.reviewer, comment=event.comment,
        claimed_evidence_level=EvidenceLevel.E3, timestamp=event.timestamp,
    )]
    state.bundle.gate = evaluate_gate(
        state.bundle.review, state.bundle.criteria, state.bundle.findings,
        state.bundle.resolutions, state.bundle.evidence, state.bundle.file_scope_decisions,
    )
    # Only AC-01 has a legacy claim; the untouched demo's AC-02/03 still block.
    original_gate = state.bundle.gate.model_dump(mode="json")
    assert state.bundle.gate.verdict is GateVerdict.BLOCKED
    assert state.bundle.gate.blocking_criteria == ["AC-02", "AC-03"]
    assert "runtime_verification_reconfirmation_required" in state.bundle.gate.reason_codes

    text = _text(exporter(state))

    assert "legacy-unlinked-audit-event" in text
    assert "E3" in text
    assert "Legacy unlinked; re-record at the active head" in text
    assert state.bundle.gate.model_dump(mode="json") == original_gate


@pytest.mark.parametrize("exporter", [export_markdown, export_html])
@pytest.mark.parametrize("forgery", ["gate", "event"])
def test_readable_history_does_not_bypass_existing_state_validation(exporter, forgery):
    state = _state_with_event()
    assert state.bundle is not None
    if forgery == "gate":
        state.bundle.gate = state.bundle.gate.model_copy(update={"verdict": GateVerdict.READY})
    else:
        state.resolution_events[0] = state.resolution_events[0].model_copy(
            update={"reviewer": "Forged actor without matching effective resolution"}
        )

    with pytest.raises(ValueError):
        exporter(state)


def test_readable_audit_does_not_rewrite_state_or_machine_reports():
    state = _state_with_event(evidence_url="https://audit.example/original")
    original_state = state.model_dump_json()
    original_json = export_json(state)
    original_csv = export_csv(state)

    for exporter in (export_markdown, export_html, export_html, export_markdown):
        assert "independent-safety-event" in _text(exporter(state))

    assert state.model_dump_json() == original_state
    assert export_json(state) == original_json
    assert export_csv(state) == original_csv
