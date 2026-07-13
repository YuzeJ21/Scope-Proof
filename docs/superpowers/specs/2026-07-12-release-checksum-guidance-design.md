# Release Checksum Guidance Design

## Problem

The v0.1.12 release notes record the wheel SHA-256, but the release has no machine-readable checksum asset. The README installs the remote wheel directly, so users have no documented path to verify the downloaded bytes before installation.

## Decision

Add `scopeproof-0.1.12-py3-none-any.whl.sha256` to the existing v0.1.12 release. Generate it from a fresh public download of the wheel using the standard `<digest>  <filename>` format. The digest must equal the value already recorded in the release notes.

Keep the direct pip URL as the shortest Quickstart. Add an optional verification block that downloads both assets, checks the file with `shasum -a 256 -c` on macOS or `sha256sum -c` on Linux, then installs the verified local wheel. This adds a verifiable path without forcing extra steps on every first-time user.

## Alternatives

- Hard-code only the digest in README. This is readable but not directly consumable by checksum tools and can drift from release assets.
- Add signing or artifact attestations. That requires new workflow permissions and infrastructure beyond this checksum gap.
- Create v0.1.13. The wheel bytes and product behavior are unchanged, so a new version would be release churn.

## Boundaries

- Do not alter or replace the existing v0.1.12 wheel.
- Do not create a tag, release, package version, Action, service, account, API, license, or dependency.
- A matching checksum proves file integrity against the published digest only; it does not establish publisher identity or reviewed-PR correctness.
- Preserve the simple direct-install path and public-repository-only product boundaries.

## Acceptance Criteria

1. The checksum is computed from a new public download, not from an unverified local build.
2. Its digest is `d3fea0a8810fcc5934586948c97037cb9299dc1a42a0f78891eea73429b9aa9f`.
3. The v0.1.12 release exposes exactly the existing wheel plus its `.sha256` file.
4. A fresh public download of both files passes macOS and Linux checksum verification formats.
5. README documents optional download, verification, and local installation while retaining direct installation.
6. Repository tests prevent removal of the versioned checksum URL and both platform commands.
7. Documentation merges through protected main without publishing a new release.

