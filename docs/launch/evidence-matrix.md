# ScopeProof Launch Evidence Matrix

| Asset | Source | What it demonstrates | What it does not demonstrate |
| --- | --- | --- | --- |
| Offline CSV-export demo | Checked-in constructed fixture | Deterministic criteria-to-evidence workflow, missing-evidence visibility, exports | A real incident, customer usage, or runtime correctness |
| Benchmark | 12 executable fixture-label pairs | Regression coverage, 0 known must-have False Ready, link validation | Production precision/recall or market validation |
| Public PR technical smoke | Public GitHub PR with proxy requirement | Public ingestion and local report generation can complete | User-confirmed requirement coverage or a confirmed product gap |
| Streamlit workbench | AppTest and local health smoke | Local reviewer flow, persistence, atomic external verification, comparison, and exports | Browser/runtime verification of the reviewed PR |
| GitHub Action advanced preview | Local payload and HTTP-mock tests | Trusted-base planning and hash-confirmed requirement boundaries | Product adoption, runtime correctness, or a default first-use path |
| Privacy readiness design | `docs/privacy-readiness.md` | Local-only retention boundary and private-pilot constraints | Hosted or private-repository availability |

## Publishing rule

Only describe the first two assets as a deliberately constructed demo and
benchmark. Describe a public-PR run as a technical smoke unless a source owner
has provided confirmed acceptance criteria and permission to publish the review.
Do not convert this matrix into usage, customer, accuracy, or runtime claims.
