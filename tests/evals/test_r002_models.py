"""Strict R-002 persisted-contract tests."""

from __future__ import annotations

import inspect
import json
import warnings
from copy import deepcopy
from hashlib import sha256
from typing import get_origin

import pytest
from pydantic import ValidationError

import scopeproof_core.evals.r002_models as r002_models
from scopeproof_core.evals.r002_models import (
    R002AnnotationUniverse,
    R002CandidateLabelSet,
    R002CaseResult,
    R002CriteriaProposal,
    R002CriteriaSet,
    R002Metric,
    R002ParsedDiff,
    R002SourceError,
    R002SourceManifest,
    canonical_sha256,
    case_projection_sha256,
    load_confirmed_criteria,
    load_confirmed_labels,
    load_source_manifest,
    validate_r002_logical_path,
)


def test_source_manifest_requires_exact_research_boundary(r002_manifest_payload):
    manifest = R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))
    assert manifest.pack_id == "R-002"
    assert manifest.classification == "public_engineering_research"
    assert manifest.eligible_for_stage_1 is False
    assert manifest.does_not_advance_stage_1 is True
    assert manifest.target_repository_code_executed is False
    assert [case.case_id for case in manifest.cases] == [
        f"R002-{number:03d}" for number in range(1, 21)
    ]
    assert len({case.repository for case in manifest.cases}) == 12
    assert len(case_projection_sha256(manifest.cases)) == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("classification", "alpha"),
        ("eligible_for_stage_1", True),
        ("does_not_advance_stage_1", False),
        ("target_repository_code_executed", True),
    ],
)
def test_research_boundary_cannot_be_promoted(r002_manifest_payload, field, value):
    r002_manifest_payload[field] = value
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


def test_case_identity_binds_instance_repository_pr_and_url(r002_manifest_payload):
    r002_manifest_payload["cases"][0]["pr_url"] = "https://github.com/other/repo/pull/1"
    with pytest.raises(ValidationError, match="case identity fields disagree"):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


@pytest.mark.parametrize(
    "mutation", ["duplicate_instance", "duplicate_url", "bad_ids", "wrong_order"]
)
def test_manifest_rejects_duplicate_or_unstable_case_identity(r002_manifest_payload, mutation):
    cases = r002_manifest_payload["cases"]
    if mutation == "duplicate_instance":
        cases[1]["instance_id"] = cases[0]["instance_id"]
    elif mutation == "duplicate_url":
        cases[1]["pr_url"] = cases[0]["pr_url"]
    elif mutation == "bad_ids":
        cases[1]["case_id"] = "R002-099"
    else:
        r002_manifest_payload["cases"] = list(reversed(cases))
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


@pytest.mark.parametrize("case_count", [19, 21])
def test_manifest_requires_exactly_twenty_cases(r002_manifest_payload, case_count):
    if case_count == 19:
        r002_manifest_payload["cases"].pop()
    else:
        r002_manifest_payload["cases"].append(deepcopy(r002_manifest_payload["cases"][-1]))
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


def test_confirmed_criteria_reject_source_owner_confirmation(r002_criteria_payload):
    r002_criteria_payload["source_owner_confirmed"] = True
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))


@pytest.mark.parametrize("value", ["", ".", "..", "a/../b", "/absolute", "a\\b"])
def test_r002_logical_path_rejects_empty_current_parent_and_platform_paths(value):
    with pytest.raises(ValueError, match="invalid R-002 logical path"):
        validate_r002_logical_path(value)


def test_criteria_require_confirmed_complete_ordered_must_have_cases(r002_criteria_payload):
    r002_criteria_payload["benchmark_owner_confirmed"] = False
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))


@pytest.mark.parametrize(
    ("state", "numerator", "denominator", "value"),
    [("value", 0, 0, 0.0), ("not_applicable", 1, 1, None), ("value", 2, 1, 2.0)],
)
def test_metric_rejects_invalid_zero_denominator_representation(
    state, numerator, denominator, value
):
    with pytest.raises(ValidationError):
        R002Metric.model_validate(
            {"state": state, "numerator": numerator, "denominator": denominator, "value": value}
        )


def test_every_persisted_model_forbids_extra_fields(r002_manifest_payload):
    r002_manifest_payload["unexpected"] = "not allowed"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


def test_label_set_defers_expected_missing_derivation_to_the_confirmed_criteria_loader():
    payload = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "annotation_universe_sha256": "2" * 64,
        "annotation_count": 1,
        "benchmark_owner_confirmed": True,
        "labels": [
            {
                "key": {
                    "case_id": "R002-001",
                    "criterion_id": "AC-01",
                    "stream": "patch",
                    "path": "scopeproof.py",
                    "new_line_number": 1,
                    "normalized_line_sha256": "3" * 64,
                },
                "relevant": False,
                "reason_code": "unrelated_candidate",
            }
        ],
        "expected_missing": [],
    }
    assert R002CandidateLabelSet.model_validate_json(json.dumps(payload)).expected_missing == ()


def test_loader_rejects_structurally_valid_non_production_source(tmp_path, r002_manifest_payload):
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(r002_manifest_payload), encoding="utf-8")
    with pytest.raises(R002SourceError, match="source_pin_mismatch"):
        load_source_manifest(path)


def test_load_source_manifest_accepts_unmodified_approved_metadata(tmp_path):
    difficulties = {
        "R002-001": "15 min - 1 hour",
        "R002-002": "<15 min fix",
        "R002-003": "15 min - 1 hour",
        "R002-004": "15 min - 1 hour",
        "R002-005": "<15 min fix",
        "R002-006": "<15 min fix",
        "R002-007": "15 min - 1 hour",
        "R002-008": "<15 min fix",
        "R002-009": "<15 min fix",
        "R002-010": "<15 min fix",
        "R002-011": ">4 hours",
        "R002-012": "15 min - 1 hour",
        "R002-013": "15 min - 1 hour",
        "R002-014": "<15 min fix",
        "R002-015": "<15 min fix",
        "R002-016": "<15 min fix",
        "R002-017": "<15 min fix",
        "R002-018": "<15 min fix",
        "R002-019": "15 min - 1 hour",
        "R002-020": "15 min - 1 hour",
    }
    payload = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source": deepcopy(r002_models.R002_SOURCE),
        "cases": [
            {
                "case_id": case.case_id,
                "instance_id": case.repository.replace("/", "__") + f"-{case.pr_number}",
                "repository": case.repository,
                "pr_number": case.pr_number,
                "pr_url": f"https://github.com/{case.repository}/pull/{case.pr_number}",
                "dataset_base_commit": case.dataset_base_commit,
                "verified_pr_head_sha": case.head_sha,
                "row_index": case.row_index,
                "difficulty": difficulties[case.case_id],
                "row_sha256": case.row_sha256,
                "problem_statement_sha256": case.problem_statement_sha256,
                "patch_sha256": case.patch_sha256,
                "test_patch_sha256": case.test_patch_sha256,
            }
            for case in r002_models.R002_APPROVED_CASES
        ],
    }
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = load_source_manifest(path)
    assert manifest.source.model_dump(mode="json") == r002_models.R002_SOURCE
    assert case_projection_sha256(manifest.cases) == r002_models.R002_APPROVED_CASES_SHA256


def test_parsed_diff_rejects_marker_counts_and_unstable_paths():
    payload = {
        "stream": "patch",
        "files": [
            {
                "stream": "patch",
                "path": "b.py",
                "hunks": [
                    {
                        "hunk_id": 1,
                        "old_start": 1,
                        "old_count": 1,
                        "new_start": 1,
                        "new_count": 1,
                        "lines": [
                            {
                                "change_type": "added",
                                "old_line_number": 1,
                                "new_line_number": 1,
                                "content": "line",
                                "normalized_line_sha256": "0" * 64,
                            }
                        ],
                    }
                ],
                "additions": 0,
                "deletions": 0,
            }
        ],
        "file_count": 0,
        "hunk_count": 0,
        "diff_line_count": 0,
    }
    with pytest.raises(ValidationError):
        R002ParsedDiff.model_validate_json(json.dumps(payload))


def test_criteria_proposal_rejects_reversed_cases_and_duplicate_problem_hashes(
    r002_criteria_payload,
):
    proposal = deepcopy(r002_criteria_payload)
    proposal["benchmark_owner_confirmed"] = False
    proposal["cases"] = [
        {
            **case,
            "problem_statement": f"ScopeProof-authored fixture text {number}.",
            "problem_statement_sha256": sha256(
                f"ScopeProof-authored fixture text {number}.".encode()
            ).hexdigest(),
        }
        for number, case in enumerate(proposal["cases"], start=1)
    ]
    proposal["cases"].reverse()
    with pytest.raises(ValidationError):
        R002CriteriaProposal.model_validate_json(json.dumps(proposal))

    proposal["cases"].reverse()
    proposal["cases"][1]["problem_statement_sha256"] = proposal["cases"][0][
        "problem_statement_sha256"
    ]
    with pytest.raises(ValidationError):
        R002CriteriaProposal.model_validate_json(json.dumps(proposal))


def test_criteria_review_case_binds_utf8_problem_statement_hash(r002_criteria_payload):
    case = deepcopy(r002_criteria_payload["cases"][0])
    case["problem_statement"] = "évidence"
    case["problem_statement_sha256"] = sha256("évidence".encode()).hexdigest()
    assert r002_models.R002CriterionReviewCase.model_validate_json(
        json.dumps(case)
    ).problem_statement
    case["problem_statement"] = "changed"
    with pytest.raises(ValidationError, match="problem statement hash"):
        r002_models.R002CriterionReviewCase.model_validate_json(json.dumps(case))


