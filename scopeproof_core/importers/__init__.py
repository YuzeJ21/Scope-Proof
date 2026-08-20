"""Bounded, non-executing import adapters for externally supplied evidence."""

from scopeproof_core.importers.junit import (
    MAX_JUNIT_BYTES,
    MAX_JUNIT_CASES,
    MAX_JUNIT_ELEMENTS,
    MAX_JUNIT_SUITES,
    JUnitImportError,
    JUnitMappingSelection,
    ParsedJUnitArtifact,
    ParsedJUnitSuite,
    build_junit_evidence_import,
    parse_junit_artifact,
)

__all__ = [
    "MAX_JUNIT_BYTES",
    "MAX_JUNIT_CASES",
    "MAX_JUNIT_ELEMENTS",
    "MAX_JUNIT_SUITES",
    "JUnitImportError",
    "JUnitMappingSelection",
    "ParsedJUnitArtifact",
    "ParsedJUnitSuite",
    "build_junit_evidence_import",
    "parse_junit_artifact",
]
