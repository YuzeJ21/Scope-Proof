# Exact-SHA Informational GitHub Check Design

## Objective

Add one opt-in, non-blocking GitHub Check Run that presents ScopeProof evidence for the current
immutable pull-request head. The check is engineering workflow output, not correctness proof,
customer validation, or a merge gate. It never executes pull-request code.

## Current boundary

The advanced-preview workflow runs only when a maintainer applies `scopeproof-review`. It currently
uses `pull_request_target`, checks out only the immutable base SHA, obtains
public pull-request evidence through the ScopeProof GitHub adapter, uploads a Markdown report, and
may publish a head-marker comment. The comment planner is pure and fork-safe, but comments are a
noisy primary presentation and do not expose a native exact-head Check lifecycle.

`main` branch protection requires only `verify` and `CodeQL`. The new check is named
`ScopeProof evidence summary (informational)` so it cannot silently replace either required check
or the existing `ScopeProof evidence review` workflow job.

## Selected design

### Pure planning model

Keep policy in `scopeproof_core.github_action` without HTTP or storage dependencies. Add strict,
frozen, `extra="forbid"` Pydantic models for:

- a `CheckRunContext` containing canonical repository identity, positive PR number, exact lowercase
  40-character head SHA, fork state, and the complete validated `CriteriaSourceProvenance`;
- validated existing Check Run identity containing positive ID, exact name, exact head SHA,
  external ID, and GitHub App identity;
- a `CheckRunOutput` containing bounded title, summary, and detail text; and
- a `CheckRunPlan` whose mode is `create`, `update`, or `skip`, whose conclusion is always
  `neutral`, and whose optional update ID is cross-validated with the mode.

The external ID is `scopeproof-check:v1:{repository}:{pr_number}:{head_sha}`. It deliberately
identifies one repository, PR, and head. Criteria-source URI, revision, source-text digest,
normalized-criteria digest, confirmer assertion, and confirmation time appear in the validated
check output. A same-head rerun updates that one trusted check with the current validated source
snapshot; it does not create duplicate checks. A different head has a different external ID and
creates a new historical record.

Only a Check Run attributed by GitHub to the `github-actions` App, with the exact check name, head,
and external ID, is eligible for update. Zero matches creates a check. One match updates it. More
than one match is ambiguous and fails closed without mutation. Fork contexts always return `skip`.

### Evidence presentation

The Check title contains the ScopeProof gate label and an explicit `(informational)` suffix. The
summary begins with “ScopeProof is an evidence assistant, not a correctness oracle.” It always
states that:

- implementation and test matches are candidates, not runtime verification;
- runtime verification must be externally supplied and separately recorded;
- missing or incomplete evidence remains missing;
- unresolved human decisions remain unresolved; and
- reviewer and source-owner identities are asserted, not authenticated.

The validated criteria-source URI, revision or `Not provided`, source-text SHA-256, and ordered
normalized-criteria SHA-256 are rendered into the detail text. The report follows these fixed
boundaries when it fits the GitHub Check output limit. If the full report would exceed that limit,
the report is omitted rather than sliced, the title becomes Needs Review, and the detail explicitly
states that no criterion verdict from the omitted report is displayed. The conclusion remains
`neutral` for Ready, Conditional, Blocked, Needs Review, and error-adjacent report content. No
conclusion means correctness or acceptance.

### GitHub transport

Add `publish_check` beside the existing backward-compatible comment publisher. It uses one
`httpx.Client` with fixed `https://api.github.com` base URL, 15-second timeout, no redirects, and no
retries. It never follows a server-provided pagination URL.

Before planning and again immediately before any write, it fetches
`/repos/{repository}/pulls/{pr_number}` and Pydantic-validates the
response. Analysis publication requires the live PR to be open. Withdrawal permits an
identity-matched closed or merged PR so a removed applicability label cannot leave a stale Ready
display. Both paths require the exact repository and event head SHA; a mismatch is stale or foreign
and fails before mutation. Withdrawal keeps the validated prior detail text byte-for-byte and puts
the revocation notice in the bounded summary, so it cannot truncate retained criterion evidence.
The same existing-Check-only path revokes a prior display when checked-in criteria confirmation is
missing or mismatched while the opt-in label remains present. State-transition notices are
canonicalized before each write, so reruns converge and never grow the summary.
The event context also carries the immutable base SHA. The publisher requires both live reads of
the base and head to match the event, and all Check writers share one repository-wide concurrency
group. The workflow validates both identities in review-command
output before retaining its verdict or exporting its report. A base-advance or force-push race
therefore fails closed instead of combining criteria, analysis, and publication from different
snapshots.
Default-base pushes run a separate trusted workflow because GitHub emits no pull-request
`synchronize` event for a base-only advance. The bounded publisher enumerates at most two full
55-item pages of open PRs targeting the pushed default branch and, only when both are full, makes
a third-page sentinel request before any write. An empty sentinel accepts exactly 110 PRs; a
nonempty sentinel fails closed. Each eligible path budgets two live pull reads, at most five
Check-list reads, one detail read, and one write. With the three collection requests, the
worst-case path is 993 REST requests,
below the standard 1,000-request-per-repository hourly limit for an Actions `GITHUB_TOKEN`. It
filters out deleted-fork records and other non-same-repository PRs, revalidates each eligible live
identity, and revokes only an existing exact-head display. Individual PR failures are collected
without preventing later independent revocation attempts, then reported as one final failure. It
performs no analysis and never checks out a pull-request head. Automatic revocation of non-default
target branches remains unsupported.

