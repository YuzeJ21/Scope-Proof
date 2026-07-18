"""Lifecycle helpers for user-owned criteria and human acceptance history."""

from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.lifecycle import (
    ResolutionEventStatus,
    append_external_verification,
    append_resolution,
    append_runtime_evidence,
    attach_analysis,
    can_record_final_acceptance,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    resolution_event_statuses,
    revise_criteria,
)

__all__ = [
    "ResolutionEventStatus",
    "ReviewComparison",
    "append_external_verification",
    "append_resolution",
    "append_runtime_evidence",
    "attach_analysis",
    "can_record_final_acceptance",
    "compare_reviews",
    "confirm_criteria",
    "current_resolutions",
    "new_review_state",
    "resolution_event_statuses",
    "revise_criteria",
]
