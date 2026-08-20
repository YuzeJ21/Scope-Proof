from copy import deepcopy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from scopeproof_core.criteria.confirmation import normalized_criteria_sha256
from scopeproof_core.demo import build_demo_review
from scopeproof_core.schemas.models import (
    JUnitEvidenceImport,
    ReviewBundle,
)

HEAD_SHA = "a" * 40
OTHER_HEAD_SHA = "b" * 40
ARTIFACT_SHA256 = "c" * 64


def exact_head_bundle() -> ReviewBundle:
    bundle = build_demo_review().model_copy(deep=True)
    bundle.review.head_sha = HEAD_SHA
    bundle.criteria_revision_number = 1
    return ReviewBundle.model_validate(bundle.model_dump(mode="python"))


def valid_import_payload(bundle: ReviewBundle | None = None) -> dict[str, object]:
    bundle = bundle or exact_head_bundle()
    provenance = bundle.review.criteria_source_provenance
    assert provenance is not None
    criterion_id = bundle.criteria[0].criterion_id
    return {
        "schema_version": "junit-import-v1",
        "import_id": "import-001",
        "repository": bundle.review.repository,
        "pr_number": bundle.review.pr_number,
        "head_sha": bundle.review.head_sha,
        "criteria_revision_number": bundle.criteria_revision_number,
        "confirmed_criteria_sha256": normalized_criteria_sha256(bundle.criteria),
        "criteria_source_provenance": provenance.model_dump(mode="python"),
        "artifact_sha256": ARTIFACT_SHA256,
        "artifact_format": "junit_xml",
        "imported_by": "QA owner",
        "imported_at": datetime(2026, 8, 20, tzinfo=UTC),
        "totals": {
            "total": 2,
            "passed": 1,
            "failures": 1,
            "errors": 0,
            "skipped": 0,
        },
        "test_cases": [
            {
                "test_case_id": "suite-0001-case-0001",
                "suite_id": "suite-0001",
                "suite_name": "unit",
                "class_name": "tests.WidgetTests",
                "test_name": "test_export",
                "status": "passed",
            },
            {
                "test_case_id": "suite-0001-case-0002",
                "suite_id": "suite-0001",
                "suite_name": "unit",
                "class_name": None,
                "test_name": "test_error",
                "status": "failure",
            },
        ],
        "criterion_mappings": [
            {
                "criterion_id": criterion_id,
                "test_case_ids": ["suite-0001-case-0001"],
            }
        ],
        "parser_warnings": ["Declared failure count differed from observed results."],
        "limitations": [
            "ScopeProof imported externally supplied results and did not execute tests."
        ],
    }


def test_junit_import_accepts_strict_exact_identity_and_sanitized_results() -> None:
    record = JUnitEvidenceImport.model_validate(valid_import_payload())

    assert record.schema_version == "junit-import-v1"
    assert record.head_sha == HEAD_SHA
    assert record.totals.total == 2
    assert record.criterion_mappings[0].test_case_ids == [
        "suite-0001-case-0001"
    ]
    assert record.model_dump_json().count("test_error") == 1


def test_junit_import_requires_explicit_schema_version() -> None:
    payload = valid_import_payload()
    payload.pop("schema_version")

    with pytest.raises(ValidationError, match="schema_version"):
        JUnitEvidenceImport.model_validate(payload)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("schema_version",), "junit-import-v2", "junit-import-v1"),
        (("head_sha",), "short", "40"),
        (("artifact_sha256",), "A" * 64, "SHA-256"),
        (("imported_by",), "   ", "non-whitespace"),
        (("parser_warnings",), [""], "non-whitespace"),
        (("limitations",), [""], "non-whitespace"),
        (("test_cases", 0, "test_name"), "", "non-whitespace"),
    ],
)
def test_junit_import_rejects_malformed_boundary_fields(
    path: tuple[str | int, ...], value: object, message: str
) -> None:
    payload = deepcopy(valid_import_payload())
    target: object = payload
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ValidationError, match=message):
        JUnitEvidenceImport.model_validate(payload)


def test_junit_import_rejects_naive_timestamp_and_extra_fields() -> None:
    payload = valid_import_payload()
    payload["imported_at"] = datetime(2026, 8, 20)
    payload["raw_xml"] = "<testsuite/>"

    with pytest.raises(ValidationError) as exc_info:
        JUnitEvidenceImport.model_validate(payload)

    rendered = str(exc_info.value)
    assert "timezone-aware" in rendered
    assert "raw_xml" in rendered


