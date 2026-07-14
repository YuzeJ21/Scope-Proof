# Post-v0.1.21 Development Version Design

## Context

ScopeProof v0.1.21 is publicly released at
`7a99db62409efb1cbbf24f276305634f8dad061d`. Protected `main` intentionally reports the exact
release version, `0.1.21`, because that tree produced the public wheel. Any later source change on
`main` must not continue identifying itself as the already published artifact.

The public release has been independently redownloaded and verified. Its tag and release target
match protected `main`, it contains exactly the wheel and checksum, and controlled clean-install
identity, list, benchmark, dependency, and loopback-health checks pass. This is controlled product
evidence, not external validation or proof of correctness.

## Decision

Advance the single checked-in version source to `0.1.22.dev0` in one protected maintenance pull
request. Update the repository contract first, observe its focused failure, then update
`scopeproof_core/version.py` and verify package metadata plus new-review provenance.

README continues to install v0.1.21. The copyable Action continues to pin the immutable v0.1.21
release-tree commit. No release or public notification beyond the required protected PR is
created.

## Alternatives considered

- Keep `0.1.21`: rejected because future unreleased source would be indistinguishable from the
  published wheel.
- Use `0.1.21.post1`: rejected because no post-release artifact is being published.
- Use `0.1.22.dev0`: selected because it truthfully marks the next unreleased development line.

## Contract

- `scopeproof_core/version.py` contains `__version__ = "0.1.22.dev0"`.
- Hatch metadata, module version, both CLIs, and a new review's `tool_version` agree.
- README and Action installation references remain on the verified v0.1.21 artifacts.
- No schema, gate, lifecycle, workflow, dependency, or product behavior changes.

## Boundaries

No release, issue comment, label, reviewer request, manually sent email, paid or LLM API, billing,
organization, second account, private repository, fork test, synthetic validation, invented
evidence, license, or external-evidence claim is created.
