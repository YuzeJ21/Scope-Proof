"""Deterministic, post-hoc R-002 miss-taxonomy contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scopeproof_core.evals.r002_taxonomy import (
    R002MissCategory,
    R002MissEntry,
    R002MissTaxonomy,
    classify_r002_miss,
)
from scopeproof_core.schemas.models import RetrievalOutcome


@pytest.mark.parametrize(
    ("outcome", "below_threshold_count", "expected"),
    [
        (
            RetrievalOutcome.NO_SEARCHABLE_TERMS,
            0,
            R002MissCategory.NO_SEARCHABLE_TERM,
        ),
        (
            RetrievalOutcome.EXACT_IDENTIFIER_NOT_FOUND,
            0,
            R002MissCategory.EXACT_IDENTIFIER_ABSENT,
        ),
        (
            RetrievalOutcome.NO_INSPECTABLE_LINES,
            0,
            R002MissCategory.WRONG_OR_UNSUPPORTED_PATH,
        ),
        (
            RetrievalOutcome.NO_TERM_OVERLAP,
            0,
            R002MissCategory.UNSUPPORTED_EVIDENCE_FORM,
        ),
        (
            RetrievalOutcome.BELOW_RELEVANCE_THRESHOLD,
            1,
            R002MissCategory.THRESHOLD_REJECTION,
        ),
        (
            RetrievalOutcome.CANDIDATES_FOUND,
            2,
            R002MissCategory.THRESHOLD_REJECTION,
        ),
        (
            RetrievalOutcome.CANDIDATES_FOUND,
            0,
            R002MissCategory.INTENTIONALLY_UNRESOLVED,
        ),
    ],
)
def test_miss_classification_is_bounded_and_deterministic(
    outcome: RetrievalOutcome,
    below_threshold_count: int,
    expected: R002MissCategory,
) -> None:
    assert (
        classify_r002_miss(
            outcome=outcome,
            below_threshold_count=below_threshold_count,
        )
        is expected
    )


def test_taxonomy_rejects_duplicate_or_non_miss_entries() -> None:
    entry = R002MissEntry(
        case_id="R002-001",
        criterion_id="AC-01",
        retrieval_outcome=RetrievalOutcome.BELOW_RELEVANCE_THRESHOLD,
        category=R002MissCategory.THRESHOLD_REJECTION,
        searched_term_count=5,
        inspectable_line_count=10,
        term_overlap_line_count=3,
        below_threshold_line_count=3,
        accepted_candidate_count=0,
        owner_label_relevant_candidate_count=2,
        retrieved_owner_label_relevant_candidate_count=0,
        reason_code="relevant_lines_rejected_by_current_thresholds",
    )
    payload = {
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "candidate_label_set_sha256": "2" * 64,
        "misses": [entry.model_dump(mode="json"), entry.model_dump(mode="json")],
    }

    with pytest.raises(ValidationError, match="miss identities must be unique"):
        R002MissTaxonomy.model_validate(payload)

    invalid = entry.model_copy(
        update={"retrieved_owner_label_relevant_candidate_count": 1}
    )
    with pytest.raises(
        ValidationError,
        match="taxonomy entries must be owner-labelled candidate misses",
    ):
        R002MissTaxonomy.model_validate(
            {**payload, "misses": [invalid.model_dump(mode="json")]}
        )


def test_frozen_taxonomy_is_hash_bound_and_preserves_research_boundary() -> None:
    root = Path(__file__).parents[2]
    payload = json.loads(
        (
            root
            / "docs"
            / "research"
            / "r002-swebench-verified"
            / "miss-taxonomy.json"
        ).read_text(encoding="utf-8")
    )
    taxonomy = R002MissTaxonomy.model_validate(payload)

    assert taxonomy.pack_id == "R-002"
    assert taxonomy.classification == "public_engineering_research"
    assert taxonomy.does_not_advance_stage_1 is True
    assert taxonomy.frozen_r002_inputs_modified is False
    assert taxonomy.frozen_r002_result_rescored is False
    assert len(taxonomy.misses) == 15
    assert taxonomy.category_counts[R002MissCategory.THRESHOLD_REJECTION] == 14
    assert taxonomy.category_counts[R002MissCategory.UNSUPPORTED_EVIDENCE_FORM] == 1
    assert sum(taxonomy.category_counts.values()) == len(taxonomy.misses)

    result = json.loads(
        (
            root / "docs" / "research" / "r002-swebench-verified" / "result.json"
        ).read_text(encoding="utf-8")
    )
    assert taxonomy.source_manifest_sha256 == result["source_manifest_sha256"]
    assert taxonomy.criteria_set_sha256 == result["criteria_set_sha256"]
    assert taxonomy.candidate_label_set_sha256 == result["candidate_label_set_sha256"]
