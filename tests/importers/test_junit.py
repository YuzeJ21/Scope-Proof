from datetime import UTC, datetime
from hashlib import sha256

import pytest
from pydantic import ValidationError

import scopeproof_core.importers.junit as junit_module
from scopeproof_core.demo import build_demo_review
from scopeproof_core.importers.junit import (
    JUnitImportError,
    JUnitMappingDocument,
    JUnitMappingSelection,
    build_junit_evidence_import,
    parse_junit_artifact,
)
from scopeproof_core.reviews.lifecycle import new_review_state
from scopeproof_core.schemas.models import JUnitCaseStatus, ReviewBundle, ReviewState

HEAD_SHA = "a" * 40
SIMPLE_XML = b'<testsuite name="unit"><testcase name="test_export"/></testsuite>'
TWO_CASE_XML = (
    b'<testsuites tests="2" failures="1" errors="0" skipped="0">'
    b'<testsuite name="unit" tests="2" failures="1">'
    b'<testcase classname="tests.Widget" name="test_export"/>'
    b'<testcase name="test_error"><failure message="boom">secret body</failure></testcase>'
    b'</testsuite></testsuites>'
)


def exact_head_state() -> ReviewState:
    bundle = build_demo_review().model_copy(deep=True)
    bundle.review.head_sha = HEAD_SHA
    bundle = ReviewBundle.model_validate(bundle.model_dump(mode="python"))
    return new_review_state(bundle)


def first_criterion_id(state: ReviewState) -> str:
    assert state.bundle is not None
    return state.bundle.criteria[0].criterion_id


def test_parser_returns_sanitized_cases_and_computed_totals() -> None:
    parsed = parse_junit_artifact(TWO_CASE_XML)

    assert parsed.artifact_sha256 == sha256(TWO_CASE_XML).hexdigest()
    assert parsed.totals.model_dump() == {
        "total": 2,
        "passed": 1,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
    }
    assert [suite.suite_id for suite in parsed.suites] == ["suite-0001"]
    assert [item.test_case_id for item in parsed.suites[0].test_cases] == [
        "suite-0001-case-0001",
        "suite-0001-case-0002",
    ]
    assert parsed.suites[0].test_cases[1].status is JUnitCaseStatus.FAILURE
    serialized = parsed.model_dump_json()
    assert "secret body" not in serialized
    assert "boom" not in serialized


def test_parser_discards_output_and_properties_with_one_bounded_warning() -> None:
    secret = "SENTINEL-OUTPUT-DO-NOT-PERSIST"
    xml = (
        '<testsuite name="unit"><properties><property name="token" value="hidden"/>'
        f'</properties><testcase name="safe"/><system-out>{secret}</system-out>'
        '<system-err>also hidden</system-err></testsuite>'
    ).encode()

    parsed = parse_junit_artifact(xml)

    assert parsed.parser_warnings == [
        "JUnit properties and output content were discarded during import."
    ]
    assert secret not in parsed.model_dump_json()
    assert "hidden" not in parsed.model_dump_json()


def test_parser_redacts_path_and_url_like_names_before_persistence() -> None:
    xml = (
        b'<testsuite name="https://ci.example.test/jobs/42">'
        b'<testcase classname="/workspace/tests/test_export.py" '
        b'name="C:\\agent\\tests\\test_export.py"/></testsuite>'
    )

    parsed = parse_junit_artifact(xml)

    suite = parsed.suites[0]
    case = suite.test_cases[0]
    assert suite.suite_name == "Redacted suite name 0001"
    assert case.suite_name == "Redacted suite name 0001"
    assert case.class_name == "Redacted class name"
    assert case.test_name == "Redacted test name 0001"
    assert parsed.parser_warnings == [
        "Path- or URL-like JUnit names were redacted during import."
    ]
    serialized = parsed.model_dump_json()
    assert "ci.example.test" not in serialized
    assert "workspace" not in serialized
    assert "agent" not in serialized


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "mailto:secret@example.test",
        "data:,TOP-SECRET",
        "urn:example:private",
        "C:relative-secret.xml",
        "case for mailto:secret@example.test",
        "artifact C:relative-secret.xml",
    ],
)
def test_parser_redacts_scheme_like_names(unsafe_name: str) -> None:
    parsed = parse_junit_artifact(
        f'<testsuite name="unit"><testcase name="{unsafe_name}"/></testsuite>'.encode()
    )

    assert parsed.suites[0].test_cases[0].test_name == "Redacted test name 0001"
    assert unsafe_name not in parsed.model_dump_json()


