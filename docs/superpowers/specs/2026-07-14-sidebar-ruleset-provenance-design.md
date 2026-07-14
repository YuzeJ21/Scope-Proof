# Sidebar Ruleset Provenance Design

## Evidence

A current-main first-use audit followed the deliberately constructed demo through source load,
explicit criteria confirmation, deterministic analysis, and the evidence matrix. The sidebar
always renders `Ruleset 1.0.0` from a literal string in `apps/web/app.py`.

The authoritative current value is `scopeproof_core.schemas.models.RULESET_VERSION`. Every
validated `Review` also persists its own `ruleset_version`, and reopened reviews intentionally
retain that historical provenance. Therefore, a reopened review created under a different ruleset
can show the correct historical value in its bundle and exports while the persistent sidebar
mislabels it as `1.0.0`.

## Decision

Render one context-aware sidebar ruleset value:

- when an active analysis bundle exists, display `bundle.review.ruleset_version`;
- before analysis exists, display the current `RULESET_VERSION` constant.

Keep the existing caption suffix exactly `local-first · public repositories only`. The sidebar
continues to describe the active review when one exists and the current engine otherwise.

## Alternatives considered

### Active review, otherwise current ruleset — selected

Preserves truthful historical provenance and eliminates the duplicate checked-in version literal.

### Always show the current engine ruleset

Rejected because a reopened historical review would still be mislabeled even though its validated
bundle preserves a different ruleset.

### Remove the sidebar ruleset

Rejected because the version is useful trust context during first use and review reopening; the
problem is the source of the value, not its presence.

## Architecture and data flow

Import `RULESET_VERSION` into the Streamlit layer from the core schema module. After deriving the
existing `bundle` local, calculate `sidebar_ruleset_version` as the active review value when
`bundle` is not `None`, otherwise as `RULESET_VERSION`. Pass that value only to the existing
sidebar caption.

No new state, helper service, persistence field, or core dependency is required. The core remains
independent from Streamlit.

## Error and trust behavior

Both possible values are already Pydantic-validated or checked-in core data. This change adds no
fallback that could conceal invalid persisted state. Unsupported or invalid records continue to
fail through the existing storage validation path.

## Verification

- Add a regression that loads an analyzed review whose validated `review.ruleset_version` differs
  from the current constant and requires the sidebar caption to show the review value.
- Preserve the blank/current-flow assertion for the checked-in `RULESET_VERSION`.
- Reject a literal `Ruleset 1.0.0` in `apps/web/app.py` so future ruleset changes cannot silently
  reintroduce drift.
- Run focused AppTests, Ruff, the complete offline suite, the deterministic benchmark,
  `pip check`, `git diff --check`, and a current-source loopback browser smoke.

## Boundaries

Do not change schemas, gates, lifecycle semantics, storage formats, exports, evidence rules,
workflow permissions, dependencies, version identity, or visible wording beyond substituting the
truthful ruleset value. No paid or LLM API, billing, fork, organization, second account, private
repository, synthetic validation, notification, or untrusted-code execution is introduced.