def test_case_result_rejects_false_ready_and_non_static_success_signals():
    payload = {
        "case_id": "R002-001",
        "repository": "alpha/one",
        "pr_number": 1,
        "head_sha": "0" * 40,
        "criterion_count": 1,
        "annotation_candidate_count": 0,
        "retrieved_candidates": [],
        "missing_explanations": [],
        "gate_verdict": "ready",
        "gate_reason_codes": ["arbitrary"],
        "blocking_criteria": [],
        "conditional_criteria": [],
        "unresolved_criteria": [],
        "check_state": "passing",
        "ci_reason_code": "successful_check_runs",
        "runtime_evidence_count": 1,
        "resolution_count": 1,
        "final_acceptance": True,
        "separation_errors": 1,
        "reference_errors": 1,
        "limitations": ["arbitrary"],
    }
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("dataset_base_commit", "not-a-sha"),
        ("verified_pr_head_sha", "A" * 40),
        ("row_sha256", "0" * 63),
        ("problem_statement_sha256", "x" * 64),
        ("patch_sha256", "0" * 65),
        ("test_patch_sha256", "0" * 63),
        ("source.revision", "0" * 39),
        ("source.sha256", "f" * 63),
    ],
)
def test_manifest_rejects_malformed_git_and_hash_shapes(r002_manifest_payload, field, value):
    if field.startswith("source."):
        r002_manifest_payload["source"][field.removeprefix("source.")] = value
    else:
        r002_manifest_payload["cases"][0][field] = value
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


@pytest.mark.parametrize("mutation", ["eleven_repositories", "three_cases_for_repository"])
def test_manifest_rejects_repository_count_and_per_repository_bounds(
    r002_manifest_payload, mutation
):
    cases = r002_manifest_payload["cases"]
    target = cases[-1] if mutation == "eleven_repositories" else cases[-3]
    target["repository"] = "golf/one"
    target["instance_id"] = f"golf__one-{target['pr_number']}"
    target["pr_url"] = f"https://github.com/golf/one/pull/{target['pr_number']}"
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


@pytest.mark.parametrize(
    "mutation", ["zero", "seventeen", "no_must_have", "unordered", "incomplete"]
)
def test_criteria_reject_collection_size_order_priority_and_missing_serialized_fields(
    r002_criteria_payload, mutation
):
    criteria = r002_criteria_payload["cases"][0]["criteria"]
    if mutation == "zero":
        r002_criteria_payload["cases"][0]["criteria"] = []
    elif mutation == "seventeen":
        r002_criteria_payload["cases"][0]["criteria"] = criteria * 17
    elif mutation == "no_must_have":
        criteria[0]["priority"] = "should_have"
    elif mutation == "unordered":
        criteria[0]["criterion_id"] = "AC-02"
    else:
        del criteria[0]["required_evidence_level"]
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))


def test_every_persisted_r002_model_family_declares_extra_forbid():
    pending = list(r002_models.R002StrictModel.__subclasses__())
    models = set()
    while pending:
        model = pending.pop()
        if model in models:
            continue
        models.add(model)
        pending.extend(model.__subclasses__())
    assert models
    assert {model.model_config.get("extra") for model in models} == {"forbid"}


def _label_payload() -> dict[str, object]:
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "annotation_universe_sha256": "2" * 64,
        "annotation_count": 1,
        "benchmark_owner_confirmed": True,
        "labels": [
            {
                "key": {
                    "case_id": "R002-001",
                    "criterion_id": "AC-01",
                    "stream": "patch",
                    "path": "scopeproof.py",
                    "new_line_number": 1,
                    "normalized_line_sha256": "3" * 64,
                },
                "relevant": False,
                "reason_code": "unrelated_candidate",
            }
        ],
        "expected_missing": [
            {
                "case_id": "R002-001",
                "criterion_id": "AC-01",
                "evidence_type": kind,
                "reason_code": "no_owner_labelled_relevant_candidate",
            }
            for kind in ("implementation", "test", "documentation", "contract")
        ],
    }


def test_loader_boundaries_reject_criteria_and_label_upstream_drift_and_extra_fields(
    tmp_path, r002_criteria_payload
):
    criteria_path = tmp_path / "criteria.json"
    criteria_path.write_text(json.dumps(r002_criteria_payload), encoding="utf-8")
    with pytest.raises(r002_models.R002AnnotationError, match="criteria_manifest_drift"):
        load_confirmed_criteria(criteria_path, "0" * 64)
    r002_criteria_payload["unexpected"] = True
    criteria_path.write_text(json.dumps(r002_criteria_payload), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_confirmed_criteria(criteria_path, "9" * 64)

    labels_path = tmp_path / "labels.json"
    labels_path.write_text(json.dumps(_label_payload()), encoding="utf-8")
    with pytest.raises(r002_models.R002AnnotationError, match="candidate_label_upstream_drift"):
        load_confirmed_labels(labels_path, "9" * 64, "1" * 64)


def test_loader_rejects_each_controlled_case_projection_mutation(
    tmp_path, monkeypatch, r002_manifest_payload
):
    r002_manifest_payload["source"] = deepcopy(r002_models.R002_SOURCE)
    baseline = R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))
    monkeypatch.setattr(
        r002_models, "R002_APPROVED_CASES_SHA256", case_projection_sha256(baseline.cases)
    )
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(r002_manifest_payload), encoding="utf-8")
    assert load_source_manifest(path) == baseline
    for field, value in {
        "case_id": "R002-099",
        "instance_id": "wrong__case-1",
        "repository": "wrong/repository",
        "pr_number": 999,
        "pr_url": "https://github.com/wrong/repository/pull/1",
        "dataset_base_commit": "f" * 40,
        "verified_pr_head_sha": "e" * 40,
        "row_index": 499,
        "difficulty": "different",
        "row_sha256": "a" * 64,
        "problem_statement_sha256": "b" * 64,
        "patch_sha256": "c" * 64,
        "test_patch_sha256": "d" * 64,
    }.items():
        payload = deepcopy(r002_manifest_payload)
        payload["cases"][0][field] = value
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises((ValidationError, R002SourceError)):
            load_source_manifest(path)


@pytest.mark.parametrize("mutation", ["reversed", "duplicate_problem_hash"])
def test_confirmed_criteria_bind_complete_case_order_and_problem_hashes(
    r002_criteria_payload, mutation
):
    if mutation == "reversed":
        r002_criteria_payload["cases"].reverse()
    else:
        r002_criteria_payload["cases"][1]["problem_statement_sha256"] = r002_criteria_payload[
            "cases"
        ][0]["problem_statement_sha256"]
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))


@pytest.mark.parametrize("mutation", ["duplicate", "unsorted"])
def test_annotation_universe_rejects_duplicate_or_unstable_candidate_keys(mutation):
    keys = [
        {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "stream": "patch",
            "path": path,
            "new_line_number": 1,
            "normalized_line_sha256": digest * 64,
        }
        for path, digest in (("a.py", "0"), ("b.py", "1"))
    ]
    if mutation == "duplicate":
        keys[1] = keys[0]
    else:
        keys.reverse()
    payload = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "candidate_count": 2,
        "candidate_keys": keys,
    }
    with pytest.raises(ValidationError):
        R002AnnotationUniverse.model_validate_json(json.dumps(payload))


def test_annotation_artifacts_use_one_explicit_structural_key_order():
    keys = [
        {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "stream": "patch",
            "path": path,
            "new_line_number": line,
            "normalized_line_sha256": digest * 64,
        }
        for path, line, digest in (("a.py", 2, "0"), ("z.py", 1, "1"))
    ]
    universe = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "candidate_count": 2,
        "candidate_keys": keys,
    }
    assert R002AnnotationUniverse.model_validate_json(json.dumps(universe)).candidate_keys
    for mutation in (list(reversed(keys)), [keys[0], keys[0]]):
        invalid = {**universe, "candidate_keys": mutation}
        with pytest.raises(ValidationError):
            R002AnnotationUniverse.model_validate_json(json.dumps(invalid))

    review_keys = [{**key, "normalized_line_sha256": sha256(b"pass").hexdigest()} for key in keys]
    review = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "annotation_universe_sha256": "2" * 64,
        "items": [{"key": key, "line_content": "pass"} for key in review_keys],
    }
    assert r002_models.R002AnnotationReview.model_validate_json(json.dumps(review)).items
    review["items"].reverse()
    with pytest.raises(ValidationError):
        r002_models.R002AnnotationReview.model_validate_json(json.dumps(review))

    labels = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "annotation_universe_sha256": "2" * 64,
        "annotation_count": 2,
        "labels": [
            {"key": key, "relevant": True, "reason_code": "direct_static_candidate"} for key in keys
        ],
        "expected_missing": [],
        "benchmark_owner_confirmed": True,
    }
    assert R002CandidateLabelSet.model_validate_json(json.dumps(labels)).labels
    labels["labels"].reverse()
    with pytest.raises(ValidationError):
        R002CandidateLabelSet.model_validate_json(json.dumps(labels))


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            r002_models.R002CandidateLineKey,
            {
                "case_id": "R002-001",
                "criterion_id": "AC-17",
                "stream": "patch",
                "path": "a.py",
                "new_line_number": 1,
                "normalized_line_sha256": "0" * 64,
            },
        ),
        (
            r002_models.R002ExpectedMissing,
            {
                "case_id": "R002-001",
                "criterion_id": "AC-17",
                "evidence_type": "implementation",
                "reason_code": "no_owner_labelled_relevant_candidate",
            },
        ),
        (
            r002_models.R002MissingExplanation,
            {
                "case_id": "R002-001",
                "criterion_id": "AC-17",
                "evidence_type": "implementation",
                "source": "scopeproof_finding",
                "finding_status": "missing",
                "reason_code": "scopeproof_finding_explicit_gap",
            },
        ),
    ],
)
def test_persisted_annotation_criterion_ids_are_limited_to_r002_range(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)


def _write_bound_manifest_and_criteria(
    tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
):
    r002_manifest_payload["source"] = deepcopy(r002_models.R002_SOURCE)
    manifest = R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))
    monkeypatch.setattr(
        r002_models, "R002_APPROVED_CASES_SHA256", case_projection_sha256(manifest.cases)
    )
    manifest_path = tmp_path / "source_manifest.json"
    manifest_path.write_text(json.dumps(r002_manifest_payload), encoding="utf-8")
    manifest_hash = canonical_sha256(manifest)
    r002_criteria_payload["source_manifest_sha256"] = manifest_hash
    criteria_path = tmp_path / "criteria.json"
    criteria_path.write_text(json.dumps(r002_criteria_payload), encoding="utf-8")
    return manifest_path, criteria_path, manifest_hash


