"""Append-only review lifecycle operations independent of Streamlit state."""

from __future__ import annotations

from enum import StrEnum

from scopeproof_core.gates.evaluator import evaluate_gate
from scopeproof_core.gates.validation import (
    validated_review_bundle,
    validated_review_state,
)
from scopeproof_core.resolution_events import current_resolutions, final_acceptance
from scopeproof_core.review_policy import acceptance_requires_comment
from scopeproof_core.schemas.models import (
    MAX_JUNIT_IMPORTS_PER_REVIEW,
    CheckState,
    CriteriaRevision,
    CriteriaSourceProvenance,
    Criterion,
    EvidenceLevel,
    HumanDecision,
    IngestionState,
    JUnitEvidenceImport,
    ResolutionEvent,
    ReviewBundle,
    ReviewState,
    RuntimeEvidence,
    normalized_criteria_sha256,
)


class ResolutionEventStatus(StrEnum):
    """Whether an append-only event currently supplies active-revision state."""

    CURRENT = "current"
    SUPERSEDED = "superseded"
    PRIOR_REVISION = "prior_revision"


def _validated_state(state: ReviewState) -> ReviewState:
    """Revalidate mutable model input before applying a lifecycle transition."""
    return validated_review_state(state)


def new_review_state(bundle: ReviewBundle) -> ReviewState:
    """Initialize lifecycle state from a revalidated analysis bundle."""
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    if not bundle.criteria:
        raise ValueError("initial analysis requires at least one criterion")
    if bundle.resolutions:
        raise ValueError("initial analysis bundle must not contain human resolutions")
    if bundle.review.final_acceptance:
        raise ValueError("initial analysis bundle must not contain final acceptance")
    if bundle.junit_evidence_imports:
        raise ValueError("initial analysis bundle must not contain JUnit imports")
    bundle = validated_review_bundle(bundle)
    if bundle.review.criteria_source_provenance is None:
        raise ValueError(
            "initial analysis bundle requires criteria source provenance"
        )
    active_bundle = bundle.model_copy(
        update={"criteria_revision_number": 1}, deep=True
    )
    source_provenance = bundle.review.criteria_source_provenance.model_copy(deep=True)
    revision = CriteriaRevision(
        number=1,
        criteria=[criterion.model_copy(deep=True) for criterion in bundle.criteria],
        source_text=bundle.source_text,
        confirmed=bundle.review.criteria_confirmed,
        confirmed_at=source_provenance.confirmed_at,
        source_provenance=source_provenance,
    )
    return ReviewState(
        review=bundle.review.model_copy(deep=True),
        criteria_revision=revision,
        bundle=active_bundle,
    )


def revise_criteria(
    state: ReviewState, criteria: list[Criterion], source_text: str
) -> ReviewState:
    """Create an unconfirmed revision and preserve the superseded analysis."""
    state = _validated_state(state)
    if not criteria:
        raise ValueError("criteria revision requires at least one criterion")
    history = [*state.analysis_history]
    if state.bundle is not None:
        history.append(state.bundle)
    validated_criteria = [
        Criterion.model_validate(criterion.model_dump(mode="python")) for criterion in criteria
    ]
    revision = CriteriaRevision(
        number=state.criteria_revision.number + 1,
        criteria=validated_criteria,
        source_text=source_text,
    )
    review = state.review.model_copy(
        update={
            "criteria_confirmed": False,
            "criteria_source_provenance": None,
            "final_acceptance": False,
        }
    )
    return state.model_copy(
        update={
            "review": review,
            "criteria_revision": revision,
            "bundle": None,
            "analysis_history": history,
        }
    )


