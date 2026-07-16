# Public-alpha outcome form

Record exactly one outcome after reviewing the evidence and decisions:

- `found_useful_gap` — ScopeProof surfaced a requirement-evidence gap the participant considered useful.
- `showed_only_known_information` — the review was understandable but added no useful new information.
- `created_friction` — qualification, criteria, evidence, decisions, outcome, export, or integration created material friction. Supply `--friction-stage`.

Example:

```bash
scopeproof alpha outcome CASE_ID \
  --review-id REVIEW_ID \
  --head-sha HEAD_SHA \
  --result created_friction \
  --friction-stage evidence \
  --notes-file outcome-notes.txt
```

Report consent and quotation consent are independent. Both default to no. Add `--report-consent` only to allow the reduced public summary; add `--quote-consent` only to permit a quotation. The public summary excludes local notes and permission fields.

Do not claim repeat usage, customer value, market demand, or correctness from one outcome.
