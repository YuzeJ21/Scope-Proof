# Exact-head runtime-evidence integrity design

Date: 2026-08-01
Status: approved for implementation
Base: public `main` at `6e3dec784f7cad9931999d4c5eac1cfe2a9006de`

## Purpose

Prevent a manual E3/E4 runtime observation from resolving a criterion unless the
observation is explicitly linked to the same public repository, pull request,
and reviewed head SHA as the owning ScopeProof review. Preserve legacy review
records for audit, but never infer a link that the old format did not record.

This is an evidence-integrity change. It does not execute target code, prove
correctness, add paid APIs, add accounts or billing, or advance Stage 1.

## Existing risk

`RuntimeEvidence` currently records criterion, artifact, scenario, environment,
result, reviewer, level, timestamp, and limitations. A `MANUALLY_VERIFIED`
resolution is paired to runtime evidence only by criterion, reviewer, and
evidence level. Those values are not an immutable identity. A record copied
from another review or an older head can therefore satisfy the structural
pairing check and contribute to a later `Ready` result.

## Considered approaches

### A. Reject every pre-link saved record

This is simple and strongly fail-closed, but it prevents users from reopening
otherwise useful review history. It is unnecessarily destructive to recovery.

### B. Infer legacy links from criterion, reviewer, and evidence level

This gives the smoothest migration, but recreates the exact ambiguity being
removed. Even a unique tuple does not prove which runtime observation the
reviewer intended to cite. This approach is rejected.

### C. Preserve legacy history and invalidate its gate effect

This is the selected approach. Legacy runtime records receive deterministic
record identities and retain the repository, PR number, and head stored by
their owning bundle. Existing manual decisions remain present but unlinked;
ScopeProof does not manufacture an association. An unlinked manual decision is
shown as requiring re-verification and is unresolved for gate purposes, so the
review becomes `Needs Review` rather than `Ready`.

## Data contract

`RuntimeEvidence` gains four provenance fields:

- `runtime_evidence_id`: an opaque, nonblank identifier;
- `repository`: the owning GitHub `owner/repository`;
- `pr_number`: the owning public pull-request number;
- `head_sha`: the exact reviewed head.

The four fields are all present or all absent. Absence represents a recoverable
legacy-unscoped record only. Public lifecycle operations reject unscoped input.
New runtime evidence is created with a UUID identity and copies repository, PR,
and head from the validated active review; these are never editable UI fields.

`HumanResolution` and `ResolutionEvent` gain an optional
`runtime_evidence_id`. Non-manual decisions must not carry it. A newly appended
`MANUALLY_VERIFIED` event must carry the exact ID of the atomically appended
runtime record. Missing IDs remain schema-valid only so historical records can
load conservatively.

## Trusted-boundary validation

Every active and historical `ReviewBundle` enforces:

1. runtime-evidence IDs are unique;
2. runtime provenance is either fully scoped or fully absent;
3. scoped runtime repository, PR, and head equal the bundle review identity;
4. a linked manual resolution resolves exactly one runtime record by ID; and
5. linked criterion, reviewer, and evidence level match the runtime record.

Lifecycle operations additionally reject wrong repository, PR, head, missing
or mismatched IDs, duplicate IDs, and any non-atomic manual-verification path.
They apply no mutation on rejection.

The deterministic gate treats an unlinked `MANUALLY_VERIFIED` resolution as
unresolved and adds `runtime_verification_reconfirmation_required`. Guidance
instructs the reviewer to record a new E3/E4 observation at the active head.
Final acceptance cannot be newly recorded while any manual verification is
unlinked. If a migrated review contains an older positive final-acceptance
event, it remains audit history but cannot make the gate `Ready`; the reviewer
must revoke it before replacing the runtime verification and then record a new
final acceptance.

## Persistence migration

The local record version advances from 2 to 3. Versions 1 and 2 remain
readable.

For each legacy active or historical bundle, migration:

1. copies the bundle's stored repository, PR, and head into each runtime item;
2. creates a deterministic UUID5 runtime ID from the review ID, bundle revision
   or position, item index, and canonical original runtime payload;
3. leaves all legacy manual resolutions and events without a link ID;
4. recomputes every affected deterministic gate; and
5. validates the complete migrated Pydantic state.

Migration never guesses a resolution-to-runtime association, deletes an old
decision, rewrites a human note, or mutates the parsed source payload in place.
Saving the reopened record writes version 3.

## Product surfaces and exports

The workbench records the active immutable identity automatically. Runtime
cards display the runtime evidence ID, repository/PR, and bound head. Manual
resolution history displays its linked ID or a clear legacy-unlinked warning.

JSON includes the new fields through validated Pydantic serialization.
Markdown and HTML show the runtime identity and head. CSV adds deterministic
runtime ID, repository, PR, head, and manual-link columns while retaining
formula-injection protections. Every export continues to validate the bundle or
review state before rendering.

Comparison remains focused on static candidate changes. It does not carry
runtime verification to a changed head. Its existing validation boundary
rejects forged linked records, while an honest legacy-unlinked decision remains
visible and unresolved.

## Two scoped workbench follow-ups

The same hardening branch fixes two review-recovery gaps without changing core
gate semantics:

1. A complete aggregate `PASSING` CI observation that contains skipped checks
   shows an uncollapsed warning that skipped checks were not executed. Names
   remain in the details expander.
2. A bundle-less revised review with stale criterion-detail inputs exposes the
   existing clear action. Clearing removes session drafts only, preserves the
   authoritative review state, permits autosave, and does not create exports
   until analysis is regenerated.

## Verification and release boundary

Each behavior is implemented test-first with an observed failing regression.
Focused suites, Ruff, the full suite, 95% coverage gate, both deterministic
benchmarks, package build, clean install, installed benchmarks, and workbench
health checks must pass on the final branch.

After merge, README, roadmap, changelog, and v0.2.3 release-audit documents are
aligned to the exact resulting `main` SHA. Historical SHA-bound evidence stays
historical. No tag, GitHub Release, asset upload, PyPI publication, outreach, or
Stage 1 credit is created by this work.