def confirm_criteria(
    state: ReviewState,
    provenance: CriteriaSourceProvenance,
) -> ReviewState:
    """Confirm the active revision against one validated source snapshot."""
    state = _validated_state(state)
    if not state.criteria_revision.criteria:
        raise ValueError("criteria confirmation requires at least one criterion")
    if state.bundle is not None:
        raise ValueError(
            "criteria confirmation requires a pending revision without an active bundle"
        )
    provenance = CriteriaSourceProvenance.model_validate(
        provenance.model_dump(mode="python")
    )
    if provenance.confirmed_at < state.criteria_revision.created_at:
        raise ValueError("criteria source confirmation predates the active revision")
    revision = CriteriaRevision.model_validate(
        {
            **state.criteria_revision.model_dump(mode="python"),
            "confirmed": True,
            "confirmed_at": provenance.confirmed_at,
            "source_provenance": provenance,
        }
    )
    review = state.review.model_copy(
        update={
            "criteria_confirmed": True,
            "criteria_source_provenance": provenance.model_copy(deep=True),
            "final_acceptance": False,
        }
    )
    return validated_review_state(
        state.model_copy(update={"criteria_revision": revision, "review": review})
    )


def attach_analysis(state: ReviewState, bundle: ReviewBundle) -> ReviewState:
    """Attach validated static analysis to a confirmed pending revision."""
    state = _validated_state(state)
    if not state.criteria_revision.criteria:
        raise ValueError("analysis attachment requires at least one criterion")
    if state.bundle is not None:
        raise ValueError(
            "analysis attachment requires a pending revision without an active bundle"
        )
    if not state.criteria_revision.confirmed:
        raise ValueError("analysis attachment requires a confirmed criteria revision")
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    if not bundle.criteria:
        raise ValueError("analysis attachment requires at least one criterion")
    if bundle.resolutions:
        raise ValueError("attached analysis must not contain human resolutions")
    if bundle.review.final_acceptance:
        raise ValueError("attached analysis must not contain final acceptance")
    bundle = validated_review_bundle(bundle)
    if (
        state.criteria_revision.source_provenance is None
        or bundle.review.criteria_source_provenance
        != state.criteria_revision.source_provenance
        or state.review.criteria_source_provenance
        != state.criteria_revision.source_provenance
    ):
        raise ValueError(
            "attached analysis criteria source provenance must match the active revision"
        )
    if bundle.criteria != state.criteria_revision.criteria:
        raise ValueError("attached analysis criteria must match the active revision")
    if bundle.source_text != state.criteria_revision.source_text:
        raise ValueError("attached analysis source must match the active revision")
    rebound_review = bundle.review.model_copy(
        update={
            "review_id": state.review.review_id,
            "created_at": state.review.created_at,
        }
    )
    if rebound_review != state.review:
        raise ValueError("attached analysis review must match the lifecycle review")
    active_bundle = bundle.model_copy(
        update={
            "criteria_revision_number": state.criteria_revision.number,
        },
        deep=True,
    )
    active_bundle.review = state.review.model_copy(deep=True)
    return validated_review_state(state.model_copy(update={"bundle": active_bundle}))


def resolution_event_statuses(
    events: list[ResolutionEvent], active_revision_number: int
) -> list[ResolutionEventStatus]:
    """Classify events without changing their append-only order or gate semantics."""
    latest_by_target: dict[tuple[bool, str | None], int] = {}
    for index, event in enumerate(events):
        if event.criteria_revision_number != active_revision_number:
            continue
        target = (event.criterion_id is None, event.criterion_id)
        latest_by_target[target] = index

    statuses: list[ResolutionEventStatus] = []
    for index, event in enumerate(events):
        if event.criteria_revision_number != active_revision_number:
            statuses.append(ResolutionEventStatus.PRIOR_REVISION)
            continue
        target = (event.criterion_id is None, event.criterion_id)
        status = (
            ResolutionEventStatus.CURRENT
            if latest_by_target[target] == index
            else ResolutionEventStatus.SUPERSEDED
        )
        statuses.append(status)
    return statuses


def _recalculate(state: ReviewState) -> ReviewState:
    if state.bundle is None:
        return state
    revision_number = state.criteria_revision.number
    review = state.review.model_copy(
        update={"final_acceptance": final_acceptance(state.resolution_events, revision_number)}
    )
    resolutions = current_resolutions(state.resolution_events, revision_number)
    bundle = state.bundle.model_copy(deep=True)
    bundle.review = review
    bundle.resolutions = resolutions
    bundle.gate = evaluate_gate(bundle.review, bundle.criteria, bundle.findings, resolutions)
    return state.model_copy(update={"review": review, "bundle": bundle})


