"""Trusted CONSTRUCTED history-only recipe, runnable against an installed wheel.

Only product-core imports are intentional: the browser journey copies this file
outside the checkout and evaluates it with the isolated installed interpreter.
No actor, observation or public-PR-shaped metadata represents actual user testing.
"""

from datetime import UTC, datetime

from scopeproof_core.demo import build_review
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    new_review_state,
    revise_criteria,
)
from scopeproof_core.reviews.selected_references import (
    append_reviewer_selected_reference,
    selectable_reference_lines,
)
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CIObservation,
    CIReasonCode,
    Criterion,
    EvidenceLevel,
    HumanDecision,
    LineChangeType,
    PullRequestSnapshot,
    RepositoryVisibility,
    ResolutionEvent,
    ReviewState,
    RuntimeEvidence,
)
from scopeproof_core.storage.json_store import JsonReviewStore

HISTORICAL_REVIEW_ID = "constructed-history-only-review"
HISTORICAL_HEAD = "f" * 40
HISTORICAL_PRODUCER_VERSION = "0.2.4-constructed-historical-producer"
HISTORICAL_UNTRUSTED_TEXT = (
    "<img src=x onerror=bad> **CONSTRUCTED inert historical result**"
)
PENDING_CRITERIA_TEXT = "CONSTRUCTED changed requirement: export JSON instead of CSV"


def historical_analysis_state() -> ReviewState:
    """Retain revision 1; skip analysis at revision 2; leave revision 3 unconfirmed."""
    timestamp = datetime(2026, 10, 31, 12, tzinfo=UTC)
    snapshot = PullRequestSnapshot(
        repository="acme/constructed-history", pr_number=17,
        repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        title="CONSTRUCTED historical inspection fixture",
        description="CONSTRUCTED offline test input; no observed public pull request.",
        html_url="https://github.com/acme/constructed-history/pull/17",
        base_sha="d" * 40, head_sha=HISTORICAL_HEAD,
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="CONSTRUCTED successful check metadata; no executed target code.",
            reason_code=CIReasonCode.SUCCESSFUL_CHECK_RUNS,
            total_check_runs=1, successful_check_runs=1,
        ),
        fetched_at=timestamp,
        files=[ChangedFile(
            path="src/export.py", status="modified",
            lines=[ChangedLine(
                change_type=LineChangeType.ADDED, line_number=1,
                content="def export_csv(rows): return rows",
            )],
        )],
    )
    criterion = Criterion(
        criterion_id="AC-01", text="CONSTRUCTED export CSV",
        required_evidence_level=EvidenceLevel.E2,
    )
    bundle = build_review(snapshot, {
        "fixture": "constructed-historical-inspection-v1",
        "deliberately_constructed_demo": True,
        "source_text": criterion.text,
        "criteria": [criterion.model_dump(mode="json")],
        "criteria_confirmed": True, "resolutions": [],
    })
    bundle.review.review_id = HISTORICAL_REVIEW_ID
    bundle.review.tool_version = HISTORICAL_PRODUCER_VERSION
    state = new_review_state(bundle)
    selected = next(iter(selectable_reference_lines(state, snapshot)))
    state = append_reviewer_selected_reference(
        state, snapshot=snapshot, selected=selected, criterion_id="AC-01",
        reviewer="CONSTRUCTED historical automatic reference actor",
        rationale="CONSTRUCTED retained static context; not execution evidence.",
        expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
    )
    runtime_id = "constructed-historical-runtime-" + "traceability" * 90
    actor = "CONSTRUCTED historical automatic decision actor"
    artifact = "https://example.test/constructed/history/runtime-report"
    state = append_external_verification(
        state,
        RuntimeEvidence(
            runtime_evidence_id=runtime_id,
            repository=snapshot.repository, pr_number=snapshot.pr_number,
            head_sha=HISTORICAL_HEAD, criterion_id="AC-01",
            artifact_reference=artifact,
            scenario="CONSTRUCTED historical CSV observation", timestamp=timestamp,
            environment="CONSTRUCTED automatic test environment",
            result="CONSTRUCTED stored result; no target execution. "
            + HISTORICAL_UNTRUSTED_TEXT,
            reviewer=actor, evidence_level=EvidenceLevel.E3,
            limitations=[
                "CONSTRUCTED fixture observation; not independent verification.",
                "Automatic fixture actors are not qualifying practitioners.",
            ],
        ),
        ResolutionEvent(
            event_id="constructed-historical-manual-decision", criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment="CONSTRUCTED historical rationale; not customer evidence.",
            evidence_url=artifact, claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime_id, reviewer=actor, timestamp=timestamp,
        ),
    )
    state = revise_criteria(state, [Criterion(
        criterion_id="AC-01", text="CONSTRUCTED skipped intermediate requirement",
        required_evidence_level=EvidenceLevel.E2,
    )], "CONSTRUCTED revision 2 was never analyzed")
    state = revise_criteria(state, [Criterion(
        criterion_id="AC-02", text=PENDING_CRITERIA_TEXT,
        required_evidence_level=EvidenceLevel.E2,
    )], PENDING_CRITERIA_TEXT)
    return ReviewState.model_validate(state.model_dump(mode="python"))
