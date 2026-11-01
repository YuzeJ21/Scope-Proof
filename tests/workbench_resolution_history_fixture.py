"""Constructed mixed legacy audit, using product imports only for installed-wheel tests."""

from datetime import datetime

from scopeproof_core.demo import build_demo_review
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.lifecycle import append_resolution, new_review_state
from scopeproof_core.schemas.models import (
    EvidenceLevel,
    HumanDecision,
    ResolutionEvent,
    ReviewState,
)

WORKBENCH_HISTORY_REVIEW_ID = "constructed-workbench-mixed-history"
WORKBENCH_HISTORY_HOSTILE_REVIEWER = (
    'Constructed <script>window.__scopeproofHistoryExecuted=true</script> recorder'
)
WORKBENCH_HISTORY_HOSTILE_NOTE = (
    'Constructed [link](https://history.invalid/note) '
    '<img src="https://history.invalid/image" '
    'onerror="window.__scopeproofHistoryExecuted=true">'
)
WORKBENCH_HISTORY_HOSTILE_URL = (
    'javascript:window.__scopeproofHistoryExecuted=true;'
    '"><a href="https://history.invalid/url">recorded</a>'
)


def workbench_resolution_history_state() -> ReviewState:
    """Retain supported loaded shapes without simulating new manual-entry transitions."""
    bundle = build_demo_review()
    bundle.review.review_id = WORKBENCH_HISTORY_REVIEW_ID
    state = append_resolution(new_review_state(bundle), ResolutionEvent(
        event_id="workbench-final-accepted-extra", final_acceptance=False,
        decision=HumanDecision.ACCEPTED,
        reviewer=WORKBENCH_HISTORY_HOSTILE_REVIEWER,
        comment=WORKBENCH_HISTORY_HOSTILE_NOTE,
        evidence_url=WORKBENCH_HISTORY_HOSTILE_URL,
        timestamp=datetime.fromisoformat("2035-03-02T01:02:03+05:45"),
    ))
    state = append_resolution(state, ResolutionEvent(
        event_id="workbench-criterion-extra-flag", criterion_id="AC-01",
        decision=HumanDecision.CHANGE_REQUIRED, final_acceptance=False,
        reviewer="Constructed criterion recorder", comment="", evidence_url="",
        timestamp=datetime.fromisoformat("2020-01-01T10:11:12-04:00"),
    ))
    # Loaded legacy review-level events may retain extra manual fields. Their
    # target remains final acceptance, so these fields never create a criterion
    # resolution or a runtime observation. Both flags remain explicitly false.
    state.resolution_events[1:1] = [
        ResolutionEvent(
            event_id="workbench-final-manual-missing", final_acceptance=False,
            decision=HumanDecision.MANUALLY_VERIFIED,
            reviewer="Constructed extra manual claimant",
            comment="Recorded extra manual assertion without a runtime observation",
            claimed_evidence_level=EvidenceLevel.E4, criteria_revision_number=1,
            timestamp=datetime.fromisoformat("2025-01-02T03:04:05"),
        ),
        ResolutionEvent(
            event_id="workbench-final-manual-linked", final_acceptance=False,
            decision=HumanDecision.MANUALLY_VERIFIED,
            reviewer="Constructed extra linked claimant",
            comment="Recorded unmatched link retained only as unapplied context",
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id="unmatched-recorded-workbench-link",
            criteria_revision_number=1,
            timestamp=datetime.fromisoformat("2024-02-03T04:05:06+00:00"),
        ),
    ]
    return validated_review_state(state)
