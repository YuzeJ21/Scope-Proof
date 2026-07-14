# Post-v0.1.18 Development Version Design

## Reproduced gap

Public release v0.1.18 and tag `v0.1.18` resolve to
`c52e87340d33bab49c776635e2dd3a328b9074b2`. Protected `main` is now
`4c67300e5164077f5cc1dca5241bf318521a067f` and includes the unreleased
confirmed-criteria analysis cue from PR #110, but the single version source
still reports `0.1.18`.

As a result, a source build and new review from post-release `main` can identify
as the public v0.1.18 artifact even though their code differs. This weakens the
existing review-provenance contract.

## Decision

Advance only the development identity and its repository contract to
`0.1.19.dev0`, following the established first-post-release convention used by
the first protected change after v0.1.17.

README installation guidance remains on the verified v0.1.18 wheel. No release,
tag, Action pin, schema, record version, product behavior, dependency, or
workflow changes.

## Contract

- `scopeproof_core/version.py` is exactly `0.1.19.dev0`.
- Hatch metadata, imported version, both CLIs, and new-review `tool_version`
  continue deriving from that single source.
- README continues installing verified public v0.1.18 assets.
- Existing stored review provenance is not rewritten.

## Boundaries

No paid API/LLM, billing, organization, private repository, fork test,
notification, release, synthetic validation, external evidence, or product
behavior is introduced.
