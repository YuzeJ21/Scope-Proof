# GitHub Pagination and Credential Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make public GitHub pull-request pagination same-origin, lineage-bound, cycle-safe, and
deterministically bounded without forwarding optional credentials or permitting partial evidence to
become Ready.

**Architecture:** `GitHubClient` owns one per-fetch request/response budget and one strict
paginated-list helper. Every `next` link is validated before use and accepted links are reissued as
relative same-origin requests. File and commit collections return bounded truncation metadata;
malformed or exhausted traversals raise a user-safe ingestion error before adapters mutate state.

**Tech Stack:** Python 3.11+, httpx, Pydantic 2, pytest, Streamlit AppTest, uv, Ruff.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle.
- Never execute target-repository code.
- Keep the core independent of Streamlit and GitHub UI layers.
- Persisted and exported objects remain Pydantic-validated.
- Failed ingestion does not mutate saved reviews or create exports.
- Gate behavior remains deterministic and fail closed; False Ready is more harmful than False
  Blocked.
- Preserve anonymous public GitHub ingestion and session-only optional credentials.
- Use ceilings of 16 requests, 10 pagination pages, 1,000 items, 4 MiB per decoded response,
  16 MiB total decoded responses, 100 files by default, and 250 commits by default.
- Product Stage 1 stays exactly zero. Do not begin Phases 2–4, release, publish, or perform outreach.

---

### Task 1: Strict traversal and shared budgets

**Files:**
- Modify: `scopeproof_core/github/client.py`
- Modify: `scopeproof_core/github/__init__.py`
- Test: `tests/github/test_pagination_and_candidates.py`
- Test: `tests/github/test_client.py`

**Interfaces:**
- Produces: `GitHubPaginationError(GitHubIngestionError)`.
- Produces: private `_FetchBudget.charge_request()`, `_FetchBudget.charge_response(response)`,
  `_FetchBudget.charge_page()`, and `_FetchBudget.charge_items(count)` methods.
- Produces: private `_PaginatedResult(items: list[dict], truncated: bool)`.
- Produces: `_get_paginated(path, *, expected_paths, canonical_path, per_page, retain_limit,
  budget)`.
- Consumes: existing `_get`, `_raise_for_pr`, and `httpx.Response` behavior.

- [ ] **Step 1: Write failing origin, lineage, and cycle tests**

Add a controlled transport that returns one valid first file page and a configurable `Link` header.
Capture all requests and assert, for example:

```python
with pytest.raises(GitHubPaginationError, match="expected GitHub API origin"):
    GitHubClient(token="session-secret", transport=transport).fetch_pull_request(PR_URL)

assert [request.url.host for request in requests] == ["api.github.com", "api.github.com"]
assert requests[-1].headers["authorization"] == "Bearer session-secret"
assert all(request.url.host != "attacker.invalid" for request in requests)
```

Parameterize `http://api.github.com/...`, `https://attacker.invalid/...`, another repository,
another PR, and `/commits` substituted for `/files`. Add repeated canonical URL, page-one/page-two
cycle, duplicate `page`, unknown query, missing `per_page`, and two `rel="next"` cases.

- [ ] **Step 2: Write failing budget tests**

Construct multi-page or padded responses and lower one ceiling per test:

```python
with pytest.raises(GitHubPaginationError, match="request budget"):
    GitHubClient(transport=transport, max_requests=2).fetch_pull_request(PR_URL)

with pytest.raises(GitHubPaginationError, match="decoded response byte budget"):
    GitHubClient(transport=transport, max_response_bytes=64).fetch_pull_request(PR_URL)
```

Cover request, page, item, single decoded response, and cumulative decoded responses independently.

- [ ] **Step 3: Run the focused tests and confirm intended red failures**

Run:

```bash
uv run pytest -q tests/github/test_pagination_and_candidates.py tests/github/test_client.py \
  -k 'pagination or budget or decoded or origin or downgrade or cycle or escape'
```

Expected: failures show `_get_all` follows unsafe links or lacks the new constructor ceilings and
error type.

- [ ] **Step 4: Implement the budget and strict target validator**

Add these private shapes in `client.py`:

```python
@dataclass
class _FetchBudget:
    requests_remaining: int
    pages_remaining: int
    items_remaining: int
    max_response_bytes: int
    total_response_bytes_remaining: int


@dataclass(frozen=True)
class _PaginatedResult:
    items: list[dict]
    truncated: bool = False
```

Extend `GitHubClient.__init__` with `max_commits=250`, `max_requests=16`,
`max_pagination_pages=10`, `max_pagination_items=1_000`, `max_response_bytes=4 * 1024 * 1024`, and
`max_total_response_bytes=16 * 1024 * 1024`. Reject non-positive limits with `ValueError`.

Implement a target validator with `urlsplit` and `parse_qsl(keep_blank_values=True)`. Require HTTPS,
hostname `api.github.com`, no user information or fragment, port absent or 443, the exact named
collection path or GitHub's `/repositories/ID` alias bound to verified PR metadata, and exactly
`[('page', positive_integer), ('per_page', expected_size)]` after deterministic sorting. Return a
relative request target and one named-path canonical identity such as:

