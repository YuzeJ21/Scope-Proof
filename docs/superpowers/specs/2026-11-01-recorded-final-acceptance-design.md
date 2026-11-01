# Recorded final acceptance in comparisons

Baseline main `c9db59480694fc41da61d46b7fba0ea4cb79df4d` is clean; post-merge CI/CodeQL passed.
The owner delegates routine design and automatic execution/agent review/guarded merge, without
personal testing or qualifying reviews. The selected outcome is a separate recorded-acceptance
view: identical Conditional gate labels can accompany different final-acceptance booleans.

## Design and alternatives

Project explicit values from validated analysis bundles, not event history from owning states.
Bundles retain the boolean but not actor, time, rationale or an event link. Reconstructing those
from revision events expands scope and is unsafe for unknown history. Another historical CLI
comparison command is a real option but would continue parity work rather than this information gap.

Add UI-independent `scopeproof_core/reviews/final_acceptance_comparison.py`:

- `FinalAcceptanceSnapshot`: frozen, extra-forbid, revalidate-always Pydantic object. Require all
  fields: repository, positive strict PR number, nonblank review/head identities, positive strict
  or literal `unknown` criteria revision, input origin, normalized-criteria SHA256, canonical tuple
  of criterion IDs, strict `recorded_final_acceptance` bool and literal
  `event_context_status='unavailable_in_analysis_snapshot'`. No actor/time/rationale defaults.
- `FinalAcceptanceComparison`: explicit fixed kind/version/boundary and previous/current snapshots;
  same repository/PR and confirmed-criteria identity. `recorded_value_changed` is recomputed from
  booleans, ignoring supplied derived values. `from_bundles` validates complete source bundles and
  builds detached projections. Unknown revisions remain unknown; no chronology inference.
- Add optional `final_acceptance_comparison=None` to `ReviewComparison` and recomputed
  `final_acceptance_compared`. All new `compare_reviews` results populate it. Missing older JSON
  means unavailable, never invented false values. When provided, require existing decision context
  and bind both sides' repo/PR/review/head/revision/input-origin/criteria IDs/digest to it. Existing
  decision-context/scope validators supply the owning identity chain. Ready requires recorded true;
  other gate labels do not imply either acceptance value. No other gate consistency is invented.

The boundary must say these local flags are asserted, not authenticated or correctness/runtime
verification. Event attribution is unavailable in analysis snapshots. False does not establish
revocation or that acceptance never happened. No acceptance or decision is carried forward.

## Presentation

Add a separate **Recorded final acceptance** section to comparison JSON/Markdown and workbench,
with previous/current **Recorded final acceptance: Yes/No**, owning identities, known/unknown
revision and **Recorded value changed: Yes/No**. Older missing projection gets an unavailable
message without Yes/No defaults. Display fixed unavailable attribution text. All dynamic text uses
existing safe renderers or inert text. Keep gate, candidate, scope and criterion decision sections
and their stated limits separate. No new controls or automatic actions.

## Boundaries and verification

No event reconstruction, authentication, criterion confirmation, decision/gate change, saved-byte
mutation, migration, dependency, source fetch or target-code execution. Preserve record v7 and
seven frozen R-002 files. Source 0.2.5 unreleased/public v0.2.4 unchanged; Stage 1 zero, Stage 3
dormant. No release/deployment/outreach or standing queue.

Constructed cases cover all boolean pairs, equal Conditional gates with differing values, missing
legacy projection, strict/missing fields, nested/derived tampering, owner/head/revision/digest binding,
unknown revisions, detached copies, inert reports/UI, and acceptance-only saved-state invalidation.
Extend one installed-wheel saved-comparison browser journey through reopen/comparison/download
with explicit constructed actors, responsive checks and saved-byte invariants. Run full unrounded
95% coverage, lint/lock, both benchmarks, clean package/browser, Python/Windows compatibility,
independent agent review, exact-head guarded merge and resulting-main verification.
