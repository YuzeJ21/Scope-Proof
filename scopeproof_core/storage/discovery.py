"""Bounded, session-only saved metadata; never gate or source verification."""

from __future__ import annotations

import json
from hashlib import sha256

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    LocalReviewId,
    ReviewState,
    SavedReviewListing,
)
from scopeproof_core.storage.json_store import JsonReviewStore

DISCOVERY_PAGE_SIZE = 10
MAX_DISCOVERY_RECORD_BYTES = 1024 * 1024
MAX_DISCOVERY_QUERY_CHARS = 200


class SavedReviewMetadata(BaseModel):
    """Fully validated saved facts, not current source, compatibility or readiness."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN, max_length=255)
    pr_number: StrictInt = Field(gt=0)
    head_sha: str = Field(min_length=1, max_length=256)
    criteria_revision_number: StrictInt = Field(gt=0)
    criteria_confirmed: StrictBool
    has_active_analysis: StrictBool
    retained_history_count: StrictInt = Field(ge=0)

    @field_validator("head_sha")
    @classmethod
    def printable_head(cls, value: str) -> str:
        if not value.strip() or not value.isprintable():
            raise ValueError("discovery head must be bounded printable saved metadata")
        return value


class SavedReviewDiscoveryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    review_id: LocalReviewId
    metadata: SavedReviewMetadata | None = None

    @model_validator(mode="after")
    def metadata_owner(self) -> SavedReviewDiscoveryEntry:
        if self.metadata is not None and self.metadata.review_id != self.review_id:
            raise ValueError("discovery metadata must match its candidate record ID")
        return self


class SavedReviewDiscoveryPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")

    page_index: StrictInt = Field(ge=0)
    total_review_count: StrictInt = Field(ge=0)
    candidate_ids_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: tuple[SavedReviewDiscoveryEntry, ...] = Field(max_length=DISCOVERY_PAGE_SIZE)

    @model_validator(mode="after")
    def complete_window(self) -> SavedReviewDiscoveryPage:
        start = self.page_index * DISCOVERY_PAGE_SIZE
        if self.total_review_count == 0:
            if self.page_index or self.entries:
                raise ValueError("empty discovery has only page zero")
            return self
        if start >= self.total_review_count:
            raise ValueError("discovery page is outside saved candidate IDs")
        if len(self.entries) != min(DISCOVERY_PAGE_SIZE, self.total_review_count - start):
            raise ValueError("discovery page must retain its complete candidate window")
        ids = [entry.review_id for entry in self.entries]
        if ids != sorted(set(ids)):
            raise ValueError("discovery page IDs must be unique and sorted")
        return self


def saved_review_ids_fingerprint(ids: list[str]) -> str:
    listing = SavedReviewListing(review_ids=ids, storage_dir="local discovery")
    return sha256(json.dumps(listing.review_ids, separators=(",", ":")).encode()).hexdigest()


def _metadata(state: ReviewState, review_id: str) -> SavedReviewMetadata:
    if state.review.review_id != review_id:
        raise ValueError("saved filename and owning review ID must match")
    return SavedReviewMetadata(
        review_id=review_id,
        state_fingerprint=JsonReviewStore.state_fingerprint(state),
        repository=state.review.repository,
        pr_number=state.review.pr_number,
        head_sha=state.review.head_sha,
        criteria_revision_number=state.criteria_revision.number,
        criteria_confirmed=state.criteria_revision.confirmed,
        has_active_analysis=state.bundle is not None,
        retained_history_count=len(state.analysis_history),
    )


def discover_saved_review_page(
    store: JsonReviewStore,
    *,
    page_index: int = 0,
) -> SavedReviewDiscoveryPage:
    if type(page_index) is not int or page_index < 0:
        raise ValueError("discovery page index must be a nonnegative integer")
    ids = store.list_review_ids()
    fingerprint = saved_review_ids_fingerprint(ids)
    start = page_index * DISCOVERY_PAGE_SIZE
    if start >= len(ids) and (ids or page_index):
        raise ValueError("discovery page is outside saved candidate IDs")
    entries = []
    for review_id in ids[start : start + DISCOVERY_PAGE_SIZE]:
        try:
            metadata = _metadata(
                store.load(review_id, max_bytes=MAX_DISCOVERY_RECORD_BYTES),
                review_id,
            )
        except (OSError, ValueError):
            metadata = None
        entries.append(SavedReviewDiscoveryEntry(review_id=review_id, metadata=metadata))
    return SavedReviewDiscoveryPage(
        page_index=page_index,
        total_review_count=len(ids),
        candidate_ids_fingerprint=fingerprint,
        entries=tuple(entries),
    )


def format_saved_review_label(entry: SavedReviewDiscoveryEntry) -> str:
    entry = SavedReviewDiscoveryEntry.model_validate(entry.model_dump(mode="python"))
    item = entry.metadata
    if item is None:
        return f"{entry.review_id} · saved details unavailable"
    return (
        f"{item.repository} · PR #{item.pr_number} · head {item.head_sha[:12]} · "
        f"criteria revision {item.criteria_revision_number} · {entry.review_id}"
    )


def matching_saved_review_ids(page: SavedReviewDiscoveryPage, query: str) -> list[str]:
    page = SavedReviewDiscoveryPage.model_validate(page.model_dump(mode="python"))
    if not isinstance(query, str) or len(query) > MAX_DISCOVERY_QUERY_CHARS:
        raise ValueError("saved detail query exceeds the 200-character limit")
    terms = query.casefold().split()
    matches = []
    for entry in page.entries:
        values = [entry.review_id]
        if entry.metadata is not None:
            item = entry.metadata
            values.extend(
                [
                    item.repository,
                    str(item.pr_number),
                    f"#{item.pr_number}",
                    item.head_sha,
                    str(item.criteria_revision_number),
                ]
            )
        searchable = " ".join(values)
        if all(term in searchable.casefold() for term in terms):
            matches.append(entry.review_id)
    return matches


def load_discovered_review(
    store: JsonReviewStore,
    review_id: str,
    *,
    expected_fingerprint: str | None = None,
) -> ReviewState:
    """Reopen fresh full validated truth only for the explicit ID/preview snapshot."""
    state = store.load(review_id)
    if state.review.review_id != review_id:
        raise ValueError("saved filename and owning review ID must match")
    if expected_fingerprint is not None and store.state_fingerprint(state) != expected_fingerprint:
        raise ValueError("saved details changed; refresh and select the review again")
    return state
