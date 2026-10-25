# Engineering verification — 2026-10-25

This record applies to the unreleased `0.2.4.dev0` integrity draft, not the published v0.2.3
wheel. Core integrity behavior is at `47ebc4f275b9f307c9305af3890782fa7578dff4`;
the release corrections, packaged-browser capture code, and six screenshots are at
`36323f36ed681b67bb062ff473eba701ff62df5c`. The JUnit adapter is a separate draft PR at
`8f8fa9e22f6d41e246773cf688c77be8462d0c07` and is not part of this source revision.

## Local environment and checks

The local checks ran on Darwin 27.0.0 arm64 with Python 3.12.0, pytest 9.1.1,
Playwright 1.62.0, and Ruff 0.15.21. The source checkout used the project's Python 3.12 virtual
environment. Browser networking was loopback-only; review, alpha, and rehearsal storage used
temporary homes. Real `~/.scopeproof` data and frozen R-002 inputs/results were not changed.

| Check from the source checkout | Result |
| --- | --- |
| `python -B -m pytest -p no:cacheprovider --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q` with `PYTHONDONTWRITEBYTECODE=1` and a `/tmp` `COVERAGE_FILE` | 2,399 passed, 2 intentional skips in 502.50 seconds; combined coverage 95.14%, above the 95% requirement. The preceding run exposed three repository-doc contract assertions after release wording was corrected; their updated assertions passed in this final run. |
| `python -B -m pytest -p no:cacheprovider -q -m browser tests/browser/test_packaged_workbench.py --tb=short` with `SCOPEPROOF_PORTFOLIO_CAPTURE_DIR=docs/portfolio/2026-10-25/assets` | 3 passed in 34.08 seconds. The installed-wheel Chromium journey built and installed the package in a fresh temporary environment, exercised criteria confirmation, analysis, exports, saved-review reopen, keyboard controls, and desktop/mobile viewports. Six captures were copied into this package only after all assertions passed. |
| `python -B -m ruff check .` and `git diff --check` | Passed. |
| `scopeproof benchmark` from a clean wheel install | 12 constructed cases, 13 criteria, zero mismatches, zero must-have False Ready outcomes, zero false blockers. |
| `scopeproof comparison-benchmark` from the same clean install | 2 constructed cases, zero mismatches. |

Two `uv build --wheel` runs from the same source tree produced byte-identical
`scopeproof-0.2.4.dev0-py3-none-any.whl` files (SHA-256
`58278094ee69cbebcb09db5917fbdfe6717ffdaab16368c89d1ea8e5121653e4`, 292,712 bytes,
103 entries). A fresh Python 3.12 virtual environment installed the wheel and resolved 41
dependencies; its CLI reported `scopeproof 0.2.4.dev0` and both installed benchmarks passed.
The wheel inventory contained no coverage file, local secret container, worktree, progress ledger,
or portfolio screenshot.

## Independent review and integration probes

Independent integrity review reproduced an A→B→A mixed-revision false-Ready risk and verified the
SHA-addressed compare repair; live read-only checks against the project PR and public fork PRs
succeeded. Independent JUnit review identified and then rechecked false-pass XML attributes and
sanitized-context comparison; 92 current-head focused importer/comparison/export tests passed.
An uncommitted merge of the current JUnit head with this integrity draft passed 339 targeted
importer, schema, and GitHub tests. A broader combined non-browser run at an earlier JUnit head
passed 2,275 tests with 1 intentional skip; it does not establish full compatibility at the
current JUnit head. Independent documentation review checked every screenshot against its caption
and the archival dispositions. Exact-head hosted CI is reported in the corresponding PRs when
terminal.

## Limits

These are automated engineering checks on constructed or read-only public inputs. They do not
authenticate a real criteria confirmer, execute a target repository, prove customer usefulness,
establish accessibility conformance, or verify a real Windows/Linux desktop workflow. Imported
JUnit XML remains external, non-gating context. GitHub comparisons over 250 commits or with
unavailable data stop ingestion rather than yielding Ready. The constructed `scope-expansion`
benchmark currently expects Ready despite an uncited changed file; a separate changed-file
inventory/gate design remains unresolved. No merge, release, deployment, or public post occurred.
