# R-001 before: Microsoft hve-core PR 2149

R-001 is **public engineering research**, not a participant, customer, market, or Alpha case. It
does not advance Stage 1. No Microsoft repository code was executed; ScopeProof only read public
GitHub metadata and files. Static candidates and observed CI are not runtime proof.

## Fixed public identity

- Issue: [microsoft/hve-core#2148](https://github.com/microsoft/hve-core/issues/2148)
- Pull request: [microsoft/hve-core#2149](https://github.com/microsoft/hve-core/pull/2149)
- Reviewed head: [`8e5277e88f0ca650549d41255eb24d74afc74772`](https://github.com/microsoft/hve-core/commit/8e5277e88f0ca650549d41255eb24d74afc74772)
- Acceptance criteria: [`acceptance-criteria.txt`](acceptance-criteria.txt), SHA-256
  `07ee2fa337b4e2b992bd9d6d39753237dd167be48456a548dd2ff36201b8fcdd`

The original 2026-07-19 report is retained outside the repository at
`/tmp/scopeproof-msft-2149-research.aWlYxR/review.md`, SHA-256
`bc114f4825aaf8c114b47a0509fc4d3235ff3708d771bc81b8fc0048903c0f39`.
The fresh pre-fix controls are ephemeral provenance under
`/tmp/scopeproof-r001-before.rpLI3m`; they are not a repository dependency and are also outside
the repository:

| Mode | Report SHA-256 | Normalized result |
| --- | --- | --- |
| Anonymous | `56944aa93d082d756a2e993d5e3780a685df9b1d0eec89caf276363b7dc45c99` | Same five-file head, complete ingestion, 48 E1 documentation candidates, blocked |
| Authenticated session | `c74a168d555b7dfc1b4bbfc848c8bcb8357560d71c5b7a31f568bae677f36109` | Same normalized result as anonymous |

## Observed limitation before the fixes

The old adapter treated the empty legacy combined-status aggregate as pending, even though the
PR exposed 94 completed check runs (89 success and 5 skipped). It therefore reported observed CI
as `pending`. All 48 selected candidates were E1 documentation, despite a relevant changed eval
definition. There were no skipped changed files or ingestion warnings, but there were also no
manual runtime records, reviewer decisions, resolutions, or final acceptance. The gate was
conservatively `blocked`.

The report intentionally is not copied here: it contains 48 third-party candidate excerpts. Its
hash and the immutable public links above make the exact source review inspectable without
vendoring unnecessary Microsoft content.
