# Changed-file scope engineering verification — 2026-10-26

This record applies to the unreleased `0.2.4.dev0` source at implementation commit
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
| Source implementation commit | `6b1be51cdcd0036e3f8ed5f7adc55b8fe4359e2c` |
| Hosted exact-head check and merge record | [PR #206](https://github.com/YuzeJ21/Scope-Proof/pull/206); the final head and resulting main are verified in GitHub after integration, since this documentation commit cannot name its own SHA. |
| Local platform | Darwin 27.0.0 arm64, Python 3.12.0, Ruff 0.15.21 |

| Check | Result |
| --- | --- |
| Isolated full suite: `uv run --no-sync pytest --cov=scopeproof_core --cov=apps --cov-report=term-missing:skip-covered --cov-fail-under=95 -q --maxfail=1 --tb=short` | 2,573 passed, 2 intentional skips in 579.94 seconds; combined coverage 95.03%, above the 95% requirement. A prior run exposed a legacy-test expectation that assumed a migrated review could be accepted without a verified inventory; the corrected fail-closed regression passed in this final run. |
| Lint: `uv run --no-sync ruff check .`; whitespace: `git diff --check` | Passed. |
| `uv run --no-sync scopeproof benchmark` | 12 constructed cases, 13 criteria, zero mismatches, zero must-have False Ready, zero uncited-file False Ready, zero false blockers. |
| `uv run --no-sync scopeproof comparison-benchmark` | 2 constructed cases, zero mismatches. |
| Installed-wheel browser journey: `uv run --no-sync pytest -q -m browser tests/browser/test_packaged_workbench.py --tb=short` with `SCOPEPROOF_PORTFOLIO_CAPTURE_DIR=docs/portfolio/2026-10-26/assets` | 5 passed in 43.09 seconds; fresh wheel/venv, desktop/mobile, saved file-scope decision, reopen, JUnit context, and exports. |
| Clean install: `uv build --wheel`, `uv venv --python 3.12`, and `uv pip install` of that wheel into the new environment | Built `scopeproof-0.2.4.dev0-py3-none-any.whl` (SHA-256 `af8c512afa7dc031186f22e882fc6c5e226a1a69ed9b96d8728f09b7fd23fd73`); installed 41 dependencies. The installed CLI reported `scopeproof 0.2.4.dev0`; both benchmarks passed with the counts above. Wheel inventory contained no coverage file, local secret container, screenshot, or repository metadata. |
| Python 3.11 and 3.13 scoped compatibility: `uv run --isolated --python <version> --extra dev --extra research pytest -q tests/gates/test_file_scope.py tests/reviews/test_file_scope_lifecycle.py tests/storage/test_file_scope_migration.py tests/reporting/test_file_scope_exports.py` | 19 passed on each interpreter. Hosted matrix and Windows checks are recorded separately after the PR reaches an exact head. |
| Frozen inputs and result | `git diff --exit-code 36358146a5167270fff7e52769ae66ee8f56f2da -- evals/r002 docs/research/r002-swebench-verified evals/labels/benchmark_scope_expansion.json` passed. Frozen scope label SHA-256 `55d448d59b72bb5c70683537c5087605fd5ccd2dd1963b3ff66a770275abd087`; R-002 result SHA-256 `2fc7115a6ffee3143d0f1d93dca1d51359f40857ec89f1c180d04d7f1e2d359f`. |

## Review and limits

Independent core and surface reviews found and prompted fixes for an orphan-evidence bypass,
decision binding, renamed-file source identity, and visibility of file-scope history in controls
and exports. Their final reviews found no material issue. The constructed reviewer in the browser
journey is explicitly labeled “Automated browser reviewer (constructed)” in
[the file-scope screen](assets/07-file-scope-decision.png). It is not a real participant.

R-002 remains a frozen 20-PR static research record. No target-repository code was executed, and
neither the original constructed label nor historical benchmark results were retuned. The
constructed fixture results do not measure real-world False Ready frequency. CI and browser
automation do not establish customer validation, accessibility conformance, a genuine Windows
desktop journey, or a completed beta. No participant contact, publication, deployment, or release
is part of this work.
