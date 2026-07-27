# R-002 retrieval miss taxonomy

Status: completed post-hoc engineering analysis. This record does not change the frozen R-002
inputs, labels, canonical result, metrics, or Stage 1 status.

## Result

The v0.2.3 diagnostic path was run offline against the 20 frozen R-002 criteria and the same
hash-bound static line universe. Five criteria retained at least one benchmark-owner-labelled
relevant candidate. The remaining 15 criteria form this miss taxonomy:

| Category | Criteria | Meaning in this record |
|---|---:|---|
| Threshold rejection | 14 | Relevant labelled lines had term overlap, but every relevant line was rejected by the existing unchanged thresholds. Two cases also returned unrelated candidates. |
| Unsupported evidence form | 1 | Relevant labelled lines existed, but none shared a normalized lexical term with the criterion. The current line-level lexical matcher cannot represent that relationship. |
| All other bounded categories | 0 | The frozen cohort did not demonstrate that category. Zero is not proof the failure mode cannot occur. |

The machine-readable [taxonomy](miss-taxonomy.json) records all ten bounded categories, one entry
for each miss, diagnostic counters, frozen upstream hashes, and explicit zeroes. Its generator is
`python -m scopeproof_core.evals.r002_taxonomy`.

## Interpretation boundary

- This is post-hoc diagnosis of a seen engineering cohort, not a new score or accuracy claim.
- `threshold_rejection` identifies the current deterministic mechanism. It does not prove that
  lowering a threshold would improve the product safely.
- The unsupported-evidence-form case demonstrates a lexical mismatch. It does not authorize
  embeddings, LLM verdicts, repository execution, or semantic correctness claims.
- R-002 criteria and relevance labels remain benchmark-owner research judgements, not
  source-owner-confirmed acceptance criteria.
- No target-repository code or tests were executed.
- R-002 still contributes zero Stage 1 validation credit.

## Product decision

Do not tune against R-002. Any retrieval change must first be specified as a narrow rule, covered
by a constructed regression fixture, and evaluated on a separately selected and independently
labelled R-003 holdout. A change must preserve zero must-have False Ready, immutable references,
implementation/test separation, deterministic reruns, and complete missing-evidence explanations.