def test_criteria_loader_binds_its_ordered_problem_hash_projection(
    tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
):
    manifest_path, criteria_path, manifest_hash = _write_bound_manifest_and_criteria(
        tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
    )
    assert manifest_path.is_file()
    assert load_confirmed_criteria(criteria_path, manifest_hash).cases[0].case_id == "R002-001"

    mutated = deepcopy(r002_criteria_payload)
    mutated["cases"][0]["problem_statement_sha256"] = "f" * 64
    criteria_path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises((ValidationError, r002_models.R002AnnotationError)):
        load_confirmed_criteria(criteria_path, manifest_hash)

    mutated = deepcopy(r002_criteria_payload)
    mutated["cases"].reverse()
    criteria_path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises((ValidationError, r002_models.R002AnnotationError)):
        load_confirmed_criteria(criteria_path, manifest_hash)

    manifest_path.unlink()
    criteria_path.write_text(json.dumps(r002_criteria_payload), encoding="utf-8")
    with pytest.raises(r002_models.R002AnnotationError):
        load_confirmed_criteria(criteria_path, manifest_hash)


def test_criteria_loader_rejects_manifest_hash_drift(
    tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
):
    _, criteria_path, _manifest_hash = _write_bound_manifest_and_criteria(
        tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
    )
    with pytest.raises(r002_models.R002AnnotationError):
        load_confirmed_criteria(criteria_path, "0" * 64)


def test_task7_labels_loader_accepts_streamed_structural_annotation_order(
    tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
):
    _manifest_path, criteria_path, manifest_hash = _write_bound_manifest_and_criteria(
        tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
    )
    criteria = load_confirmed_criteria(criteria_path, manifest_hash)
    criteria_hash = canonical_sha256(criteria)
    payload = _label_payload()
    payload["source_manifest_sha256"] = manifest_hash
    payload["criteria_set_sha256"] = criteria_hash
    payload["labels"] = [
        {
            "key": {
                "case_id": "R002-001",
                "criterion_id": "AC-01",
                "stream": "patch",
                "path": path,
                "new_line_number": line,
                "normalized_line_sha256": digest * 64,
            },
            "relevant": True,
            "reason_code": "direct_static_candidate",
        }
        for path, line, digest in (("a.py", 2, "0"), ("z.py", 1, "1"))
    ]
    payload["annotation_count"] = 2
    payload["expected_missing"] = [
        {
            "case_id": case.case_id,
            "criterion_id": criterion.criterion_id,
            "evidence_type": evidence_type.value,
            "reason_code": "no_owner_labelled_relevant_candidate",
        }
        for case in criteria.cases
        for criterion in case.criteria
        for evidence_type in r002_models.R002_STATIC_EVIDENCE_TYPES
        if (case.case_id, criterion.criterion_id, evidence_type.value)
        != ("R002-001", "AC-01", "implementation")
    ]
    universe = R002AnnotationUniverse.model_validate_json(
        json.dumps(
            {
                **{
                    key: payload[key]
                    for key in (
                        "pack_id",
                        "classification",
                        "eligible_for_stage_1",
                        "does_not_advance_stage_1",
                        "target_repository_code_executed",
                        "source_manifest_sha256",
                        "criteria_set_sha256",
                    )
                },
                "candidate_count": payload["annotation_count"],
                "candidate_keys": [label["key"] for label in payload["labels"]],
            }
        )
    )
    payload["annotation_universe_sha256"] = canonical_sha256(universe)
    path = tmp_path / "candidate_labels.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_confirmed_labels(path, manifest_hash, criteria_hash).annotation_count == 2

    payload["labels"][0]["key"]["path"] = "b.py"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(r002_models.R002AnnotationError):
        load_confirmed_labels(path, manifest_hash, criteria_hash)


@pytest.mark.parametrize(
    "mutation", ["unknown_case", "unknown_criterion", "omitted", "extra", "wrong_hash"]
)
def test_labels_loader_rejects_self_consistent_keys_and_incomplete_expected_missing(
    mutation, tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
):
    _manifest_path, criteria_path, manifest_hash = _write_bound_manifest_and_criteria(
        tmp_path, monkeypatch, r002_manifest_payload, r002_criteria_payload
    )
    criteria = load_confirmed_criteria(criteria_path, manifest_hash)
    criteria_hash = canonical_sha256(criteria)
    payload = _label_payload()
    payload["source_manifest_sha256"] = manifest_hash
    payload["criteria_set_sha256"] = criteria_hash
    payload["expected_missing"] = [
        {
            "case_id": case.case_id,
            "criterion_id": criterion.criterion_id,
            "evidence_type": evidence_type.value,
            "reason_code": "no_owner_labelled_relevant_candidate",
        }
        for case in criteria.cases
        for criterion in case.criteria
        for evidence_type in r002_models.R002_STATIC_EVIDENCE_TYPES
    ]
    if mutation == "unknown_case":
        payload["labels"][0]["key"]["case_id"] = "R002-999"
        path = tmp_path / "candidate_labels.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValidationError):
            load_confirmed_labels(path, manifest_hash, criteria_hash)
        return
    elif mutation == "unknown_criterion":
        payload["labels"][0]["key"]["criterion_id"] = "AC-99"
        path = tmp_path / "candidate_labels.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValidationError):
            load_confirmed_labels(path, manifest_hash, criteria_hash)
        return
    elif mutation == "omitted":
        payload["expected_missing"].pop()
    elif mutation == "extra":
        payload["expected_missing"].append(
            {
                "case_id": "R002-020",
                "criterion_id": "AC-02",
                "evidence_type": "implementation",
                "reason_code": "no_owner_labelled_relevant_candidate",
            }
        )
    else:
        payload["criteria_set_sha256"] = "f" * 64
    universe = R002AnnotationUniverse.model_validate_json(
        json.dumps(
            {
                **{
                    key: payload[key]
                    for key in (
                        "pack_id",
                        "classification",
                        "eligible_for_stage_1",
                        "does_not_advance_stage_1",
                        "target_repository_code_executed",
                        "source_manifest_sha256",
                        "criteria_set_sha256",
                    )
                },
                "candidate_count": payload["annotation_count"],
                "candidate_keys": [label["key"] for label in payload["labels"]],
            }
        )
    )
    payload["annotation_universe_sha256"] = canonical_sha256(universe)
    path = tmp_path / "candidate_labels.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises((ValidationError, r002_models.R002AnnotationError)):
        load_confirmed_labels(path, manifest_hash, criteria_hash)


def _safe_case_result_payload() -> dict[str, object]:
    return {
        "case_id": "R002-001",
        "repository": "astropy/astropy",
        "pr_number": 14096,
        "head_sha": "271b2875d9aae0a5875acba0b1b27dc4885fd6e5",
        "criterion_count": 1,
        "annotation_candidate_count": 1,
        "retrieved_candidates": [
            {
                "key": {
                    "case_id": "R002-001",
                    "criterion_id": "AC-01",
                    "stream": "patch",
                    "path": "a.py",
                    "new_line_number": 1,
                    "normalized_line_sha256": "1" * 64,
                },
                "evidence_type": "implementation",
                "evidence_level": "E1",
                "hunk_id": "patch:a.py:H1",
                "head_file_sha256": "2" * 64,
                "matching_rule": "exact_identifier",
                "relevance_score": 1.0,
                "owner_label_relevant": True,
            }
        ],
        "missing_explanations": [],
        "gate_verdict": "blocked",
        "gate_reason_codes": ["blocking_criteria"],
        "blocking_criteria": ["AC-01"],
        "conditional_criteria": [],
        "unresolved_criteria": [],
        "check_state": "unavailable",
        "ci_reason_code": "no_observations",
        "runtime_evidence_count": 0,
        "resolution_count": 0,
        "final_acceptance": False,
        "separation_errors": 0,
        "reference_errors": 0,
        "limitations": list(r002_models.R002_RESULT_LIMITATIONS),
    }


@pytest.mark.parametrize("mutation", ["ci_reason", "path_type", "stream_type_level", "gate_shape"])
def test_case_result_rejects_ci_classifier_and_gate_shape_mutations(mutation):
    payload = _safe_case_result_payload()
    if mutation == "ci_reason":
        payload["ci_reason_code"] = "successful_check_runs"
    elif mutation == "path_type":
        payload["retrieved_candidates"][0]["evidence_type"] = "test"
        payload["retrieved_candidates"][0]["evidence_level"] = "E2"
    elif mutation == "stream_type_level":
        payload["retrieved_candidates"][0]["key"]["stream"] = "test_patch"
    else:
        payload["gate_reason_codes"] = ["arbitrary"]
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(payload))


def test_case_result_accepts_evaluate_gate_compatible_blocked_and_needs_review_shapes():
    blocked = _safe_case_result_payload()
    blocked["criterion_count"] = 3
    blocked["conditional_criteria"] = ["AC-02"]
    blocked["unresolved_criteria"] = ["AC-03"]
    blocked["gate_reason_codes"] = [
        "blocking_criteria",
        "conditional_criteria",
        "unresolved_criteria",
    ]
    assert R002CaseResult.model_validate_json(json.dumps(blocked)).gate_verdict.value == "blocked"

    review = _safe_case_result_payload()
    review["criterion_count"] = 3
    review["gate_verdict"] = "needs_review"
    review["blocking_criteria"] = []
    review["conditional_criteria"] = ["AC-02"]
    review["unresolved_criteria"] = ["AC-03"]
    review["gate_reason_codes"] = [
        "checks_not_passing",
        "conditional_criteria",
        "unresolved_criteria",
    ]
    assert (
        R002CaseResult.model_validate_json(json.dumps(review)).gate_verdict.value == "needs_review"
    )


def test_expected_missing_is_per_evidence_type_and_ordered():
    payload = _label_payload()
    payload["labels"].append(
        {
            "key": {
                **payload["labels"][0]["key"],
                "stream": "test_patch",
                "path": "tests/test_scopeproof.py",
            },
            "relevant": True,
            "reason_code": "test_intent_candidate",
        }
    )
    payload["annotation_count"] = 2
    payload["expected_missing"] = [
        {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "evidence_type": kind,
            "reason_code": "no_owner_labelled_relevant_candidate",
        }
        for kind in ("implementation", "documentation", "contract")
    ]
    assert R002CandidateLabelSet.model_validate_json(json.dumps(payload)).expected_missing
    payload["expected_missing"].reverse()
    with pytest.raises(ValidationError, match="expected missing records must be sorted"):
        R002CandidateLabelSet.model_validate_json(json.dumps(payload))


