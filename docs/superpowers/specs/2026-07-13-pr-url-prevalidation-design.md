# Public PR URL Prevalidation Design

## Problem

The first-use flow enables `Fetch public PR` for any non-empty string. A
malformed value therefore looks actionable until the reviewer submits it, at
which point the workbench shows only `Expected` and a URL-shaped example. The
extra failed submission is avoidable, and the recovery message does not clearly
state what to change.

Current audit evidence is saved under
`first-use-audit-2026-07-13/03-invalid-url.jpg`. It shows a non-numeric pull
request path, an enabled fetch action, and the terse post-submit error.

## Intended outcome

Before any GitHub request, the workbench distinguishes blank, malformed, and
parseable public pull-request URLs:

- blank input: no warning and `Fetch public PR` remains disabled;
- malformed non-empty input: show precise format guidance and keep fetch
  disabled;
- parseable input: hide the format warning and enable fetch unless another
  existing guard, such as unsaved-review replacement protection, applies.

The ingestion client must continue parsing the URL again when fetch begins.
UI validation is early guidance, not a replacement for the trusted boundary.

## Approaches considered

### 1. Reuse `parse_pr_url` before enabling fetch — selected

Call the same deterministic parser used by `GitHubClient.fetch_pull_request`.
This guarantees the UI and ingestion boundary accept the same URL shapes and
keeps one source of truth.

### 2. Duplicate a regular expression in the Streamlit app

This would be locally simple but could drift from the client parser, creating
URLs that appear valid in one layer and fail in another.

### 3. Keep submit-time validation and only improve the error copy

This would improve recovery language but retain the unnecessary failed action
and network-intent affordance for a value known to be malformed.

## UI behavior and copy

Immediately after the public PR URL input, validate the committed non-empty
value with `parse_pr_url`.

For a malformed value, render a warning with this exact copy:

> Enter a public GitHub pull request URL in this format: `https://github.com/OWNER/REPO/pull/NUMBER`.

The example is inline code rather than a clickable link. The input remains
unchanged so the reviewer can edit it in place. The fetch button remains
disabled until the value parses.

For a valid value, render no format warning. Existing fetch errors for missing,
private, inaccessible, rate-limited, oversized, or unreachable public PRs are
unchanged because they cannot be known from URL shape alone.

## Architecture

No new validator or schema is added. `apps/web/app.py` imports
`InvalidPullRequestUrl` and `parse_pr_url` from
`scopeproof_core.github.client`, derives a `pr_url_is_valid` boolean for the
current rerun, and includes that boolean in the existing fetch-button disabled
condition.

The core remains independent from Streamlit. `GitHubClient.fetch_pull_request`
continues calling `parse_pr_url` as defense in depth.

## Accessibility and trust boundaries

- The malformed state uses `st.warning`, which exposes visible alert semantics
  rather than relying on color or a disabled button alone.
- The message names the required action and format.
- Blank input is not treated as an error because the reviewer may choose the
  deliberately constructed demo instead.
- No request is made, no repository is accessed, and no validation evidence is
  created by prevalidation.
- The change does not affect criteria confirmation, retrieval, findings,
  runtime evidence, resolutions, gates, exports, or persistence.

## Regression coverage

Add AppTest coverage proving:

1. a malformed non-empty URL shows the exact guidance and disables fetch;
2. a canonical public PR URL hides the guidance and enables fetch;
3. blank input keeps the existing disabled, non-error state.

Retain the existing parser tests and run the complete verification stack before
publication.
