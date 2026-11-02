"""Pure explicit correction of retained external mappings; never test execution."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.junit_audit import (
    _without_audit,
    effective_junit_mappings,
    junit_mapping_correction_events,
)
from scopeproof_core.schemas.models import (
    JUnitCriterionMapping,
    JUnitEvidenceImport,
    JUnitMappingCorrectionEvent,
    LocalReviewId,
    ReviewState,
    junit_mapping_sha256,
)
from scopeproof_core.storage.json_store import JsonReviewStore


def _validated_target(state: ReviewState, import_id: str) -> JUnitEvidenceImport:
    if state.bundle is None or not state.criteria_revision.confirmed:
        raise ValueError("JUnit correction requires a confirmed active analysis")
    if import_id not in state.bundle.active_junit_import_ids:
        raise ValueError("JUnit correction target must be an active retained import")
    return next(x for x in state.bundle.junit_evidence_imports if x.import_id == import_id)


def _validated_mappings(mappings) -> list[JUnitCriterionMapping]:
    return [JUnitCriterionMapping.model_validate(
        x.model_dump(mode="python") if isinstance(x, JUnitCriterionMapping) else x,
    ) for x in mappings]


def correct_junit_mappings(
    state: ReviewState,
    *,
    import_id: str,
    criterion_mappings: list[JUnitCriterionMapping],
    reviewer: str,
    reason: str,
    expected_state_fingerprint: str,
    confirm_whole_import: bool,
    occurred_at: datetime | None = None,
) -> ReviewState:
    """Append one full replacement snapshot without mutating any original review fact."""
    if type(confirm_whole_import) is not bool or not confirm_whole_import:
        raise ValueError("explicit whole-import confirmation is required")
    state = validated_review_state(state)
    if JsonReviewStore.state_fingerprint(state) != expected_state_fingerprint:
        raise ValueError("JUnit correction request is stale; reopen the saved review")
    target = _validated_target(state, import_id)
    previous = effective_junit_mappings(state.bundle, import_id)
    events = junit_mapping_correction_events(state.bundle, import_id)
    data = dict(
        import_id=target.import_id, artifact_sha256=target.artifact_sha256,
        review_id=state.review.review_id, repository=target.repository,
        pr_number=target.pr_number, head_sha=target.head_sha,
        criteria_revision_number=target.criteria_revision_number,
        confirmed_criteria_sha256=target.confirmed_criteria_sha256,
        criteria_source_provenance=target.criteria_source_provenance.model_copy(deep=True),
        previous_mapping_sha256=junit_mapping_sha256(previous),
        previous_correction_event_id=events[-1].event_id if events else None,
        criterion_mappings=_validated_mappings(criterion_mappings),
        reviewer=reviewer, reason=reason,
    )
    if occurred_at is not None:
        data["occurred_at"] = occurred_at
    event = JUnitMappingCorrectionEvent(**data)
    updated = state.model_copy(deep=True)
    updated.bundle.junit_import_events.append(event)
    updated = validated_review_state(updated)
    if _without_audit(updated) != _without_audit(state):
        raise ValueError("JUnit correction must not alter deterministic or reviewer truth")
    return updated


class JUnitMappingCorrectionDraft(BaseModel):
    """A source-free, complete staged mapping snapshot bound to its original state."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    state_fingerprint: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
    import_id: LocalReviewId
    criterion_mappings: tuple[JUnitCriterionMapping, ...] = Field(max_length=5_000)

    @model_validator(mode="after")
    def canonical_snapshot(self) -> JUnitMappingCorrectionDraft:
        junit_mapping_sha256(self.criterion_mappings)
        return self


def new_junit_correction_draft(
    state: ReviewState, import_id: str,
) -> JUnitMappingCorrectionDraft:
    state = validated_review_state(state)
    _validated_target(state, import_id)
    return JUnitMappingCorrectionDraft(
        state_fingerprint=JsonReviewStore.state_fingerprint(state), import_id=import_id,
        criterion_mappings=tuple(effective_junit_mappings(state.bundle, import_id)),
    )


def _validated_draft(
    state: ReviewState, draft: JUnitMappingCorrectionDraft,
) -> tuple[ReviewState, JUnitMappingCorrectionDraft]:
    state = validated_review_state(state)
    draft = JUnitMappingCorrectionDraft.model_validate(draft.model_dump(mode="python"))
    if draft.state_fingerprint != JsonReviewStore.state_fingerprint(state):
        raise ValueError("JUnit correction draft is stale; explicitly stage the mappings again")
    target = _validated_target(state, draft.import_id)
    _validate_draft_snapshot(state, target, draft.criterion_mappings)
    return state, draft


def _validate_draft_snapshot(state, target, mappings) -> None:
    if not mappings:
        return  # Removing all groups is permitted only while staging, never as a saved correction.
    payload = target.model_dump(mode="python")
    payload["criterion_mappings"] = [x.model_dump(mode="python") for x in mappings]
    JUnitEvidenceImport.model_validate(payload)
    known = {x.criterion_id for x in state.bundle.criteria}
    if any(x.criterion_id not in known for x in mappings):
        raise ValueError("JUnit correction mappings must reference known criteria")


def replace_junit_correction_group(
    state: ReviewState, draft: JUnitMappingCorrectionDraft, criterion_id: str,
    test_case_ids: list[str],
) -> JUnitMappingCorrectionDraft:
    state, draft = _validated_draft(state, draft)
    group = JUnitCriterionMapping(criterion_id=criterion_id, test_case_ids=test_case_ids)
    groups = [x.model_copy(deep=True) for x in draft.criterion_mappings
              if x.criterion_id != group.criterion_id]
    groups.append(group)
    groups.sort(key=lambda x: x.criterion_id)
    _validate_draft_snapshot(state, _validated_target(state, draft.import_id), groups)
    return JUnitMappingCorrectionDraft(
        state_fingerprint=draft.state_fingerprint, import_id=draft.import_id,
        criterion_mappings=tuple(groups),
    )


def remove_junit_correction_group(
    state: ReviewState, draft: JUnitMappingCorrectionDraft, criterion_id: str,
) -> JUnitMappingCorrectionDraft:
    state, draft = _validated_draft(state, draft)
    if criterion_id not in {x.criterion_id for x in draft.criterion_mappings}:
        raise ValueError("selected criterion has no staged JUnit mapping")
    return JUnitMappingCorrectionDraft(
        state_fingerprint=draft.state_fingerprint, import_id=draft.import_id,
        criterion_mappings=tuple(x.model_copy(deep=True) for x in draft.criterion_mappings
                                if x.criterion_id != criterion_id),
    )
