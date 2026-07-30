"""Derive a redacted, deterministic miss taxonomy from frozen R-002 inputs."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scopeproof_core.evals.r002_cache import R002Cache
from scopeproof_core.evals.r002_diff import parsed_case_to_changed_files
from scopeproof_core.evals.r002_models import (
    R002CaseId,
    Sha256,
    canonical_json_bytes,
    canonical_sha256,
    load_confirmed_criteria,
    load_confirmed_labels,
    load_source_manifest,
)
from scopeproof_core.evals.r002_runner import _prepare_run_cases
from scopeproof_core.evals.r002_verify import verify_evidence_reference
from scopeproof_core.retrieval.engine import retrieve_evidence_with_diagnostics
from scopeproof_core.schemas.models import (
    CheckState,
    PullRequestSnapshot,
    RetrievalOutcome,
)

R002CriterionId = Annotated[str, Field(pattern=r"^AC-(0[1-9]|1[0-6])$")]


class R002MissCategory(StrEnum):
    """Bounded R-002 miss categories; unused categories remain explicit zeroes."""

    NO_SEARCHABLE_TERM = "no_searchable_term"
    EXACT_IDENTIFIER_ABSENT = "exact_identifier_absent"
    WRONG_OR_UNSUPPORTED_PATH = "wrong_or_unsupported_path"
    UNCHANGED_FILE_DEPENDENCY = "unchanged_file_dependency"
    CROSS_FILE_BEHAVIOR = "cross_file_behavior"
    INSUFFICIENT_LOCAL_CONTEXT = "insufficient_local_context"
    UNSUPPORTED_EVIDENCE_FORM = "unsupported_evidence_form"
    THRESHOLD_REJECTION = "threshold_rejection"
    AMBIGUOUS_BENCHMARK_LABEL = "ambiguous_benchmark_label"
    INTENTIONALLY_UNRESOLVED = "intentionally_unresolved"


_CATEGORY_REASON_CODES = {
    R002MissCategory.NO_SEARCHABLE_TERM: "criterion_has_no_searchable_terms",
    R002MissCategory.EXACT_IDENTIFIER_ABSENT: "required_exact_identifier_not_found",
    R002MissCategory.WRONG_OR_UNSUPPORTED_PATH: "no_inspectable_changed_lines",
    R002MissCategory.UNSUPPORTED_EVIDENCE_FORM: (
        "owner_labelled_lines_have_no_lexical_term_overlap"
    ),
    R002MissCategory.THRESHOLD_REJECTION: (
        "relevant_lines_rejected_by_current_thresholds"
    ),
    R002MissCategory.INTENTIONALLY_UNRESOLVED: (
        "retrieval_miss_requires_bounded_follow_up"
    ),
}


def classify_r002_miss(
    *,
    outcome: RetrievalOutcome,
    below_threshold_count: int,
) -> R002MissCategory:
    """Map only demonstrated retrieval facts; do not infer semantic root causes."""
    if below_threshold_count:
        return R002MissCategory.THRESHOLD_REJECTION
    if outcome is RetrievalOutcome.NO_SEARCHABLE_TERMS:
        return R002MissCategory.NO_SEARCHABLE_TERM
    if outcome is RetrievalOutcome.EXACT_IDENTIFIER_NOT_FOUND:
        return R002MissCategory.EXACT_IDENTIFIER_ABSENT
    if outcome is RetrievalOutcome.NO_INSPECTABLE_LINES:
        return R002MissCategory.WRONG_OR_UNSUPPORTED_PATH
    if outcome is RetrievalOutcome.NO_TERM_OVERLAP:
        return R002MissCategory.UNSUPPORTED_EVIDENCE_FORM
    return R002MissCategory.INTENTIONALLY_UNRESOLVED


class R002MissEntry(BaseModel):
    """One owner-labelled criterion for which retrieval found no relevant line."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: R002CaseId
    criterion_id: R002CriterionId
    retrieval_outcome: RetrievalOutcome
    category: R002MissCategory
    searched_term_count: int = Field(ge=0)
    inspectable_line_count: int = Field(ge=0)
    term_overlap_line_count: int = Field(ge=0)
    below_threshold_line_count: int = Field(ge=0)
    accepted_candidate_count: int = Field(ge=0)
    owner_label_relevant_candidate_count: int = Field(gt=0)
    retrieved_owner_label_relevant_candidate_count: int = Field(ge=0)
    reason_code: str = Field(min_length=1, max_length=96)

    @model_validator(mode="after")
    def validate_classification(self) -> Self:
        expected = classify_r002_miss(
            outcome=self.retrieval_outcome,
            below_threshold_count=self.below_threshold_line_count,
        )
        if self.category is not expected:
            raise ValueError("miss category must match deterministic retrieval facts")
        if self.reason_code != _CATEGORY_REASON_CODES[expected]:
            raise ValueError("miss reason code must match deterministic category")
        if self.retrieved_owner_label_relevant_candidate_count:
            raise ValueError(
                "taxonomy entries must be owner-labelled candidate misses"
            )
        return self


