# Bounded JUnit Evidence Adapter Design

**Date:** 2026-08-20
**Stage:** Owner-led Stage 2 productization
**Status:** Approved for implementation by the owner
**Target branch:** `codex/junit-evidence-adapter`

## Objective

Add one local, non-executing adapter that imports bounded JUnit-style XML as
provenance-bound external test-result context. The adapter helps a reviewer
inspect supplied test results without converting them into correctness,
runtime-verification, acceptance, CI, or customer-validation claims.

The adapter never runs target-repository code, follows references, fetches a
URL, opens an artifact path found inside XML, or persists raw XML. Failed
parsing, mapping, validation, or storage leaves the saved review unchanged.

## Evidence taxonomy

Imported JUnit results are a new orthogonal record type named
`JUnitEvidenceImport`. They are not `EvidenceItem` candidates and therefore do
not become E1 or E2. They are not `RuntimeEvidence` and therefore do not become
E3 or E4. They are not `CIObservation`, `HumanResolution`, or final acceptance.

The deterministic gate continues to consume only the existing review,
criteria, findings, and current human resolutions. Adding an import cannot
create, rescue, or justify a Ready verdict. A previously valid verdict may be
displayed beside an import only because the pre-existing gate inputs still
justify it; the import remains explicitly non-gating.

Every product surface labels the record as externally supplied and states:

- ScopeProof did not execute the tests or target-repository code.
- The artifact digest proves only which bytes were imported.
- The importer identity is asserted, not authenticated.
- Explicit human mapping is organizational context, not proof that a criterion
  passed.

## Architecture

### Persisted schemas

`scopeproof_core/schemas/models.py` owns the persisted Pydantic types:

- `JUnitCaseStatus`: `passed`, `failure`, `error`, or `skipped`.
- `JUnitCaseResult`: stable document-order IDs, bounded suite/class/test names,
  and one status. Failure bodies, stdout, stderr, properties, commands, paths,
  URLs, and attachments are never persisted. Path- or URL-like names are
  replaced with deterministic redacted labels.
- `JUnitResultTotals`: total, passed, failure, error, and skipped counts whose
  sum must equal total.
- `JUnitCriterionMapping`: one confirmed criterion ID and a sorted unique list
  of stable test-case IDs.
- `JUnitEvidenceImport`: a frozen `junit-import-v1` envelope containing import
  ID, review identity, exact head, criteria revision and source provenance,
  artifact digest, sanitized case results, totals, explicit mappings, asserted
  importer metadata, warnings, and limitations.
- `JUnitImportMutationMetadata`: validated CLI result metadata.

`ReviewBundle.junit_evidence_imports` is an append-only list with an empty
default so historical records remain readable without inventing imports.
Bundle validation enforces:

- repository, PR, and exact head match the owning review;
- criteria revision and normalized digest match the active bundle;
- copied source provenance exactly matches the review;
- every mapped criterion and case exists;
- import IDs and artifact digests are unique;
- imports never appear in static evidence, runtime evidence, resolutions, or
  gate cross-references.

The outer local-review record stays at version 4 because an absent
`junit_evidence_imports` field has one unambiguous meaning: no imported JUnit
record. The nested import is independently versioned and strict.

### Parser and import service

Create `scopeproof_core/importers/junit.py`. Its public interface is:

```python
MAX_JUNIT_BYTES = 1_048_576
MAX_JUNIT_SUITES = 100
MAX_JUNIT_CASES = 5_000
MAX_JUNIT_ELEMENTS = 20_000

def parse_junit_artifact(artifact_bytes: bytes) -> ParsedJUnitArtifact: ...

def build_junit_evidence_import(
    state: ReviewState,
    artifact_bytes: bytes,
    selections: list[JUnitMappingSelection],
    *,
    importer: str,
    limitations: list[str] | None = None,
    imported_at: datetime | None = None,
    import_id: str | None = None,
) -> JUnitEvidenceImport: ...
```

`ParsedJUnitArtifact`, `ParsedJUnitSuite`, and `JUnitMappingSelection` are
strict Pydantic boundary types. Scope IDs are deterministic document-order
identifiers: `suite-0001` and `suite-0001-case-0001`. A suite selection expands
to all cases in that suite; a case selection expands to that one case. The
persisted record contains only resolved case-to-criterion mappings, so no
selector needs to be reinterpreted after import.

At least one mapping selection and at least one mapped case are required.
Mappings are never inferred from suite, class, or test names. Duplicate pairs
are canonicalized; unknown, empty, or conflicting selectors fail closed.

### XML safety and boundedness

The parser accepts bytes, checks the byte limit before decoding, and accepts
UTF-8 only. UTF-8 BOM is allowed; any other declared encoding is rejected.
Before tree construction it rejects XML containing a document type,
entities, processing instructions other than the XML declaration, or obvious
XInclude markup. After parsing it rejects any XInclude namespace element and
enforces element, suite, and test-case limits.

Accepted roots are one `testsuite` or one `testsuites` with direct
`testsuite` children. Nested suites, test cases outside suites, multiple result
markers, unknown result-marker structures, and missing test names fail closed.
Observed statuses come only from zero or one direct `failure`, `error`, or
`skipped` marker. Zero markers means passed.