def test_metrics_has_exact_persisted_ratio_field_map():
    assert set(r002_models.R002Metrics.model_fields) == {
        "owner_confirmed_label_candidate_precision",
        "criterion_candidate_coverage",
        "candidate_to_gold_file_coverage",
        "candidate_to_gold_hunk_coverage",
        "missing_evidence_explanation_completeness",
        "implementation_test_separation_errors",
        "immutable_reference_integrity_errors",
        "parse_errors",
        "schema_errors",
        "source_hash_errors",
        "source_sha_errors",
        "unexpected_ready_count",
        "normalized_rerun_mismatches",
    }


def test_case_result_rejects_zero_criterion_count():
    payload = _safe_case_result_payload()
    payload["criterion_count"] = 0
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(payload))


def test_approved_case_projection_binds_all_persisted_identity_and_content_hashes():
    cases = r002_models.R002_APPROVED_CASES
    assert [case.case_id for case in cases] == [f"R002-{number:03d}" for number in range(1, 21)]
    first = cases[0]
    assert (first.repository, first.pr_number, first.head_sha) == (
        "astropy/astropy",
        14096,
        "271b2875d9aae0a5875acba0b1b27dc4885fd6e5",
    )
    assert (
        first.row_sha256,
        first.problem_statement_sha256,
        first.patch_sha256,
        first.test_patch_sha256,
    ) == (
        "2ab9bc4442553756efedd9737e68d2c11a68954da353a12acb903c86ba414ec0",
        "938971021e89cd882f6ea33d61202fe7aa0091d7be4748b100ddc7e164db90cd",
        "57a810467af331eba7c3238bbcd78268a47e96ad75eed3e2aa8b908da99104bc",
        "3a6a8ffc9c81264bccb9990b926bc6b1c2253a9aa7ce47810b5d28ad95c2596c",
    )


def _benchmark_result_payload() -> dict[str, object]:
    case_results = []
    for number, approved in enumerate(r002_models.R002_APPROVED_CASES, start=1):
        result = _safe_case_result_payload()
        result.update(
            {
                "case_id": approved.case_id,
                "repository": approved.repository,
                "pr_number": approved.pr_number,
                "head_sha": approved.head_sha,
                "annotation_candidate_count": int(number == 1),
                "retrieved_candidates": [] if number != 1 else result["retrieved_candidates"],
            }
        )
        case_results.append(result)
    metric = {"state": "value", "numerator": 1, "denominator": 1, "value": 1.0}
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "candidate_label_set_sha256": "2" * 64,
        "scopeproof_commit": "3" * 40,
        "case_results": case_results,
        "metrics": {
            "owner_confirmed_label_candidate_precision": {
                "state": "value",
                "numerator": 1,
                "denominator": 1,
                "value": 1.0,
            },
            "criterion_candidate_coverage": metric,
            "candidate_to_gold_file_coverage": metric,
            "candidate_to_gold_hunk_coverage": metric,
            "missing_evidence_explanation_completeness": {
                "state": "not_applicable",
                "numerator": 0,
                "denominator": 0,
                "value": None,
            },
            "implementation_test_separation_errors": 0,
            "immutable_reference_integrity_errors": 0,
            "parse_errors": 0,
            "schema_errors": 0,
            "source_hash_errors": 0,
            "source_sha_errors": 0,
            "unexpected_ready_count": 0,
            "normalized_rerun_mismatches": 0,
        },
        "limitations": list(r002_models.R002_RESULT_LIMITATIONS),
        "executed_case_count": 20,
        "failed_case_count": 0,
        "skipped_case_count": 0,
        "confirmed_criterion_count": 20,
        "annotation_candidate_count": 1,
        "unexpected_ready_count": 0,
        "normalized_rerun_mismatches": 0,
        "hard_gate_errors": [],
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("confirmed_criterion_count",), 0),
        (("annotation_candidate_count",), 0),
        (("case_results", 1, "repository"), "forged/repository"),
    ],
)
def test_benchmark_result_rejects_forged_aggregate_or_case_identity(path, value):
    payload = _benchmark_result_payload()
    target: object = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    with pytest.raises(ValidationError):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))


def test_case_result_rejects_cross_case_and_out_of_range_references():
    payload = _safe_case_result_payload()
    payload["retrieved_candidates"][0]["key"]["case_id"] = "R002-002"  # type: ignore[index]
    with pytest.raises(ValidationError, match="within the case criteria"):
        R002CaseResult.model_validate_json(json.dumps(payload))

    payload = _safe_case_result_payload()
    payload["retrieved_candidates"][0]["key"]["criterion_id"] = "AC-99"  # type: ignore[index]
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(payload))


def test_case_result_preserves_core_retrieval_order_while_rejecting_duplicate_keys():
    payload = _safe_case_result_payload()
    low_score = payload["retrieved_candidates"][0]
    high_score = deepcopy(low_score)
    high_score["key"].update(  # type: ignore[index]
        {"path": "b.py", "normalized_line_sha256": "3" * 64}
    )
    high_score["hunk_id"] = "patch:b.py:H1"
    high_score["relevance_score"] = 0.9
    low_score["relevance_score"] = 0.1  # type: ignore[index]
    payload["retrieved_candidates"] = [high_score, low_score]
    payload["annotation_candidate_count"] = 2
    result = R002CaseResult.model_validate_json(json.dumps(payload))
    assert [candidate.key.path for candidate in result.retrieved_candidates] == ["b.py", "a.py"]
    assert [
        item["key"]["path"] for item in result.model_dump(mode="json")["retrieved_candidates"]
    ] == [
        "b.py",
        "a.py",
    ]
    payload["retrieved_candidates"] = [high_score, deepcopy(high_score)]
    with pytest.raises(ValidationError, match="unique"):
        R002CaseResult.model_validate_json(json.dumps(payload))


def test_missing_explanation_requires_fixed_source_reason_and_status():
    valid = {
        "case_id": "R002-001",
        "criterion_id": "AC-01",
        "evidence_type": "implementation",
        "source": "r002_retrieval_comparison",
        "finding_status": "evidence_found",
        "reason_code": "no_candidate_retrieved_for_type",
    }
    assert (
        r002_models.R002MissingExplanation.model_validate_json(json.dumps(valid)).reason_code
        == valid["reason_code"]
    )
    invalid = {**valid, "finding_status": "missing"}
    with pytest.raises(ValidationError, match="retrieval missing explanations"):
        r002_models.R002MissingExplanation.model_validate_json(json.dumps(invalid))


def test_cached_case_keeps_structural_hashes_for_later_manifest_cross_binding():
    approved = r002_models.R002_APPROVED_CASES[0]
    payload = {
        "case_id": approved.case_id,
        "row_sha256": approved.row_sha256,
        "problem_statement_sha256": approved.problem_statement_sha256,
        "patch_sha256": approved.patch_sha256,
        "test_patch_sha256": approved.test_patch_sha256,
        "parsed_case_sha256": "0" * 64,
        "verified_lines": [],
        "head_files": [],
    }
    assert (
        r002_models.R002CachedCase.model_validate_json(json.dumps(payload)).case_id
        == approved.case_id
    )
    payload["patch_sha256"] = "f" * 64
    assert (
        r002_models.R002CachedCase.model_validate_json(json.dumps(payload)).patch_sha256 == "f" * 64
    )


def _criteria_source_index_payload() -> dict[str, object]:
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_sha256": "0" * 64,
        "manifest_sha256": "1" * 64,
        "complete": True,
        "cases": [
            {
                "case_id": item.case_id,
                "problem_statement_sha256": item.problem_statement_sha256,
                "byte_length": 1,
            }
            for item in r002_models.R002_APPROVED_CASES
        ],
    }


def test_structural_indexes_require_exact_order_and_unique_content_hashes():
    source_index = _criteria_source_index_payload()
    assert r002_models.R002CriteriaSourceIndex.model_validate_json(
        json.dumps(source_index)
    ).complete
    source_index["cases"][0]["problem_statement_sha256"] = "f" * 64  # type: ignore[index]
    assert r002_models.R002CriteriaSourceIndex.model_validate_json(
        json.dumps(source_index)
    ).complete
    source_index["cases"][1]["problem_statement_sha256"] = "f" * 64  # type: ignore[index]
    with pytest.raises(ValidationError, match="unique structural problem hashes"):
        r002_models.R002CriteriaSourceIndex.model_validate_json(json.dumps(source_index))

    cache_index = {
        **_criteria_source_index_payload(),
        "criteria_set_sha256": "2" * 64,
        "cases": [
            {
                "case_id": item.case_id,
                "row_sha256": item.row_sha256,
                "problem_statement_sha256": item.problem_statement_sha256,
                "patch_sha256": item.patch_sha256,
                "test_patch_sha256": item.test_patch_sha256,
                "parsed_case_sha256": "3" * 64,
                "verified_lines": [],
                "head_files": [],
            }
            for item in r002_models.R002_APPROVED_CASES
        ],
    }
    assert r002_models.R002CacheIndex.model_validate_json(json.dumps(cache_index)).complete
    cache_index["cases"].reverse()  # type: ignore[index]
    with pytest.raises(ValidationError, match="ordered structural case IDs"):
        r002_models.R002CacheIndex.model_validate_json(json.dumps(cache_index))


