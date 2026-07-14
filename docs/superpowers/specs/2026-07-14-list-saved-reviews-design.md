# Saved review CLI discovery design

## Problem

ScopeProof already stores reviews locally and exposes safe, deterministic review-ID discovery in
the Streamlit workbench through `JsonReviewStore.list_review_ids()`. The CLI can create, export,
and delete a review, but a user returning in a fresh shell cannot discover the identifiers needed
by `scopeproof export` or `scopeproof delete` without inspecting the storage directory manually.

## Decision

Add `scopeproof list [--storage-dir PATH]` as a local-only discovery command. It will reuse
`JsonReviewStore.list_review_ids()` so directory safety, record-name validation, symlink rejection,
and deterministic sorting stay in the storage layer. The command will not parse record contents,
contact GitHub, or expose review data.

The command emits one schema-validated JSON object:

```json
{"review_ids": ["review-a", "review-b"], "storage_dir": ".scopeproof/reviews"}
```

An absent store is a successful empty result. An unsafe store remains a fail-closed CLI error.
The existing default CLI storage path is preserved.

## Trust boundaries

- Listing record identifiers is not review, test, runtime, or correctness evidence.
- Only names already accepted by the storage layer are returned.
- Record contents are not parsed, so one corrupt record cannot block discovery or leak content.
- The response is validated with Pydantic before serialization.
- No token, network call, paid API, hosted storage, or new persistence format is introduced.

## Verification

Test-drive empty, sorted, corrupt-record, and unsafe-root behavior through the CLI. Add a repository
contract for the documented command, then run Ruff, the full offline suite, the deterministic
benchmark, diff checks, clean-wheel identity and installed-command probes, and packaged workbench
health. Protected `verify` and CodeQL remain required before merge.
