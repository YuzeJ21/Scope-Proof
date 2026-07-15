# Public Beta Governance Design

## Context

ScopeProof has a tested public-alpha product, release artifacts, a contribution guide, and a
public dogfood issue. It does not yet have a durable roadmap, a changelog entry point, structured
issue forms, or a pull-request template. That makes the next-stage boundaries difficult to find and
allows feedback to arrive without the provenance needed for evidence-first triage.

This slice improves repository governance only. It does not claim beta validation, choose a
software license, create external evidence, enable a bot, or add a paid service.

## Decision

Add four small public surfaces:

1. `ROADMAP.md` defines current status, evidence-gated stages, exit conditions, and the boundary
   between work maintainers can complete locally and decisions that require genuine participants.
2. `CHANGELOG.md` starts with an Unreleased section and points readers to authoritative GitHub
   releases for historical release notes rather than reconstructing history from memory.
3. YAML issue forms collect reproducible defects and voluntary public-alpha feedback while warning
   contributors not to disclose secrets or represent constructed demos as real usage.
4. A pull-request template asks for the confirmed requirement, evidence level, verification, and
   remaining limitations.

The README and contributing guide will link to these surfaces so they are discoverable.

## Stage model

- **Current: engineering-complete public alpha.** The deterministic product and release path are
  operational; genuine repeat-use evidence is not yet available.
- **Beta-entry preparation.** Complete no-cost compatibility, onboarding, and governance work.
- **Limited beta.** Begin only after at least one genuine public-PR review has source-owner-confirmed
  criteria and a recorded human outcome.
- **Beta expansion.** Respond to repeated, independently observed friction rather than invented
  feature demand.

The roadmap must make license choice and genuine first-use evidence explicit owner decisions. It
must not turn their absence into a recurring monitor or synthetic substitute.

## Notification and cost boundary

The issue forms and template are passive repository files. This work does not create issues,
subscribe users, add scheduled workflows, enable Dependabot, or publish comments. Existing GitHub
account notification settings remain outside ScopeProof and are not changed by this slice.

## Verification

Repository contract tests require the four artifacts, their key safety language, and the README /
contribution links. The normal Ruff, full pytest suite, deterministic benchmark, and diff checks
remain the acceptance gates.
