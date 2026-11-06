"""Read-only differences between recorded requirements, never evidence equivalence."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    computed_field,
    model_validator,
)

from scopeproof_core.build_identity import CoreSourceIdentity, current_core_source_identity
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.reviews.historical_analysis import (
    Fingerprint,
    HistoricalAnalysisSelection,
    historical_analysis_fingerprint,
)
from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    RULESET_VERSION,
    CriteriaSourceProvenance,
    Criterion,
    LocalReviewId,
    ReviewBundle,
    ReviewState,
    normalized_criteria_sha256,
    source_text_sha256,
)
from scopeproof_core.storage.json_store import JsonReviewStore
from scopeproof_core.version import __version__

CRITERIA_COMPARISON_BOUNDARY = (
    "Recorded requirements only, not evidence comparison or current-head verification. "
    "Criterion IDs are recorded keys, not semantic equivalence or continuity. Saved confirmation "
    "and attribution are asserted, not authenticated; missing provenance remains unknown. "
    "Unsaved drafts are excluded. No evidence or decision is carried forward, no criteria are "
    "confirmed, and no acceptance or gate is changed. No source was fetched or executed."
)


def _complete(value: object, model: type[BaseModel]) -> dict:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if not isinstance(value, dict) or set(value) != set(model.model_fields):
        raise ValueError("criteria comparison requires complete explicit recorded fields")
    return value


class CriteriaSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    head_sha: str = Field(min_length=1)
    revision_number: StrictInt | Literal["unknown"]
    confirmed: StrictBool
    source_text: str = Field(min_length=1)
    criteria: list[Criterion]
    source_provenance: CriteriaSourceProvenance | None

    @model_validator(mode="before")
    @classmethod
    def _recorded_fields(cls, value: object) -> object:
        value = dict(_complete(value, cls))
        if not isinstance(value["criteria"], list):
            raise ValueError("criteria comparison requires an explicit ordered list")
        value["criteria"] = [_complete(item, Criterion) for item in value["criteria"]]
        if value["source_provenance"] is not None:
            value["source_provenance"] = _complete(
                value["source_provenance"], CriteriaSourceProvenance,
            )
        return value

    @model_validator(mode="after")
    def _criteria_identity(self) -> CriteriaSnapshot:
        if not self.head_sha.strip() or not self.source_text.strip() or (
            isinstance(self.revision_number, int) and self.revision_number <= 0
        ):
            raise ValueError("criteria snapshot requires recorded head, source and revision")
        ids = [item.criterion_id for item in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("criteria snapshot requires unique recorded criterion IDs")
        provenance = self.source_provenance
        if provenance is not None and (
            not self.confirmed
            or provenance.source_text_sha256 != source_text_sha256(self.source_text)
            or provenance.normalized_criteria_sha256 != normalized_criteria_sha256(self.criteria)
        ):
            raise ValueError("recorded provenance must match confirmed criteria and source")
        return self


def _fingerprint(snapshot: CriteriaSnapshot) -> str:
    snapshot = CriteriaSnapshot.model_validate(snapshot.model_dump(mode="python"))
    return sha256(snapshot.model_dump_json().encode("utf-8")).hexdigest()


class CriteriaComparisonSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    historical: HistoricalAnalysisSelection
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    previous_criteria_fingerprint: Fingerprint
    current_criteria_fingerprint: Fingerprint


class CriterionRecordChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str
    kind: Literal["only_previous", "only_current", "fields_changed", "identical"]
    previous: Criterion | None
    current: Criterion | None
    previous_position: int | None
    current_position: int | None
    changed_fields: list[str]


_DERIVED = {"criterion_changes", "source_text_changed", "source_provenance_changed",
            "criterion_order_changed"}


class RecordedCriteriaDiff(BaseModel):
    """Compare complete recorded requirements without comparing evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    previous: CriteriaSnapshot
    current: CriteriaSnapshot

    @model_validator(mode="before")
    @classmethod
    def _derived_fields(cls, value: object) -> object:
        if isinstance(value, dict):
            return {key: item for key, item in value.items() if key not in _DERIVED}
        return value

    @model_validator(mode="after")
    def _same_pull_request(self) -> RecordedCriteriaDiff:
        if (self.previous.repository.casefold(), self.previous.pr_number) != (
            self.current.repository.casefold(), self.current.pr_number,
        ):
            raise ValueError("criteria comparison requires the same pull request")
        return self

    @computed_field
    @property
    def criterion_changes(self) -> list[CriterionRecordChange]:
        previous = {item.criterion_id: (index, item)
                    for index, item in enumerate(self.previous.criteria, 1)}
        current = {item.criterion_id: (index, item)
                   for index, item in enumerate(self.current.criteria, 1)}
        rows = []
        for key in sorted(previous.keys() | current.keys()):
            old_position, old = previous.get(key, (None, None))
            new_position, new = current.get(key, (None, None))
            changed = sorted(
                field for field in Criterion.model_fields
                if old is not None and new is not None
                and getattr(old, field) != getattr(new, field)
            )
            kind = ("only_current" if old is None else "only_previous" if new is None
                    else "fields_changed" if changed else "identical")
            rows.append(CriterionRecordChange(
                criterion_id=key, kind=kind, previous=old, current=new,
                previous_position=old_position, current_position=new_position,
                changed_fields=changed,
            ))
        return rows

    @computed_field
    @property
    def source_text_changed(self) -> bool:
        return self.previous.source_text != self.current.source_text

    @computed_field
    @property
    def source_provenance_changed(self) -> bool:
        return self.previous.source_provenance != self.current.source_provenance

    @computed_field
    @property
    def criterion_order_changed(self) -> bool:
        shared = {item.criterion_id for item in self.previous.criteria} & {
            item.criterion_id for item in self.current.criteria
        }
        previous = [item.criterion_id for item in self.previous.criteria
                    if item.criterion_id in shared]
        current = [item.criterion_id for item in self.current.criteria
                   if item.criterion_id in shared]
        return previous != current


