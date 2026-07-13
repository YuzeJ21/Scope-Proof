# Export Identity Completeness Implementation Plan

**Goal:** Make every ScopeProof export identify the same durable review and exact base-to-head analysis.

**Architecture:** Keep identity data in the existing Pydantic-validated `Review` model. Render those
stored values directly in each exporter; do not introduce a clock call, schema migration, or mutable
report metadata.

## Task 1: Lock the cross-format contract with failing tests

1. Extend the exporter agreement test to require review ID, base SHA, and ISO `created_at` in JSON,
   Markdown, CSV, and HTML.
2. Extend the structured CSV assertion to require `base_sha` and `review_created_at`.
3. Add an HTML regression proving new free-text identity values are escaped.
4. Run focused tests and confirm failures are caused only by the missing fields.

## Task 2: Implement minimal deterministic rendering

1. Add review ID, base SHA, and stored review timestamp to the Markdown identity block.
2. Add `base_sha` and `review_created_at` to the CSV schema and rows.
3. Add escaped review ID, base SHA, and stored review timestamp to the HTML identity summary.
4. Run focused tests and Ruff.

## Task 3: Verify distribution behavior

1. Run the complete offline test suite.
2. Run the deterministic benchmark and confirm zero known must-have False Ready and False Blocker
   mismatches.
3. Build the wheel and run installed CLI exports in all four formats from a temporary environment.
4. Confirm every real report contains the same review identity fields and no report changes across a
   repeated export of the same stored review.
5. Review the diff, commit intentionally, publish one protected PR, wait for required checks, and merge
   only when green.
