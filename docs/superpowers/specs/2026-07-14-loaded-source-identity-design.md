# Loaded Source Identity Design

## Problem

After ScopeProof fetches a public pull request, the first-use screen says only that the PR loaded.
Before confirming acceptance criteria, the operator cannot see the validated repository, pull-request
number, or immutable head SHA that the forthcoming analysis will use. The URL input is not enough:
it is operator-entered text rather than the normalized identity returned by GitHub and validated by
`PullRequestSnapshot`.

Current browser evidence against `https://github.com/octocat/Hello-World/pull/1` shows the success
notice and criteria input but no fetched source identity. The identity appears only after analysis in
the final verdict area, which is too late for the criteria-confirmation boundary.

## Goal

Keep the loaded, validated source identity visible from successful source loading through criteria
confirmation and analysis. The summary must let an operator verify the repository, pull-request
number, full head SHA, changed-file count, and ingestion state before confirming criteria.

## Approaches Considered

### Recommended: persistent compact source summary

Render a compact bordered container whenever `st.session_state["snapshot"]` contains a validated
`PullRequestSnapshot`. Show the normalized repository and PR number, the full head SHA in a code
block, and a caption containing changed-file count and ingestion state. This uses existing validated
state, stays visible across Streamlit reruns, and does not alter evidence or gate semantics.

### Expand the one-time success notice

Include identity fields only in `source_load_notice`. This is smaller, but the notice is popped on the
next rerun and therefore disappears while the operator edits or confirms criteria. It does not satisfy
the persistent provenance requirement.

### Add a new source-details page or expander

A separate surface could display title, commits, checks, and files. It adds navigation and hides the
minimum identity behind another interaction. That scope is not justified by the reproduced gap.

## Design

Add a Streamlit-only helper that accepts `PullRequestSnapshot` and renders:

1. `Loaded source` as a short section label.
2. `<repository> · PR #<number>` from the validated snapshot.
3. `Head SHA` followed by the complete `snapshot.head_sha` in a code block.
4. `<N> changed file(s) fetched · <state> ingestion` with correct singular/plural copy.

Call the helper after the one-time source-load or source-reload notice and before ingestion limitation
guidance and the criteria input. Rendering from session state makes the identity persistent through
criteria editing, confirmation, and analysis. The deliberately constructed demo uses the same
validated snapshot boundary and remains covered by the existing persistent demo disclosure; the
summary must not describe it as external or production validation.

## Boundaries

- Do not change `PullRequestSnapshot`, persistence, exports, retrieval, findings, or gates.
- Do not shorten the head SHA or derive identity from the user-entered URL.
- Do not add repository links, network calls, tokens, or external assets.
- Keep all rendering in `apps/web/app.py`; the core remains independent from Streamlit.
- Preserve the existing partial-ingestion warning and recovery guidance.

## Tests

Add a Streamlit regression test that patches the GitHub client with a validated snapshot, fetches a
public PR, and asserts that repository, PR number, full head SHA, changed-file count, and complete
ingestion state are visible before any criteria are prepared. The test must also prove analysis is
still disabled. Existing partial-ingestion tests continue to prove the conservative limitation path.

Run the focused Streamlit test, the complete offline suite, Ruff, deterministic benchmark, and a
current local browser flow against the real public PR. The fixed screenshot must show the persistent
identity summary before criteria confirmation.