class CriteriaRevisionComparison(RecordedCriteriaDiff):
    report_kind: Literal["scopeproof_criteria_revision_comparison"]
    schema_version: StrictInt = Field(ge=1, le=1)
    boundary: Literal[CRITERIA_COMPARISON_BOUNDARY]
    selection: CriteriaComparisonSelection
    validation_tool_version: str
    validation_ruleset_version: str
    validation_source_identity: CoreSourceIdentity

    @model_validator(mode="after")
    def _bound_snapshots(self) -> CriteriaRevisionComparison:
        identity = (self.selection.historical.review_id,
                    self.selection.repository, self.selection.pr_number)
        if any((snapshot.review_id, snapshot.repository, snapshot.pr_number) != identity
               for snapshot in (self.previous, self.current)):
            raise ValueError("criteria snapshots must match their selected owning identity")
        if (
            _fingerprint(self.previous) != self.selection.previous_criteria_fingerprint
            or _fingerprint(self.current) != self.selection.current_criteria_fingerprint
        ):
            raise ValueError("criteria comparison snapshots differ from the selected saved facts")
        if self.current.revision_number == "unknown" or (
            self.previous.revision_number != "unknown"
            and self.previous.revision_number >= self.current.revision_number
        ):
            raise ValueError("retained criteria revision must precede the saved current revision")
        if (
            self.validation_tool_version != __version__
            or self.validation_ruleset_version != RULESET_VERSION
            or self.validation_source_identity != current_core_source_identity()
        ):
            raise ValueError("criteria comparison validation identity differs from policy")
        return self


def analysis_criteria_snapshot(bundle: ReviewBundle) -> CriteriaSnapshot:
    """Project a selected analysis's recorded criteria and source metadata."""
    return CriteriaSnapshot(
        review_id=bundle.review.review_id, repository=bundle.review.repository,
        pr_number=bundle.review.pr_number,
        head_sha=bundle.review.head_sha, revision_number=bundle.criteria_revision_number,
        confirmed=bundle.review.criteria_confirmed, source_text=bundle.source_text,
        criteria=[item.model_copy(deep=True) for item in bundle.criteria],
        source_provenance=bundle.review.criteria_source_provenance,
    )


def _snapshots(state: ReviewState, index: int) -> tuple[CriteriaSnapshot, CriteriaSnapshot]:
    if type(index) is not int or not 0 <= index < len(state.analysis_history):
        raise ValueError("selected retained criteria are unavailable")
    revision = state.criteria_revision
    return analysis_criteria_snapshot(state.analysis_history[index]), CriteriaSnapshot(
        review_id=state.review.review_id, repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha, revision_number=revision.number,
        confirmed=revision.confirmed, source_text=revision.source_text,
        criteria=[item.model_copy(deep=True) for item in revision.criteria],
        source_provenance=revision.source_provenance,
    )


def _selection(state: ReviewState, index: int) -> CriteriaComparisonSelection:
    previous, current = _snapshots(state, index)
    return CriteriaComparisonSelection(
        repository=state.review.repository, pr_number=state.review.pr_number,
        historical=HistoricalAnalysisSelection(
            review_id=state.review.review_id,
            state_fingerprint=JsonReviewStore.state_fingerprint(state), history_index=index,
            analysis_fingerprint=historical_analysis_fingerprint(state.analysis_history[index]),
        ), previous_criteria_fingerprint=_fingerprint(previous),
        current_criteria_fingerprint=_fingerprint(current),
    )


def prepare_criteria_comparison(
    store: JsonReviewStore, state: ReviewState, history_index: int,
) -> CriteriaComparisonSelection:
    state = validated_review_state(state)
    expected = _selection(state, history_index)
    with store.locked_load(state.review.review_id) as saved:
        if saved.review.review_id != state.review.review_id or _selection(
            saved, history_index,
        ) != expected:
            raise ValueError("saved criteria changed; reopen and explicitly select again")
        return expected


@contextmanager
def locked_criteria_comparison(
    store: JsonReviewStore, selection: CriteriaComparisonSelection,
) -> Iterator[CriteriaRevisionComparison]:
    selection = CriteriaComparisonSelection.model_validate(selection.model_dump(mode="python"))
    historical = selection.historical
    with store.locked_load(historical.review_id) as saved:
        if saved.review.review_id != historical.review_id or _selection(
            saved, historical.history_index,
        ) != selection:
            raise ValueError("saved requirements changed; reopen and explicitly select again")
        previous, current = _snapshots(saved, historical.history_index)
        yield CriteriaRevisionComparison(
            report_kind="scopeproof_criteria_revision_comparison", schema_version=1,
            boundary=CRITERIA_COMPARISON_BOUNDARY, selection=selection.model_copy(deep=True),
            previous=previous.model_copy(deep=True), current=current.model_copy(deep=True),
            validation_tool_version=__version__, validation_ruleset_version=RULESET_VERSION,
            validation_source_identity=current_core_source_identity(),
        )