def append_resolution(state: ReviewState, event: ResolutionEvent) -> ReviewState:
    """Append an event, bind it to the active revision, and rerun the deterministic gate."""
    state = _validated_state(state)
    event = ResolutionEvent.model_validate(event.model_dump())
    if any(existing.event_id == event.event_id for existing in state.resolution_events):
        raise ValueError("resolution event ID must be unique")
    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording a resolution")
    if event.decision is HumanDecision.MANUALLY_VERIFIED:
        raise ValueError(
            "manual verification must be recorded with append_external_verification"
        )
    if event.criterion_id is not None and state.review.final_acceptance:
        active_resolutions = {
            resolution.criterion_id: resolution
            for resolution in current_resolutions(
                state.resolution_events, state.criteria_revision.number
            )
        }
        current_resolution = active_resolutions.get(event.criterion_id)
        if (
            current_resolution is not None
            and current_resolution.decision is HumanDecision.MANUALLY_VERIFIED
        ):
            raise ValueError(
                "final acceptance must be revoked before replacing manual verification"
            )
    if event.final_acceptance is True and not can_record_final_acceptance(state):
        raise ValueError("final acceptance prerequisites are not satisfied")
    if event.criterion_id is not None and event.criterion_id not in {
        criterion.criterion_id for criterion in state.bundle.criteria
    }:
        raise ValueError("resolution event must reference a criterion in the active review")
    if event.criterion_id is not None:
        criterion_by_id = {
            criterion.criterion_id: criterion for criterion in state.bundle.criteria
        }
        finding_by_id = {
            finding.criterion_id: finding for finding in state.bundle.findings
        }
        criterion = criterion_by_id[event.criterion_id]
        finding = finding_by_id.get(event.criterion_id)
        if (
            finding is not None
            and event.decision is not None
            and acceptance_requires_comment(
                event.decision,
                finding.evidence_level,
                criterion.required_evidence_level,
            )
            and not event.comment.strip()
        ):
            raise ValueError(
                "a reviewer comment is required when accepting below the required "
                "evidence level"
            )
    bound_event = ResolutionEvent.model_validate(
        {
            **event.model_dump(),
            "criteria_revision_number": state.criteria_revision.number,
        }
    )
    updated_events = [*state.resolution_events, bound_event]
    updated = state.model_copy(update={"resolution_events": updated_events})
    return validated_review_state(_recalculate(updated))


def append_runtime_evidence(state: ReviewState, evidence: RuntimeEvidence) -> ReviewState:
    """Append a manual runtime record without upgrading static findings or gate truth."""

    state = _validated_state(state)
    evidence = RuntimeEvidence.model_validate(evidence.model_dump())
    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording runtime evidence")
    if evidence.criterion_id not in {criterion.criterion_id for criterion in state.bundle.criteria}:
        raise ValueError("runtime evidence must reference a criterion in the active review")
    if evidence.runtime_evidence_id is None:
        raise ValueError("runtime evidence must include the active review identity")
    if (
        evidence.repository,
        evidence.pr_number,
        evidence.head_sha,
    ) != (
        state.review.repository,
        state.review.pr_number,
        state.review.head_sha,
    ):
        raise ValueError("runtime evidence must match the active review identity")
    if any(
        existing.runtime_evidence_id == evidence.runtime_evidence_id
        for existing in state.bundle.runtime_evidence
    ):
        raise ValueError("runtime evidence ID must be unique")
    bundle = state.bundle.model_copy(deep=True)
    bundle.runtime_evidence.append(evidence.model_copy(deep=True))
    return validated_review_state(state.model_copy(update={"bundle": bundle}))


