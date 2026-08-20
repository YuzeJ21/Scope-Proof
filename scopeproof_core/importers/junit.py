"""Parse bounded JUnit XML bytes without executing or dereferencing artifact content."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import uuid4
from xml.etree import ElementTree

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from scopeproof_core.criteria.confirmation import normalized_criteria_sha256
from scopeproof_core.gates.validation import validated_review_state
from scopeproof_core.schemas.models import (
    JUnitCaseResult,
    JUnitCaseStatus,
    JUnitCriterionMapping,
    JUnitEvidenceImport,
    JUnitResultTotals,
    ReviewState,
)

MAX_JUNIT_BYTES = 1_048_576
MAX_JUNIT_SUITES = 100
MAX_JUNIT_CASES = 5_000
MAX_JUNIT_ELEMENTS = 20_000
MAX_JUNIT_NAME_LENGTH = 512

_EXACT_HEAD = re.compile(r"^[a-f0-9]{40}$")
_XML_ENCODING = re.compile(
    r"<\?xml\b[^>]*\bencoding\s*=\s*(['\"])([^'\"]+)\1",
    re.IGNORECASE,
)
_OTHER_PROCESSING_INSTRUCTION = re.compile(
    r"<\?(?!xml(?:\s|\?>))",
    re.IGNORECASE,
)
_STABLE_SCOPE = r"^suite-\d{4}(?:-case-\d{4})?$"
_DISCARDED_WARNING = (
    "JUnit properties and output content were discarded during import."
)
_COUNT_WARNING = (
    "Declared JUnit counts differed from the sanitized observed results."
)
_FIXED_LIMITATIONS = (
    "ScopeProof did not execute the imported tests or target-repository code.",
    "The artifact digest does not prove criterion correctness or runtime behavior.",
    "The asserted importer identity is not authenticated.",
)


class JUnitImportError(ValueError):
    """A bounded public error that never exposes artifact contents."""


class ParsedJUnitSuite(BaseModel):
    """One sanitized suite projection with deterministic document-order IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    suite_id: str = Field(pattern=r"^suite-\d{4}$")
    suite_name: str = Field(min_length=1, max_length=MAX_JUNIT_NAME_LENGTH)
    test_cases: list[JUnitCaseResult] = Field(default_factory=list)


class ParsedJUnitArtifact(BaseModel):
    """Validated parser output containing no raw XML or ignored bodies."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["junit-parsed-v1"] = "junit-parsed-v1"
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    artifact_format: Literal["junit_xml"] = "junit_xml"
    suites: list[ParsedJUnitSuite] = Field(max_length=MAX_JUNIT_SUITES)
    totals: JUnitResultTotals
    parser_warnings: list[str] = Field(default_factory=list, max_length=100)


class JUnitMappingSelection(BaseModel):
    """One explicit human choice before selectors are resolved to case IDs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    scope_id: str = Field(pattern=_STABLE_SCOPE)
    criterion_id: str = Field(min_length=1)

    @field_validator("criterion_id")
    @classmethod
    def normalize_criterion_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("criterion ID must contain non-whitespace text")
        return normalized


