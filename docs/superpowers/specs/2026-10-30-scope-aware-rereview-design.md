# Scope-aware re-review

The owner requested renewed product development on 2026-10-30, without personal testing or
qualifying participant reviews. This replaces the maintenance-only operating choice, not the
evidence rules. Stage 1 remains closed at zero; Stage 3 remains dormant.

## Problem and outcome

An automatically constructed comparison remains byte-identical after adding an uncited changed
file to the current review and recomputing its valid gate. Both heads already need review, so
the status label hides the extra work. A reviewer should see changed inventory facts and current
unresolved file scope beside candidate changes, including in comparison Markdown and JSON.

## Approaches

- Another release preparation cycle distributes existing repairs but does not address this gap.
- Add scope context to the existing comparison (chosen): reuse validated review facts, preserve
  gate behavior, and explain differences without fetching or executing target code.
- Broader retrieval or collaboration changes would address different problems and need separate
  designs. They are outside this milestone.

The owner delegated routine choices and opted out of design questions. The implementation uses
the existing Python/Pydantic core, Streamlit UI, CLI comparison and export surfaces.

## Contract

- Project each head's inventory, linked changed-file citations, latest attributable file-scope
  decisions and ingestion limitations into a Pydantic snapshot. Bind decisions to that snapshot's
  review, head, criteria revision and digest. Never transfer a prior decision.
- Distinguish unknown inventory from a verified empty inventory. When either inventory is unknown,
  inventory deltas are unknown. Keep each known side available for inspection.
- Compare paths deterministically. Report additions to the inventory, absence from the current
  inventory and changes to recorded status/previous-path metadata. Do not infer source deletion,
  rename pairing, generated-file exemption, content equality or correctness from these facts.
- Show current unresolved inspected paths using the existing gate's citation/outside-criteria
  rules, plus previous decisions whose paths are now unresolved. A within-criteria decision still
  needs a candidate citation. Preserve skipped paths/warnings and partial ingestion explicitly.
- Keep presentation-derived fields recomputed during Pydantic revalidation. Reject contradictory
  identities and malformed paths/decision projections at export boundaries.
- Render scope before detailed candidate changes. Treat repository paths, notes and warnings as
  inert text; escape Markdown. Older comparison objects without scope remain readable as unknown.
- Do not change gates, saved-record format, criterion confirmation, retrieval, R-002, dependencies,
  publication, public assets or the frozen private v0.2.5 candidate at main `4f12ae0`.

## Finish line

Core/export/UI regressions cover added, absent, renamed, generated, uncited/cited files; latest
decisions, historical unknowns, partial ingestion, malicious text, exact-head tampering and
nonmutation. Full 95% coverage, deterministic benchmarks, installed browser/package and hosted
compatibility checks pass, independent review is resolved, and the guarded merge is verified.
This completes one engineering capability; no demand or genuine-use claim follows.
