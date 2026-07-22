"""Strict R-002 persisted-contract tests."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from scopeproof_core.evals.r002_models import (
    R002CandidateLabelSet,
    R002CriteriaSet,
    R002Metric,
    R002SourceError,
    R002SourceManifest,
    case_projection_sha256,
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
