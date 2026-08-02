# Exact-head runtime-evidence candidate verification

## Evidence identity and boundary

- Date: 2026-08-01 (America/Toronto)
- Current public `main`: `6e3dec784f7cad9931999d4c5eac1cfe2a9006de`
- Current public-main tree: `cf34a4004861a294d25005f7f598068b740bbde9`
- Last completed public-main UX merge: PR #179
- Verified implementation: `95b2dc44132edad796f0316d846cd35e536443f6`
- Verified implementation tree: `0514c42d59aa69dee65be536a9fa449eff6a6530`
- Current disposition: `READY FOR DRAFT REVIEW`
- Publication state: candidate not merged, tagged, or released; v0.2.1 remains
  the only published install.

All full-suite, coverage, benchmark, build, installed-command, and workbench
health results in this record belong only to the clean verified implementation
commit above. This evidence document was written afterward. Its evidence commit
therefore changes the source distribution and is not part of the recorded
artifact hashes. Repository contracts, Ruff, diff checks, and repository
hygiene are rerun on the evidence commit; required GitHub CI must verify the
final complete PR head. No self-referential SHA or package-hash claim is made.

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
| `uv run python -m pytest -q` | 1747 passed and 1 skipped in 122.18 seconds. |
| Combined coverage with `--cov-fail-under=95` | 1747 passed and 1 skipped; 8,561 statements, 411 missed, exact total 95.20%; threshold passed. |
| `uv run scopeproof benchmark` | 12 cases and 13 criteria executed; zero mismatches, status mismatches, must-have False Ready outcomes, false blockers, or unexecuted declared categories. |
| `uv run scopeproof comparison-benchmark` | Two cases; zero mismatches; aggregate 3 Added, 1 Modified, 1 Relocated, 3 Removed, and 1 Unchanged; `does_not_advance_stage_1` remained true. |
| `uv run python -m pytest -q tests/test_repository_contracts.py` | 67 passed before tracked documentation edits. |
| `git diff --check` | Passed with no output. |
| Branch forbidden-generated-path scan | Exited 1 with no matches. The tracked aggregate scan still found only the two intentional inherited `.scopeproof` Action inputs. |

The frozen R-002 corpus was not rerun in this Task 5 wave. Its historical
20-case results, tracked hashes, and zero-Stage-1 boundary remain preserved in
the platform/package matrix and research record; none is presented as new
candidate evidence.

## Built package and installed runtime

A fresh build from the verified implementation used a new temporary directory.
The evidence commit and this document were absent from those bytes.

| Artifact | Size | Inventory | SHA-256 |
| --- | ---: | ---: | --- |
| `scopeproof-0.2.3-py3-none-any.whl` | 247,571 bytes | 99 wheel entries | `5b1422fe1117abcb63d69e725d9ac2ecad012d4faa11a23c5a2bc62d75a7ae64` |
| `scopeproof-0.2.3.tar.gz` | 5,805,868 bytes | 532 source-distribution entries | `ff7a733c2c801be5a26963756bf3c7d4cc85a096869d1eaa20f1c16a5b127b2c` |

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

No browser walkthrough was performed on this exact candidate. The prior PR #179
pointer walkthrough, 1280×720 and 390×844 observations, screenshots, and partial
keyboard attempts remain historical evidence for their named source targets.
They are not promoted to current-candidate evidence.

The following remain unverified for this candidate:

- Python 3.11 at the exact branch head until required GitHub CI runs;
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

- Stage 0 is repaired and locally verified on the candidate. Public `main`
  remains pending candidate merge and exact-resulting-main verification.
- Stage 1 remains `waiting_for_inbound_public_alpha_submission`: 0/5 qualifying
  reviews, 0/3 independent practitioners, 0/3 repositories, 0/3 independently
  observed under-ten-minute completions, and 0/2 reuse-intent signals.
- Stages 2–4 remain gated by their genuine-use and owner-decision conditions.
- Benchmarks, tests, package installation, health, prior browser rehearsals,
  owner operation, and this audit all contribute zero Stage 1 credit.
- No push, pull request creation, merge, tag, GitHub Release, asset upload, PyPI
  publication, outreach, account, billing resource, or target-repository code
  execution is authorized or performed by this Task 5 implementation.
- After the evidence commit, local affected-input checks run on that exact
  commit. Required GitHub CI must verify the final complete PR head. Merge and
  exact-main verification remain controller actions; v0.2.3 publication remains
  a distinct owner decision requiring fresh final-main assets and checksums.
