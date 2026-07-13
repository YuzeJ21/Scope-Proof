# Export Provenance Consistency Design

## Problem

The approved MVP contract says review exports contain both the tool version and ruleset version,
but current formats disagree. A real CLI review from current main produced:

- JSON with tool `0.1.15.dev0` and ruleset `1.0.0`;
- Markdown with the ruleset but no tool version;
- CSV with `ruleset_version` but no `tool_version` column;
- HTML with neither version in its review identity summary.

This weakens audit reproducibility because two human-readable reports can share repository, PR, and
head SHA while omitting which ScopeProof producer or deterministic rule set generated them.

## Decision

Make identity provenance explicit in every export without introducing a new schema or renderer
abstraction:

- Markdown adds `**Tool version:**` beside the existing Ruleset line.
- CSV adds `tool_version` immediately before `ruleset_version` and populates every criterion row.
- HTML adds Tool and Ruleset values to the existing review identity paragraph.
- JSON remains unchanged because validated model serialization already contains both values.

The wording and field names use values from `bundle.review`; exporters never inspect package
metadata or replace provenance stored in an older review.

## Compatibility

- Markdown and HTML gain additive identity text.
- CSV gains one additive column. Existing columns retain their names, order relative to each other,
  and values; strict positional consumers must adopt the new documented column.
- Loading or exporting a historical saved review reports its historical `tool_version`, not the
  currently installed version.
- Gate, evidence, runtime evidence, resolution history, final acceptance, record version, and
  ruleset behavior remain unchanged.

## Safety and Error Behavior

All values come from an already validated `Review` model. Markdown keeps code formatting, CSV uses
the existing `csv.DictWriter`, and HTML escapes both values before rendering. No user-supplied raw
HTML, external call, runtime inference, repository-code execution, or persistence mutation is added.

## Verification

- Format-specific regression tests require tool and ruleset provenance in Markdown, CSV, and HTML.
- A historical review test proves exporters preserve an explicitly stored old tool version.
- Existing export structure, evidence links, runtime-evidence separation, and HTML escaping tests
  remain green.
- A real CLI fixture review exports all four formats; each contains tool `0.1.15.dev0` and ruleset
  `1.0.0` in its format-appropriate representation.
- Ruff, the full offline suite, deterministic benchmark, and diff hygiene remain green.

This correction ships with the next coherent release batch and does not justify a standalone
release or notification-only GitHub activity.
