# Release Wheel Quickstart Design

## Problem

The v0.1.11 release notes describe a validated release wheel, but the GitHub Release originally had no downloadable assets. The README Quickstart also assumes a source checkout and editable development installation, which makes first use harder than necessary and mixes user and contributor setup.

## Decision

Publish the wheel built from the exact v0.1.11 tag as a GitHub Release asset, then make that immutable versioned asset the primary user installation path. Keep the editable `.[dev]` installation in a separate contributor section.

The user path creates a virtual environment, installs the versioned wheel URL, verifies the installed offline benchmark, and launches the packaged Streamlit entry point with `scopeproof web`. The contributor path retains the current editable setup and repository-local app command.

## Alternatives

- Install directly from the default branch. This is mutable and can change without a release decision.
- Install from the tag through Git. This requires Git and rebuilds locally instead of using the already verified release artifact.
- Publish a new release only to add the asset. This creates unnecessary release churn because v0.1.11 already contains and documents the packaging work.

## Scope and Boundaries

- Use only `scopeproof-0.1.11-py3-none-any.whl` built from tag commit `6f6353adc5a6b8057f66eb8c993cb69dbb47e177`.
- Do not add or choose a software license.
- Do not add PyPI, package registries, Actions, services, accounts, billing, or paid APIs.
- Do not claim that artifact installation proves reviewed pull-request behavior.
- Do not create a new release.

## Acceptance Criteria

1. The v0.1.11 release exposes the wheel at its versioned GitHub download URL.
2. A newly downloaded asset has SHA-256 `d9a92c047e901b7370b3a09b0480b9cae527ec4dc2e302ec7546cf8832234634`.
3. A clean environment installs the asset and runs all 12 benchmark cases with no mismatch, False Ready, or false blocker.
4. README Quickstart uses the release wheel and installed `scopeproof` commands without requiring a source checkout.
5. README clearly separates contributor editable installation from user installation.