def test_preparation_and_redaction_audits_reject_partial_or_inconsistent_summaries():
    case_ids = [item.case_id for item in r002_models.R002_APPROVED_CASES]
    criteria_preparation = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "phase": "criteria_sources",
        "complete": True,
        "executed_case_count": 20,
        "failed_case_count": 0,
        "skipped_case_count": 0,
        "case_ids": case_ids,
        "errors": [],
        "hard_gate_errors": [],
    }
    assert r002_models.R002CriteriaSourcePreparationResult.model_validate_json(
        json.dumps(criteria_preparation)
    ).complete
    criteria_preparation["skipped_case_count"] = 1
    with pytest.raises(ValidationError, match="complete 20/0/0"):
        r002_models.R002CriteriaSourcePreparationResult.model_validate_json(
            json.dumps(criteria_preparation)
        )

    audit = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "passed": True,
        "tracked_file_count": 1,
        "raw_value_count": 2,
        "checked_value_sha256": ["0" * 64, "1" * 64],
    }
    assert r002_models.R002RedactionAudit.model_validate_json(json.dumps(audit)).passed
    audit["checked_value_sha256"].reverse()  # type: ignore[index]
    with pytest.raises(ValidationError, match="sorted unique"):
        r002_models.R002RedactionAudit.model_validate_json(json.dumps(audit))


def _verified_line_payload() -> dict[str, object]:
    approved = r002_models.R002_APPROVED_CASES[0]
    return {
        "stream": "patch",
        "path": "a.py",
        "hunk_id": "patch:a.py:H1",
        "new_line_number": 7,
        "normalized_line_sha256": "1" * 64,
        "head_file_sha256": "2" * 64,
        "head_sha": approved.head_sha,
        "permalink": (
            f"https://github.com/{approved.repository}/blob/{approved.head_sha}/a.py#L7-L7"
        ),
    }


def test_hunk_ids_are_bounded_stream_path_bound_strings():
    parsed_file = {
        "stream": "patch",
        "path": "a.py",
        "hunks": [
            {
                "hunk_id": "patch:a.py:H1",
                "old_start": 1,
                "old_count": 0,
                "new_start": 1,
                "new_count": 0,
                "lines": [],
            }
        ],
        "additions": 0,
        "deletions": 0,
    }
    assert r002_models.R002ParsedFile.model_validate_json(json.dumps(parsed_file)).hunks[0].hunk_id
    for hunk_id in ("patch:a.py:H0", "test_patch:a.py:H1", "patch:b.py:H1", "1"):
        payload = deepcopy(parsed_file)
        payload["hunks"][0]["hunk_id"] = hunk_id
        with pytest.raises(ValidationError):
            r002_models.R002ParsedFile.model_validate_json(json.dumps(payload))
    duplicated = deepcopy(parsed_file)
    duplicated["hunks"].append({**duplicated["hunks"][0], "hunk_id": "patch:a.py:H1"})
    with pytest.raises(ValidationError):
        r002_models.R002ParsedFile.model_validate_json(json.dumps(duplicated))


def test_verified_permalink_is_canonical_and_cache_lines_join_head_files():
    line = _verified_line_payload()
    assert (
        r002_models.R002VerifiedLine.model_validate_json(json.dumps(line)).permalink
        == line["permalink"]
    )
    for permalink in (
        line["permalink"].replace("#L7-L7", "#L7"),
        line["permalink"].replace("#L7-L7", "#L6-L7"),
        line["permalink"].replace("/a.py#", "/wrong.py#"),
        line["permalink"].replace("271b2875d9aae0a5875acba0b1b27dc4885fd6e5", "f" * 40),
        line["permalink"] + "?query=forbidden",
    ):
        with pytest.raises(ValidationError):
            r002_models.R002VerifiedLine.model_validate_json(
                json.dumps({**line, "permalink": permalink})
            )
    wrong_repository = {
        **line,
        "permalink": line["permalink"].replace("astropy/astropy", "wrong/repository"),
    }
    assert r002_models.R002VerifiedCaseLines.model_validate_json(
        json.dumps(
            {
                "case_id": "R002-001",
                "head_sha": line["head_sha"],
                "lines": [wrong_repository],
            }
        )
    ).lines

    approved = r002_models.R002_APPROVED_CASES[0]
    cache_case = {
        "case_id": approved.case_id,
        "row_sha256": approved.row_sha256,
        "problem_statement_sha256": approved.problem_statement_sha256,
        "patch_sha256": approved.patch_sha256,
        "test_patch_sha256": approved.test_patch_sha256,
        "parsed_case_sha256": "3" * 64,
        "verified_lines": [line],
        "head_files": [
            {
                "logical_path": "a.py",
                "head_sha": approved.head_sha,
                "byte_length": 1,
                "content_sha256": "2" * 64,
            }
        ],
    }
    assert (
        r002_models.R002CachedCase.model_validate_json(json.dumps(cache_case)).case_id
        == approved.case_id
    )
    cache_case["head_files"][0]["content_sha256"] = "4" * 64
    with pytest.raises(ValidationError):
        r002_models.R002CachedCase.model_validate_json(json.dumps(cache_case))
    cache_case["head_files"][0]["content_sha256"] = "2" * 64
    cache_case["head_files"] = []
    with pytest.raises(ValidationError):
        r002_models.R002CachedCase.model_validate_json(json.dumps(cache_case))


def test_case_result_requires_sorted_reasons_bounded_disjoint_criteria_and_closed_rule():
    review = _safe_case_result_payload()
    review["gate_verdict"] = "needs_review"
    review["blocking_criteria"] = []
    review["conditional_criteria"] = ["AC-02"]
    review["unresolved_criteria"] = ["AC-03"]
    review["criterion_count"] = 3
    review["gate_reason_codes"] = [
        "checks_not_passing",
        "conditional_criteria",
        "unresolved_criteria",
    ]
    review["retrieved_candidates"][0]["hunk_id"] = "patch:a.py:H1"  # type: ignore[index]
    review["retrieved_candidates"][0]["matching_rule"] = "exact_identifier"  # type: ignore[index]
    assert R002CaseResult.model_validate_json(json.dumps(review)).gate_reason_codes == tuple(
        review["gate_reason_codes"]
    )
    review["gate_reason_codes"].reverse()  # type: ignore[index]
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(review))

    blocked = _safe_case_result_payload()
    blocked["criterion_count"] = 17
    blocked["retrieved_candidates"][0]["hunk_id"] = "patch:a.py:H1"  # type: ignore[index]
    blocked["retrieved_candidates"][0]["matching_rule"] = "exact_identifier"  # type: ignore[index]
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(blocked))
    blocked["criterion_count"] = 2
    blocked["blocking_criteria"] = ["AC-02"]
    blocked["conditional_criteria"] = ["AC-02"]
    with pytest.raises(ValidationError):
        R002CaseResult.model_validate_json(json.dumps(blocked))


def test_retrieved_matching_rule_and_retrieval_explanation_status_are_closed():
    candidate = {
        "key": {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "stream": "patch",
            "path": "a.py",
            "new_line_number": 1,
            "normalized_line_sha256": "1" * 64,
        },
        "evidence_type": "implementation",
        "evidence_level": "E1",
        "hunk_id": "patch:a.py:H1",
        "head_file_sha256": "2" * 64,
        "matching_rule": "exact_identifier",
        "relevance_score": 1.0,
        "owner_label_relevant": True,
    }
    assert r002_models.R002RetrievedCandidate.model_validate_json(
        json.dumps(candidate)
    ).matching_rule
    candidate["matching_rule"] = "raw repository text"
    with pytest.raises(ValidationError):
        r002_models.R002RetrievedCandidate.model_validate_json(json.dumps(candidate))
    candidate["matching_rule"] = "keyword_overlap"
    candidate["hunk_id"] = "test_patch:a.py:H1"
    with pytest.raises(ValidationError):
        r002_models.R002RetrievedCandidate.model_validate_json(json.dumps(candidate))

    for reason_code in (
        "no_candidate_retrieved_for_type",
        "retrieved_only_owner_labelled_irrelevant",
    ):
        explanation = {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "evidence_type": "implementation",
            "source": "r002_retrieval_comparison",
            "finding_status": "evidence_found",
            "reason_code": reason_code,
        }
        assert r002_models.R002MissingExplanation.model_validate_json(json.dumps(explanation))


def test_confirmed_r002_criteria_are_deeply_immutable_and_hash_stable(r002_criteria_payload):
    criteria_set = R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))
    criterion = criteria_set.cases[0].criteria[0]
    before = canonical_sha256(criteria_set)
    assert isinstance(criterion, r002_models.R002Criterion)
    with pytest.raises(ValidationError):
        criterion.text = "mutated after confirmation"
    with pytest.raises(ValidationError):
        criterion.priority = r002_models.Priority.SHOULD_HAVE
    assert canonical_sha256(criteria_set) == before
    core = r002_models.Criterion(
        criterion_id="AC-01",
        text="Core criterion input.",
        source_span="problem_statement:L1-L1",
    )
    copied = r002_models.R002CriterionCase.model_validate(
        {
            "case_id": "R002-001",
            "problem_statement_sha256": "0" * 64,
            "criteria": (core,),
        }
    ).criteria[0]
    assert isinstance(copied, r002_models.R002Criterion)
    assert copied is not core


def test_verified_lines_use_natural_hunk_order_not_lexical_hunk_id_order():
    lines = []
    for number in range(1, 11):
        line = _verified_line_payload()
        line["hunk_id"] = f"patch:a.py:H{number}"
        line["new_line_number"] = number
        line["permalink"] = line["permalink"].replace("#L7-L7", f"#L{number}-L{number}")
        lines.append(line)
    payload = {
        "case_id": "R002-001",
        "head_sha": lines[0]["head_sha"],
        "lines": lines,
    }
    assert (
        len(r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(payload)).lines) == 10
    )
    approved = r002_models.R002_APPROVED_CASES[0]
    cache_payload = {
        "case_id": approved.case_id,
        "row_sha256": approved.row_sha256,
        "problem_statement_sha256": approved.problem_statement_sha256,
        "patch_sha256": approved.patch_sha256,
        "test_patch_sha256": approved.test_patch_sha256,
        "parsed_case_sha256": "3" * 64,
        "verified_lines": lines,
        "head_files": [
            {
                "logical_path": "a.py",
                "head_sha": approved.head_sha,
                "byte_length": 1,
                "content_sha256": "2" * 64,
            }
        ],
    }
    assert (
        len(
            r002_models.R002CachedCase.model_validate_json(json.dumps(cache_payload)).verified_lines
        )
        == 10
    )
    payload["lines"][1], payload["lines"][9] = payload["lines"][9], payload["lines"][1]
    with pytest.raises(ValidationError, match="sorted and unique"):
        r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(payload))
    cache_payload["verified_lines"] = payload["lines"]
    with pytest.raises(ValidationError, match="sorted unique"):
        r002_models.R002CachedCase.model_validate_json(json.dumps(cache_payload))


