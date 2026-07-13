# CLI Error Recovery Design

## Problem

A clean-installed `scopeproof review` successfully reviewed public PR #22 and exported its validated record in JSON, Markdown, CSV, and HTML. However, a malformed PR URL or missing requirements file produced a full Python traceback with internal installation paths instead of a concise operator error.

## Design

Keep all domain exception classification in the existing GitHub, storage, criteria, and Pydantic layers. At the CLI boundary, retain the parser instance and catch only expected user-facing exception families around handler execution:

- `GitHubIngestionError` for malformed URLs, inaccessible PRs, rate limits, network errors, and safety limits.
- `OSError` for missing, unreadable, or unwritable local files.
- `ValueError` for invalid local content and Pydantic validation failures.

Pass these messages to `ArgumentParser.error()`, which emits standard `scopeproof: error: ...` stderr and exits with status 2. Do not catch arbitrary `RuntimeError`, `AssertionError`, or `Exception`; unexpected programming defects must retain diagnostic tracebacks.

## Documentation

Add an installed CLI workflow to the README using a public PR URL, a reviewer-authored one-criterion-per-line requirements file, local review storage, and export commands. State that the requirements must be explicitly confirmed by the reviewer before running the command and that the optional token is neither required nor persisted.

## Verification

- Red-green tests for malformed PR URL and missing requirements file.
- Existing success-path CLI tests remain unchanged.
- Build and install a wheel in a fresh environment.
- Re-run the source-owner-confirmed PR #22 technical review and four exports.
- Verify malformed input returns exit 2, concise stderr, and no traceback.

## Boundaries

The change adds no API call, paid service, credential persistence, verdict behavior, evidence rule, or GitHub write. It does not treat the PR #22 technical review as customer or external validation.
