# R-002 SWE-bench Verified static engineering benchmark

Status: completed public engineering research. This record contributes zero Stage 1 validation
credit and does not establish correctness, runtime behavior, acceptance, customer use, or market
validation.

R-002 broadens static engineering coverage across 20 historical public PRs. It measures owner-confirmed research-label candidate matching and immutable-reference integrity. It does not measure customer precision, real False Ready rate, correctness, runtime behavior, or acceptance.
No target-repository code was executed.

## Scope and provenance

- Source: `SWE-bench/SWE-bench_Verified`, `default/test`, immutable revision
  `91aa3ed51b709be6457e12d00300a6a596d4c6a3`.
- Source file: `data/test-00000-of-00001.parquet`, 2,090,470 bytes,
  SHA-256 `43ed5a3d1d98da36472c1ade65ddd2085d7b4ff694fcaf6a023a07c5c1f32f21`.
- Source population: 500 rows, 500 unique instances, 12 repositories.
- Cohort: 20 cases across all 12 repositories, with at most two cases per repository.
- Source manifest SHA-256:
  `05729529a256088befdecc7abb2ba229d6088fb3ed2ff6084462536a1ad12726`.
- Confirmed criteria SHA-256:
  `bb62a7f5bd891322cfcf7ef6681d61dec63b8d2c28078e2aef35a756e1485ece`.
- Confirmed candidate-label set SHA-256:
  `e1ba509a9569195d68e718708f2585941052a7eeb2099d46a3697963f8a2abe8`.
- Exact scored ScopeProof commit: `4ba3c11829fc39dfe6e0caa6b99e4537ccba66f5`.
- Frozen inputs contain 20 criteria, 1,160 independently labelled candidate pairs, and 41
  expected-missing records.

The deterministic selection validates the pinned source first, gives every repository one case,
assigns eight additional slots by descending repository case count and repository name, orders
eligible rows by `SHA256("<pinned-file-sha256>:<instance_id>")`, takes each repository quota,
then orders the final cohort by repository and instance ID before assigning `R002-001` through
`R002-020`. Selection did not inspect ScopeProof output, criteria, patch complexity, labels, or
gate results.

## Result

Two separately launched, network-denied offline runs produced byte-identical canonical JSON:

| Measure | Result |
|---|---:|
| Executed / failed / skipped cases | 20 / 0 / 0 |
| Gate distribution | 18 Blocked / 2 Needs Review |
| Unexpected Ready | 0 |
| Normalized rerun mismatches | 0 |
| Retrieved candidates | 22 |
| Missing-evidence explanations | 41 |
| Owner-confirmed label candidate precision | 18 / 22 (81.82%) |
| Criterion candidate coverage | 5 / 20 (25.00%) |
| Candidate-to-labelled-file coverage | 10 / 47 (21.28%) |
| Candidate-to-labelled-hunk coverage | 13 / 81 (16.05%) |
| Missing-explanation completeness | 41 / 41 (100.00%) |

Implementation/test separation, immutable-reference, parse, schema, source-hash, and source-SHA
error counts were all zero. Every visible CI state remained unavailable with no observations.
There was no runtime evidence, resolution, or final acceptance.

The [canonical redacted result](result.json) contains the complete machine-readable metrics and
per-case static references.

## Package equivalence

The exact scored commit produced:

- wheel SHA-256 `414d90089d07fec377c9b79eeb062f63830f17545a79d990bccb118e7206b554`;
- source-distribution SHA-256
  `0ea08e686c57aae257009ec2d81a277f4254d92194285965a622c7a05b899d42`.

Both archives contain exactly the three redacted R-002 inputs under `evals/r002`: source manifest,
confirmed criteria, and confirmed labels. They contain no ignored research cache or annotation
review. A clean wheel installation outside the checkout emitted output byte-identical to the
source-checkout result when explicitly bound to the same commit and immutable local cache.

## Fixed limitations

- Criteria and relevance labels are benchmark-owner research judgements, not source-owner
  confirmation.
- Only static historical diff and immutable PR-head evidence was evaluated.
- No target code or tests were executed and current CI was not observed.
- Candidate evidence does not prove correctness or criterion satisfaction.
- R-002 contributes zero Stage 1 validation credit.

Stage 1 remains `waiting_for_inbound_public_alpha_submission`; Stages 2–4 remain gated.