def test_parser_reports_declared_count_mismatches_without_trusting_them() -> None:
    parsed = parse_junit_artifact(
        b'<testsuite name="unit" tests="99" failures="4" errors="0" skipped="0">'
        b'<testcase name="safe"/></testsuite>'
    )

    assert parsed.totals.total == 1
    assert parsed.totals.passed == 1
    assert parsed.parser_warnings == [
        "Declared JUnit counts differed from the sanitized observed results."
    ]


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        (b'<?xml version="1.0" encoding="ISO-8859-1"?><testsuite name="x"/>', "UTF-8"),
        (b'<!DOCTYPE testsuite><testsuite name="x"/>', "forbidden XML construct"),
        (
            b'<!DOCTYPE testsuite [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b'<testsuite name="x"><testcase name="&xxe;"/></testsuite>',
            "forbidden XML construct",
        ),
        (b'<?xml-stylesheet href="https://example.test/x"?><testsuite name="x"/>', "processing"),
        (
            b'<testsuite xmlns:xi="http://www.w3.org/2001/XInclude" name="x">'
            b'<xi:include href="file:///etc/passwd"/></testsuite>',
            "XInclude",
        ),
        (b'<root/>', "root"),
        (b'<testsuites><testcase name="outside"/></testsuites>', "direct testsuite"),
        (
            b'<testsuite name="outer"><testsuite name="nested">'
            b'<testcase name="x"/></testsuite></testsuite>',
            "(?i)nested",
        ),
        (b'<testsuite name="x"><testcase/></testsuite>', "test name"),
        (
            b'<testsuite name="x"><testcase name="ambiguous"><failure/><error/>'
            b'</testcase></testsuite>',
            "multiple result",
        ),
        (b'<testsuite name="x">', "malformed"),
    ],
)
def test_parser_rejects_unsafe_or_ambiguous_xml_without_leaking_input(
    xml: bytes, message: str
) -> None:
    with pytest.raises(JUnitImportError, match=message) as exc_info:
        parse_junit_artifact(xml)

    assert "file:///etc/passwd" not in str(exc_info.value)
    assert "example.test" not in str(exc_info.value)


def test_parser_rejects_non_bytes_invalid_utf8_and_blank_input() -> None:
    with pytest.raises(TypeError, match="bytes"):
        parse_junit_artifact("<testsuite/>")  # type: ignore[arg-type]
    with pytest.raises(JUnitImportError, match="UTF-8"):
        parse_junit_artifact(b"\xff\xfe")
    with pytest.raises(JUnitImportError, match="empty"):
        parse_junit_artifact(b"")


def test_parser_enforces_byte_suite_case_and_element_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(junit_module, "MAX_JUNIT_BYTES", len(SIMPLE_XML) - 1)
    with pytest.raises(JUnitImportError, match="byte limit"):
        parse_junit_artifact(SIMPLE_XML)

    monkeypatch.setattr(junit_module, "MAX_JUNIT_BYTES", 1_048_576)
    monkeypatch.setattr(junit_module, "MAX_JUNIT_SUITES", 1)
    with pytest.raises(JUnitImportError, match="suite limit"):
        parse_junit_artifact(
            b'<testsuites><testsuite name="a"/><testsuite name="b"/></testsuites>'
        )

    monkeypatch.setattr(junit_module, "MAX_JUNIT_CASES", 1)
    with pytest.raises(JUnitImportError, match="test-case limit"):
        parse_junit_artifact(
            b'<testsuite name="a"><testcase name="one"/><testcase name="two"/>'
            b'</testsuite>'
        )

    monkeypatch.setattr(junit_module, "MAX_JUNIT_CASES", 5_000)
    monkeypatch.setattr(junit_module, "MAX_JUNIT_ELEMENTS", 2)
    with pytest.raises(JUnitImportError, match="element limit"):
        parse_junit_artifact(
            b'<testsuite name="a"><testcase name="one"><skipped/></testcase>'
            b'</testsuite>'
        )


def test_mapping_selection_is_strict_and_non_blank() -> None:
    selection = JUnitMappingSelection(
        scope_id="suite-0001", criterion_id="AC-01"
    )
    assert selection.scope_id == "suite-0001"
    with pytest.raises(ValidationError):
        JUnitMappingSelection.model_validate(
            {"scope_id": "suite-0001", "criterion_id": "AC-01", "extra": True}
        )
    with pytest.raises(ValidationError, match="non-whitespace"):
        JUnitMappingSelection(scope_id="suite-0001", criterion_id=" ")


def test_mapping_document_requires_exact_artifact_digest() -> None:
    payload = {
        "schema_version": "junit-mapping-v1",
        "selections": [{"scope_id": "suite-0001", "criterion_id": "AC-01"}],
    }

    with pytest.raises(ValidationError, match="artifact_sha256"):
        JUnitMappingDocument.model_validate(payload)

    document = JUnitMappingDocument.model_validate(
        {**payload, "artifact_sha256": "a" * 64}
    )
    assert document.artifact_sha256 == "a" * 64


def test_mapping_document_requires_explicit_schema_version() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        JUnitMappingDocument.model_validate(
            {
                "artifact_sha256": "a" * 64,
                "selections": [
                    {"scope_id": "suite-0001", "criterion_id": "AC-01"}
                ],
            }
        )


