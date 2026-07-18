# Owner rehearsal: local engineering evidence

Use this notification-free rehearsal only to check the local intake shape and deterministic review
workflow. It is deliberately constructed engineering evidence only: it does not establish an
independent participant, a qualified inbound case, external runtime verification, a completed
participant outcome, or correctness. It does not advance Stage 1.

Do not create a public issue, comment, release note, or notification for this rehearsal. Keep every
output in a new temporary local directory and delete it when the engineering check is complete.

## Copyable local runbook

From the repository root, use one temporary directory for this run. The checked requirements are
the four atomic criteria paired with the deliberately constructed CSV-export fixture.

```bash
run_dir="$(uv run python -c 'import os, tempfile; print(os.path.realpath(tempfile.mkdtemp(prefix="scopeproof-owner-rehearsal.")))')"

uv run scopeproof owner-rehearsal init \
  --pr https://github.com/scopeproof/demo-stock-research/pull/17 \
  --requirements-source https://github.com/scopeproof/demo-stock-research/issues/17 \
  --criteria-authority "I am the owner of this deliberately constructed rehearsal and authorize these criteria." \
  --requirements evals/rehearsals/owner_rehearsal_criteria.txt \
  --source-owner-confirmed \
  --confirmed-no-confidential-information \
  --storage-dir "$run_dir/alpha-rehearsals"
```

This creates one deterministic owner-rehearsal record and prints its ID plus the fixed exclusion
fields. Copy the printed ID into `rehearsal_id`; creation proves only that local rehearsal input
validated and persisted, not that any public URL was reachable or that anyone participated.

```bash
rehearsal_id='<printed-rehearsal-id>'
uv run scopeproof owner-rehearsal show "$rehearsal_id" \
  --storage-dir "$run_dir/alpha-rehearsals"
```

This reloads the saved local record. Confirm its fixed `owner_rehearsal` classification and
ineligibility fields; it does not convert the record into an alpha case or outcome.

```bash
uv run scopeproof review --fixture evals/fixtures/csv_export_pr.json \
  --requirements evals/rehearsals/owner_rehearsal_criteria.txt \
  --storage-dir "$run_dir/reviews" \
  --report "$run_dir/review.json"
```

This runs local deterministic coverage against the deliberately constructed fixture, saves a
review, and writes a JSON report. It proves neither runtime behavior nor correctness; inspect the
missing-evidence explanations and keep the conservative gate result when must-have evidence is
missing. Copy the printed review ID into `review_id`.

```bash
review_id='<printed-review-id>'
uv run scopeproof export "$review_id" \
  --storage-dir "$run_dir/reviews" \
  --format csv > "$run_dir/review.csv"
uv run scopeproof comparison-benchmark
```

The export reloads the saved review and renders a local CSV. The comparison benchmark checks the
bundled constructed re-review classifications across two paired previous/current cases. Together
they are reproducible engineering checks, not participant, customer, market, external-use, or
Stage 1 evidence.
