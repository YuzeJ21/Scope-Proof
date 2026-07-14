# Post-v0.1.19 Development Version Design

## Reproduced gap

Public release and tag `v0.1.19` resolve to
`b6d09df88d37f7b2bb4b80e202331bc72f500d09`. The release commit still reports
`0.1.19`, which is correct for the published artifact but would let any later
source build or newly created review on `main` retain that same public identity.

## Decision

Advance only the unreleased development identity and its repository contract to
`0.1.20.dev0`, following the established first-post-release convention used
after v0.1.18.

README installation guidance remains on the verified v0.1.19 wheel. No release,
tag, Action pin, schema, record version, product behavior, dependency, or
workflow changes.

## Contract

- `scopeproof_core/version.py` is exactly `0.1.20.dev0`.
- Hatch metadata, imported version, both CLIs, and new-review `tool_version`
  continue deriving from that single source.
- README continues installing verified public v0.1.19 assets.
- Existing stored review provenance is not rewritten.

## Boundaries

No paid API/LLM, billing, organization, private repository, fork test,
notification beyond the protected PR, release, synthetic validation, external
evidence, or product behavior is introduced.