def test_junit_import_rejects_inconsistent_totals() -> None:
    payload = valid_import_payload()
    payload["totals"] = {
        "total": 2,
        "passed": 2,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
    }

    with pytest.raises(ValidationError, match="sum to total"):
        JUnitEvidenceImport.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("suite_name", "/private/workspace/unit"),
        ("class_name", "C:\\agent\\tests.Widget"),
        ("test_name", "https://ci.example.test/jobs/42"),
        ("test_name", "mailto:secret@example.test"),
    ],
)
def test_persisted_junit_case_rejects_path_or_url_like_names(
    field: str, value: str
) -> None:
    payload = valid_import_payload()
    payload["test_cases"][0][field] = value  # type: ignore[index]

    with pytest.raises(ValidationError, match="path- or URL-like"):
        JUnitEvidenceImport.model_validate(payload)


def test_junit_import_rejects_unknown_or_duplicate_case_mapping() -> None:
    unknown = valid_import_payload()
    unknown["criterion_mappings"] = [
        {
            "criterion_id": exact_head_bundle().criteria[0].criterion_id,
            "test_case_ids": ["suite-9999-case-9999"],
        }
    ]
    with pytest.raises(ValidationError, match="mapped test case IDs must resolve"):
        JUnitEvidenceImport.model_validate(unknown)

    duplicate = valid_import_payload()
    duplicate["criterion_mappings"] = [
        {
            "criterion_id": exact_head_bundle().criteria[0].criterion_id,
            "test_case_ids": [
                "suite-0001-case-0001",
                "suite-0001-case-0001",
            ],
        }
    ]
    with pytest.raises(ValidationError, match="sorted and unique"):
        JUnitEvidenceImport.model_validate(duplicate)


def test_junit_import_rejects_one_case_mapped_to_multiple_criteria() -> None:
    bundle = exact_head_bundle()
    first, second = bundle.criteria[:2]
    payload = valid_import_payload(bundle)
    payload["criterion_mappings"] = [
        {
            "criterion_id": first.criterion_id,
            "test_case_ids": ["suite-0001-case-0001"],
        },
        {
            "criterion_id": second.criterion_id,
            "test_case_ids": ["suite-0001-case-0001"],
        },
    ]

    with pytest.raises(ValidationError, match="multiple criteria"):
        JUnitEvidenceImport.model_validate(payload)


def test_review_bundle_accepts_matching_import_and_preserves_legacy_absence() -> None:
    bundle = exact_head_bundle()
    payload = bundle.model_dump(mode="python")
    payload["junit_evidence_imports"] = [valid_import_payload(bundle)]

    reopened = ReviewBundle.model_validate(payload)

    assert reopened.junit_evidence_imports[0].artifact_sha256 == ARTIFACT_SHA256
    legacy_payload = bundle.model_dump(mode="python")
    legacy_payload.pop("junit_evidence_imports", None)
    assert ReviewBundle.model_validate(legacy_payload).junit_evidence_imports == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository", "other/repository", "JUnit import identity"),
        ("pr_number", 999, "JUnit import identity"),
        ("head_sha", OTHER_HEAD_SHA, "JUnit import identity"),
        ("criteria_revision_number", 2, "criteria revision"),
        ("confirmed_criteria_sha256", "d" * 64, "criteria digest"),
    ],
)
def test_review_bundle_rejects_import_from_another_review_or_criteria_snapshot(
    field: str, value: object, message: str
) -> None:
    bundle = exact_head_bundle()
    imported = valid_import_payload(bundle)
    imported[field] = value
    payload = bundle.model_dump(mode="python")
    payload["junit_evidence_imports"] = [imported]

    with pytest.raises(ValidationError, match=message):
        ReviewBundle.model_validate(payload)


def test_review_bundle_rejects_unknown_criterion_and_duplicate_import_identity() -> None:
    bundle = exact_head_bundle()
    imported = valid_import_payload(bundle)
    imported["criterion_mappings"] = [
        {
            "criterion_id": "AC-UNKNOWN",
            "test_case_ids": ["suite-0001-case-0001"],
        }
    ]
    payload = bundle.model_dump(mode="python")
    payload["junit_evidence_imports"] = [imported]
    with pytest.raises(ValidationError, match="known criteria"):
        ReviewBundle.model_validate(payload)

    first = valid_import_payload(bundle)
    second = deepcopy(first)
    second["import_id"] = "import-002"
    duplicate_digest = bundle.model_dump(mode="python")
    duplicate_digest["junit_evidence_imports"] = [first, second]
    with pytest.raises(ValidationError, match="artifact digests must be unique"):
        ReviewBundle.model_validate(duplicate_digest)

    second["artifact_sha256"] = "e" * 64
    second["import_id"] = first["import_id"]
    duplicate_id = bundle.model_dump(mode="python")
    duplicate_id["junit_evidence_imports"] = [first, second]
    with pytest.raises(ValidationError, match="import IDs must be unique"):
        ReviewBundle.model_validate(duplicate_id)
