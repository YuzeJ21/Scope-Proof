# ScopeProof v0.2.3 integrity and reviewer-loop verification

> **Historical evidence boundary:** This audit remains bound to its named commit, tree, version,
> and environment. The [current status](../../releases/v0.2.3-status-and-next-stages.md) supersedes
> unqualified present-state inferences and does not rewrite the results below.

## Evidence identity and boundary

- Date: 2026-08-03 (America/Toronto)
- Product-code target: `a77ea6e945cb3c63be434d061bfece9d1df5df41`
- Product-code tree: `c8c3b537c0728394f13c11ac2f7e80435047dc2a`
- Base: local and remote `main` aligned at `d67fe948` before this branch
- Branch: `codex/integrity-reviewer-loop`
- Publication: none; v0.2.3 remains untagged and unreleased
- Product validation: unchanged; Stage 1 remains zero and Stages 2–4 remain gated

This report records local engineering evidence for the named product-code tree. The
documentation commit that contains this report necessarily has a later tree. Protected pull-request
and resulting-main checks remain the authority if the branch is integrated.

No target repository code was executed. No Figma call, paid API, billing resource, account, private
repository, outreach, notification, comment, tag, release, or release asset was created. Constructed
fixtures and owner-operated checks contribute zero Stage 1 credit.

## Verified changes

- Missing, null, or empty GitHub file patches are excluded, named in `skipped_files`, and make
  ingestion partial. Non-string patches and missing, blank, or malformed filenames fail with a
  bounded adapter error.
- A reopened review prepares its canonical PR URL and unique bounded unchanged-candidate paths for
  a current-head check without carrying prior acceptance forward.
- Evidence-matrix cards expose candidate count, rationale, missing evidence, recommended action,
  and direct navigation to the existing criterion workspace.
- Invalid saved criterion selections recover deterministically; the first untouched session still
  begins with the first confirmed criterion.
- Accepting below the required candidate-evidence level requires an attributable note and states
  that the note does not raise the evidence level.
- Re-review comparison exposes Changed candidates first, exact Unchanged references in a collapsed
  section, and validated Markdown and JSON comparison downloads.
- Optional source revision and local storage path are progressively disclosed; live public reviews
  are not labelled as the bundled constructed demo.

Evidence IDs, retrieval thresholds, evidence levels, finding semantics, gate precedence, persisted
review schema, and the frozen R-002 inputs and results were not changed.

## Verification results

| Check | Result |
| --- | --- |
| `uv lock --check` | Passed; 60 packages resolved. |
| `uv run ruff check .` | Passed. |
| Full tests with product-code coverage | 1,905 passed, 1 intentional live test skipped in 502.30 seconds. |
| Coverage gate | 9,043 statements, 440 missed, 95.13%; 95% requirement passed. |
| Repository contracts | 74 passed. |
| Constructed acceptance benchmark | 12 cases, 13 criteria, zero mismatches, zero must-have False Ready, zero false blockers, evidence-link precision 1.0. |
| Constructed comparison benchmark | 2 cases, zero mismatches; 3 Added, 1 Modified, 1 Relocated, 3 Removed, 1 Unchanged. |
| R-002 tracked inputs/results | No diff; the full test suite retained their repository and byte-integrity contracts. |
| `git diff --check` | Passed. |

The benchmark results are deterministic engineering evidence, not target runtime, customer,
correctness, or market validation.

## Built artifacts and clean installation

Artifacts were built from the named product-code target into a task-owned temporary directory and
installed into a fresh Python 3.12.0 environment.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `scopeproof-0.2.3-py3-none-any.whl` | 258,014 bytes | `ee05155a6180ead9408e3d683bb944a56370fa10ba33f9d68928060a349cdf44` |
| `scopeproof-0.2.3.tar.gz` | 5,875,074 bytes | `c4ac941edc493c381e42c383d58d51bb711a1253701c9829f4fccc650d7c6721` |

From outside the checkout:

- `scopeproof --version` returned `scopeproof 0.2.3`;
- `scopeproof-web --version` returned `scopeproof-web 0.2.3`;
- both installed constructed benchmarks reproduced zero mismatches;
- the installed workbench returned health body `ok` and root HTTP 200 on task-owned port 8767;
  and
- the server was stopped and no listener remained.

These are internal candidate artifacts. They were not uploaded and are not published release
assets.

## Remaining evidence gates

- R-003 may proceed only through its prospective outcome-blind selection and separate criteria and
  label confirmations; R-002 cannot be used for threshold tuning.
- Stage 1 still requires genuine non-owner use with public source-owner-confirmed requirements.
- CLI lifecycle parity and typed non-executing evidence adapters remain separate pilot-critical
  design candidates; adding them requires bounded specifications and must not become generic code
  review, target-code execution, or automatic approval.
- Keyboard-only completion, real screen-reader operation, actual 200% zoom, Python 3.13, Windows,
  and Linux desktop workflows remain unsupported by current evidence.
- A tag, GitHub Release, checksums, or publication requires a separate owner decision and fresh
  exact-release-tree verification.
