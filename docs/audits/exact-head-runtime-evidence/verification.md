# Exact-head merged-product runtime-evidence verification

Machine-readable evidence manifest:
[`verification.json`](verification.json). The manifest is the structured
repository-contract input; this document remains the human-readable audit.

## Evidence identity and boundary

- Date: 2026-08-02 (America/Toronto)
- Merged product commit: `2a320df966eff30c05a2b1dce607a247201fa165`
- Merged pull request: PR #180
- Merged product tree: `add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8`
- Independently verified PR head: `ed9f9c0cf6b7cf7cc25403d6138e7a8391f55e0f`
- Verified PR-head tree: `add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8`
- Current disposition: `STAGE 0 ENGINEERING FOUNDATION RESTORED`
- Publication state: source merged but not tagged or released; v0.2.1 remains
  the only published install and v0.2.3 remains unreleased.

All full-suite, coverage, benchmark, build, installed-command, and workbench
health results in this record belong only to independently verified head
`ed9f9c0cf6b7cf7cc25403d6138e7a8391f55e0f` and product tree
`add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8`. PR #180 merged that exact tree.
This post-merge documentation alignment was written afterward and therefore
changes the repository tree and source distribution. Its affected checks run
on the alignment tree, and pull-request CI must cover the final alignment; the
product-tree package hashes do not cover these documentation changes. No
self-referential final alignment SHA or package-hash claim is made.

This is owner-operated engineering evidence. It does not prove correctness,
target-repository runtime behavior, participant usability, customer demand,
accessibility conformance, broad platform support, or Stage 1 progress.

## Implemented integrity behavior

- New E3/E4 records carry a nonblank `runtime_evidence_id`, repository, PR
  number, and exact reviewed head copied from the validated active review.
- The paired manual decision carries the same ID. Trusted schema, bundle,
  lifecycle, gate, persistence, comparison, presentation, and export boundaries
  reject missing new identity, duplicate IDs, foreign repositories, wrong PRs,
  wrong heads, missing records, or criterion/reviewer/evidence-level mismatch.
- Local record version 3 remains able to read versions 1 and 2. Migration gives
  old runtime records deterministic identities but never invents a human
  decision link. Legacy-unlinked decisions remain audit history and become
  `Needs Review` with `runtime_verification_reconfirmation_required` until the
  reviewer revokes any older positive final acceptance and re-records runtime
  verification at the active head.
- JSON, Markdown, CSV, and HTML retain validated runtime identity and linked or
  legacy-unlinked state. Runtime provenance remains evidence, not correctness.
- A complete passing CI observation with skipped runs now shows a visible
  warning while retaining its deterministic `PASSING` state and keeping names
  in the details expander.
- A revised bundle-less review with stale criterion-detail input exposes the
  existing clear action. Clearing preserves authoritative review state, resumes
  autosave, and does not enable exports until deterministic reanalysis.

## Clean source and deterministic verification

Environment: macOS 26.5.1 build 25F80, Apple silicon (`arm64`), Python 3.12.0,
and uv 0.11.29.

| Command | Exact result at the verified implementation |
| --- | --- |
| `uv sync --extra dev --extra research --locked` | Resolved 60 packages and checked 55 packages. |
| `uv lock --check` | Passed; resolved 60 packages. |
| `uv run ruff check .` | Passed: `All checks passed!` |
| `uv run python -m pytest -q` | 1751 passed and 1 skipped. |
| Combined coverage with `--cov-fail-under=95` | 1751 passed and 1 skipped; 8,588 statements, 416 missed, exact total 95.16%; threshold passed. |
| `uv run scopeproof benchmark` | 12 cases and 13 criteria executed; zero mismatches, status mismatches, must-have False Ready outcomes, false blockers, or unexecuted declared categories. |
| `uv run scopeproof comparison-benchmark` | Two cases; zero mismatches; aggregate 3 Added, 1 Modified, 1 Relocated, 3 Removed, and 1 Unchanged; `does_not_advance_stage_1` remained true. |
| `uv run python -m pytest -q tests/test_repository_contracts.py` | 68 passed on merged product commit `2a320df966eff30c05a2b1dce607a247201fa165` before the docs-only alignment. |
| `git diff --check` | Passed with no output. |
| Branch forbidden-generated-path scan | Exited 1 with no matches. The tracked aggregate scan still found only the two intentional inherited `.scopeproof` Action inputs. |

The frozen R-002 corpus was not rerun in this Task 5 wave. Its historical
20-case results, tracked hashes, and zero-Stage-1 boundary remain preserved in
the platform/package matrix and research record; none is presented as new PR
#180 product-tree evidence.

