"""Trusted constructed saved-review recipe, runnable from an installed wheel."""

from datetime import UTC, datetime

from scopeproof_core.demo import build_review
from scopeproof_core.reviews.lifecycle import append_file_scope_decision, new_review_state
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
    LineChangeType,
    PullRequestSnapshot,
    RepositoryVisibility,
    ReviewState,
)

CURRENT_REVIEW_ID = "saved-comparison-current"
PREVIOUS_REVIEW_ID = "saved-comparison-previous"
CURRENT_HEAD = "b" * 40
PREVIOUS_HEAD = "a" * 40
HISTORY_HEAD = "c" * 40


def _constructed_state(
    review_id: str, head: str, *, added_path: bool,
    revision_number: int = 1, selected_context: str | None = None,
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
        check_state=CheckState.PASSING,
        ci_observation=CIObservation(
            state=CheckState.PASSING,
            reason="Constructed successful check metadata; no runtime verification.",
            reason_code=CIReasonCode.SUCCESSFUL_CHECK_RUNS,
            total_check_runs=1, successful_check_runs=1,
        ),
        fetched_at=datetime(2026, 10, 30, 12, tzinfo=UTC), files=files,
    )
    criterion = Criterion(
        criterion_id="AC-01", text="Export CSV", required_evidence_level=EvidenceLevel.E2,
    )
    bundle = build_review(snapshot, {
        "fixture": "constructed-durable-saved-comparison-v1",
        "deliberately_constructed_demo": True,
        "source_text": "Export CSV",
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


def saved_comparison_states(
    *, selected_references: bool = False,
) -> tuple[ReviewState, ReviewState]:
    """Return compatible constructed active/history and separate-record analyses."""
    current = _constructed_state(
        CURRENT_REVIEW_ID, CURRENT_HEAD, added_path=True, revision_number=2,
        selected_context="current" if selected_references else None,
    )
    historical = _with_prior_scope_decision(
        _constructed_state(
            CURRENT_REVIEW_ID, HISTORY_HEAD, added_path=False,
            selected_context="historical" if selected_references else None,
        )
    )
    previous = _with_prior_scope_decision(
        _constructed_state(
            PREVIOUS_REVIEW_ID, PREVIOUS_HEAD, added_path=False,
            selected_context="previous" if selected_references else None,
        )
    )
    assert current.bundle is not None and historical.bundle is not None
    current.criteria_revision.number = 2
    current.bundle.criteria_revision_number = 2
    current.analysis_history = [historical.bundle]
    return (
        ReviewState.model_validate(current.model_dump(mode="python")),
        ReviewState.model_validate(previous.model_dump(mode="python")),
    )
