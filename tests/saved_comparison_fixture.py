"""Trusted constructed saved-review recipe, runnable from an installed wheel."""

from datetime import UTC, datetime

from scopeproof_core.demo import build_review
from scopeproof_core.reviews.lifecycle import (
    append_external_verification,
    append_file_scope_decision,
    append_resolution,
    new_review_state,
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
    FileScopeDecision,
    HumanDecision,
    LineChangeType,
    PullRequestSnapshot,
    RepositoryVisibility,
    ResolutionEvent,
    ReviewState,
    RuntimeEvidence,
)

CURRENT_REVIEW_ID = "saved-comparison-current"
PREVIOUS_REVIEW_ID = "saved-comparison-previous"
CURRENT_HEAD = "b" * 40
PREVIOUS_HEAD = "a" * 40
HISTORY_HEAD = "c" * 40
FOREIGN_HISTORY_HEAD = "e" * 40


def _constructed_state(
    review_id: str, head: str, *, added_path: bool,
    revision_number: int = 1, selected_context: str | None = None,
    failing_checks: bool = False,
    requirement_text: str = "Export CSV",
) -> ReviewState:
    files = [
        ChangedFile(
            path="src/export.py", status="modified",
            lines=[ChangedLine(
                change_type=LineChangeType.ADDED, line_number=1,
                content="def export_csv(rows): return rows",
            )],
        ),
        ChangedFile(
            path="notes.md", status="added",
            lines=[ChangedLine(
                change_type=LineChangeType.ADDED, line_number=1,
                content="Constructed unrelated project note.",
            )],
        ),
    ]
    if added_path:
        files.append(ChangedFile(
            path="src/unrelated.py", status="added",
            lines=[ChangedLine(
                change_type=LineChangeType.ADDED, line_number=1,
                content="raise AssertionError('CONSTRUCTED-TARGET-CODE-MUST-NOT-RUN')",
            )],
        ))
    snapshot = PullRequestSnapshot(
        repository="acme/widget", repository_visibility=RepositoryVisibility.VERIFIED_PUBLIC,
        pr_number=7, title="Constructed durable saved-comparison example",
        description="Constructed test input, not an observed public pull request.",
        html_url="https://github.com/acme/widget/pull/7",
        base_sha="d" * 40, head_sha=head,
        check_state=CheckState.FAILING if failing_checks else CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.FAILING if failing_checks else CheckState.PASSING,
            reason="Constructed check metadata; no runtime verification.",
            reason_code=(
                CIReasonCode.FAILING_CHECK_RUNS if failing_checks
                else CIReasonCode.SUCCESSFUL_CHECK_RUNS
            ),
            total_check_runs=1,
            successful_check_runs=int(not failing_checks), failing_check_runs=int(failing_checks),
        ),
        fetched_at=datetime(2026, 10, 30, 12, tzinfo=UTC), files=files,
    )
    criterion = Criterion(
        criterion_id="AC-01", text=requirement_text, required_evidence_level=EvidenceLevel.E2,
    )
    bundle = build_review(snapshot, {
        "fixture": "constructed-durable-saved-comparison-v1",
        "deliberately_constructed_demo": True,
        "source_text": requirement_text,
        "criteria": [criterion.model_dump(mode="json")],
        "criteria_confirmed": True,
        "resolutions": [],
    })
    bundle.review.review_id = review_id
    state = new_review_state(bundle)
    state.criteria_revision.number = revision_number
    state.bundle.criteria_revision_number = revision_number
    if selected_context is not None:
        from scopeproof_core.storage.json_store import JsonReviewStore

        selected = next(
            item for item in selectable_reference_lines(state, snapshot)
            if item.file_path == "notes.md"
        )
        state = append_reviewer_selected_reference(
            state, snapshot=snapshot, selected=selected, criterion_id="AC-01",
            reviewer=f"Constructed {selected_context} reference reviewer",
            rationale=f"Constructed {selected_context} source context; not execution evidence.",
            expected_state_fingerprint=JsonReviewStore.state_fingerprint(state),
        )
        reference = state.bundle.reviewer_selected_references[0]
        state.bundle.reviewer_selected_references[0] = reference.model_copy(update={
            "reference_id": f"constructed-{selected_context}-reference",
            "selected_at": datetime(2026, 10, 30, 12, tzinfo=UTC),
        })
    return ReviewState.model_validate(state.model_dump(mode="python"))