## Merged-main workflow verification

GitHub's final run state was independently rechecked at `2026-08-02T05:47:39Z`.
All three runs are bound to exact merge SHA
`2a320df966eff30c05a2b1dce607a247201fa165`:

| Workflow | Run | Event | Final state |
| --- | --- | --- | --- |
| CI | [30734386610](https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386610) | `push` on `main` | `completed` / `success`; locked-environment, Python 3.11 compatibility, and verify succeeded |
| CodeQL | [30734386396](https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386396) | GitHub `dynamic` run on `main` | `completed` / `success`; actions and Python analysis succeeded |
| Pages | [30734386626](https://github.com/YuzeJ21/Scope-Proof/actions/runs/30734386626) | `push` on `main` | `completed` / `success`; build and deploy succeeded |

These runs verify the merged product snapshot. They do not publish v0.2.3 and
do not cover this later documentation-alignment tree.

## Built package and installed runtime

A fresh build from the verified implementation used a new temporary directory.
The evidence commit and this document were absent from those bytes.

| Artifact | Size | Inventory | SHA-256 |
| --- | ---: | ---: | --- |
| `scopeproof-0.2.3-py3-none-any.whl` | 248,171 bytes | 99 wheel entries | `70bdca1a0d609c81ac8cd2274dc4915612067cfdb1c2205276faafd7c6358ac8` |
| `scopeproof-0.2.3.tar.gz` | 5,818,424 bytes | 534 source-distribution entries | `7fff8ba0b6b6c85ae0f22fe487762de8a525d04145c50eab46792233b798573e` |

Both inventories had zero forbidden-path matches for review storage, coverage,
virtual environments, Git or local SDD data, caches, bytecode, build outputs,
and common credential names.

The wheel installed into a fresh Python 3.12 virtual environment outside the
checkout with 48 installed packages. `pip check` reported no broken
requirements. From `/tmp`:

- `scopeproof --version` returned `scopeproof 0.2.3`;
- `scopeproof-web --version` returned `scopeproof-web 0.2.3`;
- the installed 12-case benchmark repeated with zero mismatches, zero must-have
  False Ready outcomes, zero false blockers, and no unexecuted categories;
- the installed two-case comparison benchmark repeated with zero mismatches and
  retained `does_not_advance_stage_1: true`; and
- the installed workbench launched on `127.0.0.1:8515`, where
  `/_stcore/health` returned exact body `ok`.

The wrapper and child server were terminated, the health endpoint became
unreachable, and no listener or `scopeproof-web` process remained. The build
directory, virtual environment, isolated home, coverage file, pytest/Ruff
caches, and Python bytecode were removed. A fresh complete package run supplied
the results above; an earlier shutdown-timing probe was discarded and is not
used as green evidence.

## Platform and accessibility gaps

No browser walkthrough was performed on the verified PR #180 product tree. The
prior PR #179 pointer walkthrough, 1280×720 and 390×844 observations,
screenshots, and partial keyboard attempts remain historical evidence for their
named source targets. They are not promoted to PR #180 evidence.

The following remain unverified for the merged product tree:

- a local Python 3.11 desktop run (merged-main CI did exercise Python 3.11);
- Python 3.13;
- Windows and Linux desktop workflows;
- a complete keyboard-only review;
- VoiceOver, NVDA, JAWS, or another real screen reader;
- actual 200% browser zoom; and
- WCAG conformance.

Workbench health proves only that the installed local server started and
responded. It is not a browser-flow, accessibility, participant, production, or
target-runtime result.

## Stage and publication boundary

- Stage 0's engineering foundation is restored on merged product commit
  `2a320df966eff30c05a2b1dce607a247201fa165` and independently verified tree
  `add81a2d0ba7e64f8e4318a1959bbe7e6e4acfc8`.
- Stage 1 remains `waiting_for_inbound_public_alpha_submission`: 0/5 qualifying
  reviews, 0/3 independent practitioners, 0/3 repositories, 0/3 independently
  observed under-ten-minute completions, and 0/2 reuse-intent signals.
- Stages 2–4 remain gated by their genuine-use and owner-decision conditions.
- Benchmarks, tests, package installation, health, prior browser rehearsals,
  owner operation, and this audit all contribute zero Stage 1 credit.
- PR #180 is merged. No v0.2.3 tag, GitHub Release, asset upload, PyPI
  publication, outreach, account, billing resource, or target-repository code
  execution is created by this docs-only alignment.
- Local affected-input checks cover the later alignment tree, and pull-request
  CI must cover its final form. v0.2.3 publication remains a distinct owner
  decision requiring fresh release-tree assets and checksums.
