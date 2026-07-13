# Evidence Matrix Contract Completeness Design

## Problem

The accepted public MVP contract says the evidence matrix displays criterion, priority,
provisional status, evidence level, confidence band, evidence count, concern, and human resolution.
The current Streamlit matrix omits evidence count, concern, and human resolution. Human-readable
exports are also inconsistent: Markdown omits confidence, count, and concern; CSV omits count and
concern; HTML omits confidence, count, concern, and human resolution. This prevents a reviewer from
comparing the on-screen summary with exported audit records without opening each criterion detail.

## Decision

Render the complete existing matrix contract from the validated `ReviewBundle` in the Streamlit UI,
Markdown, CSV, and HTML:

- `Evidence count` is `len(finding.evidence_ids)`. It counts deterministic candidate evidence bound
  to the provisional finding only.
- `Concern` is the existing `finding.reason` and does not infer a new conclusion.
- `Human resolution` is the current `HumanResolution.decision`; unresolved criteria display
  `Unresolved` in human-readable summaries and an empty value in CSV.
- `Confidence` remains the existing `finding.confidence_band`.

JSON is unchanged because it already preserves findings, evidence IDs, and resolutions in validated
structured objects. Manual runtime evidence remains separate and is never added to the static
candidate evidence count or used to upgrade provisional findings.

## Approaches Considered

1. Update only Streamlit. Rejected because exports would continue to disagree with the screen.
2. Update only exports. Rejected because the primary review workflow would still hide required
   summary information.
3. Update the UI and all human-readable exports from the same stored fields. Selected because it
   satisfies the explicit matrix and export-parity contracts without changing domain behavior.

## Presentation

The Streamlit and Markdown tables add `Count`, `Concern`, and `Human resolution`; Markdown also adds
`Confidence`. HTML adds the same columns. CSV adds `evidence_count` and `concern` beside its existing
confidence and human-decision columns. Existing detail sections, filters, and compact per-row fallback
text remain unchanged.

## Safety and Compatibility

- No evidence retrieval, verification, human-resolution, lifecycle, or gate semantics change.
- No schema, dependency, API, billing, network, telemetry, or credential behavior changes.
- HTML values are escaped; Markdown table cells retain the existing pipe/newline escaping behavior.
- Candidate evidence and manual runtime evidence remain visibly and semantically separate.
- Existing CSV columns remain unchanged; new columns are additive.

## Verification

Regression tests will prove all required matrix fields in AppTest, Markdown, parsed CSV, and HTML;
prove an unresolved criterion is labeled explicitly; prove HTML escapes concern text; and confirm the
candidate count excludes manual runtime evidence. Verification includes focused tests, Ruff, the full
offline suite, deterministic benchmark, built-wheel CLI exports, and a real Streamlit HTTP/AppTest
smoke before protected publication.
