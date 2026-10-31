# Recorded reviewer decision and runtime context in comparisons

## Selected gap

After PR #232, live main `58c916016d5999b6ce6c1a37f0b612cc9beb663f` was clean and its post-merge
CI, CodeQL and base-advance workflows had passed; no PR was open. The owner delegated the next
bounded product task without personal testing or qualifying reviews. Independent source inspection
found that `_resolution_decisions` and `changed_human_resolutions` retain only the decision enum.
A note, asserted reviewer, timestamp or linked observation could change under the same label
without any corresponding decision-context output. Saved data was intact; this was a comparison
inspection/handoff gap, not evidence of a faulty gate or demonstrated customer demand.

## Delivered scope and integrity

The [design](../superpowers/specs/2026-10-30-decision-context-comparison-design.md) chooses a separate
informational projection instead of changing established enum-delta semantics or opening another
historical-viewer/adapter project. It covers the latest criterion resolutions and retained runtime
records in each validated analysis. It does not compare full event history or review-level final
acceptance; existing scope, reference, JUnit and gate sections retain their own behavior.

- Core models retain both repository/PR/review/head/revision/input-origin identities, full side
  criteria provenance, complete latest `HumanResolution` and retained `RuntimeEvidence` records.
  Complete explicit nested projection fields prevent invented default timestamps or actors.
- Existing compatible-criteria validation applies. Serialized context also validates standalone
  ownership, criteria identity, known criteria, unique identified records and exact explicit runtime
  links. Owning comparison scope, side provenance and old enum deltas must agree with the context.
- Canonical complete-record comparison reports identical context, only previous, only current or
  changed context per criterion. List order is irrelevant; duplicated genuinely unlinked observations
  are preserved. Derived rows, runtime-link labels and availability are recomputed rather than
  trusted from input. Source models and derived rows are detached copies.
- An exact runtime ID plus existing scope/criterion/reviewer/level checks supplies a link. Names,
  URLs, ordering and shared criteria do not infer one. Legacy unlinked observations/decisions remain
  unlinked, and old comparison JSON without this projection remains unavailable rather than empty.
- Workbench and comparison JSON/Markdown show complete records, both owning identities and the
  asserted/recorded evidence boundary. Untrusted notes, results, actor names and identities are inert
  text or escaped code; artifact links use existing safe-reference rendering. No artifact is fetched,
  executed, authenticated or re-verified. Existing saved-state fingerprints and session/download
  leases guard runtime-only changes as well as other saved changes.

Existing candidate deltas/counts, decision-label deltas, criteria-requiring-decision-review logic,
scope, findings, final acceptance and deterministic gates remain unchanged. The new projection is
non-gating reporting context; this does not remove original runtime evidence from its original
review's established validation/gate rules. No records or migrations are added to record version 7.

## Automated evidence

New constructed cases cover same-label changes in notes, attribution, levels, timestamps, explicit
runtime links, artifacts, scenarios, environments, results and limitations; known-empty/missing
context; legacy unlinked records; full-field completeness; owner/provenance/link tampering; derived
claim tampering; canonical ordering and duplicate preservation; detached mutation; safe rendering;
and no artifact access/execution. Independent adversarial tests are authored separately from the
implementation. Existing whole-record guards are exercised with runtime-only changes in current,
baseline, own-history and foreign-history records, including an already-created download callback.

The opt-in installed-browser fixture has fixed explicitly constructed automatic actors and scoped
observations. Its manual-decision labels model stored data only; no human testing is claimed.
Default fixture behavior remains unchanged. Installed Chromium checks complete persisted records
against JSON/Markdown and workbench details through restart/reopen and active/own/foreign history
comparison, retaining saved-byte/gate invariants and desktop/phone/200% CSS zoom layout checks.
CSS zoom is labeled as automation, not native browser zoom or accessibility conformance.

Independent whole-branch review reproduced a Python-input bypass before integration: tuples or
iterators could skip the complete nested-record check and allow default timestamps. Regression
tests reproduced this before the fix. Projection collections now require explicit lists before
Pydantic's nested defaults can run, including standalone rows; mutable model inputs are serialized
and revalidated. Additional installed-browser checks use runtime IDs longer than 1,000 characters
and inert HTML/Markdown-like recorded result text at desktop, phone and 200% CSS zoom.

Full coverage, lint/lock, deterministic benchmark, clean installation, package/browser, available
Python/Windows compatibility, independent review, exact-head CI and resulting-main outcomes are
source-bound in the integration PR and private verification report. Earlier or interrupted runs
are not promoted to a passing final result. Current browser coverage remains seventeen checks:
three installed-wheel journeys, eight constructed selector checks and six helper/capture checks.

## Limits and remaining gate

Recorded facts/internal hashes do not establish authentic identity, artifact availability, behavior,
cross-head equivalence or independent usefulness. Complete context is bounded by the existing saved
record/read limits; there is no new global index, execution service or event-history replay.

The seven frozen R-002 inputs/results and historical expectations/scores are unchanged. Current
source stays unreleased `0.2.5`; public v0.2.4 and historical private candidate artifacts are unchanged.
Stage 1 remains closed at zero, Stage 2 owner-led and Stage 3 dormant. No personal testing,
qualifying reviews, participant contact, publication, deployment, accessibility claim or beta follows.
Genuine independent use and usefulness remain missing evidence, not an automatic engineering task.
No standing follow-on queue is created by completing this selected outcome.
