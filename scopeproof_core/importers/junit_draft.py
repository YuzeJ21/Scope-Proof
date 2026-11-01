"""Session-only explicit JUnit mappings, bound to complete review and local bytes."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.importers.junit import (
    JUnitMappingSelection,
    build_junit_evidence_import,
    parse_junit_artifact,
)
from scopeproof_core.schemas.models import JUnitEvidenceImport, ReviewState
from scopeproof_core.storage.json_store import JsonReviewStore

Fingerprint = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]


class JUnitMappingDraft(BaseModel):
    """No raw XML, saved-import edits, timestamps or implied runtime verification."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    state_fingerprint: Fingerprint
    artifact_sha256: Fingerprint
    selections: tuple[JUnitMappingSelection, ...] = Field(max_length=5_000)

    @model_validator(mode="after")
    def _canonical_selectors(self) -> JUnitMappingDraft:
        pairs = []
        for item in self.selections:
            validated = JUnitMappingSelection.model_validate(item.model_dump(mode="python"))
            if validated != item:
                raise ValueError("draft selectors must already be normalized")
            pairs.append((item.criterion_id, item.scope_id))
        if pairs != sorted(set(pairs)):
            raise ValueError("draft selectors must be canonical unique pairs")
        return self


def new_junit_mapping_draft(state: ReviewState, artifact_bytes: bytes) -> JUnitMappingDraft:
    state = validated_review_state(state)
    if (
        state.bundle is None or not state.criteria_revision.confirmed
        or not state.review.criteria_confirmed or state.review.criteria_source_provenance is None
        or re.fullmatch(r"[0-9a-f]{40}", state.review.head_sha) is None
    ):
        raise ValueError(
            "JUnit draft requires confirmed active criteria, provenance and an exact head"
        )
    parsed = parse_junit_artifact(artifact_bytes)
    return JUnitMappingDraft(
        state_fingerprint=JsonReviewStore.state_fingerprint(state),
        artifact_sha256=parsed.artifact_sha256, selections=(),
    )


def _validated_context(
    state: ReviewState, artifact_bytes: bytes, draft: JUnitMappingDraft,
) -> JUnitMappingDraft:
    draft = JUnitMappingDraft.model_validate(draft.model_dump(mode="python"))
    current = new_junit_mapping_draft(state, artifact_bytes)
    if (draft.state_fingerprint, draft.artifact_sha256) != (
        current.state_fingerprint, current.artifact_sha256,
    ):
        raise ValueError("JUnit mapping draft changed; explicitly stage the mappings again")
    return draft


def extend_junit_mapping_draft(
    state: ReviewState,
    artifact_bytes: bytes,
    draft: JUnitMappingDraft,
    selections: list[JUnitMappingSelection],
    *,
    importer: str,
) -> JUnitMappingDraft:
    draft = _validated_context(state, artifact_bytes, draft)
    if not selections:
        raise ValueError("select a criterion and at least one JUnit scope to stage")
    incoming = [
        JUnitMappingSelection.model_validate(item.model_dump(mode="python")) for item in selections
    ]
    pairs = sorted({(item.criterion_id, item.scope_id) for item in (*draft.selections, *incoming)})
    candidate = JUnitMappingDraft(
        state_fingerprint=draft.state_fingerprint, artifact_sha256=draft.artifact_sha256,
        selections=tuple(JUnitMappingSelection(criterion_id=criterion, scope_id=scope)
                         for criterion, scope in pairs),
    )
    # Existing builder owns scope resolution, overlap, duplicate-artifact and import policy.
    build_drafted_junit_import(state, artifact_bytes, candidate, importer=importer)
    return candidate


def remove_junit_mapping_criterion(
    state: ReviewState, artifact_bytes: bytes, draft: JUnitMappingDraft, criterion_id: str,
) -> JUnitMappingDraft:
    draft = _validated_context(state, artifact_bytes, draft)
    if criterion_id not in {item.criterion_id for item in draft.selections}:
        raise ValueError("selected criterion has no staged JUnit mapping")
    return JUnitMappingDraft(
        state_fingerprint=draft.state_fingerprint, artifact_sha256=draft.artifact_sha256,
        selections=tuple(item for item in draft.selections if item.criterion_id != criterion_id),
    )


def build_drafted_junit_import(
    state: ReviewState,
    artifact_bytes: bytes,
    draft: JUnitMappingDraft,
    *,
    importer: str,
    limitations: list[str] | None = None,
) -> JUnitEvidenceImport:
    draft = _validated_context(state, artifact_bytes, draft)
    return build_junit_evidence_import(
        state, artifact_bytes, list(draft.selections), importer=importer, limitations=limitations,
    )
