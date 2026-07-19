# R-001 after: corrected deterministic review

R-001 is **public engineering research**, not a participant, customer, market, or Alpha case. It
does not advance Stage 1. No Microsoft repository code was executed; ScopeProof only read public
GitHub metadata and files. Static candidates and observed CI are not runtime proof.

## Identity and execution boundary

- Issue: [microsoft/hve-core#2148](https://github.com/microsoft/hve-core/issues/2148)
- Pull request: [microsoft/hve-core#2149](https://github.com/microsoft/hve-core/pull/2149)
- Head verified immediately before both runs:
  [`8e5277e88f0ca650549d41255eb24d74afc74772`](https://github.com/microsoft/hve-core/commit/8e5277e88f0ca650549d41255eb24d74afc74772)
- Requirements SHA-256: `07ee2fa337b4e2b992bd9d6d39753237dd167be48456a548dd2ff36201b8fcdd`
- Classification: `public_engineering_research`; Stage 1 credit: `0`.

Fresh outputs stay in `/tmp/scopeproof-r001-after.XbYrL3` and are represented by hashes:

| Mode | Report SHA-256 | Normalized result |
| --- | --- | --- |
| Anonymous | `1013c3b9af86215d776562f9fb137172e77cc252d1ec10133c5f7d3dc919851a` | Complete ingestion; blocked |
| Authenticated session | `c592d58622e0dba608d581c9297aad87cc362cdab8341bdcf558d8be1a67e3b4` | Equal to anonymous after removing review IDs, timestamps, saved-at values, and local paths |

The optional GitHub session token was read only into the authenticated Python process. It was not
printed, written, committed, or passed as a command argument.

## Corrected observations

- Ingestion was `complete`, with zero warnings and zero skipped changed files.
- Observed CI is `passing`: **94 total**, **89 success**, 0 pending, 0 failing, 0 neutral, and
  **5 skipped** check runs; the empty legacy status collection has 0 concrete statuses and no
  authority over completed check runs.
- The five skipped checks are inert observed metadata, not execution evidence:
  - `Eval Validation / Eval Report`
  - `Eval Validation / Eval Execute (${{ matrix.kind }})`
  - `ADR Consistency Validation / Upload ADR SARIF`
  - `ADR Consistency Validation / Validate ADR Consistency`
  - `Docusaurus Tests / Docusaurus Unit Tests`
  These checks remained skipped and provide no runtime proof.
- Candidate selection remains bounded at 48: 47 E1 documentation candidates plus one E2 test
  candidate, [`evals/agent-behavior/eval.yaml:L1340`](https://github.com/microsoft/hve-core/blob/8e5277e88f0ca650549d41255eb24d74afc74772/evals/agent-behavior/eval.yaml#L1340-L1340), for AC-04.
  Relevant eval definitions show test intent, not execution; no Microsoft test or eval was run.
- No manual runtime evidence, resolutions, reviewer decisions, or final acceptance exists. The
  gate remains `blocked` for `blocking_criteria` and `unresolved_criteria`.

## Exact normalized comparison to the pre-fix controls

Only review identity, created/saved timestamps, and local file paths were normalized. PR head,
requirements, ingestion, candidate type/level/path/line/score/limitations, findings, gate, CI
observation, and research context were compared.

1. CI changed from `pending` to `passing` because completed successful check runs now outrank an
   empty legacy `pending` aggregate.
2. AC-04 adds the E2 eval-definition candidate at `evals/agent-behavior/eval.yaml:L1340`, score
   `0.417`, with the explicit limitation “Candidate test/eval definition shows test intent, not
   execution”. To preserve the eight-candidate limit, the prior E1 documentation candidate at
   `.github/agents/hve-core/task-planner.agent.md:L190`, score `0.500`, is no longer selected.
3. AC-04's finding evidence level becomes E2 because its selected set includes the E2 candidate.
   Its status, confidence, missing evidence, recommendation, and the overall blocked gate remain
   unchanged. All other selected candidate content and findings remain unchanged.

This is an engineering-quality improvement to evidence presentation, not validation that the
Microsoft change is correct.