def test_verified_line_identity_excludes_hunk_id_and_resolves_once():
    first = _verified_line_payload()
    second = {**first, "hunk_id": "patch:a.py:H2"}
    verified_payload = {
        "case_id": "R002-001",
        "head_sha": first["head_sha"],
        "lines": [first, second],
    }
    with pytest.raises(ValidationError, match="sorted and unique"):
        r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(verified_payload))

    approved = r002_models.R002_APPROVED_CASES[0]
    cache_payload = {
        "case_id": approved.case_id,
        "row_sha256": approved.row_sha256,
        "problem_statement_sha256": approved.problem_statement_sha256,
        "patch_sha256": approved.patch_sha256,
        "test_patch_sha256": approved.test_patch_sha256,
        "parsed_case_sha256": "3" * 64,
        "verified_lines": [first, second],
        "head_files": [
            {
                "logical_path": "a.py",
                "head_sha": approved.head_sha,
                "byte_length": 1,
                "content_sha256": "2" * 64,
            }
        ],
    }
    with pytest.raises(ValidationError, match="sorted unique"):
        r002_models.R002CachedCase.model_validate_json(json.dumps(cache_payload))

    accepted = r002_models.R002VerifiedCaseLines.model_validate_json(
        json.dumps({**verified_payload, "lines": [first]})
    )
    assert accepted.by_path_and_line("a.py", 7).hunk_id == "patch:a.py:H1"


def test_annotation_review_requires_nonempty_bounded_ordered_unique_items():
    def item(path: str) -> dict[str, object]:
        content = "ScopeProof-authored fixture."
        return {
            "key": {
                "case_id": "R002-001",
                "criterion_id": "AC-01",
                "stream": "patch",
                "path": path,
                "new_line_number": 1,
                "normalized_line_sha256": sha256(content.encode("utf-8")).hexdigest(),
            },
            "line_content": content,
        }

    payload = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": "0" * 64,
        "criteria_set_sha256": "1" * 64,
        "annotation_universe_sha256": "2" * 64,
        "items": [item("a.py"), item("b.py")],
    }
    assert len(r002_models.R002AnnotationReview.model_validate_json(json.dumps(payload)).items) == 2
    payload["items"].reverse()
    with pytest.raises(ValidationError, match="sorted"):
        r002_models.R002AnnotationReview.model_validate_json(json.dumps(payload))
    payload["items"] = [item("a.py"), item("a.py")]
    with pytest.raises(ValidationError, match="unique"):
        r002_models.R002AnnotationReview.model_validate_json(json.dumps(payload))
    payload["items"] = []
    with pytest.raises(ValidationError):
        r002_models.R002AnnotationReview.model_validate_json(json.dumps(payload))
    bounded_item = r002_models.R002AnnotationReviewItem.model_validate_json(
        json.dumps(item("a.py"))
    )
    with pytest.raises(ValidationError):
        r002_models.R002AnnotationReview.model_validate(
            {**payload, "items": (bounded_item,) * 250001}
        )


def test_projection_recomputes_owner_confirmed_candidate_precision():
    payload = _benchmark_result_payload()
    payload["metrics"]["owner_confirmed_label_candidate_precision"] = {
        "state": "value",
        "numerator": 0,
        "denominator": 1,
        "value": 0.0,
    }
    with pytest.raises(ValidationError, match="owner-confirmed candidate precision"):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))
    payload["metrics"]["owner_confirmed_label_candidate_precision"] = {
        "state": "value",
        "numerator": 1,
        "denominator": 1,
        "value": 1.0,
    }
    assert r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload)).metrics
    no_candidates = _benchmark_result_payload()
    no_candidates["case_results"][0]["retrieved_candidates"] = []  # type: ignore[index]
    no_candidates["metrics"]["owner_confirmed_label_candidate_precision"] = {
        "state": "not_applicable",
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    for field in (
        "criterion_candidate_coverage",
        "candidate_to_gold_file_coverage",
        "candidate_to_gold_hunk_coverage",
    ):
        no_candidates["metrics"][field] = {
            "state": "value",
            "numerator": 0,
            "denominator": 1,
            "value": 0.0,
        }
    assert r002_models.R002BenchmarkResult.model_validate_json(json.dumps(no_candidates)).metrics
    for status in ("missing", "partial", "needs_review"):
        explanation = {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "evidence_type": "implementation",
            "source": "scopeproof_finding",
            "finding_status": status,
            "reason_code": "scopeproof_finding_explicit_gap",
        }
        assert r002_models.R002MissingExplanation.model_validate_json(json.dumps(explanation))


def test_successful_metrics_require_complete_missing_evidence_explanations():
    payload = _benchmark_result_payload()
    for incomplete in (
        {"state": "value", "numerator": 0, "denominator": 1, "value": 0.0},
        {"state": "value", "numerator": 1, "denominator": 2, "value": 0.5},
    ):
        payload["metrics"]["missing_evidence_explanation_completeness"] = incomplete
        with pytest.raises(ValidationError, match="missing evidence explanations"):
            r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))

    payload["metrics"]["missing_evidence_explanation_completeness"] = {
        "state": "not_applicable",
        "numerator": 0,
        "denominator": 0,
        "value": None,
    }
    assert r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload)).metrics


def test_annotation_review_text_binds_key_hash_and_single_line_utf8_limits():
    def item(content: str, *, digest: str | None = None, **context: str) -> dict[str, object]:
        return {
            "key": {
                "case_id": "R002-001",
                "criterion_id": "AC-01",
                "stream": "patch",
                "path": "a.py",
                "new_line_number": 1,
                "normalized_line_sha256": digest or sha256(content.encode("utf-8")).hexdigest(),
            },
            "line_content": content,
            **context,
        }

    assert (
        r002_models.R002AnnotationReviewItem.model_validate_json(json.dumps(item(""))).line_content
        == ""
    )
    assert r002_models.R002AnnotationReviewItem.model_validate_json(
        json.dumps(item("é" * 32768))
    ).line_content
    for invalid in (
        item("correct", digest="0" * 64),
        item("bad\nline"),
        item("é" * 32769),
        item("valid", previous_line="bad\rcontext"),
        item("valid", next_line="bad\ncontext"),
    ):
        with pytest.raises(ValidationError):
            r002_models.R002AnnotationReviewItem.model_validate_json(json.dumps(invalid))


def test_projection_uses_only_the_task8_candidate_label_set_hash_field():
    payload = _benchmark_result_payload()
    assert r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))
    payload["candidate_labels_sha256"] = "f" * 64
    with pytest.raises(ValidationError):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))


def test_per_case_annotation_count_covers_retrieved_candidates_and_rejects_redistribution():
    case = _safe_case_result_payload()
    case["annotation_candidate_count"] = 0
    with pytest.raises(ValidationError, match="annotation candidate count"):
        R002CaseResult.model_validate_json(json.dumps(case))

    result = _benchmark_result_payload()
    result["case_results"][0]["annotation_candidate_count"] = 0  # type: ignore[index]
    result["case_results"][1]["annotation_candidate_count"] = 1  # type: ignore[index]
    with pytest.raises(ValidationError, match="annotation candidate count"):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(result))


def test_every_persisted_r002_collection_has_a_finite_parse_time_maximum():
    pending = list(r002_models.R002StrictModel.__subclasses__())
    models = set()
    while pending:
        model = pending.pop()
        if model in models:
            continue
        models.add(model)
        pending.extend(model.__subclasses__())
    unbounded = []
    for model in models:
        for name, field in model.model_fields.items():
            if get_origin(field.annotation) not in {tuple, list}:
                continue
            maxima = [getattr(metadata, "max_length", None) for metadata in field.metadata]
            if not any(isinstance(maximum, int) and maximum >= 0 for maximum in maxima):
                unbounded.append(f"{model.__name__}.{name}")
    assert not unbounded


def test_result_collection_bounds_fail_before_result_after_validation():
    payload = _safe_case_result_payload()
    payload["criterion_count"] = 16
    payload["blocking_criteria"] = [f"AC-{number:02d}" for number in range(1, 18)]
    with pytest.raises(ValidationError, match="at most 16 items"):
        R002CaseResult.model_validate_json(json.dumps(payload))

    payload = _safe_case_result_payload()
    payload["missing_explanations"] = [
        {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "evidence_type": "implementation",
            "source": "scopeproof_finding",
            "finding_status": "missing",
            "reason_code": "scopeproof_finding_explicit_gap",
        }
        for _ in range(65)
    ]
    with pytest.raises(ValidationError, match="at most 64 items"):
        R002CaseResult.model_validate_json(json.dumps(payload))


def test_benchmark_annotation_candidate_count_has_pack_cap():
    payload = _benchmark_result_payload()
    for case in payload["case_results"]:  # type: ignore[index]
        case["annotation_candidate_count"] = 250000
    payload["annotation_candidate_count"] = 5_000_000
    with pytest.raises(ValidationError, match="less than or equal to 250000"):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))


def test_parsed_case_file_and_hunk_bounds_are_exact():
    zero_hunk_file = {
        "stream": "patch",
        "path": "a.py",
        "hunks": [],
        "additions": 0,
        "deletions": 0,
    }
    with pytest.raises(ValidationError, match="at least 1 item"):
        r002_models.R002ParsedFile.model_validate_json(json.dumps(zero_hunk_file))

    files = [
        {
            "stream": "patch",
            "path": f"a{number}.py",
            "hunks": [
                {
                    "hunk_id": f"patch:a{number}.py:H1",
                    "old_start": 1,
                    "old_count": 0,
                    "new_start": 1,
                    "new_count": 0,
                    "lines": [],
                }
            ],
            "additions": 0,
            "deletions": 0,
        }
        for number in range(33)
    ]
    with pytest.raises(ValidationError, match="at most 32 items"):
        r002_models.R002ParsedCase.model_validate_json(
            json.dumps(
                {
                    "case_id": "R002-001",
                    "files": files,
                    "file_count": 33,
                    "hunk_count": 33,
                    "diff_line_count": 0,
                }
            )
        )


