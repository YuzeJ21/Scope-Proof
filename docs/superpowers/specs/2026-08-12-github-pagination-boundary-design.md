# GitHub Pagination and Credential Boundary Design

## Status and scope

This design implements the owner-approved Phase 1 boundary from verified `main` commit
`73e3ecb76d4856a156ad23d711e585ed2af499e7`. It is limited to ScopeProof's read-only public
GitHub pull-request ingestion. It does not add private-repository support, execute repository code,
change evidence interpretation, alter criteria confirmation, or advance Product Stage 1.

## Current problem

`GitHubClient._get_all` accepts every absolute `rel="next"` URL supplied by a response and sends
it through an `httpx.Client` whose default headers may contain the optional GitHub token. It also
collects every file and commit page before enforcing `max_files`. There is no origin or endpoint
lineage check, cycle detection, or deterministic request, page, item, or decoded-response-size
budget.

The result is both a credential-forwarding boundary defect and an unbounded resource-consumption
path. The supported source remains anonymous public GitHub; a token may improve rate limits but
must remain session-only and must never be forwarded outside the intended API origin.

## Considered approaches

### A. Strict pagination inside `GitHubClient` with one per-fetch budget — selected

Replace `_get_all` with a small bounded collection helper. Validate each `next` URL before a
request, convert an accepted URL to a relative same-origin target, track visited targets, and share
one budget across pull-request metadata, file pages, commit pages, and CI metadata. This is the
smallest core-first correction and protects every current CLI and Streamlit caller.

### B. Disable pagination

Only accept the first GitHub page. This removes the forwarding risk but silently turns ordinary
multi-page public pull requests into incomplete evidence and breaks supported behavior.

### C. Strip `Authorization` only for absolute URLs

This prevents one credential leak but still permits off-origin traffic, endpoint escape, cycles,
and unbounded downloads. It does not satisfy the ingestion trust boundary.

## Core architecture

Add a private per-fetch budget object and a private paginated-collection result in
`scopeproof_core/github/client.py`.

The budget tracks:

- all HTTP requests made by one pull-request fetch;
- all followed pagination pages;
- all decoded list items across file and commit collections;
- decoded bytes for each response and cumulatively across the fetch.

Default ceilings are explicit constructor values: 16 requests, 10 pagination pages, 1,000
paginated items, 4 MiB per decoded response, 16 MiB cumulatively, 100 files, and 250 commits.
Tests can lower each ceiling without changing production policy. Exhaustion raises a deterministic
`GitHubPaginationError`, a `GitHubIngestionError` subtype.

Every response is charged after transport decoding and before JSON parsing. Request allowance is
charged before the request. This ensures an oversized or excessive response cannot be accepted
merely because later projection would discard most of it.

## Pagination target contract

A `next` target is accepted only when all conditions hold:

1. The URL is absolute HTTPS with hostname exactly `api.github.com`, no user information, no
   fragment, and the default HTTPS port.
2. Its path exactly matches the collection path initially requested for that pull request. A file
   page cannot become a commit page, another repository, another pull request, or another endpoint.
3. Its query contains exactly one positive integer `page` and one `per_page` matching the initial
   page size; unknown and duplicate parameters are rejected.
4. The response exposes at most one unambiguous `rel="next"` target.
5. The canonical path-and-query target has not already been requested or visited.

Validation happens before issuing the request. An accepted absolute target is rendered as a
canonical relative path before it reaches the shared client, so the optional authorization header
cannot be forwarded off-origin. Malformed, ambiguous, downgraded, off-origin, escaped, repeated,
cyclic, or over-budget traversal fails the entire fetch closed.

## Bounded collection behavior

Files are requested with the smallest permitted page size that can observe one item beyond
`max_files` (up to GitHub's 100-item page maximum). Collection stops immediately when either an
overflow item is observed or a valid `next` link proves more files exist after `max_files`. Only
the first `max_files` entries are analyzed, the snapshot is `partial`, and warnings truthfully say
that additional changed files were not retrieved. Observed overflow filenames may be listed, but
unretrieved names are never fabricated.

Commits use 100-item pages and stop after observing at most one item beyond `max_commits`. The
first `max_commits` commits remain in GitHub order. Truncation marks the snapshot `partial` and adds
a bounded warning; ScopeProof does not claim complete commit history.

All retained files and commits preserve GitHub response order. A non-list collection payload or a
non-object entry is malformed input and fails closed. Existing patch-byte and total-diff limits
remain independent, conservative partial-evidence boundaries.

## Data flow and mutation safety

CLI and Streamlit continue to call `GitHubClient.fetch_pull_request`. The client constructs a
Pydantic-validated `PullRequestSnapshot` only after all required ingestion succeeds. Known file,
commit, or patch truncation produces a validated partial snapshot; structural or budget failures
produce no snapshot.

CLI review and Alpha initialization already fetch before their first store write. Streamlit already
assigns fetched state only after the client call succeeds. Focused regressions bind these adapter
properties to `GitHubPaginationError`: existing saved reviews and session values remain unchanged,
and no report/export is created.

The deterministic gate already forbids `Ready` when ingestion is partial or warnings/skipped files
exist. A focused regression will prove that a client-produced truncated snapshot remains non-Ready
through the normal bundle and gate path.

## Test strategy

Tests use only `httpx.MockTransport`, local fixtures, temporary storage, and Streamlit AppTest.
They first demonstrate failures for off-origin links and token forwarding, HTTP downgrade,
repository/endpoint escape, repeated URLs and cycles, ambiguous/malformed links, request/page/item
exhaustion, per-response and cumulative decoded-size exhaustion, file early-stop behavior, bounded
commit history, and deterministic ordering.

Adapter regressions prove pagination failure is non-mutating in CLI and Streamlit. Gate coverage
proves bounded partial evidence cannot produce an unsupported `Ready` result. Existing anonymous
public-PR, candidate-file, CI observation, packaging, browser, and benchmark coverage remains green.

## Evidence and product boundaries

- ScopeProof remains an evidence assistant, not a correctness oracle.
- No target-repository code is executed.
- Criteria confirmation remains mandatory.
- Persisted and exported objects remain Pydantic-validated.
- Optional GitHub credentials remain session-only and are never logged or exported.
- False Ready remains more harmful than False Blocked.
- The GitHub Action remains opt-in and informational.
- Product Stage 1 remains exactly zero across all five targets.
- Phases 2–4, R-002, R-003, releases, tags, publishing, outreach, accounts, RBAC, billing, and paid
  APIs remain out of scope.