class JUnitMappingDocument(BaseModel):
    """Strict local mapping-file contract for CLI imports."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["junit-mapping-v1"] = "junit-mapping-v1"
    selections: list[JUnitMappingSelection] = Field(min_length=1, max_length=5_000)


def _local_name(tag: object) -> str:
    if not isinstance(tag, str):
        raise JUnitImportError("JUnit XML contains an unsupported element tag.")
    if tag.startswith("{http://www.w3.org/2001/XInclude}"):
        raise JUnitImportError("JUnit XML must not contain XInclude elements.")
    if tag.startswith("{"):
        raise JUnitImportError("JUnit XML namespaces are unsupported.")
    return tag


def _bounded_name(value: str | None, *, fallback: str | None = None) -> str:
    normalized = (value or "").strip()
    if not normalized and fallback is not None:
        normalized = fallback
    if not normalized:
        raise JUnitImportError("JUnit test cases require a non-blank test name.")
    if len(normalized) > MAX_JUNIT_NAME_LENGTH:
        raise JUnitImportError("JUnit names exceed the supported length.")
    return normalized


def _optional_bounded_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_JUNIT_NAME_LENGTH:
        raise JUnitImportError("JUnit names exceed the supported length.")
    return normalized


def _declared_count(element: ElementTree.Element, name: str) -> int | None:
    raw = element.attrib.get(name)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise JUnitImportError("JUnit declared counts must be non-negative integers.") from None
    if value < 0:
        raise JUnitImportError("JUnit declared counts must be non-negative integers.")
    return value


def _totals_for_cases(cases: list[JUnitCaseResult]) -> JUnitResultTotals:
    counts = {
        JUnitCaseStatus.PASSED: 0,
        JUnitCaseStatus.FAILURE: 0,
        JUnitCaseStatus.ERROR: 0,
        JUnitCaseStatus.SKIPPED: 0,
    }
    for item in cases:
        counts[item.status] += 1
    return JUnitResultTotals(
        total=len(cases),
        passed=counts[JUnitCaseStatus.PASSED],
        failures=counts[JUnitCaseStatus.FAILURE],
        errors=counts[JUnitCaseStatus.ERROR],
        skipped=counts[JUnitCaseStatus.SKIPPED],
    )


def _declared_counts_differ(
    element: ElementTree.Element, totals: JUnitResultTotals
) -> bool:
    declared = {
        "tests": _declared_count(element, "tests"),
        "failures": _declared_count(element, "failures"),
        "errors": _declared_count(element, "errors"),
        "skipped": _declared_count(element, "skipped"),
    }
    observed = {
        "tests": totals.total,
        "failures": totals.failures,
        "errors": totals.errors,
        "skipped": totals.skipped,
    }
    return any(value is not None and value != observed[name] for name, value in declared.items())


def _parse_case(
    element: ElementTree.Element,
    *,
    suite_id: str,
    suite_name: str,
    case_number: int,
) -> tuple[JUnitCaseResult, bool]:
    result_markers: list[str] = []
    discarded = False
    for child in element:
        name = _local_name(child.tag)
        if name in {"failure", "error", "skipped"}:
            result_markers.append(name)
        elif name in {"properties", "system-out", "system-err"}:
            discarded = True
        else:
            raise JUnitImportError("JUnit test case contains an unsupported result structure.")
    if len(result_markers) > 1:
        raise JUnitImportError("JUnit test case contains multiple result markers.")
    marker = result_markers[0] if result_markers else "passed"
    try:
        result = JUnitCaseResult(
            test_case_id=f"{suite_id}-case-{case_number:04d}",
            suite_id=suite_id,
            suite_name=suite_name,
            class_name=_optional_bounded_name(element.attrib.get("classname")),
            test_name=_bounded_name(element.attrib.get("name")),
            status=JUnitCaseStatus(marker),
        )
    except ValidationError:
        raise JUnitImportError("JUnit names exceed the supported length or shape.") from None
    return result, discarded


def _parse_suite(
    element: ElementTree.Element, suite_number: int
) -> tuple[ParsedJUnitSuite, bool, bool]:
    suite_id = f"suite-{suite_number:04d}"
    suite_name = _bounded_name(
        element.attrib.get("name"), fallback=f"Unnamed suite {suite_number:04d}"
    )
    test_cases: list[JUnitCaseResult] = []
    discarded = False
    for child in element:
        name = _local_name(child.tag)
        if name == "testcase":
            if len(test_cases) >= MAX_JUNIT_CASES:
                raise JUnitImportError("JUnit artifact exceeds the test-case limit.")
            case, case_discarded = _parse_case(
                child,
                suite_id=suite_id,
                suite_name=suite_name,
                case_number=len(test_cases) + 1,
            )
            test_cases.append(case)
            discarded = discarded or case_discarded
        elif name == "testsuite":
            raise JUnitImportError("Nested JUnit test suites are unsupported.")
        elif name in {"properties", "system-out", "system-err"}:
            discarded = True
        else:
            raise JUnitImportError("JUnit test suite contains an unsupported structure.")
    totals = _totals_for_cases(test_cases)
    differs = _declared_counts_differ(element, totals)
    return (
        ParsedJUnitSuite(
            suite_id=suite_id,
            suite_name=suite_name,
            test_cases=test_cases,
        ),
        discarded,
        differs,
    )


def parse_junit_artifact(artifact_bytes: bytes) -> ParsedJUnitArtifact:
    """Return a bounded sanitized projection without interpreting external references."""

    if not isinstance(artifact_bytes, bytes):
        raise TypeError("JUnit artifact input must be bytes")
    if not artifact_bytes:
        raise JUnitImportError("JUnit artifact is empty.")
    if len(artifact_bytes) > MAX_JUNIT_BYTES:
        raise JUnitImportError("JUnit artifact exceeds the byte limit.")
    try:
        text = artifact_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise JUnitImportError("JUnit artifact must use UTF-8 encoding.") from None
    encoding_match = _XML_ENCODING.search(text)
    if encoding_match is not None and encoding_match.group(2).lower().replace("_", "-") not in {
        "utf-8",
        "utf8",
    }:
        raise JUnitImportError("JUnit artifact must use UTF-8 encoding.")
    upper_text = text.upper()
    if "<!DOCTYPE" in upper_text or "<!ENTITY" in upper_text:
        raise JUnitImportError("JUnit artifact contains a forbidden XML construct.")
    if _OTHER_PROCESSING_INSTRUCTION.search(text):
        raise JUnitImportError("JUnit artifact contains a forbidden processing instruction.")
    if "HTTP://WWW.W3.ORG/2001/XINCLUDE" in upper_text or "<XI:INCLUDE" in upper_text:
        raise JUnitImportError("JUnit XML must not contain XInclude elements.")
    try:
        root = ElementTree.fromstring(text)
    except (ElementTree.ParseError, ValueError):
        raise JUnitImportError("JUnit artifact contains malformed XML.") from None
    elements = list(root.iter())
    if len(elements) > MAX_JUNIT_ELEMENTS:
        raise JUnitImportError("JUnit artifact exceeds the element limit.")
    for element in elements:
        _local_name(element.tag)

    root_name = _local_name(root.tag)
    if root_name == "testsuite":
        suite_elements = [root]
        root_discarded = False
    elif root_name == "testsuites":
        suite_elements = []
        root_discarded = False
        for child in root:
            child_name = _local_name(child.tag)
            if child_name == "testsuite":
                suite_elements.append(child)
            elif child_name in {"properties", "system-out", "system-err"}:
                root_discarded = True
            else:
                raise JUnitImportError(
                    "JUnit testsuites root requires direct testsuite children."
                )
    else:
        raise JUnitImportError("JUnit artifact root must be testsuite or testsuites.")
    if len(suite_elements) > MAX_JUNIT_SUITES:
        raise JUnitImportError("JUnit artifact exceeds the suite limit.")

    suites: list[ParsedJUnitSuite] = []
    discarded = root_discarded
    declared_mismatch = False
    total_cases = 0
    for suite_number, element in enumerate(suite_elements, start=1):
        suite, suite_discarded, suite_mismatch = _parse_suite(element, suite_number)
        total_cases += len(suite.test_cases)
        if total_cases > MAX_JUNIT_CASES:
            raise JUnitImportError("JUnit artifact exceeds the test-case limit.")
        suites.append(suite)
        discarded = discarded or suite_discarded
        declared_mismatch = declared_mismatch or suite_mismatch

    all_cases = [item for suite in suites for item in suite.test_cases]
    totals = _totals_for_cases(all_cases)
    if root_name == "testsuites":
        declared_mismatch = declared_mismatch or _declared_counts_differ(root, totals)
    warnings: list[str] = []
    if discarded:
        warnings.append(_DISCARDED_WARNING)
    if declared_mismatch:
        warnings.append(_COUNT_WARNING)
    return ParsedJUnitArtifact(
        artifact_sha256=sha256(artifact_bytes).hexdigest(),
        suites=suites,
        totals=totals,
        parser_warnings=warnings,
    )


def build_junit_evidence_import(
    state: ReviewState,
    artifact_bytes: bytes,
    selections: list[JUnitMappingSelection],
    *,
    importer: str,
    limitations: list[str] | None = None,
    imported_at: datetime | None = None,
    import_id: str | None = None,
) -> JUnitEvidenceImport:
    """Bind sanitized external test results to one exact active review snapshot."""

    state = validated_review_state(state)
    if state.bundle is None:
        raise ValueError("JUnit import requires an active analysis")
    bundle = state.bundle
    provenance = bundle.review.criteria_source_provenance
    if provenance is None or not bundle.review.criteria_confirmed:
        raise ValueError("JUnit import requires confirmed criteria provenance")
    if _EXACT_HEAD.fullmatch(bundle.review.head_sha) is None:
        raise ValueError("JUnit import requires an exact 40-character head SHA")
    normalized_importer = importer.strip()
    if not normalized_importer:
        raise ValueError("JUnit importer must contain non-whitespace text")
    supplied_limitations = [] if limitations is None else [item.strip() for item in limitations]
    if any(not item for item in supplied_limitations):
        raise ValueError("JUnit limitations must contain non-whitespace text")
    if not selections:
        raise JUnitImportError("JUnit import requires at least one explicit mapping.")
    validated_selections = [
        JUnitMappingSelection.model_validate(item.model_dump(mode="python"))
        for item in selections
    ]
    parsed = parse_junit_artifact(artifact_bytes)
    if any(
        existing.artifact_sha256 == parsed.artifact_sha256
        for existing in bundle.junit_evidence_imports
    ):
        raise JUnitImportError("Duplicate JUnit artifact digest is already imported.")
    resolved_import_id = import_id or str(uuid4())
    if any(existing.import_id == resolved_import_id for existing in bundle.junit_evidence_imports):
        raise JUnitImportError("Duplicate JUnit import ID is already recorded.")

    known_criteria = {criterion.criterion_id for criterion in bundle.criteria}
    scopes: dict[str, list[str]] = {}
    test_cases: list[JUnitCaseResult] = []
    for suite in parsed.suites:
        suite_case_ids = [item.test_case_id for item in suite.test_cases]
        scopes[suite.suite_id] = suite_case_ids
        for item in suite.test_cases:
            scopes[item.test_case_id] = [item.test_case_id]
            test_cases.append(item)
    mapped: dict[str, set[str]] = defaultdict(set)
    for selection in validated_selections:
        if selection.criterion_id not in known_criteria:
            raise JUnitImportError("JUnit mapping references an unknown criterion.")
        case_ids = scopes.get(selection.scope_id)
        if case_ids is None:
            raise JUnitImportError("JUnit import references an unknown mapping scope.")
        if not case_ids:
            raise JUnitImportError("JUnit mapping scope contains no test cases.")
        mapped[selection.criterion_id].update(case_ids)
    if not mapped or not any(mapped.values()):
        raise JUnitImportError("JUnit import requires at least one explicit mapping.")
    criterion_mappings = [
        JUnitCriterionMapping(
            criterion_id=criterion_id,
            test_case_ids=sorted(case_ids),
        )
        for criterion_id, case_ids in sorted(mapped.items())
    ]
    return JUnitEvidenceImport(
        import_id=resolved_import_id,
        repository=bundle.review.repository,
        pr_number=bundle.review.pr_number,
        head_sha=bundle.review.head_sha,
        criteria_revision_number=state.criteria_revision.number,
        confirmed_criteria_sha256=normalized_criteria_sha256(bundle.criteria),
        criteria_source_provenance=provenance.model_copy(deep=True),
        artifact_sha256=parsed.artifact_sha256,
        imported_by=normalized_importer,
        imported_at=imported_at or datetime.now(UTC),
        totals=parsed.totals,
        test_cases=sorted(test_cases, key=lambda item: item.test_case_id),
        criterion_mappings=criterion_mappings,
        parser_warnings=parsed.parser_warnings,
        limitations=list(dict.fromkeys((*_FIXED_LIMITATIONS, *supplied_limitations))),
    )