```python
return f"{expected_path}?page={page}&per_page={per_page}"
```

Count `rel="next"` occurrences from all Link header values and require zero or one. Track the
initial and every accepted canonical target in a local `visited` set before requesting it.

Modify `_get` to take an optional budget, charge a request before transport, and charge
`len(response.content)` before return. Export `GitHubPaginationError` from `github/__init__.py`.

- [ ] **Step 5: Run focused tests until green**

Run:

```bash
uv run pytest -q tests/github/test_pagination_and_candidates.py tests/github/test_client.py
uv run ruff check scopeproof_core/github tests/github/test_pagination_and_candidates.py \
  tests/github/test_client.py
```

Expected: all selected tests pass with no lint output.

- [ ] **Step 6: Commit the core boundary intentionally**

```bash
git add scopeproof_core/github/client.py scopeproof_core/github/__init__.py \
  tests/github/test_pagination_and_candidates.py tests/github/test_client.py
git commit -m "fix: constrain GitHub pagination traversal"
```

### Task 2: Bounded files, commits, and fail-closed evidence

**Files:**
- Modify: `scopeproof_core/github/client.py`
- Modify: `tests/github/test_pagination_and_candidates.py`
- Modify: `tests/github/test_client.py`
- Modify: `tests/gates/test_evaluator.py`

**Interfaces:**
- Consumes: Task 1 `_FetchBudget` and `_get_paginated`.
- Produces: file results retained in GitHub order at `max_files` with at most one observed overflow.
- Produces: commit results retained in GitHub order at `max_commits` with at most one observed
  overflow.
- Preserves: `PullRequestSnapshot.ingestion_state`, `warnings`, and `skipped_files` Pydantic rules.

- [ ] **Step 1: Write failing early-file-stop and commit-bound tests**

Make the transport record collection URLs. For files, use `max_files=1` and return two entries on
the first page plus a `next` link that would fail if requested:

```python
snapshot = GitHubClient(transport=transport, max_files=1).fetch_pull_request(PR_URL)
assert [item.path for item in snapshot.files] == ["src/000.py"]
assert not any(url.params.get("page") == "2" for url in file_requests)
assert snapshot.ingestion_state is IngestionState.PARTIAL
```

For commits, set `max_commits=2`, return three ordered entries, and assert the first two are retained,
the next page is not requested, and a commit-history warning is present. Add a two-page ordering test
whose retained SHA list exactly matches API order.

- [ ] **Step 2: Run the bounded-collection tests and confirm intended red failures**

Run:

```bash
uv run pytest -q tests/github/test_pagination_and_candidates.py tests/github/test_client.py \
  -k 'early or file_limit or commit_limit or deterministic_order'
```

Expected: current code requests extra pages or lacks `max_commits` and commit partial-state behavior.

- [ ] **Step 3: Implement smallest-overflow collection behavior**

Create one `_FetchBudget` at the start of `fetch_pull_request` and pass it to every `_get`. Request
files with `per_page=min(100, max_files + 1)` and commits with
`per_page=min(100, max_commits + 1)`. Invoke:

```python
file_result = self._get_paginated(
    f"{root}/pulls/{pr_number}/files",
    expected_paths=frozenset({named_path, verified_numeric_path}),
    canonical_path=named_path,
    per_page=file_page_size,
    retain_limit=self.max_files,
    budget=budget,
)
```

The helper stops when it observes `retain_limit + 1` items or when it has retained exactly the limit
and a valid `next` proves more exist. It never follows that unnecessary link. For a truncated file
collection, keep only observed overflow filenames in `skipped_files` and use wording that does not
invent the number or names of unretrieved files. Apply the same bounded result to commits and mark
the snapshot partial with a commit-history warning.

- [ ] **Step 4: Prove client-produced partial evidence cannot be Ready**

Add a gate regression using a `Review` populated from the truncated snapshot:

```python
review.ingestion_state = snapshot.ingestion_state
review.ingestion_warnings = snapshot.warnings
review.skipped_files = snapshot.skipped_files
decision = evaluate_gate(review, [criterion], [finding], [accepted_resolution])
assert decision.verdict is GateVerdict.NEEDS_REVIEW
assert "partial_ingestion" in decision.reason_codes
```

- [ ] **Step 5: Run focused tests and commit intentionally**

```bash
uv run pytest -q tests/github/test_pagination_and_candidates.py tests/github/test_client.py \
  tests/gates/test_evaluator.py
uv run ruff check scopeproof_core/github tests/github tests/gates/test_evaluator.py
git add scopeproof_core/github/client.py tests/github/test_pagination_and_candidates.py \
  tests/github/test_client.py tests/gates/test_evaluator.py
git commit -m "fix: bound GitHub file and commit evidence"
```

### Task 3: CLI and Streamlit mutation safety

