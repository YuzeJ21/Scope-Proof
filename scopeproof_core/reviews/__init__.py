"""Lifecycle helpers for user-owned criteria and human acceptance history."""

from scopeproof_core.reviews.comparison import ReviewComparison, compare_reviews
from scopeproof_core.reviews.lifecycle import (
    append_resolution,
    append_runtime_evidence,
    confirm_criteria,
    current_resolutions,
    new_review_state,
    revise_criteria,
)

__all__ = [
    "ReviewComparison",
    "append_resolution",
    "append_runtime_evidence",
    "compare_reviews",
    "confirm_criteria",
    "current_resolutions",
    "new_review_state",
    "revise_criteria",
]
