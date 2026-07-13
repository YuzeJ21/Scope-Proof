# One-Command Report Design

## Problem

The installed CLI currently requires two commands to produce a report: `scopeproof review` prints metadata containing a generated review ID, then the operator must copy that ID into `scopeproof export`. This is scriptable but creates avoidable first-use friction for a real public PR.

## Decision

Add optional `--report PATH` to `scopeproof review`. Infer the existing deterministic exporter from the case-insensitive suffix: `.md`, `.json`, `.csv`, or `.html`. Before reading requirements or contacting GitHub, reject unsupported suffixes and any path that already exists. Never overwrite a report.

The review still persists its validated local state and prints the existing JSON metadata. When a report is requested and successfully written, add a `report` field containing the path. The separate `scopeproof export REVIEW_ID` workflow remains unchanged for repeat exports and other formats.

## Data and failure flow

1. Parse arguments and validate the report suffix and nonexistence.
2. Parse user-confirmed criteria and ingest the public PR or trusted fixture.
3. Build the validated review bundle and save the versioned local review state.
4. Render that validated state through the existing exporter and write UTF-8 text to the requested path.
5. Print metadata only after both persistence and requested report output succeed.

If report writing fails after local persistence, the CLI exits with the existing concise `scopeproof: error:` path rather than claiming full success. It does not delete the valid saved review record. Unexpected programming errors retain tracebacks.

## Alternatives

- Replace metadata stdout with a report selected by `--report-format`. This breaks existing scripts and hides the saved review path.
- Add a shell one-liner that parses the review ID. This is harder to use across shells and operating systems.
- Infer the report format from content or a separate format flag. The filename suffix already gives one deterministic source of truth.

## Boundaries

- Never overwrite an existing file.
- Accept only `.md`, `.json`, `.csv`, and `.html` suffixes.
- Render only validated ScopeProof review state through existing exporters.
- Do not execute reviewed repository code or convert static evidence into runtime verification.
- Add no service, account, billing, API, LLM, license, or dependency.

## Release

This is a user-visible installed CLI improvement, so version 0.1.13 is justified. After the protected implementation merge and merged-main gates pass, build one wheel from the exact merge commit, publish v0.1.13 with wheel and checksum assets, redownload both, and verify the one-command report from the installed wheel. Do not publish intermediate releases.

## Acceptance Criteria

1. Existing `review` behavior and metadata remain unchanged when `--report` is absent.
2. A requested Markdown, JSON, CSV, or HTML report is written in the same command.
3. Metadata includes the report path only when requested.
4. Existing paths and unsupported suffixes fail before ingestion with exit 2, actionable text, and no traceback.
5. The saved review remains schema-valid and contains no token.
6. README documents the one-command public-PR path while retaining repeat export guidance.
7. A clean-installed wheel produces and validates reports outside the source checkout.
8. v0.1.13 targets the exact protected-main merge commit and provides matching wheel/checksum assets.