def _head_bound_cache_index_payload(
    *, head_counts: list[int], byte_length: int
) -> dict[str, object]:
    cases = []
    for approved, count in zip(r002_models.R002_APPROVED_CASES, head_counts, strict=True):
        cases.append(
            {
                "case_id": approved.case_id,
                "row_sha256": approved.row_sha256,
                "problem_statement_sha256": approved.problem_statement_sha256,
                "patch_sha256": approved.patch_sha256,
                "test_patch_sha256": approved.test_patch_sha256,
                "parsed_case_sha256": "3" * 64,
                "verified_lines": [],
                "head_files": [
                    {
                        "logical_path": f"head-{number}.py",
                        "head_sha": approved.head_sha,
                        "byte_length": byte_length,
                        "content_sha256": f"{number + 1:064x}",
                    }
                    for number in range(count)
                ],
            }
        )
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_sha256": "0" * 64,
        "manifest_sha256": "1" * 64,
        "criteria_set_sha256": "2" * 64,
        "complete": True,
        "cases": cases,
    }


def test_head_file_request_and_byte_limits_hold_at_preparation_and_cache_pack_layers():
    preparation_cases = [
        {
            "case_id": item.case_id,
            "status": "prepared",
            "head_file_count": 7 if number < 8 else 6,
            "candidate_line_count": 0,
        }
        for number, item in enumerate(r002_models.R002_APPROVED_CASES)
    ]
    preparation = {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "phase": "evidence",
        "complete": True,
        "criteria_set_sha256": "0" * 64,
        "executed_case_count": 20,
        "failed_case_count": 0,
        "skipped_case_count": 0,
        "head_file_count": 128,
        "candidate_line_count": 0,
        "cases": preparation_cases,
        "errors": [],
        "hard_gate_errors": [],
    }
    assert (
        r002_models.R002PreparationResult.model_validate_json(
            json.dumps(preparation)
        ).head_file_count
        == 128
    )
    preparation["cases"][8]["head_file_count"] = 7  # type: ignore[index]
    preparation["head_file_count"] = 129
    with pytest.raises(ValidationError, match="less than or equal to 128"):
        r002_models.R002PreparationResult.model_validate_json(json.dumps(preparation))

    exact = _head_bound_cache_index_payload(head_counts=[7] * 8 + [6] * 12, byte_length=1)
    assert r002_models.R002CacheIndex.model_validate_json(json.dumps(exact)).complete
    too_many = _head_bound_cache_index_payload(head_counts=[7] * 9 + [6] * 11, byte_length=1)
    with pytest.raises(ValidationError, match="request limit"):
        r002_models.R002CacheIndex.model_validate_json(json.dumps(too_many))

    case_exact = _head_bound_cache_index_payload(
        head_counts=[4] + [0] * 19, byte_length=4 * 1024 * 1024
    )
    assert r002_models.R002CachedCase.model_validate_json(
        json.dumps(case_exact["cases"][0])
    ).head_files
    case_over = _head_bound_cache_index_payload(
        head_counts=[5] + [0] * 19, byte_length=4 * 1024 * 1024
    )
    with pytest.raises(ValidationError, match="case exceeds"):
        r002_models.R002CachedCase.model_validate_json(json.dumps(case_over["cases"][0]))

    byte_exact = _head_bound_cache_index_payload(
        head_counts=[7] * 8 + [6] * 12, byte_length=1024 * 1024
    )
    assert r002_models.R002CacheIndex.model_validate_json(json.dumps(byte_exact)).complete
    byte_over = _head_bound_cache_index_payload(
        head_counts=[7] * 8 + [6] * 12, byte_length=1024 * 1024
    )
    byte_over["cases"][0]["head_files"][0]["byte_length"] += 1  # type: ignore[index]
    with pytest.raises(ValidationError, match="byte limit"):
        r002_models.R002CacheIndex.model_validate_json(json.dumps(byte_over))


def test_preparation_candidate_line_counts_have_case_and_pack_limits():
    def preparation(counts: list[int]) -> dict[str, object]:
        return {
            "pack_id": "R-002",
            "classification": "public_engineering_research",
            "eligible_for_stage_1": False,
            "does_not_advance_stage_1": True,
            "target_repository_code_executed": False,
            "phase": "evidence",
            "complete": True,
            "criteria_set_sha256": "0" * 64,
            "executed_case_count": 20,
            "failed_case_count": 0,
            "skipped_case_count": 0,
            "head_file_count": 0,
            "candidate_line_count": sum(counts),
            "cases": [
                {
                    "case_id": case.case_id,
                    "status": "prepared",
                    "head_file_count": 0,
                    "candidate_line_count": count,
                }
                for case, count in zip(r002_models.R002_APPROVED_CASES, counts, strict=True)
            ],
            "errors": [],
            "hard_gate_errors": [],
        }

    exact = preparation([50_000] * 20)
    assert (
        r002_models.R002PreparationResult.model_validate_json(
            json.dumps(exact)
        ).candidate_line_count
        == 1_000_000
    )

    with pytest.raises(ValidationError, match="less than or equal to 50000"):
        r002_models.R002PreparationCaseResult.model_validate_json(
            json.dumps(
                {
                    "case_id": "R002-001",
                    "status": "prepared",
                    "head_file_count": 0,
                    "candidate_line_count": 50_001,
                }
            )
        )
    with pytest.raises(ValidationError, match="less than or equal to 1000000"):
        r002_models.R002PreparationResult.model_validate_json(
            json.dumps(preparation([50_001] + [50_000] * 19))
        )
    with pytest.raises(ValidationError, match="less than or equal to 1000000"):
        r002_models.R002PreparationResult.model_validate_json(
            json.dumps(preparation([5_000_000] + [0] * 19))
        )
    with pytest.raises(ValidationError, match="less than or equal to 50000"):
        r002_models.R002PreparationResult.model_validate_json(
            json.dumps(preparation([50_001, 49_999] + [50_000] * 18))
        )


def _parsed_line_payload(content: str, *, number: int = 1) -> dict[str, object]:
    return {
        "change_type": "added",
        "old_line_number": None,
        "new_line_number": number,
        "content": content,
        "normalized_line_sha256": sha256(content.encode("utf-8")).hexdigest(),
    }


