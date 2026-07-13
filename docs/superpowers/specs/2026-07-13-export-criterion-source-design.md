# Export Criterion Source Transparency Design

## Problem

The accepted MVP reporting contract requires criterion source in exports. JSON already preserves both
the exact confirmed `ReviewBundle.source_text` and every criterion's validated `criterion_source`.
Markdown, CSV, and HTML currently show normalized criterion text without either source field. A reader
therefore cannot tell from those reports whether a criterion came from user-confirmed requirements or
an explicit local rule pack, nor compare the normalized list with the confirmed input.

## Decision

Render both existing validated source layers without changing schemas:

- Markdown adds a `Confirmed Requirements Source` section containing the exact source text and adds a
  `Source` column to the evidence matrix.
- CSV adds `requirements_source_text` and `criterion_source` columns to every flat criterion row.
- HTML adds an escaped confirmed-source section and a `Source` table column.

JSON remains unchanged because it already contains both fields. The values are rendered as stored;
no source inference, normalization, or evidence generation occurs during export.

## Safety and Compatibility

- The change is additive and limited to report rendering.
- Criteria must still be user-confirmed before analysis; gates and evidence semantics do not change.
- HTML source text is escaped and line breaks are rendered without executable content.
- No API, network call, dependency, billing, secret, or untrusted-code execution is added.
- Existing export determinism and historical-review preservation remain intact.

## Verification

Regression tests will require exact source text and criterion-source classification in all formats,
including HTML escaping. Focused tests, Ruff, the complete offline suite, deterministic benchmark,
wheel build, and installed CLI exports will run before protected publication.