def saved_requirements_states() -> tuple[ReviewState, ReviewState]:
    """One PR with different criteria in active and retained saved analyses."""
    current = _constructed_state(
        CURRENT_REVIEW_ID, CURRENT_HEAD, added_path=True,
        requirement_text="CONSTRUCTED Export JSON <img src=https://example.invalid/fixture>",
    )
    previous = _constructed_state(
        PREVIOUS_REVIEW_ID, PREVIOUS_HEAD, added_path=False, revision_number=2,
    )
    retained = _constructed_state(
        PREVIOUS_REVIEW_ID, FOREIGN_HISTORY_HEAD, added_path=False,
        requirement_text="CONSTRUCTED Export XML",
    )
    previous.analysis_history = [retained.bundle]
    return current, previous


def _with_prior_scope_decision(state: ReviewState) -> ReviewState:
    provenance = state.review.criteria_source_provenance
    assert provenance is not None
    return append_file_scope_decision(state, FileScopeDecision(
        event_id=f"{state.review.review_id}-{state.review.head_sha[0]}-scope",
        review_id=state.review.review_id, head_sha=state.review.head_sha,
        criteria_revision_number=state.criteria_revision.number,
        normalized_criteria_sha256=provenance.normalized_criteria_sha256,
        path="notes.md", disposition="outside_confirmed_criteria",
        note="Constructed note reviewed against the confirmed CSV criterion.",
        reviewer="Constructed saved-comparison reviewer",
        timestamp=datetime(2026, 10, 30, 12, tzinfo=UTC),
    ))


def _with_decision_context(state: ReviewState, context: str) -> ReviewState:
    """Record explicitly constructed observations, never actual target execution."""
    label = context.replace("-", " ")
    actor = f"CONSTRUCTED {label} automatic decision actor"
    artifact = f"https://example.test/constructed/{context}/runtime-report"
    # Exercise wrapping of valid long recorded identities in real installed UI.
    runtime_id = f"constructed-{context}-runtime-" + "traceability" * 90
    timestamp = datetime(2026, 10, 30, 12, tzinfo=UTC)
    return append_external_verification(
        state,
        RuntimeEvidence(
            runtime_evidence_id=runtime_id,
            repository=state.review.repository,
            pr_number=state.review.pr_number,
            head_sha=state.review.head_sha,
            criterion_id="AC-01",
            artifact_reference=artifact,
            scenario=f"CONSTRUCTED {label} CSV export observation",
            timestamp=timestamp,
            environment=f"CONSTRUCTED {label} automatic test environment",
            result=(
                f"CONSTRUCTED {label} recorded result; no target code was executed. "
                "<img src=x onerror=bad> **Untrusted recorded text**"
            ),
            reviewer=actor,
            evidence_level=EvidenceLevel.E3,
            limitations=[
                f"CONSTRUCTED {label} observation; no genuine external verification.",
                "Automatic fixture actors are not independent practitioners.",
            ],
        ),
        ResolutionEvent(
            event_id=f"constructed-{context}-manual-decision",
            criterion_id="AC-01",
            decision=HumanDecision.MANUALLY_VERIFIED,
            comment=f"CONSTRUCTED {label} decision rationale; not customer evidence.",
            evidence_url=artifact,
            claimed_evidence_level=EvidenceLevel.E3,
            runtime_evidence_id=runtime_id,
            reviewer=actor,
            timestamp=timestamp,
        ),
    )


