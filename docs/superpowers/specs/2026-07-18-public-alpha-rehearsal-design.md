# Truthful Owner Rehearsal Design

## Problem

ScopeProof has a genuine public-alpha path, but the repository owner also needs a safe way to
exercise intake and the deterministic review workflow without creating a GitHub issue, triggering
notifications, or pretending that owner/Codex activity is an independent participant submission.

The genuine issue form deliberately requires the submitter to attest that the case is not a
constructed demo or invented validation. An owner/Codex rehearsal cannot truthfully make that
attestation. Reusing `AlphaCaseRecord` would also make a constructed record look structurally
eligible for a participant outcome. The rehearsal therefore needs a separate fail-closed contract.

## Evidence boundary

The rehearsal is local engineering evidence only. It can demonstrate that the owner-facing intake
shape validates, persists, reloads, and discloses its exclusion boundary. A separate controlled
command sequence can exercise criteria parsing, deterministic candidate retrieval, missing-evidence
explanations, gate evaluation, review persistence, export, and re-review comparison.

It cannot establish:

- an independent participant;
- a qualified inbound public-alpha issue;
- external runtime verification;
- a completed participant outcome;
- Stage 1 progress, adoption, customer validation, or market validation; or
- correctness of a pull request or replacement for QA.

## Chosen architecture

Add a separate owner-rehearsal contract under `scopeproof_core.alpha` without inheriting from or
converting to `AlphaQualification` or `AlphaCaseRecord`.

`AlphaRehearsalInput` validates the intake-shaped owner inputs:

- canonical GitHub public-PR-shaped URL;
- public-HTTPS-shaped requirements URL;
- a nonblank criteria-authority statement;
- explicit source-owner confirmation;
- explicit no-confidential-information confirmation; and
- one or more normalized, unique criteria.

Offline validation cannot prove that an arbitrary hostname is publicly reachable. It therefore
rejects HTTP, credentials in URLs, localhost, `.local`, and private, loopback, link-local,
reserved, or unspecified IP literals, while describing the result only as public-shaped input.

`AlphaRehearsalRecord` adds immutable, machine-readable classification:

- `submission_mode = "owner_rehearsal"`;
- `eligible_for_stage_1 = false`;
- `external_participant = false`;
- `external_validation = false`; and
- a stable exclusion reason stating that owner/Codex rehearsal is engineering evidence only.

The rehearsal ID is derived from the canonical validated input JSON with SHA-256. The persisted
record contains no timestamp, outcome, review ID, reviewed SHA, consent, participant role, or
free-form notes. The same inputs therefore produce the same ID and serialization, and a second save
fails rather than silently overwriting the first record.

`JsonAlphaRehearsalStore` uses its own `alpha-rehearsals` directory and ID regex. It supports only
create, load, and sorted list operations. It never updates a record and never enumerates genuine
alpha-case files.

Expose the path as top-level `scopeproof owner-rehearsal init|show`, not as a genuine `scopeproof
alpha` outcome path. The command has no outcome, reviewed-SHA, participant-role, publication,
external-verification, or Stage 1 flags.

## Controlled end-to-end rehearsal

The checked-in rehearsal input uses only deliberately constructed example data. The verification
run will:

1. create and reload the rehearsal record;
2. run `scopeproof review --fixture` with a deliberately constructed fixture;
3. reload and export the saved review;
4. assert that the gate remains conservative when evidence is missing; and
5. run the bundled comparison benchmark covering Unchanged, Relocated, Modified, Added, and
   Removed.

These combined commands exercise the engineering workflow without connecting the constructed
rehearsal to a genuine alpha case or outcome.

## Genuine-case isolation

The following invariants are regression-tested:

- rehearsal payloads fail `AlphaQualification` and `AlphaCaseRecord` validation;
- genuine outcome and public-summary services reject non-`AlphaCaseRecord` inputs explicitly;
- rehearsal storage rejects genuine alpha IDs and genuine storage rejects rehearsal IDs;
- fixed eligibility and evidence-boundary fields cannot be overridden;
- extra participant, outcome, review, consent, or publication fields are rejected;
- tampered persisted JSON and symlinked roots or files fail closed; and
- CLI output always includes the machine-readable exclusion boundary.

## Onboarding alignment

The public participant quickstart must begin with the inbound case form for alpha research and
route unsubmitted users to Standard review. The public feedback form must map exactly to the three
validated `AlphaOutcome` choices; incomplete reviews do not become completed outcomes. The pricing
research question will describe its required dropdown honestly while retaining “Prefer not to
answer.” Mobile navigation will keep the Public alpha shortcut visible.

Active product documentation will use one canonical inactive token:

`waiting_for_inbound_public_alpha_submission`

Historical design and plan documents remain historical records and are not rewritten.

## Release and notification policy

No public rehearsal issue, comment, release note, or notification-only event is created. The work
ships through one protected pull request because it changes a public CLI surface and onboarding
contracts. A new release is not required unless the repository's release policy separately demands
one after the merged change; release activity is never manufactured as validation.
