# ScopeProof: making acceptance evidence safe to review

**Core integrity revision:** unreleased `0.2.4.dev0` draft at
`47ebc4f275b9f307c9305af3890782fa7578dff4`. The public install remains v0.2.3. This is
an engineering case study using constructed data and automated verification, not a customer case.

## Problem and decision

A public pull request can have green CI while an agreed acceptance criterion still lacks
inspectable support. ScopeProof lets a reviewer confirm the exact criteria, inspect candidate
implementation and test lines, record missing evidence and decisions, and export the record. It
must not call a static code line a test run or a human acceptance decision.

The integrity review found two additional ways to mislead a reviewer: mutable GitHub file/commit
pages could come from a different PR revision than the saved head, and a reconstructed bundle
could contain unsupported candidate levels or a finding whose claimed level had no cited support.
False Ready is the more harmful outcome, so inconsistent input stops the review.

## What changed

- Public PR ingestion rechecks the head and base and cross-checks retained mutable file and commit
  results against GitHub's SHA-addressed comparison. An A→B→A transition that restores the original
  head still fails when retained page data disagree with the SHA-addressed comparison. CI is
  read by exact head SHA.
- The shared Pydantic `ReviewBundle` boundary rejects candidate type/level mismatches, foreign
  heads and live-public permalinks, unsupported finding levels, findings with neither cited
  evidence nor an explicit missing explanation, and unscoped live runtime records.
- Every app test resolves review, alpha, and rehearsal storage under a per-test temporary home.
  The packaged browser journey uses a separate temporary runtime home.

The [architecture diagram](architecture.md) shows where each trust decision occurs.

## Demonstrated workflow

The [automated walkthrough](walkthrough.md) uses a deliberately constructed demo and an installed
wheel. It covers criteria confirmation, candidate and missing evidence, reviewer controls,
validated exports, and an adversarial changed-head regression. The screenshots are automated
Chromium captures of the constructed local workbench; the typed confirmer is a fixture actor,
not a genuine requirements owner.

## Evidence and limits

The regression suite exercises head movement, base movement, pagination, and an A→B→A mutation;
schema tests exercise semantic relationships at the saved/exported bundle boundary. The exact
commands, outcomes, environment, and coverage result are recorded in
[verification](verification.md). Imported or manually entered external results remain claims;
ScopeProof does not execute target code. A SHA-addressed comparison with more than 250 commits is
currently rejected, and unavailable GitHub comparison data stops ingestion.

Scope expansion outside the confirmed criteria is not yet a deterministic Ready prerequisite. The
constructed benchmark includes a `scope-expansion` case with an uncited changed file and an
expected Ready outcome; a separate changed-file inventory/gate design remains unresolved. This
integrity repair does not close that product gap.

No independent participant review, adoption, demand, accessibility conformance, Windows desktop
workflow, or production correctness has been established. Stage 1 remains closed without
qualifying external cases. Merge, release, deployment, and publication remain separate decisions.
