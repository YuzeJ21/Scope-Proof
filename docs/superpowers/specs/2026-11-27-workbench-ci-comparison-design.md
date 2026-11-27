# Workbench CI context comparison

The owner authorized executing the next stages: integrate #305 and #306, then expose
the existing same-commit CI comparison in the workbench. This remains Stage 2 engineering;
independent usefulness and repeat use are not measured by constructed checks.

## Outcome and approach

A reviewer opts into comparing the currently displayed CI manifest with an explicitly
uploaded previous manifest. Reuse `compare_ci_status` and its offline HTML exporter.
Show one row per expected test with both mappings, effective results and supplying runs;
show the run-record changes and both input digests. Previous/current mean supplied order.

Chosen implementation: a small workbench module alongside `ci_status.py`, consuming the
existing current manual upload or configured local input and one optional previous upload.
A second independent pair of uploads would duplicate the current-context selector and invite
comparison against a context different from the displayed one. A UI-specific comparison
engine would duplicate evidence semantics. Neither alternative is needed.

Configured-local input needs a byte-returning reader so parsing, digest and comparison use
one bounded read. Preserve existing model/digest APIs as wrappers over that reader.

## Integrity and user behavior

- Comparison is opt-in; the ordinary CI panel and snapshot remain usable unchanged.
- Both inputs are at most 1 MiB and must match the same active confirmed review, criteria
  and exact head. Invalid prior input produces a concise error and no comparison download.
- Download callbacks retain immutable input bytes and recheck both source fingerprints
  before and after rendering. For local current input, reread through the exact-review
  no-follow bounded reader; for uploaded inputs, check the corresponding upload bytes.
- A session lease expires old callbacks on rerun, either upload change, mode change or
  review replacement. Use the existing deferred review export for saved-record fingerprint,
  changed-source, acceptance-note and pending-draft guards. Rebuild against the revalidated
  authoritative bundle inside that wrapper.
- The HTML name includes reviewed head and both digests. Keep provenance, externally
  supplied context labels and recorded acceptance separate. No execution chronology claim.
- No gate/evidence change, storage migration, dependency, release, publication or outreach.

## Verification

Observe failing regressions before implementation. Exercise actual AppTest uploads and
saved-review callbacks: constructed B skip-to-fail comparison, manual/configured current,
missing/invalid/oversize/mismatched inputs, explicit opt-in, review switching, upload removal
and replacement, source mutation during rendering, saved-record change, pending drafts and
source contradictions. Verify input and saved-record bytes unchanged. Add an installed-wheel
browser journey that downloads and reads the report offline. Run relevant source checks,
Ruff and exact-head full hosted CI including Windows and browser checks. Preserve frozen
walkthrough and R-002 artifacts.

## Remaining stages

Integrate only verified PR heads and verify resulting main. This authorization covers that
integration and bounded UI work. Public package/Pages publication and participant contact
are separate actions; neither is initiated. Stage 3 needs genuine independent-use evidence;
Stage 4 needs demonstrated access, sharing or integration constraints.