Declared JUnit counts are not trusted. ScopeProof computes totals from parsed
cases. A non-negative declared count that differs from the observed count adds
a deterministic warning. Invalid numeric declarations fail closed. Presence of
ignored `system-out`, `system-err`, or `properties` adds one bounded warning;
their contents are never retained.

### Lifecycle and atomic persistence

Add `append_junit_evidence_import(state, record)` to the core lifecycle. It
revalidates both objects, verifies the active bundle and all identity fields,
rejects duplicate artifact digests and IDs, appends a deep copy, and confirms
that findings, resolutions, runtime evidence, final acceptance, and the
deterministic gate are byte-for-byte unchanged.

The CLI uses `JsonReviewStore.mutate`, so parsing and lifecycle validation run
inside the serialized read-transition-write boundary. Any exception prevents
the replacement write. Streamlit applies the same lifecycle function to its
validated session state; the existing local-save path performs persistence.

Criteria revision moves the prior active bundle, including its import records,
to analysis history. A later active analysis begins with no imports. There is
no automatic carry-forward or remapping.

### CLI

Add two commands:

```text
scopeproof inspect-junit ARTIFACT
scopeproof import-junit REVIEW_ID ARTIFACT --mapping MAPPING.json \
  --importer "Asserted name" [--limitation TEXT ...] [--storage-dir PATH]
```

`inspect-junit` prints the validated sanitized parser result, including scope
IDs and computed totals. It never persists anything.

The strict mapping document is:

```json
{
  "schema_version": "junit-mapping-v1",
  "artifact_sha256": "COPY_THE_64_CHARACTER_DIGEST_FROM_INSPECT_JUNIT",
  "selections": [
    {"scope_id": "suite-0001", "criterion_id": "AC-01"}
  ]
}
```

`import-junit` reads the explicitly named local artifact and mapping files,
requires the mapping digest to match the bounded artifact bytes, builds the
record through the shared core service, applies the atomic lifecycle transition,
and prints `JUnitImportMutationMetadata`. It never persists file paths or raw XML.

### Streamlit

Add a collapsed section named `Import external JUnit results` beside the
selected criterion controls, visually separate from candidate evidence and
`Record optional external verification (E3/E4)`.

The user uploads one XML file, enters an asserted importer, previews sanitized
suites/cases and warnings, explicitly selects one or more scope IDs, and maps
them to the already selected criterion. Save is disabled until the artifact,
importer, and mapping are valid. Successful save appends the import in session,
clears upload/mapping form state, and shows the non-gating boundary. Failure
shows a bounded error and leaves the state unchanged.

Recorded imports are shown by selected criterion and display digest, exact
review identity, mapped sanitized cases/statuses, asserted importer, timestamp,
warnings, and limitations. Raw XML and ignored output never render.

### Exports and comparison

JSON naturally includes validated import envelopes. Markdown and HTML add an
`Imported external test results` section using inert escaped text. CSV adds
criterion-level imported artifact digests, mapped case IDs/statuses, asserted
importers, warnings, and limitations with spreadsheet-formula neutralization.

Comparison revalidates both bundles and projects imported records by artifact
digest plus explicit mapping signature. It reports added, removed, unchanged,
or mapping-modified imports. Changed imported context adds affected criteria to
`criteria_requiring_decision_review` only when the previous bundle has a human
resolution for that criterion. It does not copy a resolution or alter either
gate.

### Browser proof

The installed-wheel Chromium regression creates a synthetic exact-head saved
review using installed ScopeProof code, opens it in the packaged workbench,
uploads a small local JUnit fixture, explicitly maps its suite to a criterion,
saves the import, verifies the displayed boundary, saves/reopens the review,
and downloads JSON and Markdown containing the artifact digest but not raw XML
or ignored output. Browser networking remains loopback-only.

## Error behavior

Public errors are deterministic categories rather than parser internals:

- artifact too large;
- unsupported encoding;
- forbidden XML construct;
- malformed or unsupported JUnit structure;
- suite/case/element limit exceeded;
- invalid or unknown mapping scope;
- review identity, criteria, or provenance mismatch;
- duplicate or conflicting import;
- stale saved-state mutation.

No error includes raw XML, failure text, stdout/stderr, local file contents, or
credentials.

## Verification and non-goals

The implementation requires focused red-green tests plus the complete suite,
95% coverage gate, repository contracts, deterministic and comparison
benchmarks, reproducible wheels, clean installation, installed CLIs and
benchmarks, workbench health, installed-wheel Chromium, supported Python lanes,
hosted Windows, final diff audit, and independent review.

This slice does not authenticate reviewers, add accounts, host source or
artifacts, support private repositories, make the GitHub Action required,
release or publish `0.2.4`, retune R-002, generate R-003, begin Stage 3, reopen
Stage 1, or claim accessibility, customer, demand, adoption, or correctness
evidence.

Stage 1 remains closed as not pursued at 0/5 qualifying reviews, 0/3
independent practitioners, 0/3 public repositories, 0/3 independently observed
under-ten-minute completions, and 0/2 reuse-intent signals.
