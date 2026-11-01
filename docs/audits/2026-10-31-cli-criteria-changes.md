# Headless saved requirements-change handoff

Baseline main `06b8333aca2f7692436c2748fad3f500272e6a82` (PR #237) was clean with post-merge
CI, CodeQL and base advance successful. Independent read-only assessment selected one recipient
workflow gap: scripts can now discover/export retained analyses, but cannot explain the saved new
requirements alongside the old ones without the workbench. Evidence comparison correctly refuses
changed criteria or no-active records; its policy must remain separate.

## Supported outcome

`export-criteria-changes` accepts an explicit one-based history position and expected whole-state
fingerprint from `history`. It validates through the existing Pydantic request and criteria report
models; reuses prepare/locked-consumer services and JSON/Markdown renderers; and retains the record
lock through complete rendering and stdout/file publication. Optional files use the established
atomic no-overwrite helper. No selection defaults/fallback or nested non-reentrant locks are added.

The output contains complete previous/current criteria records and positions, source text, recorded
heads/revisions, asserted confirmation and available provenance. Exact JSON whitespace is preserved;
same IDs remain keys rather than semantic continuity. Pending saved requirements stay unconfirmed,
unsaved drafts are absent, and missing provenance remains unknown. The limited requirements report
does not relax full historical acceptance-report eligibility. No evidence equivalence, decision
carry-forward, acceptance, gate, persistence, migration, source fetch or target execution is added.

## Automatic evidence and boundaries

Focused regressions cover pending/no-active data, exact complete fields/whitespace, duplicate heads,
unknown revision/provenance, strict required requests, owner mismatch, stale current/history state
before preparation/consumption, complete-render failure, saved-byte preservation, protected output
targets and locks through stdout/file publication. A trusted constructed installed recipe exercises
catalog selection, JSON/Markdown handoff, legacy provenance separation, stale refusal and unchanged
saved records outside the checkout. Hypothetical legacy fixtures are made internally consistent
before their first save; no real historical input, frozen expectation or benchmark result is rewritten.

The execution packet records valid missing-command RED, GREEN results, independent agent review,
full unrounded 95% coverage, lint/lock/diff, both deterministic benchmarks, clean package/browser
verification, hosted Python/Windows checks, exact-head guarded merge and resulting-main results:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-10-31-cli-criteria-changes`.
Pending checks are not counted as passed; exact commits/results are recorded there and in the PR
after execution. Existing seventeen browser checks retain their three-journey/eight-selection/
six-helper composition; installed CLI journeys are separate.

This is constructed automatic engineering evidence, not demonstrated recipient demand, genuine
independent use, personal testing, qualifying practitioner review or accessibility conformance.
Core stays UI-independent; source remains unreleased 0.2.5 and public v0.2.4 unchanged. Record v7,
frozen R-002 and all gates/decisions are preserved. Stage 1 counts stay zero; Stage 3 remains dormant
until genuine independent use and separate authorization. No release, deployment, outreach or
standing feature queue is created. CLI requirements editing/reanalysis, two-record historical
evidence comparison and final-acceptance comparison remain deferred options requiring fresh need.