It then reads only
`/repos/{repository}/commits/{head_sha}/check-runs` with the exact informational check name,
`per_page=100`, and integer pages 1 through 5. Each page is Pydantic-validated. A malformed page,
off-contract pagination signal, sixth page, repeated page, duplicate trusted identity, permission
failure, or HTTP failure fails closed. Because paths are locally constructed against the fixed base
URL, the token cannot follow an off-origin `Link` target.

Create requests POST to `/repos/{repository}/check-runs`; update requests PATCH the validated
positive check ID. Request bodies are strict Pydantic models serialized with `model_dump`. They set
`status="completed"` and `conclusion="neutral"`. The publisher never imports or mutates review
storage. A publication failure may leave GitHub response state unknown, but a retry re-reads the
exact external ID and converges without duplicating a trusted same-head check. Local saved reviews
remain byte-identical.

### Event runner and workflow

Extend the runner with `--requirements`, `--confirmation`, and `--publish-check`. The runner
validates the confirmation against the exact requirements bytes and ordered normalized criteria;
it does not trust a Boolean flag for check publication. Missing token, fork context, invalid
confirmation, malformed event, stale live head, or GitHub API error cannot publish a positive or
blocking conclusion.

The repository workflow and copyable example change to the unprivileged `pull_request` event so the
analysis never runs under `pull_request_target`. They continue to check out only
`github.event.pull_request.base.sha`, keep
credentials disabled, never fetch or check out the pull-request head, and never run target code.
They add `checks: write`, reduce `pull-requests` to read-only use, and publish the custom check only
for a labeled, same-repository PR with a validated confirmation. Fork pull requests receive the
platform's read-only token and the publication step is skipped before any write. The workflow stops invoking comment
publication, avoiding double noise. The old comment planner, publisher, and CLI flag remain for
backward compatibility.

The copyable example is updated in a final documentation commit to pin the preceding implementation
commit by full SHA. The pin therefore contains the complete Check lifecycle without attempting a
self-referential final-head pin.

## Failure and security behavior

- No feature path executes target-repository code, tests, hooks, installers, build commands, or
  downloaded artifacts.
- No feature path uses `pull_request_target` to inspect or execute pull-request content.
- Forks and missing tokens perform no Check API request.
- Stale or foreign repository, PR, head, App, external-ID, URL, or check-ID identities fail closed.
- GitHub reads are bounded to one PR request and five 100-item Check pages before one optional write.
- Tokens remain only in the Authorization header and are never logged, persisted, or exported.
- A failed Check request cannot mutate a `JsonReviewStore` record.
- The existing Action remains opt-in, advanced, and informational. Branch protection is unchanged.

## Testing

Use strict red-green cycles for the pure planner, publisher, runner, and workflow. Tests cover
create, update, changed head, duplicates, stale head, repository and PR mismatch, fork, missing
token, malformed Pydantic responses, App mismatch, external-ID mismatch, check-ID mismatch, page
budget, API errors, neutral-only output, criteria provenance, report truncation, and saved-review
non-mutation. Existing comment behavior remains green.

Final verification includes Ruff, the complete suite with at least 95 percent combined coverage,
repository contracts, both deterministic benchmarks, reproducible wheels, clean installation,
supported Python lanes, Windows compatibility, loopback workbench health, installed-wheel Chromium,
diff and commit audit, and independent exact-head review.

## Explicit exclusions

This slice does not merge its own PR, modify branch protection, create a required check, release,
tag, publish a package, begin Stage 3, conduct outreach, activate optional discovery, authenticate
reviewers, support private repositories, host source processing, scan security, review generic code,
fix target code, retune R-002, or generate R-003. Stage 1 remains
`closed_not_pursued_by_owner` with every historical external-evidence count at zero.