def append_junit_evidence_import(
    state: ReviewState,
    evidence_import: JUnitEvidenceImport,
) -> ReviewState:
    """Append non-gating external test context to one exact active review."""

    state = _validated_state(state)
    if state.bundle is None:
        raise ValueError("JUnit import requires an active analysis")
    bundle = state.bundle
    if len(bundle.junit_evidence_imports) >= MAX_JUNIT_IMPORTS_PER_REVIEW:
        raise ValueError(
            f"review may contain at most {MAX_JUNIT_IMPORTS_PER_REVIEW} JUnit imports"
        )
    evidence_import = JUnitEvidenceImport.model_validate(
        evidence_import.model_dump(mode="python")
    )
    if (
        evidence_import.repository,
        evidence_import.pr_number,
        evidence_import.head_sha,
    ) != (
        state.review.repository,
        state.review.pr_number,
        state.review.head_sha,
    ):
        raise ValueError("JUnit import must match the active review identity")
    if evidence_import.criteria_revision_number != state.criteria_revision.number:
        raise ValueError("JUnit import criteria revision must match the active revision")
    if evidence_import.confirmed_criteria_sha256 != normalized_criteria_sha256(
        state.criteria_revision.criteria
    ):
        raise ValueError("JUnit import criteria digest must match the active revision")
    if (
        state.criteria_revision.source_provenance is None
        or evidence_import.criteria_source_provenance
        != state.criteria_revision.source_provenance
    ):
        raise ValueError("JUnit import criteria provenance must match the active revision")
    known_criteria = {
        criterion.criterion_id for criterion in state.criteria_revision.criteria
    }
    if any(
        mapping.criterion_id not in known_criteria
        for mapping in evidence_import.criterion_mappings
    ):
        raise ValueError("JUnit import mappings must reference active criteria")
    if any(
        existing.artifact_sha256 == evidence_import.artifact_sha256
        for existing in bundle.junit_evidence_imports
    ):
        raise ValueError("JUnit artifact is already imported")
    if any(
        existing.import_id == evidence_import.import_id
        for existing in bundle.junit_evidence_imports
    ):
        raise ValueError("JUnit import ID is already recorded")

    unchanged_gate = bundle.gate.model_copy(deep=True)
    unchanged_findings = [item.model_copy(deep=True) for item in bundle.findings]
    unchanged_resolutions = [item.model_copy(deep=True) for item in bundle.resolutions]
    unchanged_runtime = [item.model_copy(deep=True) for item in bundle.runtime_evidence]
    unchanged_events = [item.model_copy(deep=True) for item in state.resolution_events]
    unchanged_final_acceptance = state.review.final_acceptance
    updated_bundle = bundle.model_copy(deep=True)
    updated_bundle.junit_evidence_imports.append(evidence_import.model_copy(deep=True))
    updated = validated_review_state(state.model_copy(update={"bundle": updated_bundle}))
    assert updated.bundle is not None
    if (
        updated.bundle.gate != unchanged_gate
        or updated.bundle.findings != unchanged_findings
        or updated.bundle.resolutions != unchanged_resolutions
        or updated.bundle.runtime_evidence != unchanged_runtime
        or updated.resolution_events != unchanged_events
        or updated.review.final_acceptance is not unchanged_final_acceptance
    ):
        raise ValueError("JUnit import must not alter deterministic or human review truth")
    return updated