class R002MissTaxonomy(BaseModel):
    """Hash-bound engineering analysis that never changes the frozen R-002 score."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pack_id: str = Field(default="R-002", pattern=r"^R-002$")
    classification: str = Field(default="public_engineering_research")
    does_not_advance_stage_1: bool = True
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_label_set_sha256: Sha256
    frozen_r002_inputs_modified: bool = False
    frozen_r002_result_rescored: bool = False
    misses: tuple[R002MissEntry, ...]
    category_counts: dict[R002MissCategory, int] = Field(default_factory=dict)
    limitations: tuple[str, ...] = (
        "This post-hoc taxonomy explains frozen engineering-benchmark misses only.",
        "It is not an accuracy claim, customer validation, or a basis for retuning R-002.",
        "No target-repository code was executed.",
        "Categories use deterministic retrieval facts and benchmark-owner labels.",
    )

    @model_validator(mode="after")
    def validate_taxonomy(self) -> Self:
        identities = [(item.case_id, item.criterion_id) for item in self.misses]
        if len(identities) != len(set(identities)):
            raise ValueError("miss identities must be unique")
        if identities != sorted(identities):
            raise ValueError("miss entries must use canonical identity order")
        expected_counts = Counter(item.category for item in self.misses)
        normalized_counts = {
            category: self.category_counts.get(category, 0)
            for category in R002MissCategory
        }
        if set(self.category_counts) != set(R002MissCategory):
            raise ValueError("category counts must include every bounded category")
        if normalized_counts != {
            category: expected_counts[category] for category in R002MissCategory
        }:
            raise ValueError("category counts must match miss entries")
        if (
            self.classification != "public_engineering_research"
            or not self.does_not_advance_stage_1
            or self.frozen_r002_inputs_modified
            or self.frozen_r002_result_rescored
        ):
            raise ValueError("R-002 taxonomy research boundary must remain fixed")
        return self


def build_r002_miss_taxonomy(
    *,
    pack_root: Path,
    cache_root: Path,
) -> R002MissTaxonomy:
    """Recompute diagnostics against the frozen cohort without changing its result."""
    manifest = load_source_manifest(pack_root / "source_manifest.json")
    manifest_hash = canonical_sha256(manifest)
    criteria = load_confirmed_criteria(pack_root / "criteria.json", manifest_hash)
    criteria_hash = canonical_sha256(criteria)
    labels = load_confirmed_labels(
        pack_root / "candidate_labels.json",
        manifest_hash,
        criteria_hash,
    )
    label_hash = canonical_sha256(labels)
    cache = R002Cache(cache_root)
    prepared = _prepare_run_cases(
        manifest=manifest,
        criteria=criteria,
        cache=cache,
    )
    relevant_keys = {label.key for label in labels.labels if label.relevant}
    misses: list[R002MissEntry] = []
    for item in prepared:
        snapshot = PullRequestSnapshot(
            repository=item.case.repository,
            pr_number=item.case.pr_number,
            title=f"R-002 {item.case.case_id}",
            description="",
            html_url=item.case.pr_url,
            base_sha=item.case.dataset_base_commit,
            head_sha=item.case.verified_pr_head_sha,
            check_state=CheckState.UNAVAILABLE,
            files=parsed_case_to_changed_files(item.parsed),
        )
        result = retrieve_evidence_with_diagnostics(
            snapshot,
            list(item.criterion_case.criteria),
        )
        retrieved_keys = {
            verify_evidence_reference(
                case=item.case,
                evidence=evidence,
                verified_lines=item.verified,
            )
            for evidence in result.evidence
        }
        for diagnostic in result.diagnostics:
            owner_relevant = {
                key
                for key in relevant_keys
                if key.case_id == item.case.case_id
                and key.criterion_id == diagnostic.criterion_id
            }
            retrieved_relevant = owner_relevant & retrieved_keys
            if not owner_relevant or retrieved_relevant:
                continue
            category = classify_r002_miss(
                outcome=diagnostic.outcome,
                below_threshold_count=diagnostic.below_threshold_line_count,
            )
            misses.append(
                R002MissEntry(
                    case_id=item.case.case_id,
                    criterion_id=diagnostic.criterion_id,
                    retrieval_outcome=diagnostic.outcome,
                    category=category,
                    searched_term_count=len(diagnostic.searched_terms),
                    inspectable_line_count=diagnostic.inspectable_line_count,
                    term_overlap_line_count=diagnostic.term_overlap_line_count,
                    below_threshold_line_count=diagnostic.below_threshold_line_count,
                    accepted_candidate_count=diagnostic.accepted_candidate_count,
                    owner_label_relevant_candidate_count=len(owner_relevant),
                    retrieved_owner_label_relevant_candidate_count=0,
                    reason_code=_CATEGORY_REASON_CODES[category],
                )
            )
    ordered = tuple(sorted(misses, key=lambda item: (item.case_id, item.criterion_id)))
    counts = Counter(item.category for item in ordered)
    return R002MissTaxonomy(
        source_manifest_sha256=manifest_hash,
        criteria_set_sha256=criteria_hash,
        candidate_label_set_sha256=label_hash,
        misses=ordered,
        category_counts={
            category: counts[category] for category in R002MissCategory
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit the deterministic redacted R-002 miss taxonomy."
    )
    parser.add_argument("--pack-root", type=Path, default=Path("evals/r002"))
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".scopeproof/research/r002"),
    )
    args = parser.parse_args(argv)
    result = build_r002_miss_taxonomy(
        pack_root=args.pack_root,
        cache_root=args.cache_dir,
    )
    sys.stdout.buffer.write(canonical_json_bytes(result) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
