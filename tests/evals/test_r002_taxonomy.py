"""Deterministic, post-hoc R-002 miss-taxonomy contracts."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import scopeproof_core.evals.r002_taxonomy as taxonomy_module
from scopeproof_core.evals.r002_taxonomy import (
    R002MissCategory,
    R002MissEntry,
    R002MissTaxonomy,
    build_r002_miss_taxonomy,
    classify_r002_miss,
    main,
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


def test_empty_taxonomy_build_is_hash_bound_and_keeps_all_categories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = object()
    criteria = object()
    labels = SimpleNamespace(labels=[])
    hashes = iter(("0" * 64, "1" * 64, "2" * 64))
    monkeypatch.setattr(taxonomy_module, "load_source_manifest", lambda _: manifest)
    monkeypatch.setattr(
        taxonomy_module,
        "load_confirmed_criteria",
        lambda _path, _manifest_hash: criteria,
    )
    monkeypatch.setattr(
        taxonomy_module,
        "load_confirmed_labels",
        lambda _path, _manifest_hash, _criteria_hash: labels,
    )
    monkeypatch.setattr(taxonomy_module, "canonical_sha256", lambda _: next(hashes))
    monkeypatch.setattr(taxonomy_module, "_prepare_run_cases", lambda **_: ())

    result = build_r002_miss_taxonomy(
        pack_root=tmp_path / "pack",
        cache_root=tmp_path / "cache",
    )

    assert result.misses == ()
    assert result.source_manifest_sha256 == "0" * 64
    assert result.criteria_set_sha256 == "1" * 64
    assert result.candidate_label_set_sha256 == "2" * 64
    assert result.category_counts == {category: 0 for category in R002MissCategory}


def test_taxonomy_cli_emits_canonical_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    payload = R002MissTaxonomy(
        source_manifest_sha256="0" * 64,
        criteria_set_sha256="1" * 64,
        candidate_label_set_sha256="2" * 64,
        misses=(),
        category_counts={category: 0 for category in R002MissCategory},
    )
    captured: dict[str, Path] = {}

    def fake_build(*, pack_root: Path, cache_root: Path) -> R002MissTaxonomy:
        captured.update(pack_root=pack_root, cache_root=cache_root)
        return payload

    monkeypatch.setattr(taxonomy_module, "build_r002_miss_taxonomy", fake_build)

    assert main(
        [
            "--pack-root",
            str(tmp_path / "pack"),
            "--cache-dir",
            str(tmp_path / "cache"),
        ]
    ) == 0

    assert captured == {
        "pack_root": tmp_path / "pack",
        "cache_root": tmp_path / "cache",
    }
    assert json.loads(capsysbinary.readouterr().out) == payload.model_dump(mode="json")
