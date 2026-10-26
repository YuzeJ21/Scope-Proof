# Constructed changed-file scope checks

This directory holds a current, constructed expectation for the existing
`scope-expansion` fixture. The frozen label in `evals/labels/benchmark_scope_expansion.json`
still says `expected_gate: ready` (SHA-256
`55d448d59b72bb5c70683537c5087605fd5ccd2dd1963b3ff66a770275abd087`).
The new gate cannot treat that uncited auth file as resolved, so
`current_gate_expectations.json` expects `needs_review` and reports the historical
expectation separately. No original fixture, label, or R-002 input/result was changed.

| Constructed case | Current expectation | Checked behavior |
| --- | --- | --- |
| Uncited `src/auth.py` | Needs Review | A changed path with no finding-linked candidate cannot accompany Ready. |
| Candidate exists but finding does not cite it | Needs Review | Orphan evidence cannot clear the path. |
| Generated-looking, renamed, unrelated-looking path | Needs Review | Names and statuses never imply out of scope. |
| Reviewer marks outside confirmed criteria | Eligible for Ready only after other gates | Decision binds review ID, head, criteria revision and digest; reviewer and note remain in history. |
| Reviewer marks within confirmed criteria | Needs Review until cited | Scope classification does not invent candidate evidence. |
| Skipped file or unknown legacy inventory | Needs Review | A decision cannot waive incomplete ingestion or unknown inventory. |

These are automated fixture and reviewer-simulation checks, not independently observed
product use or a measured real-world False Ready rate. The benchmark reports
`uncited_file_false_ready` separately and fails when it is nonzero.