def test_builder_expands_explicit_suite_mapping_and_binds_review() -> None:
    state = exact_head_state()
    criterion_id = first_criterion_id(state)

    record = build_junit_evidence_import(
        state,
        TWO_CASE_XML,
        [JUnitMappingSelection(scope_id="suite-0001", criterion_id=criterion_id)],
        importer=" QA owner ",
        limitations=[" Browser lane not supplied. "],
        imported_at=datetime(2026, 8, 20, tzinfo=UTC),
        import_id="import-001",
    )

    assert record.artifact_sha256 == sha256(TWO_CASE_XML).hexdigest()
    assert record.criterion_mappings[0].test_case_ids == [
        "suite-0001-case-0001",
        "suite-0001-case-0002",
    ]
    assert record.repository == state.review.repository
    assert record.pr_number == state.review.pr_number
    assert record.head_sha == state.review.head_sha
    assert record.criteria_revision_number == state.criteria_revision.number
    assert record.imported_by == "QA owner"
    assert record.limitations[-1] == "Browser lane not supplied."
    assert all(
        "did not execute" in item or "not" in item.lower()
        for item in record.limitations[:3]
    )


def test_builder_expands_case_mapping_and_canonicalizes_duplicate_pairs() -> None:
    state = exact_head_state()
    criterion_id = first_criterion_id(state)
    selection = JUnitMappingSelection(
        scope_id="suite-0001-case-0002", criterion_id=criterion_id
    )

    record = build_junit_evidence_import(
        state,
        TWO_CASE_XML,
        [selection, selection],
        importer="QA",
    )

    assert record.criterion_mappings[0].test_case_ids == [
        "suite-0001-case-0002"
    ]


def test_builder_rejects_one_case_mapped_to_multiple_criteria() -> None:
    state = exact_head_state()
    assert state.bundle is not None
    first, second = state.bundle.criteria[:2]

    with pytest.raises(JUnitImportError, match="multiple criteria"):
        build_junit_evidence_import(
            state,
            SIMPLE_XML,
            [
                JUnitMappingSelection(
                    scope_id="suite-0001", criterion_id=first.criterion_id
                ),
                JUnitMappingSelection(
                    scope_id="suite-0001-case-0001",
                    criterion_id=second.criterion_id,
                ),
            ],
            importer="QA",
        )


def test_builder_bounds_envelope_validation_errors_without_echoing_input() -> None:
    state = exact_head_state()
    secret = "SECRET-CREDENTIAL-" + "x" * 280

    with pytest.raises(JUnitImportError, match="metadata is invalid") as exc_info:
        build_junit_evidence_import(
            state,
            SIMPLE_XML,
            [
                JUnitMappingSelection(
                    scope_id="suite-0001",
                    criterion_id=first_criterion_id(state),
                )
            ],
            importer=secret,
        )

    assert secret not in str(exc_info.value)
    assert "SECRET-CREDENTIAL" not in str(exc_info.value)


@pytest.mark.parametrize(
    ("selections", "importer", "message"),
    [
        ([], "QA", "explicit mapping"),
        (
            [JUnitMappingSelection(scope_id="suite-9999", criterion_id="AC-01")],
            "QA",
            "unknown mapping scope",
        ),
        (
            [
                JUnitMappingSelection(
                    scope_id="suite-0001", criterion_id="AC-UNKNOWN"
                )
            ],
            "QA",
            "unknown criterion",
        ),
        ([JUnitMappingSelection(scope_id="suite-0001", criterion_id="AC-01")], " ", "importer"),
    ],
)
def test_builder_rejects_missing_or_invalid_human_mapping(
    selections: list[JUnitMappingSelection], importer: str, message: str
) -> None:
    state = exact_head_state()
    if selections and selections[0].criterion_id == "AC-01":
        selections = [
            selection.model_copy(
                update={"criterion_id": first_criterion_id(state)}
            )
            for selection in selections
        ]

    with pytest.raises((JUnitImportError, ValueError), match=message):
        build_junit_evidence_import(
            state,
            SIMPLE_XML,
            selections,
            importer=importer,
        )


def test_builder_requires_active_confirmed_exact_head_review() -> None:
    state = exact_head_state()
    criterion_id = first_criterion_id(state)
    mapping = [
        JUnitMappingSelection(scope_id="suite-0001", criterion_id=criterion_id)
    ]

    no_bundle = state.model_copy(update={"bundle": None})
    with pytest.raises(ValueError, match="active analysis"):
        build_junit_evidence_import(no_bundle, SIMPLE_XML, mapping, importer="QA")

    non_exact = state.model_copy(deep=True)
    non_exact.review.head_sha = "constructed-head"
    assert non_exact.bundle is not None
    non_exact.bundle.review.head_sha = "constructed-head"
    with pytest.raises(ValueError, match="exact 40-character"):
        build_junit_evidence_import(non_exact, SIMPLE_XML, mapping, importer="QA")


def test_builder_rejects_blank_limitations_without_exposing_artifact() -> None:
    state = exact_head_state()
    mapping = [
        JUnitMappingSelection(
            scope_id="suite-0001", criterion_id=first_criterion_id(state)
        )
    ]
    with pytest.raises(ValueError, match="limitations"):
        build_junit_evidence_import(
            state,
            SIMPLE_XML,
            mapping,
            importer="QA",
            limitations=[""],
        )
