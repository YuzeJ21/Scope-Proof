# Export Identity Completeness Design

## Problem

The accepted public MVP contract says exports contain the review identity, repository, pull request,
head SHA, version provenance, and a generation timestamp. The validated `Review` model already stores
`review_id`, `base_sha`, `head_sha`, `created_at`, `tool_version`, and `ruleset_version`, and JSON
exports retain all of them. The human-readable exports are inconsistent:

- Markdown and HTML omit the review ID, base SHA, and review creation timestamp.
- CSV includes the review ID but omits the base SHA and review creation timestamp.

Two reports can therefore be harder to associate with the same durable local review or the exact
base-to-head comparison that produced its evidence.

## Decision

Expose the existing validated review identity consistently in every export:

- Markdown adds review ID, base SHA, and `created_at` labeled as `Review created`.
- CSV adds `base_sha` and `review_created_at` columns alongside the existing identity columns.
- HTML adds review ID, base SHA, and `created_at` labeled as `Review created` in its identity summary.

Serialize the timestamp through Pydantic's JSON mode, matching the canonical JSON export. Reuse the
stored review timestamp instead of calling the clock during export. This keeps repeated exports of the
same validated review byte-for-byte deterministic and preserves historical identity when reopened.

## Alternatives Considered

1. Generate a new timestamp every time an exporter runs. Rejected because identical validated input
   would no longer produce reproducible output, and the timestamp would not identify the analysis.
2. Add a new report-envelope schema with a separate export timestamp. Rejected for this bounded slice
   because every exporter currently accepts a validated `ReviewBundle` or `ReviewState`, persisted
   records do not store an export event, and no product behavior needs that extra lifecycle concept.
3. Keep format-specific subsets. Rejected because it preserves the verified contract mismatch and
   makes cross-format audit comparison unnecessarily difficult.

## Safety and Compatibility

- No evidence, finding, human resolution, gate, or lifecycle semantics change.
- No untrusted repository code is executed.
- No API, dependency, credential, billing, telemetry, or network behavior is added.
- Historical stored review fields are rendered as stored; current package values do not overwrite them.
- CSV is additive: existing columns and values remain unchanged.
- All rendered HTML values are escaped.

## Verification

Regression tests will assert the same review ID, base SHA, and ISO-formatted review creation timestamp
in JSON, Markdown, CSV, and HTML; verify historical values remain intact; and cover HTML escaping for
the newly rendered identity values. Focused exporter tests, Ruff, the full offline suite, deterministic
benchmark, packaging checks, and real CLI exports will run before protected publication.