**Files:**
- Modify: `tests/cli/test_cli.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: public `GitHubPaginationError` from Task 1.
- Preserves: CLI fetch-before-save and Streamlit assign-after-fetch behavior.
- Produces: explicit non-mutation regressions for stored records, reports, and session state.

- [ ] **Step 1: Write the CLI non-mutation regressions**

Patch `GitHubClient.fetch_pull_request` to raise `GitHubPaginationError("GitHub pagination target
was rejected.")`. For `review` and `alpha init`, capture existing store bytes and assert:

```python
with pytest.raises(SystemExit) as error:
    main(arguments)
assert error.value.code == 2
assert record.read_bytes() == before
assert not report_path.exists()
```

Also assert the captured error omits tokens, raw rejected URLs, local paths, and traceback text.

- [ ] **Step 2: Write the Streamlit non-mutation regression**

Prepare criteria and capture `pr_url`, requirements text, criteria models, `review_state`, `bundle`,
and snapshot-related session keys. Raise `GitHubPaginationError` from fetch and assert those values
are unchanged, no download appears, and the rendered error contains `No review data was changed.`

- [ ] **Step 3: Run adapter tests and make only a confirmed adapter correction if required**

```bash
uv run pytest -q tests/cli/test_cli.py -k 'pagination or fetch_failure'
uv run pytest -q tests/apps/test_streamlit_app.py -k 'public_pr_fetch_failure or pagination'
```

Expected: tests pass on existing fetch-before-mutate behavior. If one fails, change only the
assignment/write ordering demonstrated by that regression; do not refactor unrelated UI or CLI code.

- [ ] **Step 4: Lint and commit the regressions intentionally**

```bash
uv run ruff check tests/cli/test_cli.py tests/apps/test_streamlit_app.py
git add tests/cli/test_cli.py tests/apps/test_streamlit_app.py
git commit -m "test: preserve state on pagination failure"
```

### Task 4: Documentation and complete verification

**Files:**
- Modify: `CHANGELOG.md`
- Modify only confirmed defects found by verification, with a failing regression first.

**Interfaces:**
- Consumes: completed Phase 1 implementation and tests.
- Produces: repository-truth change record and exact verification evidence.

- [ ] **Step 1: Update the unreleased changelog truth**

Add one `0.2.4.dev0` bullet stating that public GitHub pagination is same-origin, lineage-bound,
cycle-safe, and deterministically bounded. Do not make release, adoption, platform, accessibility,
or customer claims.

- [ ] **Step 2: Run source verification**

```bash
uv run ruff check .
uv run pytest -q --import-mode=importlib --cov=scopeproof_core --cov=apps \
  --cov-report=term-missing --cov-fail-under=95
uv run pytest -q tests/test_repository_contracts.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Expected: complete suite passes with at least 95% combined coverage; repository contracts pass;
acceptance benchmark has zero mismatches and zero must-have False Ready outcomes; comparison
benchmark has zero mismatches.

- [ ] **Step 3: Run artifact and installed-runtime verification**

Build twice in isolated directories and compare wheel bytes and SHA-256. Inventory both archives,
install one wheel in a clean environment, validate dependencies, compare source/distribution/review
schema and both CLI version surfaces, run both installed benchmarks, check exact loopback health,
run the installed-wheel Chromium regression, and run supported Python lanes 3.11, 3.12, and 3.13.

Expected: two byte-identical wheels; no unexpected packaged files; all version surfaces equal
`0.2.4.dev0`; zero benchmark mismatches; health and browser regression pass; unsupported
environments are classified without fabrication.

- [ ] **Step 4: Audit and commit named documentation/tests**

```bash
git diff --check
git status --short
git diff --name-only origin/main...HEAD
git log --oneline --decorate origin/main..HEAD
```

Inspect generated files, secrets, absolute local paths, packaging inputs, the exact branch base, and
the preserved root `.coverage 2`. Stage only `CHANGELOG.md` and any named regression files not
already committed.

### Task 5: Independent review and ready PR

**Files:**
- Modify only confirmed Critical or Important defects, each with a failing regression first.

**Interfaces:**
- Consumes: the exact verified Phase 1 branch head.
- Produces: ready PR `fix: bound GitHub pagination and credential forwarding`.

- [ ] **Step 1: Run independent read-only review**

```bash
codex review --base origin/main
```

Require zero unresolved Critical or Important findings. Reproduce every proposed defect before
changing code; fix confirmed findings test-first and repeat affected plus complete verification.

- [ ] **Step 2: Push and open the ready PR**

Push `codex/github-pagination-boundary` and open a ready PR against the exact verified `main` base.
The description records scope, red-green evidence, verification results, credential/evidence
boundaries, Stage 1 zeros, and unsupported environments.

- [ ] **Step 3: Monitor every available check to terminal conclusions**

Inspect CI, CodeQL, Pages, dependency workflows, review threads, mergeability, commit list, and final
diff. Diagnose a failed check systematically; repair only confirmed Phase 1 defects on the same
branch and rerun affected/full verification.

- [ ] **Step 4: Stop at the owner gate**

Do not merge the Phase 1 PR or begin Phase 2. Report exact base/head SHAs, commits, diff, checks,
review findings, unsupported environments, PR #186 automatic state, `.coverage 2` proof, Stage 1
zero counts, and the owner's exact merge-or-hold decision.
