"""Read one retained analysis without promoting it to current review authority."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from scopeproof_core.build_identity import CoreSourceIdentity, current_core_source_identity
from scopeproof_core.gates.validation import validated_review_bundle, validated_review_state
from scopeproof_core.schemas.models import RULESET_VERSION, LocalReviewId, ReviewBundle, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__

HISTORICAL_ANALYSIS_BOUNDARY = (
    "Historical recorded analysis, validated under the installed policy; not current-head "
    "verification or acceptance. Saved observations and reviewer identities are asserted, not "
    "authenticated. No source or artifact was fetched or executed, no analysis was rerun, and no "
    "decision is carried forward. Full owning decision-event history is not reconstructed."
)
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class HistoricalAnalysisUnavailable(ValueError):
    """A selected retained analysis no longer matches its saved record."""


class HistoricalAnalysisSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    state_fingerprint: Fingerprint
    history_index: Annotated[StrictInt, Field(ge=0)]
    analysis_fingerprint: Fingerprint


def historical_analysis_fingerprint(bundle: ReviewBundle) -> str:
    """Bind full validated recorded data, including its producer and known/unknown revision."""
    validated = validated_review_bundle(bundle)
    return sha256(validated.model_dump_json().encode("utf-8")).hexdigest()


class HistoricalAnalysisReport(BaseModel):
    """Historical-only handoff; the producer and current validator stay distinct."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    report_kind: Literal["scopeproof_historical_analysis"]
    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    boundary: Literal[HISTORICAL_ANALYSIS_BOUNDARY]
    selection: HistoricalAnalysisSelection
    analysis: ReviewBundle
    validation_tool_version: str
    validation_ruleset_version: str
    validation_source_identity: CoreSourceIdentity

    @model_validator(mode="before")
    @classmethod
    def _require_recorded_producer(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(value.get("analysis"), dict):
            review = value["analysis"].get("review")
            if isinstance(review, dict) and any(
                field not in review for field in ("tool_version", "ruleset_version")
            ):
                raise ValueError("historical report requires explicit recorded producer fields")
        return value

    @model_validator(mode="after")
    def _historical_identity(self) -> HistoricalAnalysisReport:
        if self.analysis.review.review_id != self.selection.review_id:
            raise ValueError("historical analysis must match the selected owning record")
        if historical_analysis_fingerprint(self.analysis) != self.selection.analysis_fingerprint:
            raise ValueError("historical analysis fingerprint does not match recorded facts")
        if (
            self.validation_tool_version != __version__
            or self.validation_ruleset_version != RULESET_VERSION
            or self.validation_source_identity != current_core_source_identity()
        ):
            raise ValueError("historical report validation identity differs from installed policy")
        return self


def _selected_bundle(state: ReviewState, history_index: int) -> ReviewBundle:
    if type(history_index) is not int or not 0 <= history_index < len(state.analysis_history):
        raise HistoricalAnalysisUnavailable("selected retained analysis is unavailable")
    return state.analysis_history[history_index]


def _require_owner(state: ReviewState, review_id: str) -> None:
    if state.review.review_id != review_id:
        raise HistoricalAnalysisUnavailable("saved filename and historical owner identity differ")


def prepare_historical_analysis(
    store: JsonReviewStore, state: ReviewState, history_index: int,
) -> HistoricalAnalysisSelection:
    """Apply one explicit retained position only if the entire opened record is saved."""
    state = validated_review_state(state)
    _selected_bundle(state, history_index)
    expected = store.state_fingerprint(state)
    with store.locked_load(state.review.review_id) as saved:
        _require_owner(saved, state.review.review_id)
        if store.state_fingerprint(saved) != expected:
            raise HistoricalAnalysisUnavailable("saved review changed; reopen and select again")
        return HistoricalAnalysisSelection(
            review_id=state.review.review_id, state_fingerprint=expected,
            history_index=history_index,
            analysis_fingerprint=historical_analysis_fingerprint(
                _selected_bundle(saved, history_index)
            ),
        )


@contextmanager
def locked_historical_analysis(
    store: JsonReviewStore, selection: HistoricalAnalysisSelection,
) -> Iterator[HistoricalAnalysisReport]:
    """Recheck saved truth and hold its existing mutation lock through the consumer."""
    selection = HistoricalAnalysisSelection.model_validate(selection.model_dump(mode="python"))
    with store.locked_load(selection.review_id) as saved:
        _require_owner(saved, selection.review_id)
        if store.state_fingerprint(saved) != selection.state_fingerprint:
            raise HistoricalAnalysisUnavailable("saved history changed; reopen and select again")
        analysis = _selected_bundle(saved, selection.history_index)
        if historical_analysis_fingerprint(analysis) != selection.analysis_fingerprint:
            raise HistoricalAnalysisUnavailable("selected historical analysis changed")
        yield HistoricalAnalysisReport(
            report_kind="scopeproof_historical_analysis", schema_version=1,
            boundary=HISTORICAL_ANALYSIS_BOUNDARY, selection=selection.model_copy(deep=True),
            analysis=analysis.model_copy(deep=True), validation_tool_version=__version__,
            validation_ruleset_version=RULESET_VERSION,
            validation_source_identity=current_core_source_identity(),
        )