def append_external_verification(
    state: ReviewState,
    evidence: RuntimeEvidence,
    event: ResolutionEvent,
) -> ReviewState:
    """Atomically record external runtime evidence and its manual verification decision."""

    state = _validated_state(state)
    evidence = RuntimeEvidence.model_validate(evidence.model_dump())
    event = ResolutionEvent.model_validate(event.model_dump())
    if state.bundle is None:
        raise ValueError("Run a confirmed analysis before recording external verification")
    if evidence.runtime_evidence_id is None:
        raise ValueError("runtime evidence must include the active review identity")
    if (
        evidence.repository,
        evidence.pr_number,
        evidence.head_sha,
    ) != (
        state.review.repository,
        state.review.pr_number,
        state.review.head_sha,
    ):
        raise ValueError("runtime evidence must match the active review identity")
    if event.decision is not HumanDecision.MANUALLY_VERIFIED:
        raise ValueError("external verification requires a manually verified decision")
    if event.runtime_evidence_id != evidence.runtime_evidence_id:
        raise ValueError(
            "external verification inputs must use the same runtime evidence ID"
        )
    if evidence.criterion_id != event.criterion_id:
        raise ValueError("external verification inputs must reference the same active criterion")
    if evidence.criterion_id not in {
        criterion.criterion_id for criterion in state.bundle.criteria
    }:
        raise ValueError("external verification inputs must reference the same active criterion")
    if evidence.reviewer != event.reviewer:
        raise ValueError("external verification inputs must use the same reviewer")
    if evidence.evidence_level != event.claimed_evidence_level:
        raise ValueError("external verification inputs must use the same evidence level")
    if evidence.evidence_level not in {EvidenceLevel.E3, EvidenceLevel.E4}:
        raise ValueError("external verification requires E3 or E4 evidence")
    if any(
        existing.runtime_evidence_id == evidence.runtime_evidence_id
        for existing in state.bundle.runtime_evidence
    ):
        raise ValueError("runtime evidence ID must be unique")
    if any(existing.event_id == event.event_id for existing in state.resolution_events):
        raise ValueError("resolution event ID must be unique")
    active_resolutions = {
        resolution.criterion_id: resolution
        for resolution in current_resolutions(
            state.resolution_events, state.criteria_revision.number
        )
    }
    current_resolution = active_resolutions.get(evidence.criterion_id)
    if (
        state.review.final_acceptance
        and current_resolution is not None
        and current_resolution.decision is HumanDecision.MANUALLY_VERIFIED
    ):
        raise ValueError(
            "final acceptance must be revoked before replacing manual verification"
        )

    bound_event = ResolutionEvent.model_validate(
        {
            **event.model_dump(),
            "criteria_revision_number": state.criteria_revision.number,
        }
    )
    bundle = state.bundle.model_copy(deep=True)
    bundle.runtime_evidence.append(evidence.model_copy(deep=True))
    updated = state.model_copy(
        update={
            "bundle": bundle,
            "resolution_events": [*state.resolution_events, bound_event],
        }
    )
    return validated_review_state(_recalculate(updated))


def can_record_final_acceptance(state: ReviewState) -> bool:
    """Return whether the active revision has every deterministic prerequisite."""

    if not state.criteria_revision.criteria or (
        state.bundle is not None and not state.bundle.criteria
    ):
        return False
    state = _validated_state(state)
    if state.bundle is None or state.review.final_acceptance:
        return False
    if (
        state.review.criteria_source_provenance is None
        or state.criteria_revision.source_provenance
        != state.review.criteria_source_provenance
        or state.bundle.review.criteria_source_provenance
        != state.review.criteria_source_provenance
    ):
        return False
    if not state.review.criteria_confirmed:
        return False
    if state.review.ingestion_state is not IngestionState.COMPLETE:
        return False
    if state.review.ingestion_warnings or state.review.skipped_files:
        return False
    if state.review.check_state is not CheckState.PASSING:
        return False

    accepted_decisions = {
        HumanDecision.ACCEPTED,
        HumanDecision.ACCEPTED_EXCEPTION,
        HumanDecision.MANUALLY_VERIFIED,
        HumanDecision.NOT_IN_SCOPE,
    }
    active_resolutions = {
        resolution.criterion_id: resolution
        for resolution in current_resolutions(
            state.resolution_events, state.criteria_revision.number
        )
    }
    return all(
        criterion.criterion_id in active_resolutions
        and active_resolutions[criterion.criterion_id].decision in accepted_decisions
        and (
            active_resolutions[criterion.criterion_id].decision
            is not HumanDecision.MANUALLY_VERIFIED
            or active_resolutions[criterion.criterion_id].runtime_evidence_id is not None
        )
        for criterion in state.bundle.criteria
    )
