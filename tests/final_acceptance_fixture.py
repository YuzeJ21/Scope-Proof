"""Constructed local flags, not observed practitioner acceptance or runtime proof."""

from scopeproof_core.gates.evaluator import unresolved_changed_file_paths
from scopeproof_core.reviews.lifecycle import append_file_scope_decision, append_resolution
from scopeproof_core.schemas.models import FileScopeDecision, HumanDecision, ResolutionEvent
from tests.saved_comparison_fixture import saved_comparison_states


def acceptance_comparison_states(*, previous=False, current=True):
    current_state, previous_state = saved_comparison_states()
    results = []
    for state, accepted in ((current_state, current), (previous_state, previous)):
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
                note="CONSTRUCTED explicit scope choice, not inferred product acceptance.",
                reviewer="CONSTRUCTED automatic acceptance-fixture actor",
            ))
        for criterion in state.bundle.criteria:
            state = append_resolution(state, ResolutionEvent(
                criterion_id=criterion.criterion_id, decision=HumanDecision.ACCEPTED_EXCEPTION,
                reviewer="CONSTRUCTED automatic acceptance-fixture actor",
                comment="CONSTRUCTED exception; not runtime verification or practitioner use.",
            ))
        if accepted:
            state = append_resolution(state, ResolutionEvent(
                final_acceptance=True, reviewer="CONSTRUCTED automatic acceptance-fixture actor",
                comment="CONSTRUCTED recorded flag; not authenticated or qualifying acceptance.",
            ))
        results.append(state)
    return tuple(results)
