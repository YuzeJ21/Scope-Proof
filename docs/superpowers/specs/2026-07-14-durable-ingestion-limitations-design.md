# Durable Ingestion Limitations Design

## Problem

The GitHub adapter already records bounded-ingestion warnings and skipped changed-file paths on `PullRequestSnapshot`. The review boundary copies only `ingestion_state`, so the specific limitations disappear before local storage and export. The Streamlit app consequently reports that a large PR loaded without disclosing which files were omitted or how to recover.

This does not produce a False Ready because partial ingestion already blocks the gate. It does weaken the evidence trail: an operator can see that review is incomplete only after analysis, cannot see the omitted paths, and cannot recover the details from a reopened record or exported report.

## Decision

Make ingestion limitations durable review provenance.

- Add `ingestion_warnings: list[str]` and `skipped_files: list[str]` to `Review`, with empty-list defaults for backward-compatible loading.
- Copy both fields from every `PullRequestSnapshot` at the application, CLI, and demo review boundaries.
- Show a single warning panel immediately after a partial source loads and after a saved partial review reopens. The panel states that analysis is bounded, that skipped paths were not inspected, and that the operator should narrow the PR or split it before relying on a complete review.
- Put the skipped paths in a collapsed expander to preserve the existing compact Streamlit hierarchy.
- Include ingestion state, warnings, and skipped paths in Markdown, CSV, HTML, and JSON exports. JSON gains the fields automatically through the validated model; text formats render them explicitly.
- Add the same fields to CLI completion metadata so a non-UI operator cannot miss a partial fetch.

## Safety and trust boundaries

- Gate behavior remains unchanged and deterministic: partial ingestion remains `Needs Review`.
- Warnings and paths are provenance, never evidence that a criterion passed.
- Paths and warning text are treated as untrusted repository content. HTML is escaped; Markdown list content is escaped for structural characters; CSV uses the standard writer.
- No repository code is executed.
- Existing review records remain loadable because both new fields default to empty lists.
- No paid API, LLM, organization, fork, private repository, or synthetic validation is introduced.

## UI behavior

The existing success notice remains. Directly below it, a partial source shows:

> Partial PR ingestion: ScopeProof did not inspect every changed file. Results remain bounded to the files retrieved, and the gate cannot be Ready. Narrow or split the PR, then reload it for a complete review.

Adapter warnings follow as plain text. When paths exist, a collapsed `Skipped changed files (N)` expander lists them as code-styled items. Reopened reviews render the same panel from stored `Review` provenance, even though no live snapshot is restored.

## Verification

- Schema and storage compatibility tests.
- Review-boundary tests for web, CLI, and demo construction.
- Export contract tests, including hostile HTML and Markdown path characters.
- Streamlit tests for live partial source and reopened partial review.
- Full unit suite, lint, benchmark, and a current-vs-fixed browser run against a real public PR with more than 100 changed files.

