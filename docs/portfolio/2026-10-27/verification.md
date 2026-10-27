# Stage 2 post-merge engineering evidence — 2026-10-27

This dated record covers unreleased `0.2.4.dev0` source at `main`
`8f01cf237b75da30796d1879f3fbde7b8a5ef6d5` (tree
`340009faea9a6e0ae99f2b0f321568864df45c74`). It closes the exact-head
and resulting-main checks for the [changed-file scope repair](../2026-10-26/verification.md)
and the subsequent Pages trigger control. Published v0.2.3 does not contain
these changes. All results below are engineering evidence, not independent use.

| Boundary | Verified revision and result |
| --- | --- |
| [PR #206](https://github.com/YuzeJ21/Scope-Proof/pull/206) | Exact head `fde9317ee14501c554d53dcb5de63b4144b0fd56` passed [PR CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40399843587) and merged as `42893c63b1da0f4b4845e9c2f4a92952fff02022`. [Resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40404725088) passed 2,581 tests, 2 intentional skips, 95.0455% unrounded coverage, both deterministic benchmarks, Python 3.11/3.13 and Windows compatibility, installed-wheel checks, and 5 packaged-browser checks. |
| [PR #207](https://github.com/YuzeJ21/Scope-Proof/pull/207) | Exact head `b5c6f2e837c0549b5baad251a8d7c1750e9821d8` passed [PR CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40428339454) and merged as `8f01cf237b75da30796d1879f3fbde7b8a5ef6d5`. The PR head and merged main have the same tree. [Resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40431365174) passed 2,581 tests, 2 intentional skips, 95.0534% unrounded coverage, both deterministic benchmarks, Python 3.11/3.13 and Windows compatibility, installed-wheel checks, and 5 packaged-browser checks. Exact-head CodeQL and code review also completed without findings. |

The constructed benchmark executed 12 cases and 13 criteria with zero mismatches
and zero uncited-file False Ready outcomes; the comparison benchmark executed
2 cases with zero mismatches. These constructed results do not measure real-world
False Ready frequency. The installed-wheel browser reviewer was explicitly
labeled as automation. No target-repository code was executed.

## Deployment and frozen-evidence boundary

PR #206's merge triggered [Pages run 40404724868](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40404724868).
It was cancelled after its deploy step completed; GitHub's final deployment
status is `error`. This record does not claim that no deployment attempt occurred.
PR #207 then restricted the Pages workflow to manual dispatch and guarded its
deploy job by event name. At this verification, the newest Pages run and
deployment still belonged to PR #206's merge commit. No Pages run or deployment
was created for `8f01cf237b75da30796d1879f3fbde7b8a5ef6d5`. Manual
dispatch itself was not exercised. The latest GitHub Release remained v0.2.3.

The frozen R-002 inputs and result, and the original constructed
`scope-expansion` label, were unchanged from baseline
`36358146a5167270fff7e52769ae66ee8f56f2da` (`git diff --exit-code` over
`evals/r002`, `docs/research/r002-swebench-verified`, and
`evals/labels/benchmark_scope_expansion.json`). The label SHA-256 remained
`55d448d59b72bb5c70683537c5087605fd5ccd2dd1963b3ff66a770275abd087`;
the R-002 result SHA-256 remained
`2fc7115a6ffee3143d0f1d93dca1d51359f40857ec89f1c180d04d7f1e2d359f`.

## Readiness limit

Stage 1 remains closed with external-evidence counts at zero. Stage 2 remains
owner-led productization. The owner does not want qualifying participant reviews
or personal product testing; none was conducted for this record. Stage 3 stays
gated on genuine independent use and a separate owner decision. Automated CI,
browser journeys, and simulated reviewers cannot fill that gap. Real screen-reader
behavior and Windows/Linux desktop journeys remain unverified, so this record
does not claim accessibility conformance or a completed beta. No participant
outreach, release, publication, or deployment was initiated in this closure work.
