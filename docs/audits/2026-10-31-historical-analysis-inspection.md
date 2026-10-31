# Retained historical analysis inspection and handoff

## Selected gap and source baseline

After PR #233, live main `80870aff7affed5c5a97c026daf3507bebcd53b6` and its CI, CodeQL and
base-advance workflows were green; both checkouts were clean and no PR was open. The owner
delegated one automatically executable product improvement without personal testing or qualifying
reviews. Independent source inspection confirmed that retained analyses were preserved in saved
state/whole-state JSON, but their UI access required a compatible active comparison. History-only
pending revisions and changed criteria could not obtain a standalone historical handoff. This was
an inspection gap, not lost data or verified practitioner demand.

## Delivered behavior and integrity

The [design](../superpowers/specs/2026-10-31-historical-analysis-inspection-design.md) chooses a
separate read-only historical inspector. Existing comparison compatibility stays strict and no
historical bundle is promoted into current state. It adds no persistence schema or record migration.

- An explicit retained position is bound to the entire saved-state fingerprint and its complete
  validated analysis fingerprint. Reopen/reset, changed storage/selection, history replacement or
  reordering, and runtime/reference-only mutations invalidate the choice and prior callbacks.
  Filename and owning record identity must match. Record locks remain held through consumers.
- Pydantic historical reports identify report kind/schema/boundary, owner/history position,
  historical head and known/unknown criteria revision, original producer and current validation
  tool/ruleset/observed-core identity. The analysis fingerprint prevents changed/defaulted data
  from quietly becoming recorded history. These hashes are consistency checks, not authentication
  or execution attestation. Validation source identity excludes dependencies/UI, as disclosed.
- The inspector works with a saved unconfirmed current revision and no active bundle, or different
  criteria. It reads saved history only: current drafts do not enter it and it adds no save,
  acceptance, source reload or editable decision controls. Current authority controls stay intact.
- JSON carries the historical typed envelope. Markdown leads with historical-only scope and
  revision, then reuses the safe complete bundle report with explicitly historical title/status.
  Standalone CSV/HTML revision defaults are not reused and those formats are not added for history.
  Full owning resolution-event history is not reconstructed from current events.
- Loading older records may conservatively migrate/revalidate gates under installed policy.
  Historical output states that context; it does not claim an unverified original gate or current
  readiness. Original recorded producer metadata stays distinct, including absent/unknown values.
- Existing provenance eligibility remains mandatory for both full reports. A legacy analysis
  without criteria-source provenance shows identity and the precise unavailable-report limitation;
  no provenance or revision is invented. Original saved JSON bytes remain unchanged.
- Deferred historical downloads check their receipt and lease generation, reload under the record
  lock, render, then check the lease again. No stale prefetched bytes, target artifact fetching,
  source loading, reanalysis or target-code execution is introduced.

The workbench uses literal identity text/wrapping code and a read-only safe Markdown preview.
Generated escaped code tags are converted to sufficiently delimited native Markdown code spans;
untrusted code characters remain inert without enabling unsafe HTML. Downloaded Markdown retains
the original safe report format. Current analysis, confirmation, decisions, scope, gates and frozen
research remain unchanged.

## Automated evidence and limits

Constructed core/report cases cover history-only and changed criteria, strict receipts, whole-record
and analysis tampering, no generated historical timestamps, unknown revisions, old producers,
legacy missing provenance, storage damage/ownership, held locks, detached copies and no artifact
access/execution. Independently authored safety tests use synthetic actors and real lifecycle
operations. Initial test fixture errors (invalid criterion identifiers and ownership/event cases)
were corrected without weakening production validation; valid missing-feature RED and restored
GREEN results were recorded separately.

AppTests cover explicit choice, read-only inspection, pending-draft separation, missing history or
provenance, stale views/downloads, same-record reopen, post-render lease checks, inert readable
preview and a valid constructed historical Ready that never creates current acceptance. The
installed-wheel journey adds another server restart into a history-only record with changed
unconfirmed revision 3 and retained revision 1, old constructed producer, runtime/reference facts
and malicious-looking inert text. It verifies both downloads against complete original saved facts,
unchanged bytes/current state, and actual-section screenshots/dimensions at desktop, phone and
200% CSS zoom. CSS zoom is automation, not native zoom or accessibility conformance.

Full 95% coverage, lint/lock/contracts, unchanged deterministic benchmarks, clean package/browser,
available Python/Windows compatibility, independent review/fixes, exact-head merge and resulting
main outcomes are source-bound in the integration PR and private verification packet. Suite counts
remain seventeen browser checks: three installed-wheel journeys (one extended), eight constructed
selector checks and six helper/capture checks; not seventeen complete end-to-end journeys.

Source stays unreleased 0.2.5; public v0.2.4, historical private candidate and seven frozen R-002
inputs/results remain unchanged. Stage 1 stays closed at zero, Stage 2 owner-led and Stage 3 dormant.
No personal testing, qualifying reviews, participant contact, release, deployment, new adapter,
accounts/billing or public post follows. Actual usefulness, independent use and accessibility
conformance remain unknown. This selected outcome creates no standing follow-on queue.

## Independent review correction

The whole-branch review reproduced missing saved producer versions becoming today's constructor
defaults in the historical report. The loader now marks omitted tool/ruleset versions `unknown`
for saved current and retained reviews in all seven supported formats; explicit recorded values
and new-review constructor defaults remain unchanged. Historical report envelopes also require
explicit producer fields, even when a missing field's default could match the fingerprint.
Saved bytes and record version remain unchanged. Regression RED/GREEN covers omitted individual
and paired fields, preserved counterparts, current validation identity and report reparse rejection.
The earlier-head installed-browser run was cancelled as incomplete after this finding; final
verification uses a fresh package built after the correction.

The installed browser then reproduced report-preview overflow on both macOS and Linux. Real DOM
measurements identified Markdown descendant overflow; scoped wrapping and horizontally scrollable
tables reduced the panel's scroll width to its client width at desktop, phone and 200% CSS zoom.
The product applies only constant trusted CSS under the historical preview key, while report HTML
remains disabled. No evidence is hidden, truncated or placed in a fixed-height scrolling report.
The strict original panel/page geometry assertions remain; additional checks require every table's
last column to be reachable after scrolling. Earlier failing runs remain separate from final proof.
