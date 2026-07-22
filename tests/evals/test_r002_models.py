"""Strict R-002 persisted-contract tests."""

from __future__ import annotations

import json
from copy import deepcopy

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


def test_label_set_derives_expected_missing_for_an_unlabelled_relevant_candidate():
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
    with pytest.raises(ValidationError, match="expected missing records must be derived"):
        R002CandidateLabelSet.model_validate_json(json.dumps(payload))


def test_loader_rejects_structurally_valid_non_production_source(tmp_path, r002_manifest_payload):
    path = tmp_path / "source_manifest.json"
    path.write_text(json.dumps(r002_manifest_payload), encoding="utf-8")
    with pytest.raises(R002SourceError, match="source_pin_mismatch"):
        load_source_manifest(path)


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
        {**case, "problem_statement": "ScopeProof-authored fixture text."}
        for case in proposal["cases"]
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
