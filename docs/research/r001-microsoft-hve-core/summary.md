# R-001 evidence-quality summary

R-001 is **public engineering research** based on
[microsoft/hve-core#2148](https://github.com/microsoft/hve-core/issues/2148) and
[PR #2149](https://github.com/microsoft/hve-core/pull/2149), fixed at
[`8e5277e88f0ca650549d41255eb24d74afc74772`](https://github.com/microsoft/hve-core/commit/8e5277e88f0ca650549d41255eb24d74afc74772).
It does not advance Stage 1. No Microsoft repository code was executed; ScopeProof only read
public GitHub metadata and files. Static candidates and observed CI are not runtime proof.

## Result

The current anonymous and authenticated-session reviews are identical after normalizing only
review ID, created/saved timestamps, and local paths. Both have complete ingestion, no warnings,
no skipped changed files, a `passing` observed-CI state (94 total, 89 success, 5 skipped), one E2
eval-definition candidate alongside 47 E1 documentation candidates, no runtime evidence, no
reviewer decisions, no resolutions, no final acceptance, and a conservative `blocked` gate.

The skipped eval execute/report checks remain skipped. The changed eval definition is E2 test
intent only, not execution. Passing observed CI does not turn candidate evidence into runtime
verification or acceptance.

## Inspectable artifacts

- Exact source requirements: [`requirements.txt`](requirements.txt), SHA-256
  `07ee2fa337b4e2b992bd9d6d39753237dd167be48456a548dd2ff36201b8fcdd`
- [Pre-fix record](before.md), including original report SHA-256
  `bc114f4825aaf8c114b47a0509fc4d3235ff3708d771bc81b8fc0048903c0f39`
- [Post-fix record](after.md), including anonymous SHA-256
  `1013c3b9af86215d776562f9fb137172e77cc252d1ec10133c5f7d3dc919851a`
  and authenticated-session SHA-256
  `c592d58622e0dba608d581c9297aad87cc362cdab8341bdcf558d8be1a67e3b4`

The compact record intentionally excludes the full generated reports and third-party excerpts;
those reports remain in `/tmp` and are hash-addressed above. The remaining external condition is
unchanged: Stage 1 stays `waiting_for_inbound_public_alpha_submission`, and Stages 2–4 remain
gated on genuine completed public-alpha evidence.
