# Changed-file scope engineering verification — 2026-10-26

This record applies to the unreleased `0.2.4.dev0` source in PR #206, first implemented at
`6b1be51cdcd0036e3f8ed5f7adc55b8fe4359e2c`, based on verified main
`36358146a5167270fff7e52769ae66ee8f56f2da`. The final exact head and resulting main are
available from [PR #206](https://github.com/YuzeJ21/Scope-Proof/pull/206) after integration.
Published v0.2.3 does not contain this repair. The seven screenshots in [assets](assets/) were
captured by installed-wheel browser automation against constructed local data. They do not depict
independent product use.

## Scope and result

The historical constructed `scope-expansion` case had an uncited changed `src/auth.py` and
returned Ready. The original label still says Ready; the separate current expectation says
Needs Review. The current deterministic gate reports `uncited_changed_files`, and an orphan
candidate that no finding cites cannot clear the path. An attributable reviewer can classify a
path as outside the confirmed criteria for the exact review head and criteria revision. A
within-criteria classification still needs finding-linked evidence. Skipped paths and historical
records without a verified inventory remain unresolved. No file name, rename, or generated-looking
status grants a scope exception.

The [Stage 3 readiness assessment](../../releases/2026-10-26-stage3-readiness-assessment.md)
keeps the independent-use and separate authorization gates open. Automated tests, simulated
reviewers, and captured browser screens are engineering evidence only.

## Exact source and check matrix

| Boundary | Exact revision or result |
| --- | --- |
| Baseline main | `36358146a5167270fff7e52769ae66ee8f56f2da` |
| First source implementation commit | `6b1be51cdcd0036e3f8ed5f7adc55b8fe4359e2c` |
| Hosted exact-head check and merge record | [PR #206](https://github.com/YuzeJ21/Scope-Proof/pull/206); the final head and resulting main are verified in GitHub after integration, since this documentation commit cannot name its own SHA. |
| Local platform | Darwin 27.0.0 arm64, Python 3.12.0, Ruff 0.15.21 |

| Check | Result |
| --- | --- |
| Isolated full suite: `uv run --no-sync pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q --maxfail=1 --tb=short` | 2,581 passed, 2 intentional skips in 551.53 seconds; combined unrounded coverage 95.0851%, above the 95% requirement. An earlier run exposed a legacy-test expectation that assumed a migrated review could be accepted without a verified inventory; the corrected fail-closed regression passed in this final run. |
| Lint: `uv run --no-sync ruff check .`; whitespace: `git diff --check` | Passed. |
| `uv run --no-sync scopeproof benchmark` | 12 constructed cases, 13 criteria, zero mismatches, zero must-have False Ready, zero uncited-file False Ready, zero false blockers. |
| `uv run --no-sync scopeproof comparison-benchmark` | 2 constructed cases, zero mismatches. |
| Installed-wheel browser journey: `uv run --no-sync pytest -q -m browser tests/browser/test_packaged_workbench.py --tb=short` | 5 passed in 35.94 seconds on the final source; fresh wheel/venv, desktop/mobile, saved file-scope decision, reopen, JUnit context, and exports. An earlier passing run with `SCOPEPROOF_PORTFOLIO_CAPTURE_DIR=docs/portfolio/2026-10-26/assets` produced the seven screenshots. |
| Clean install: `uv build --wheel`, `uv venv --python 3.12`, and `uv pip install` of that wheel into a new environment | Built `scopeproof-0.2.4.dev0-py3-none-any.whl` (SHA-256 `70ae8931bfc6aee3be0a2f56d437d0279331ea43cd3ef329b38bec0d2d371ff4`); installed 41 dependencies. The installed CLI reported `scopeproof 0.2.4.dev0`; both benchmarks passed with the counts above. Final wheel inventory contained no coverage file, local secret container, screenshot, or repository metadata. |
| Python 3.11 and 3.13 scoped compatibility: `uv run --isolated --python <version> --extra dev --extra research pytest -q tests/gates/test_file_scope.py tests/reviews/test_file_scope_lifecycle.py tests/storage/test_file_scope_migration.py tests/reporting/test_file_scope_exports.py` | 19 passed on each interpreter. Hosted matrix and Windows checks are recorded separately after the PR reaches an exact head. |
| Frozen inputs and result | `git diff --exit-code 36358146a5167270fff7e52769ae66ee8f56f2da -- evals/r002 docs/research/r002-swebench-verified evals/labels/benchmark_scope_expansion.json` passed. Frozen scope label SHA-256 `55d448d59b72bb5c70683537c5087605fd5ccd2dd1963b3ff66a770275abd087`; R-002 result SHA-256 `2fc7115a6ffee3143d0f1d93dca1d51359f40857ec89f1c180d04d7f1e2d359f`. |

## Review and limits

Independent core and surface reviews found and prompted fixes for an orphan-evidence bypass,
decision binding, renamed-file source identity, and visibility of file-scope history in controls
and exports. Their final reviews found no material issue. The constructed reviewer in the browser
journey is explicitly labeled “Automated browser reviewer (constructed)” in
[the file-scope screen](assets/07-file-scope-decision.png). It is not a real participant.

An initial exact-head Windows job passed the new scope regressions but failed its installed
benchmark because Git's CRLF checkout changed the raw bytes of the frozen scope label. The
follow-up checksum normalizes CRLF pairs only; a dedicated regression accepts that checkout form
and still rejects an edited label. Independent review caught and resolved a Windows-only flaw in
the test's own CRLF fixture construction. The next hosted head passed Windows but its full-suite
log showed 12,635 statements with 632 missed, or 94.9980%: the coverage plugin printed a failure
while GitHub marked the step successful. An explicit unrounded coverage check was added to CI,
along with regressions for previously untested file-scope validation branches. The final hosted
matrix must pass above 95% at the new exact head before merge;
[PR #206 checks](https://github.com/YuzeJ21/Scope-Proof/pull/206/checks) are the authoritative
record.

R-002 remains a frozen 20-PR static research record. No target-repository code was executed, and
neither the original constructed label nor historical benchmark results were retuned. The
constructed fixture results do not measure real-world False Ready frequency. CI and browser
automation do not establish customer validation, accessibility conformance, a genuine Windows
desktop journey, or a completed beta. No participant contact, publication, deployment, or release
is part of this work.
