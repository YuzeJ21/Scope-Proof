# ScopeProof privacy and private-repository readiness

## Current boundary

ScopeProof is local-first and public-repository only. An optional GitHub token
exists only in the active CLI process or Streamlit session: it is never stored
in local review JSON, exports, fixtures, or command output. ScopeProof has no
hosted storage, account system, GitHub App, or private-repository ingestion.

This is a readiness design, not a claim that private support exists.

## Retention and deletion

| Data | Location | Retention / deletion |
| --- | --- | --- |
| Public PR metadata, excerpts, evidence, findings, decisions | User-selected local JSON review directory after save | User deletes its review JSON or directory; ScopeProof has no hosted copy. |
| Optional GitHub token | Process/session memory | Cleared at process/session end. |
| Requirements and reviewer notes | In memory and saved local review, if saved | Deleted with the local review record. |
| Action events/logs | Repository owner's GitHub environment | Owner controls retention; ScopeProof must not print tokens. |

Saved records contain repository identity, immutable SHAs, excerpts, and human
notes. Users control this local data and should use a protected directory.

## Future private posture

Prefer local CLI or in-repository GitHub Actions, not a hosted service. A future
private slice must use user-provided credentials or GitHub-native secrets,
remain read-only, never persist tokens, and keep public/offline operation.

Minimum read scope: `contents: read` and `pull-requests: read`. No
administration, workflow, deployment, package, organization, or broad write
scope is acceptable. A future comment/check adapter needs separate review and
may never use elevated credentials for fork-origin pull requests.

## Threat model

| Threat | Current control | Required before private support |
| --- | --- | --- |
| Token in records or reports | Tokens are excluded from schemas and exports | Redaction regression tests for every adapter/log path. |
| PR code execution | ScopeProof only reads GitHub data | Preserve; runtime evidence needs its own isolated design. |
| Fork credential exposure | Planner returns no write plan; workflow avoids `pull_request_target` | Continue payload fixture tests. |
| Stale/wrong evidence | Immutable head-SHA links and head-change detection | Mandatory stale-head warning for current claims. |
| Residual source data | No hosted copy; local user-owned records | Test and document any future atomic local delete command. |

## Audit and operating rules

Local `ReviewState` keeps criteria revisions and append-only resolution events;
it is an audit trail, not a tamper-proof ledger. A private pilot must retain the
ruleset version and source SHA, request least privilege, never upload code or
notes to ScopeProof infrastructure, keep forks non-mutating, and test secret
redaction, no-token persistence, deletion, and public/offline compatibility.
