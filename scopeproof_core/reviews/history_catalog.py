"""Descriptive retained-history metadata for explicit, stale-safe handoff."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from scopeproof_core.build_identity import CoreSourceIdentity
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.historical_analysis import (
    Fingerprint,
    historical_analysis_fingerprint,
)
from scopeproof_core.schemas.models import GITHUB_REPOSITORY_PATTERN, LocalReviewId, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

HISTORY_CATALOG_BOUNDARY = (
    "Descriptive saved history, not current-head verification or acceptance. Positions refer "
    "only to this saved-state fingerprint. Recorded producer and actor context is asserted, "
    "not authenticated; no export eligibility or new verdict is established."
)


class HistoricalExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    history_position: Annotated[StrictInt, Field(gt=0)]
    expected_state_fingerprint: Fingerprint


class RetainedAnalysisEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    history_position: Annotated[StrictInt, Field(gt=0)]
    head_sha: str
    criteria_revision_number: Annotated[StrictInt, Field(gt=0)] | Literal["unknown"]
    criteria_confirmed: StrictBool
    analysis_fingerprint: Fingerprint
    tool_version: str
    ruleset_version: str
    analysis_source_identity: CoreSourceIdentity | None


class RetainedAnalysisCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    report_kind: Literal["scopeproof_retained_analysis_catalog"]
    schema_version: Literal[1]
    boundary: Literal[HISTORY_CATALOG_BOUNDARY]
    review_id: LocalReviewId
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: Annotated[StrictInt, Field(gt=0)]
    state_fingerprint: Fingerprint
    current_head_sha: str
    current_criteria_revision_number: Annotated[StrictInt, Field(gt=0)]
    current_criteria_confirmed: StrictBool
    has_active_analysis: StrictBool
    entries: tuple[RetainedAnalysisEntry, ...]

    @model_validator(mode="after")
    def _stored_order(self) -> RetainedAnalysisCatalog:
        if [entry.history_position for entry in self.entries] != list(
            range(1, len(self.entries) + 1)
        ):
            raise ValueError("history catalog positions must be complete and in stored order")
        return self


def build_history_catalog(state: ReviewState) -> RetainedAnalysisCatalog:
    """Describe a validated saved snapshot without computing verdicts or selecting an entry."""
    state = validated_review_state(state)
    return RetainedAnalysisCatalog(
        report_kind="scopeproof_retained_analysis_catalog", schema_version=1,
        boundary=HISTORY_CATALOG_BOUNDARY, review_id=state.review.review_id,
        repository=state.review.repository, pr_number=state.review.pr_number,
        state_fingerprint=JsonReviewStore.state_fingerprint(state),
        current_head_sha=state.review.head_sha,
        current_criteria_revision_number=state.criteria_revision.number,
        current_criteria_confirmed=state.criteria_revision.confirmed,
        has_active_analysis=state.bundle is not None,
        entries=tuple(RetainedAnalysisEntry(
            history_position=position, head_sha=bundle.review.head_sha,
            criteria_revision_number=bundle.criteria_revision_number,
            criteria_confirmed=bundle.review.criteria_confirmed,
            analysis_fingerprint=historical_analysis_fingerprint(bundle),
            tool_version=bundle.review.tool_version, ruleset_version=bundle.review.ruleset_version,
            analysis_source_identity=bundle.review.analysis_source_identity,
        ) for position, bundle in enumerate(state.analysis_history, 1)),
    )