def _with_recorded_acceptance(state: ReviewState, *, accepted: bool) -> ReviewState:
    """Construct explicit scope/exception decisions; never claim practitioner acceptance."""
    from scopeproof_core.gates.evaluator import unresolved_changed_file_paths

    actor = "CONSTRUCTED automatic acceptance-fixture actor"
    for path in sorted(unresolved_changed_file_paths(
        state.review, state.bundle.findings, state.bundle.evidence,
        state.bundle.file_scope_decisions,
    )):
        state = append_file_scope_decision(state, FileScopeDecision(
            review_id=state.review.review_id, head_sha=state.review.head_sha,
            criteria_revision_number=state.criteria_revision.number,
            normalized_criteria_sha256=(
                state.review.criteria_source_provenance.normalized_criteria_sha256
            ), path=path, disposition="outside_confirmed_criteria",
            note="CONSTRUCTED scope choice; not inferred acceptance.", reviewer=actor,
        ))
    state = append_resolution(state, ResolutionEvent(
        criterion_id="AC-01", decision=HumanDecision.ACCEPTED_EXCEPTION,
        comment="CONSTRUCTED exception; not runtime verification or practitioner use.",
        reviewer=actor,
    ))
    if accepted:
        state = append_resolution(state, ResolutionEvent(
            final_acceptance=True, reviewer=actor,
            comment="CONSTRUCTED recorded flag; not authenticated or qualifying acceptance.",
        ))
    return state


def saved_comparison_states(
    *, selected_references: bool = False, foreign_history: bool = False,
    decision_context: bool = False, final_acceptance_context: bool = False,
    previous_checks_failing: bool = False,
) -> tuple[ReviewState, ReviewState]:
    """Return compatible constructed active/history and separate-record analyses."""
    current_id = CURRENT_REVIEW_ID + ("-acceptance" if final_acceptance_context else "")
    previous_id = PREVIOUS_REVIEW_ID + ("-acceptance" if final_acceptance_context else "")
    current = _constructed_state(
        current_id, CURRENT_HEAD, added_path=True, revision_number=2,
        selected_context="current" if selected_references else None,
    )
    historical = _with_prior_scope_decision(
        _constructed_state(
            current_id, HISTORY_HEAD, added_path=False,
            selected_context="historical" if selected_references else None,
        )
    )
    previous = _with_prior_scope_decision(
        _constructed_state(
            previous_id, PREVIOUS_HEAD, added_path=False,
            revision_number=2 if foreign_history else 1,
            selected_context="previous" if selected_references else None,
            failing_checks=previous_checks_failing,
        )
    )
    if decision_context:
        current = _with_decision_context(current, "current")
        historical = _with_decision_context(historical, "historical")
        previous = _with_decision_context(previous, "previous")
    if final_acceptance_context:
        current = _with_recorded_acceptance(current, accepted=True)
        historical = _with_recorded_acceptance(historical, accepted=False)
        previous = _with_recorded_acceptance(previous, accepted=False)
    assert current.bundle is not None and historical.bundle is not None
    current.criteria_revision.number = 2
    current.bundle.criteria_revision_number = 2
    current.analysis_history = [historical.bundle]
    if decision_context or final_acceptance_context:
        current.resolution_events = [
            *historical.resolution_events, *current.resolution_events,
        ]
    if foreign_history:
        foreign_historical = _with_prior_scope_decision(_constructed_state(
            previous_id, FOREIGN_HISTORY_HEAD, added_path=False,
            selected_context="foreign-history" if selected_references else None,
        ))
        if decision_context:
            foreign_historical = _with_decision_context(foreign_historical, "foreign-history")
        if final_acceptance_context:
            foreign_historical = _with_recorded_acceptance(foreign_historical, accepted=False)
        previous.analysis_history = [foreign_historical.bundle]
        if decision_context or final_acceptance_context:
            previous.resolution_events = [
                *foreign_historical.resolution_events, *previous.resolution_events,
            ]
    return (
        ReviewState.model_validate(current.model_dump(mode="python")),
        ReviewState.model_validate(previous.model_dump(mode="python")),
    )
