# Task 4 report — CLI and trusted-base Action provenance

## Scope

Implemented the approved Task 4 slice from committed Task 3 base `9fe23a8`:

- `scopeproof review` now requires an explicit typed `--confirmation FILE`.
- Requirements text is read and normalized criteria are parsed before confirmation
  validation; fixture or GitHub ingestion starts only after the exact text and ordered
  criteria digests match.
- The validated immutable criteria-source provenance is carried into the review bundle,
  lifecycle state, saved record, and CLI metadata.
- Genuine Alpha CLI initialization uses the same validated snapshot and preserves the
  public-summary non-disclosure boundary.
- Both trusted-base workflows pass the already validated confirmation file into the
  review command without changing triggers, permissions, checkout identity, fork behavior,
  comment behavior, or `continue-on-error` semantics.
- The repository-owned confirmation artifact is now the typed provenance shape and is
  bound to the exact current `.scopeproof/requirements.txt` bytes and normalized criteria.

This is engineering evidence. It does not prove criterion correctness, customer demand,
Alpha participation, runtime behavior of a target repository, or Stage 1 progress.

## RED/GREEN evidence

### Typed confirmation artifact

- RED: `uv run pytest -q tests/criteria/test_confirmation.py`
  - Result: `5 failed, 5 passed`.
  - Expected failures showed that the old validator rejected the typed shape, accepted the
    legacy hash-only shape, and did not validate ordered normalized criteria.
- GREEN: the same suite passed `10 passed` after the validator was changed to return
  `CriteriaSourceProvenance` and check both exact-source and canonical-criteria digests.

### CLI pre-ingestion boundary

- RED: focused new CLI cases produced `2 failed, 2 passed`.
  - Missing `--confirmation` still allowed the review handler to reach GitHub fetching.
  - The parser rejected the new flag because it did not yet exist.
- GREEN: the same focused cases passed `4 passed` after requiring the flag and validating
  the snapshot before fixture reads or GitHub client calls.

### Trusted-base workflows

- RED: the new workflow contract failed `1 failed` because the review command did not pass
  `.scopeproof/requirements-confirmation.json`.
- GREEN: both repository and copyable workflows pass the same confirmation path after the
  existing no-network validator.

## Recomputed repository snapshot

- Source URI:
  `https://github.com/YuzeJ21/Scope-Proof/blob/a2fdecbd5918535f4db35bfdf7da64156f393b67/.scopeproof/requirements.txt`
- Source revision: `a2fdecbd5918535f4db35bfdf7da64156f393b67`
- Exact UTF-8 source digest:
  `f7314191acbae91972e85a75b4f1237b8ef7c91de1e9a75871386e2efd630ae6`
- Ordered canonical criteria digest:
  `716a651581a12acf78fe7fa45c53b37dfc57ca33c1641480b2ebbdac2107d64f`

Both digests were recomputed from the current file with the production parser and hashing
helper; no preflight digest was trusted blindly.

## Final focused verification

Command:

```text
uv run pytest -q tests/criteria/test_confirmation.py tests/cli/test_cli.py tests/github_action/test_workflow_files.py tests/github_action/test_contract.py tests/github_action/test_runner.py
```

Result: `104 passed`.

Additional checks:

- Ruff on every touched Python file: passed.
- Repository confirmation through the installed CLI validator: passed and emitted the
  six-field typed provenance payload.
- `git diff --check`: passed.

## Preserved boundaries

- No untrusted PR-head code is checked out or executed.
- The Action remains informational and non-required.
- Fork publication remains non-mutating.
- No paid API, account, billing, private-repository, outreach, generic review, security,
  auto-fix, tag, Release, or validation-claim scope was added.
- The copyable Action source pin was intentionally left unchanged for Task 7.
- Concurrent Task 5 and Task 6 changes were not staged or altered by this commit.