def test_parsed_line_uses_utf8_byte_bounds_no_newlines_and_exact_hash():
    exact = _parsed_line_payload("a" * 65536)
    assert (
        r002_models.R002ParsedLine.model_validate_json(json.dumps(exact)).content
        == exact["content"]
    )
    with pytest.raises(ValidationError, match="65,536"):
        r002_models.R002ParsedLine.model_validate_json(
            json.dumps(_parsed_line_payload("a" * 65537))
        )
    assert r002_models.R002ParsedLine.model_validate_json(
        json.dumps(_parsed_line_payload("é" * 32768))
    ).content
    with pytest.raises(ValidationError, match="65,536"):
        r002_models.R002ParsedLine.model_validate_json(
            json.dumps(_parsed_line_payload("é" * 32769))
        )
    with pytest.raises(ValidationError, match="newlines"):
        r002_models.R002ParsedLine.model_validate_json(
            json.dumps(_parsed_line_payload("bad\nline"))
        )
    wrong_hash = _parsed_line_payload("valid")
    wrong_hash["normalized_line_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="normalized hash"):
        r002_models.R002ParsedLine.model_validate_json(json.dumps(wrong_hash))
    assert (
        r002_models.R002ParsedLine.model_validate_json(json.dumps(_parsed_line_payload(""))).content
        == ""
    )


def _parsed_file_with_added_lines(path: str, stream: str, count: int) -> dict[str, object]:
    return {
        "stream": stream,
        "path": path,
        "hunks": [
            {
                "hunk_id": f"{stream}:{path}:H1",
                "old_start": 1,
                "old_count": 0,
                "new_start": 1,
                "new_count": count,
                "lines": [
                    _parsed_line_payload("", number=number) for number in range(1, count + 1)
                ],
            }
        ],
        "additions": count,
        "deletions": 0,
    }


def _parsed_file_with_empty_hunks(path: str, count: int) -> dict[str, object]:
    return {
        "stream": "patch",
        "path": path,
        "hunks": [
            {
                "hunk_id": f"patch:{path}:H{number}",
                "old_start": number,
                "old_count": 0,
                "new_start": number,
                "new_count": 0,
                "lines": [],
            }
            for number in range(1, count + 1)
        ],
        "additions": 0,
        "deletions": 0,
    }


def test_parsed_diff_and_case_enforce_exact_aggregate_hunk_and_line_caps():
    diff = {
        "stream": "patch",
        "files": [_parsed_file_with_empty_hunks("a.py", 256)],
        "file_count": 1,
        "hunk_count": 256,
        "diff_line_count": 0,
    }
    assert r002_models.R002ParsedDiff.model_validate_json(json.dumps(diff)).hunk_count == 256
    diff["files"] = [_parsed_file_with_empty_hunks("a.py", 257)]
    diff["hunk_count"] = 257
    with pytest.raises(ValidationError, match="at most 256 items"):
        r002_models.R002ParsedDiff.model_validate_json(json.dumps(diff))

    split_hunks = {
        "case_id": "R002-001",
        "files": [
            _parsed_file_with_empty_hunks("a.py", 256),
            _parsed_file_with_empty_hunks("b.py", 1),
        ],
        "file_count": 2,
        "hunk_count": 257,
        "diff_line_count": 0,
    }
    with pytest.raises(ValidationError, match="less than or equal to 256"):
        r002_models.R002ParsedCase.model_validate_json(json.dumps(split_hunks))

    exact_lines = {
        "case_id": "R002-001",
        "files": [
            _parsed_file_with_added_lines("a.py", "patch", 25000),
            _parsed_file_with_added_lines("tests/b.py", "test_patch", 25000),
        ],
        "file_count": 2,
        "hunk_count": 2,
        "diff_line_count": 50000,
    }
    assert (
        r002_models.R002ParsedCase.model_validate_json(json.dumps(exact_lines)).diff_line_count
        == 50000
    )
    over_lines = deepcopy(exact_lines)
    over_lines["files"][1] = _parsed_file_with_added_lines("tests/b.py", "test_patch", 25001)
    over_lines["diff_line_count"] = 50001
    with pytest.raises(ValidationError, match="less than or equal to 50000"):
        r002_models.R002ParsedCase.model_validate_json(json.dumps(over_lines))


def test_parsed_case_direct_constructor_reconstructs_omitted_counts():
    parsed_file = r002_models.R002ParsedFile.model_validate_json(
        json.dumps(
            {
                "stream": "patch",
                "path": "a.py",
                "hunks": [
                    {
                        "hunk_id": "patch:a.py:H1",
                        "old_start": 1,
                        "old_count": 0,
                        "new_start": 1,
                        "new_count": 0,
                        "lines": [],
                    }
                ],
                "additions": 0,
                "deletions": 0,
            }
        )
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        parsed = r002_models.R002ParsedCase(case_id="R002-001", files=(parsed_file,))
    assert (parsed.file_count, parsed.hunk_count, parsed.diff_line_count) == (1, 1, 0)
    signature = inspect.signature(r002_models.R002ParsedCase)
    assert all(
        signature.parameters[field].default is not inspect.Parameter.empty
        for field in ("file_count", "hunk_count", "diff_line_count")
    )
    assert all(
        not r002_models.R002ParsedCase.model_fields[field].is_required()
        for field in ("file_count", "hunk_count", "diff_line_count")
    )
    schema = r002_models.R002ParsedCase.model_json_schema()["properties"]
    assert schema["file_count"]["type"] == "integer"
    assert (
        r002_models.R002ParsedCase.model_validate_json(json.dumps(parsed.model_dump(mode="json")))
        == parsed
    )
    with pytest.raises(ValidationError, match="counts must match"):
        r002_models.R002ParsedCase.model_validate_json(
            json.dumps(
                {
                    "case_id": "R002-001",
                    "files": [],
                    "file_count": 1,
                    "hunk_count": 0,
                    "diff_line_count": 0,
                }
            )
        )

    for malformed_files in ([], "bad", [None], [{}], 7):
        with pytest.raises(ValidationError):
            r002_models.R002ParsedCase.model_validate(
                {"case_id": "R002-001", "files": malformed_files}
            )


def test_parsed_file_rejects_overlapping_hunk_ranges_and_accepts_adjacent_ranges():
    def hunk(number: int, start: int, count: int) -> dict[str, object]:
        return {
            "hunk_id": f"patch:a.py:H{number}",
            "old_start": start,
            "old_count": 0,
            "new_start": start,
            "new_count": count,
            "lines": [
                _parsed_line_payload("x", number=line) for line in range(start, start + count)
            ],
        }

    adjacent = {
        "stream": "patch",
        "path": "a.py",
        "hunks": [hunk(1, 1, 1), hunk(2, 2, 1)],
        "additions": 2,
        "deletions": 0,
    }
    assert r002_models.R002ParsedFile.model_validate_json(json.dumps(adjacent)).hunks
    overlapping = deepcopy(adjacent)
    overlapping["hunks"] = [hunk(1, 1, 2), hunk(2, 2, 1)]
    overlapping["additions"] = 3
    with pytest.raises(ValidationError, match="overlap"):
        r002_models.R002ParsedFile.model_validate_json(json.dumps(overlapping))
    duplicate_zero = deepcopy(adjacent)
    duplicate_zero["hunks"] = [hunk(1, 1, 0), hunk(2, 1, 0)]
    duplicate_zero["additions"] = 0
    with pytest.raises(ValidationError, match="ambiguous"):
        r002_models.R002ParsedFile.model_validate_json(json.dumps(duplicate_zero))

    def removed_hunk(number: int, start: int, count: int) -> dict[str, object]:
        return {
            "hunk_id": f"patch:b.py:H{number}",
            "old_start": start,
            "old_count": count,
            "new_start": start,
            "new_count": 0,
            "lines": [
                {
                    "change_type": "removed",
                    "old_line_number": line,
                    "new_line_number": None,
                    "content": "x",
                    "normalized_line_sha256": sha256(b"x").hexdigest(),
                }
                for line in range(start, start + count)
            ],
        }

    old_overlap = {
        "stream": "patch",
        "path": "b.py",
        "hunks": [removed_hunk(1, 1, 2), removed_hunk(2, 2, 1)],
        "additions": 0,
        "deletions": 3,
    }
    with pytest.raises(ValidationError, match="overlap"):
        r002_models.R002ParsedFile.model_validate_json(json.dumps(old_overlap))


def test_r002_error_reason_code_allowlists_are_exact_and_closed():
    source_codes = {
        "source_pin_mismatch",
        "approved_cohort_mismatch",
        "parquet_bytes_mismatch",
        "parquet_row_count_mismatch",
        "parquet_schema_mismatch",
        "parquet_field_type_mismatch",
        "parquet_uncompressed_limit",
        "row_count_mismatch",
        "unique_instance_count_mismatch",
        "repository_count_mismatch",
        "instance_pr_suffix_mismatch",
        "manifest_selection_mismatch",
        "manifest_row_mismatch",
    }
    assert r002_models.R002SourceError.allowed_reason_codes == source_codes
    assert all(r002_models.R002SourceError(code).reason_code == code for code in source_codes)
    with pytest.raises(RuntimeError):
        r002_models.R002SourceError("unregistered")

    annotation_codes = {
        "criteria_source_cache_manifest_mismatch",
        "problem_statement_hash_mismatch",
        "prepared_cache_evidence_drift",
        "criteria_manifest_drift",
        "prepared_cache_criteria_drift",
        "annotation_pair_limit",
        "label_upstream_hash_drift",
        "annotation_criterion_drift",
        "reannotation_required",
        "expected_missing_drift",
        "label_proposal_must_be_unconfirmed",
        "candidate_labels_not_confirmed",
        "criteria_manifest_context_invalid",
        "criteria_manifest_projection_drift",
        "candidate_label_upstream_drift",
        "annotation_universe_drift",
    }
    assert r002_models.R002AnnotationError.allowed_reason_codes == annotation_codes
    assert all(
        r002_models.R002AnnotationError(code).reason_code == code for code in annotation_codes
    )
    with pytest.raises(RuntimeError):
        r002_models.R002AnnotationError("unregistered")


def test_verified_sidecars_accept_fake_heads_but_require_internal_consistency():
    head = "f" * 40
    line = {
        "stream": "patch",
        "path": "a.py",
        "hunk_id": "patch:a.py:H1",
        "new_line_number": 1,
        "normalized_line_sha256": "1" * 64,
        "head_file_sha256": "2" * 64,
        "head_sha": head,
        "permalink": f"https://github.com/fixture/repo/blob/{head}/a.py#L1-L1",
    }
    payload = {"case_id": "R002-001", "head_sha": head, "lines": [line]}
    assert r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(payload)).lines
    wrong_head = deepcopy(payload)
    wrong_head["lines"][0]["head_sha"] = "e" * 40
    wrong_head["lines"][0]["permalink"] = wrong_head["lines"][0]["permalink"].replace(
        head, "e" * 40
    )
    with pytest.raises(ValidationError, match="share one immutable head"):
        r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(wrong_head))
    inconsistent_path = deepcopy(payload)
    inconsistent_path["lines"].append(
        {
            **line,
            "hunk_id": "patch:a.py:H2",
            "new_line_number": 2,
            "head_file_sha256": "3" * 64,
            "permalink": f"https://github.com/fixture/repo/blob/{head}/a.py#L2-L2",
        }
    )
    with pytest.raises(ValidationError, match="stream and head-file hash"):
        r002_models.R002VerifiedCaseLines.model_validate_json(json.dumps(inconsistent_path))


def test_missing_explanations_cannot_contradict_retrieved_evidence():
    payload = _safe_case_result_payload()
    payload["missing_explanations"] = [
        {
            "case_id": "R002-001",
            "criterion_id": "AC-01",
            "evidence_type": "implementation",
            "source": "scopeproof_finding",
            "finding_status": "missing",
            "reason_code": "scopeproof_finding_explicit_gap",
        }
    ]
    with pytest.raises(ValidationError, match="owner-relevant"):
        R002CaseResult.model_validate_json(json.dumps(payload))

    payload["retrieved_candidates"][0]["owner_label_relevant"] = False  # type: ignore[index]
    assert R002CaseResult.model_validate_json(json.dumps(payload)).missing_explanations
    payload["missing_explanations"][0].update(  # type: ignore[index]
        {
            "source": "r002_retrieval_comparison",
            "finding_status": "evidence_found",
            "reason_code": "no_candidate_retrieved_for_type",
        }
    )
    with pytest.raises(ValidationError, match="no-candidate"):
        R002CaseResult.model_validate_json(json.dumps(payload))
    payload["missing_explanations"][0]["reason_code"] = "retrieved_only_owner_labelled_irrelevant"  # type: ignore[index]
    assert R002CaseResult.model_validate_json(json.dumps(payload)).missing_explanations


def test_projection_recomputes_all_case_observable_metric_numerators():
    payload = _benchmark_result_payload()
    for field in (
        "criterion_candidate_coverage",
        "candidate_to_gold_file_coverage",
        "candidate_to_gold_hunk_coverage",
    ):
        payload["metrics"][field] = {
            "state": "value",
            "numerator": 0,
            "denominator": 1,
            "value": 0.0,
        }
        with pytest.raises(ValidationError, match="observable metric numerators"):
            r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))
        payload["metrics"][field] = {
            "state": "value",
            "numerator": 1,
            "denominator": 1,
            "value": 1.0,
        }
    payload["metrics"]["missing_evidence_explanation_completeness"] = {
        "state": "value",
        "numerator": 1,
        "denominator": 1,
        "value": 1.0,
    }
    with pytest.raises(ValidationError, match="observable metric numerators"):
        r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload))


def test_structural_projection_accepts_fake_heads_for_private_helpers():
    payload = _benchmark_result_payload()
    for result in payload["case_results"]:  # type: ignore[index]
        result["head_sha"] = "f" * 40
    assert r002_models.R002BenchmarkResult.model_validate_json(json.dumps(payload)).case_results
