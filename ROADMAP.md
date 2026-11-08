# ScopeProof Roadmap

ScopeProof is a reviewer-first public-repository evidence assistant. The deterministic engine,
local workbench, CLI, exports, benchmark, packaging, and protected CI are engineering evidence only.
They do not prove
runtime correctness, adoption, or beta readiness.

This roadmap separates owner-led productization from external validation. Stage 1 is
`closed_not_pursued_by_owner` with all external-evidence counts at zero. Stage 2 is
`owner_led_productization_active`, with the no-install example complete and one measured
saved-history validation improvement;
this owner decision does not create customer validation. Stage 3 is dormant and gated.
The owner is not pursuing personal testing or qualifying participant reviews.

## Current priorities — 2026-11-07

Updated 2026-11-08: PR #276 completed the constructed report download; resulting-main CI
42502782742 passed. The selected follow-up is a bounded saved-history operating-envelope
assessment and the smallest repair justified by a reproduced constraint. Ordered per-revision
event projection removes repeated full-history scans while retaining all validation. See the
[measurement and limits](docs/audits/2026-11-08-history-event-validation.md).
No new release or deployment is selected.

The product direction is **explain and revisit an acceptance decision**. Confirmed intent,
exact-head evidence, explicit gaps, recorded decisions and later comparison form the working
product; acceptance checking alone is not distinctive. The [November 2 product and market review](docs/commercialization/product-direction-2026-11-02.md)
documents direct overlap and adoption constraints without claiming superiority or demand.

| Stage and order | Concrete outcome | Finish line or boundary |
| --- | --- | --- |
| Stage 2 — completed on source | Carry complete normalized criteria from preparation into an automated CLI review without rebuilding intent. | Source-bound editable draft; explicit confirmation; stable IDs/order/priority/type/source metadata and required evidence levels; malformed/stale rejection before ingestion/writes; automated and independent agent review plus exact-head CI. See the [bounded assessment](docs/audits/2026-11-02-typed-criteria-handoff.md). |
| Stage 2 — completed on source | A recipient can transfer and safely reopen a saved review through supported CLI controls and the existing workbench. | Preserve complete record bytes, history and provenance; validate versions and gates; bounded regular files; atomic no-overwrite import under the original ID; installed reopening and independent automated review. See the [transfer assessment](docs/audits/2026-11-02-saved-review-transfer.md). |
| Stage 2 — completed on source, PR #250 | Complete sender-to-recipient saved-review handoff entirely in the local workbench. | Explicit saved-record download, upload inspection, byte-bound consent/import and existing guarded reopen; original history/provenance preserved, collisions and stale callbacks rejected. See the [workbench handoff assessment](docs/audits/2026-11-02-workbench-review-handoff.md). |
| Stage 2 — completed, PR #251 | Make the accumulated workflow coherent to evaluate. | One [evaluation entry](docs/evaluation-guide.md) with the release/source version map and a constructed handoff. |
| P0 — distribution verified at `72cac01` | Package the accumulated reviewer workflow and verify an upgrade from the public writer. | Matching direct and source-built wheel bytes, isolated installs, artifact hashes and a constructed native v5-to-v9 upgrade on copies. Each packet names its source commit. |
| P1 — workbench folder selection in v0.2.5 | Run sender and recipient workbenches on one computer using separate review folders. | Explicit launch option, visible selected folder and installed browser handoff with both instances under one OS account. |
| P2 — publication complete | Publish v0.2.5 as a downloadable evaluation release. | The public wheel, source archive, and checksum manifest matched the verified candidate. Both archives passed fresh installation. See the [release verification](docs/releases/v0.2.5-public-verification.md). |
| Stage 2 — completed on source, PR #254 | Keep later saved-review edits from being deleted under earlier consent. | Bind workbench confirmation to the selected file and recheck it under the store lock. Require fresh consent after a change, including when metadata is unavailable. |
| Stage 2 — completed on source, PR #255 | Explain differences between reviews with the same verdict. | Workbench and Markdown/JSON show newly reported, no longer reported, and persistent reasons from both validated analyses. Older comparisons distinguish missing context from an empty reason list. |
| Stage 2 — completed on source, PR #256 | Let a recipient open a complete acceptance report offline without installing ScopeProof. | Workbench downloads the validated HTML report with exact-head status, reasons, and next actions ahead of evidence and audit history. Apply the existing click-time export guards. |
| Stage 2 — completed on source, PR #257 | Capture why a reviewer recorded or revoked final acceptance. | Workbench adds an optional note to the existing attributable audit event and keeps unsubmitted notes out of saved records and reports. |
| Stage 2 — completed on source, PR #259 | See what is blocking a decision as soon as an analysis finishes or a saved analysis reopens. | Show the reviewed head, recorded verdict, blockers, recorded final acceptance, and local save status. Open the first blocking criterion and distinguish recorded results from matching source and refresh-required status. |
| Stage 2 — completed on source, PR #261 | Find unresolved file scope even when criteria or checks determine the verdict. | Show the inspected-path count and a bounded preview, distinguish unavailable inventory, and link to the existing scope controls without changing a review or draft. |
| Stage 2 — completed on source, PR #262 | Keep an obsolete acceptance report from being treated as current when later source loading fails. | Apply a confirmed same-PR contradiction before optional candidate loading. Preserve the saved record, expire authoritative downloads, and distinguish unknown transport outcomes. |
| Stage 2 — completed on source, PR #263 | Start a same-PR re-review with the saved requirements and source details ready to confirm. | Copy only revalidated same-PR requirements into editable drafts, clear the confirmer, and require fresh confirmation before running a new analysis. |
| Stage 2 — completed on source, PR #264 | See how recorded requirements changed between separately saved analyses of one PR. | Require an explicit baseline and validate both saved records. Show heads, source details and criterion changes in a read-only view while keeping the evidence comparison guard. |
| Stage 2 — completed on source, PR #265 | Share the recorded requirements changes with a recipient who has neither saved review. | Download Markdown with both record IDs and heads, the baseline position, source provenance, and criterion changes. Validate both records again at download time and expire old selections. |
| Stage 2 — completed on source, PR #266 | Inspect an uncited changed file and continue comparing saved analyses, checking the current head, or navigating to the next blocking criterion. | Selecting a file or diff page keeps those actions available. An unsubmitted disposition or explanation still pauses them. Explicit scope decisions and exact-head gate rules stay in force. |
| Stage 2 — completed on source, PR #267 | Know why a saved analysis requires refresh when fresh observations conflict. | The decision overview distinguishes an observed different head, changed check details at the reviewed head, and explicit non-public visibility. Keep the explanation in the current session and preserve the saved review and export guards. |
| Stage 2 — completed on source, PR #268 | Recover when a selected saved analysis cannot be used for evidence comparison. | Explain which relationship check failed or when records need to be reopened or reselected. Point to requirements-only comparison for eligible same-PR criteria or source differences. Preserve exact-head and comparison rules. |
| Stage 2 — completed on source, PR #269 | Keep an unsubmitted scope decision with its review when a replacement, source load, or criteria change would invalidate it. | Require saving or explicitly discarding the draft before changing its context. Discard in place and keep read-only inspection available. Preserve recorded decisions and report rules. |
| Stage 2 — publication and public verification complete | Deliver the consolidated v0.2.6 evaluation workflow as downloadable artifacts. | The [v0.2.6 Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) identifies final source `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`, wheel, source archive, checksum manifest and completed public-download verification. No further release follows automatically. |
| Stage 2 — completed on source, PR #272 | Preserve rich native v0.2.6 saved-review histories as development readers change. | Immutable records from the actual public writer, provenance-bound generation, active and unconfirmed historical-only states, complete-state preservation through load/copy-only resave/transfer/reopen, active reports and pending current-report denial, Linux/Windows CI and independent engineering review. Resulting main `069af259ac17b6c555d10b10f36e7211b068aac4` is verified. See the [bounded assessment](docs/audits/2026-11-07-native-v026-compatibility.md). No current data-loss defect was asserted. |
| Stage 2 — completed on source, PR #273 | Show the recorded criteria revision in CSV/HTML reports of explicitly selected analyses. | Use the validated bundle's revision, including `unknown`, instead of inventing revision 1. Preserve full-state labels, pending current-report denial, producer/history and analysis-only boundaries. Resulting main `1d1358097dc34c69c68e93dc5d45066ff4506b1e` passed CI attempt 2; the initial browser timeout remains documented. See the [revision-label assessment](docs/audits/2026-11-07-historical-report-revision.md). |
| Stage 2 — completed on source, PR #274 | Stop a browser test from rejecting a committed saved-review ID solely because a generic rerun signal was missed. | Retain actual validated reopening, saved-state/history checks and the same timeout. Natural baseline passes and controlled signal-loss replay remain distinct; the precise natural Streamlit transition remains unproven. Resulting main `37799a04942e2926bf9c73882a9e0f4e1e44698f` passed CI. See the [observer assessment](docs/audits/2026-11-07-browser-observer-reopen.md). |
| Stage 2 — source and publication complete, PR #275 | Find the current verified evaluation release and understand saved decisions, offline handoff and revisiting from the existing website. | Main `388b7dae276253ac015efd852cd510bc3999f9fd` passed CI, then separately authorized Pages run `42494611672` deployed that exact revision. All 12 files matched source; 20 link destinations and desktop/mobile/media checks passed. The [earlier source-only assessment](docs/audits/2026-11-08-evaluation-page-alignment.md) retains its historical boundary. No website alignment or publication task remains open. |
| Stage 2 — bounded report example prepared in source | Inspect an actual acceptance report before installing ScopeProof. | [Downloadable constructed HTML](docs/examples/offline-handoff/README.md), generated by the verified public v0.2.6 exporter from the unchanged native active record. Preserve Action required, explicit simulation/synthetic-link labels, strict input/recipe/raw/presented provenance, offline rendering/no-network checks, independent review, exact-head/main CI and public repository-download verification. No application feature, package or Pages deployment. |
| P3 — Stage 3 dormant | Determine whether independent practitioners find the acceptance handoff useful and reuse it. | Genuine independent-use evidence and separate authorization. |

### Product and architecture checkpoint

The completed consolidated milestone is the **published, publicly verified `0.2.6` evaluation release**:
**explain a saved acceptance decision, share it offline, and safely revisit it after changes**.
The verified v0.2.5 fallback source is `72cac01`. The later PR #254–#269 source outcomes above
are included in v0.2.6 and absent from v0.2.5. See [v0.2.6 changes](CHANGELOG.md#026--evaluation-release-build)
and the [version guide](docs/evaluation-guide.md#choose-the-right-version).
The [private `0.2.6.dev0` candidate packet](docs/releases/v0.2.6-dev0-evaluation-candidate.md)
remains a historical unpublished artifact. Its checks do not verify final v0.2.6 bytes.
The owner-authorized final v0.2.6 publication and automatic public-download verification completed
on 2026-11-07, without personal testing or qualifying reviews. The
[GitHub Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) is authoritative
for availability, final source `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`, all three assets and
completed public verification. Current source is unpublished `0.2.7.dev0`; v0.2.5 remains a verified fallback.

[PR #272](https://github.com/YuzeJ21/Scope-Proof/pull/272) completed native released-writer
compatibility at resulting main `069af259ac17b6c555d10b10f36e7211b068aac4`.
[Resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42428549217) passed
4,860 tests with 36 intentional skips, 95.5067% unrounded coverage, seven installed CLI checks
and 32 browser-suite checks. These are constructed engineering checks, not independent-use
or qualifying-review evidence. The corpus and frozen research remain immutable.

[PR #273](https://github.com/YuzeJ21/Scope-Proof/pull/273) completed CSV/HTML revision labels at
main `1d1358097dc34c69c68e93dc5d45066ff4506b1e`.
[Main CI attempt 2](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42441483388/attempts/2)
passed 4,872 tests, 36 intentional skips, 95.5067% coverage, seven installed CLI checks and 32
browser-suite checks. Attempt 1 passed its other checks but retained one 10-second observer wait
timeout before Reopen; two fresh local journeys passed unchanged before the one failed-job retry.
The passing retry did not prove that timing issue repaired. This investigation adds three further
natural baseline passes and a separate controlled signal-loss replay with the real installed app.
The replay supports the scoped test wait repair; the precise natural Streamlit transition remains
unproven. These results do not change product-stage or genuine-use evidence.

[PR #274](https://github.com/YuzeJ21/Scope-Proof/pull/274) completed that scoped test repair at
main `37799a04942e2926bf9c73882a9e0f4e1e44698f`.
[Resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42450620236) passed
4,872 tests, 38 intentional skips, 95.5067% unrounded coverage, seven installed CLI checks and 34
browser-suite checks. CodeQL and base-advance checks also passed. This closes that selected
investigation; it does not reopen a general observer-hardening queue.

[PR #275](https://github.com/YuzeJ21/Scope-Proof/pull/275) completed evaluation-page source
alignment at main `388b7dae276253ac015efd852cd510bc3999f9fd`.
[Resulting-main CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42490554348) passed
4,872 tests, 38 intentional skips, 95.5067% coverage, seven installed CLI checks and 34 browser-suite
checks. The separately authorized [Pages run](https://github.com/YuzeJ21/Scope-Proof/actions/runs/42494611672)
published that exact revision. Public byte/link/render/media verification passed; this closes both
the source and publication milestones without advancing product validation.

| Priority | Gap and action | Completion criterion / decision |
| --- | --- | --- |
| P0 — final v0.2.6 distribution complete | Published the consolidated workflow from one fixed final-version source commit. | Final wheel, source archive and checksum manifest were publicly downloaded and verified. Release-source main checks passed 4,842 tests with 95.5067% coverage; installed checks passed seven CLI checks and 32 browser-suite checks. Use the Release entry for source and exact artifact identities; the historical dev0 packet is not a substitute. |
| Lifecycle consolidation complete | Confirm intent, analyze, record decisions, save, share offline, observe source changes, prepare fresh requirements and compare. | Consequential transition checks, including stale downloads, source contradictions and pending scope drafts, are retained. The release preparation queue is closed; no additional parity feature is selected. |
| Native released-writer compatibility complete, PR #272 | A published v0.2.6 rich saved history remains intact under the verified development reader. | Two immutable, provenance-bound actual-writer records now run in Linux/Windows CI. Complete-state and producer/history preservation, copy-only resave, transfer, reopening, active reports and pending current-report denial are covered. Exact-head and resulting-main checks passed. This closes the durable coverage gap; no current data-loss repair or further corpus generation is selected. |
| Selected-analysis revision labels complete, PR #273 | CSV/HTML reports use the validated selected bundle's recorded revision, including `unknown`. | Full-state labels, pending current-report denial, producer/history and analysis-only boundaries remain intact. Dedicated historical JSON/Markdown and download controls are unchanged. Exact-head and resulting-main checks passed; the initial browser timeout remains recorded separately. |
| Browser synchronization complete, PR #274 | A settled saved-review ID was rejected by a test waiting for a generic script-state transition. | The scoped control wait retains actual reopening and history checks at the same timeout. Exact-head and resulting-main checks passed; natural and controlled evidence stay separate. No further observer task is selected. |
| Evaluation website complete, PR #275 plus authorized publication | The existing page now identifies v0.2.6/source0.2.7.dev0 and describes save/share/revisit. | The exact `388b7da` site is public and verified. Keep its historic source-only assessment separate from the later deployment evidence; do not restart that slice. |
| No-install evaluation example complete, PR #276 | An evaluator can download a constructed handoff report before installation through the existing guide. | Actual public v0.2.6 export provenance, labelled boundaries, deterministic ZIP/HTML, offline rendering and public download checks passed. Resulting main c749917 passed CI with 4,884 tests, 38 skips and 95.5124% unrounded coverage. Do not repeat sample generation or deploy another site. |
| Measured history constraint — bounded repair | Valid large records repeatedly scan every audit event for each historical analysis. | New separate constructed cases reproduce the constraint below the unchanged cap. Group validated events once by revision, preserve every projection/gate/evidence/temporal check, and require regression, independent engineering review and exact-head CI. Local largest-case comparison preparation measured 12.191 → 3.924 seconds; this is not a UI guarantee or customer workload. See the assessment. |
| R-002 omission classification complete | The [existing miss taxonomy](docs/research/r002-swebench-verified/miss-taxonomy.md) classified the 15 frozen misses: 14 threshold rejections and one lexical mismatch. | Frozen inputs/results and the 5/20 candidate baseline stay unchanged. Do not repeat classification, retune or relabel R-002. No new retrieval change or separately labelled holdout is selected. |
| Conditional architecture follow-up | Workbench session-state guards remain distributed; complete-state validation/serialization and memory costs remain after the bounded event-scan repair. Stores reject records above 64 MiB; that cap is not a responsiveness guarantee. Filesystem operations depend on platform support. | Retain existing stale-state, Windows and storage regressions. The measured event-scan repair does not authorize further extraction, caching or storage changes. Require another consequential reproduced constraint before such work. No rewrite, database or multiuser service is selected. |
| Stage 3 — dormant | Usefulness, operator/recipient fit and independent reuse are unproven. | Genuine independent-use evidence and separate authorization; no personal testing or qualifying reviews are requested by this roadmap. If such evidence is not pursued, remain an engineering reference/evaluation product. |

**Product strengths:** explicit intent, inspectable gaps, exact-head history and portable decision
handoff already form a coherent engineering demonstration. **Product limits:** local setup,
public-only intake, evaluation-only use rights, asserted identities and unvalidated usefulness
constrain adoption. Acceptance-criteria checking overlaps with existing review tools; the lifecycle
is a hypothesis worth explaining, not established differentiation.

**Architecture strengths:** the deterministic core is independent of the workbench, persistence
and exports are schema-validated, stale operations fail closed, and target code is not executed.
**Architecture limits:** producer identity and current validation are different; there is no
historical executable replay. Candidate verification must preserve the producer and name the
installed reader separately. No policy/schema change is required merely to verify v9-to-v9 upgrade.

No additional adapter family, accounts, hosted processing, billing or generic code review is
needed for this outcome. Licensing expansion, authenticated collaboration and private-repository
support require a separately chosen product direction. Do not start them automatically.

### Reusable goal prompts

**Executed consolidation goal — retain as a reproducible prompt:**

> Create and pursue a bounded ScopeProof consolidation and evaluation-candidate goal. Establish
> live main and public-release identities; reconcile the changes since v0.2.5 and close completed
> milestones. Build unpublished `0.2.6.dev0` wheel and source artifacts from a fixed commit. Verify
> clean installations, source-built parity, actual published-v0.2.5 writer compatibility on copied
> constructed records, installed CLI/browser journeys, frozen benchmarks and required CI. Preserve
> producer/history/provenance and all AGENTS.md evidence, confirmation and fail-closed boundaries.
> Record artifact hashes, source identity, results and limits; obtain independent engineering
> review, merge only after exact-head checks pass and verify main. No personal testing, qualifying
> reviews, publication, deployment or outreach. Stop when the candidate evidence is reviewable.

**Executed native released-writer compatibility goal — closed by PR #272:**

> Create and pursue one bounded ScopeProof compatibility goal. Establish unpublished `0.2.7.dev0`
> source separately from public v0.2.6. Use the verified actual public v0.2.6 writer to produce
> explicitly constructed rich active and unconfirmed saved histories through supported APIs.
> Retain immutable record bytes, reproducible generation and schema-validated artifact provenance.
> Make complete state, producer identities, history and existing decisions a permanent regression
> contract through load, copy-only resave, complete-record transfer, recipient reopen and exports.
> Exercise the contract through existing Linux/Windows CI, obtain independent engineering review,
> merge on green exact-head checks and verify resulting main, then stop. This closes a durable
> coverage gap, not a demonstrated current data-loss defect. Preserve all evidence/confirmation
> gates, public-release guards and frozen R-002. No personal testing, qualifying reviews, new
> publication, deployment, outreach, parity feature queue or repeated R-002 investigation.

**Executed historical-analysis revision-label goal — closed by PR #273:**

> Create and pursue one bounded ScopeProof report-correction goal. Reproduce the CSV/HTML
> revision-label error using an explicitly selected retained analysis from the immutable native
> v0.2.6 corpus. Render the validated bundle's recorded criteria revision, including `unknown`,
> without fabricating a current ReviewState. Preserve current-state labels, pending-report denial,
> analysis-only boundaries, producer/history provenance, schemas, deterministic gates and frozen
> R-002. Add regressions, run required automated checks at the existing 95% coverage floor and
> packaged journeys, obtain independent engineering review, merge on green exact-head CI and
> verify resulting main, then stop. Keep source at unpublished `0.2.7.dev0`; public v0.2.6 is
> unchanged. No personal testing, qualifying reviews, new release, deployment, outreach or
> additional report format/download path.

**Executed browser synchronization goal — closed by PR #274:**

> Create and pursue one bounded ScopeProof browser-observer investigation. Preserve the captured
> CI timeout and passing rerun evidence; attempt a bounded natural reproduction and keep those
> observations separate from clearly labelled controlled signal-loss replay with the real installed
> app. Repair only the demonstrated test synchronization defect: use the server-computed saved
> review ID commit outcome, retain the empty/disabled precondition, actual validated reopening and
> saved-state/history assertions, and keep the same timeout. Do not relax the generic observer,
> add blind retries or change product/core/gate behavior. Preserve source `0.2.7.dev0`, public v0.2.6,
> frozen R-002 and native records. Run required automated checks at the existing 95% coverage floor,
> independently review, merge on green exact-head CI and verify resulting main, then stop. Do not
> claim the exact natural Streamlit mechanism is known. No personal testing, qualifying reviews,
> new release, deployment, outreach or new product feature.

**Executed website alignment goal — closed by PR #275 and separate publication:**

> Create and pursue one bounded ScopeProof evaluation-entry goal. Verify live main and public
> release identity; close PR #274 in current guidance. Correct the existing static page to
> distinguish public v0.2.6 and unpublished 0.2.7.dev0, route readers to the evaluation guide,
> and explain saved decisions, offline HTML handoff and revisiting. Preserve earlier constructed
> media with accurate scope, evidence boundaries, evaluation-only rights and dormant Stage 3.
> Check desktop/mobile private previews, links, existing contracts and required CI; independently
> review, merge on green exact-head checks and verify resulting main. Preserve manual-only Pages.
> No personal testing, qualifying reviews, publication, deployment, outreach or new feature.

**Bounded no-install sample goal — retain as a reproducible prompt:**

> Create and pursue one ScopeProof evaluation-artifact goal. Generate a self-contained HTML report
> with the verified public v0.2.6 exporter from the existing immutable constructed active record.
> Keep Action required and final acceptance No; add only a prominent simulation/synthetic-link
> disclosure and separately bind input, recipe, raw export and presented bytes with strict Pydantic
> provenance. Link the repository download before installation in README/evaluation guide. Verify
> offline desktop/mobile rendering and no network, automate tests and independent review, merge
> after exact-head checks pass and verify resulting main and public download. Preserve frozen
> benchmarks and historical records. No package release, Pages deployment, personal testing,
> qualifying reviews, outreach or Stage 3 claim. Stop after this artifact; no new feature queue.

**Future publication goal — requires separate authorization:**

> After explicit authorization for a named evaluation version and fixed candidate, recheck the
> candidate's source, final version, artifact hashes, compatibility and CI. Publish only that
> downloadable evaluation release, then independently fetch and verify the public wheel, source
> archive and checksum manifest and repeat isolated installed checks. Preserve evaluation-only
> positioning. Do not deploy, contact participants or claim genuine-use evidence or Stage 3.

The implementation notes below describe each historical milestone. Their then-unreleased wording
is dated evidence; the current priorities and version guide above govern the present direction.

## Current operating decision

**Current development source/package version is 0.2.7.dev0.** The published v0.2.6 download and its
completed public verification are bound to final source `68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1` in the
[Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6). Check its final assets
and verification before installing; the current development tree is not a new published release.
The verified v0.2.5 fallback and its public checks are bound to
`72cac01ea6abb99beaf714396eb610fa39fe84f0`.
The [v0.2.4 verification record](docs/releases/v0.2.4-public-verification.md) and the
[PR #221 private candidate guide](docs/releases/v0.2.5-evaluation-candidate.md) preserve their
own source and artifact identities.
The [native saved-review upgrade rehearsal](docs/research/2026-10-29-v023-v024-upgrade.md)
verified one constructed published-v0.2.3 writer → published-v0.2.4 reader history: original
facts and linked decisions survived, while missing changed-file inventory correctly changed
both old Ready gates to Needs review. That question is closed and required no product fix or
policy change. The [covered-suite maintenance record](docs/audits/2026-10-29-verification-performance.md)
addresses observed verification delay with a measured CI-only engine change, unchanged coverage
accounting and all existing gates. That CI-only question is closed by merged PR #218. The
[dependency-floor assessment](docs/audits/2026-10-29-runtime-dependency-floor.md) then found that
the historical Streamlit minimum cannot use the maintained Pillow baseline, and reproduced a
separate browser upload defect at exactly 1 MiB. Current install guidance names the maintained
dependency constraints, including the locked Pydantic baseline after broader source checks exposed
R-002 strict-validation failures at Pydantic 2.8.0. The published package's metadata still permits
that incompatible older combination in v0.2.4. PR #219 integrated the upload repair shipped in v0.2.5, letting the
full-size artifact reach the unchanged fail-closed parser limit, with unit and installed-browser
regressions. The [source declaration alignment](docs/audits/2026-10-29-dependency-baseline-alignment.md)
now enforces the maintained Pydantic, Streamlit and direct Pillow floors, retaining all resolved
lock versions. These are verified baseline choices, not proven earliest compatible versions.
The older-stack
browser observation remains partial because its saved-review selector differs from the current
test helper; it is not a full compatibility pass. The upload, dependency, CI and candidate
preparation questions are closed. The v0.2.6 distribution and public verification are complete.
PR #272 closed the native released-writer compatibility contract and PR #273 closed CSV/HTML
revision labels. PR #274 closed its bounded browser wait repair; PR #275 and the separately
authorized exact-revision Pages publication closed the website milestone. The no-install
constructed report example is the bounded outcome in the
[current priorities](#current-priorities--2026-11-07). This remains evaluation
distribution, not a Stage 3 beta. No personal testing or qualifying reviews are required. No further release,
deployment, outreach or participant program follows automatically.

Maintain the confirmed-criteria → exact-head candidate evidence → missing evidence → reviewer
decisions → re-review workflow. Its usefulness and primary-operator hypothesis (engineer or
technical QA reviewer, with a PM or requirements owner receiving the report) remain unvalidated.
The [market comparison](docs/commercialization/market-comparison-2026-11-02.md) documents substantial
overlap, including Tiden, CodeRabbit, Qodo, Qase, Spec Kit, and Kiro; it supports no novelty or
superiority claim.

On 2026-10-30 the owner asked to review product gaps and continue development instead of repeating
maintenance and release preparation. Stage 2 therefore follows named reviewer outcomes with
automated acceptance evidence. Finish the selected milestone, its checks and current-document
alignment before selecting another item. Do not generate an endless queue, repeat closed
investigations or request participant reviews to create activity. Additional adapters,
authenticated identity and integrations remain separately scoped options.

## Current release and validation state

The GitHub Release record is authoritative for publication availability.
ScopeProof v0.2.6 is published and all three public assets are verified from final source
`68f5c7af9cdaafe97ab72c1a7f6c8784f65a44e1`. Use the
[v0.2.6 Release entry](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.6) for exact source,
artifact hashes and completed public-download checks. ScopeProof v0.2.5 is published as a fallback;
v0.2.5 is available from the
[v0.2.5 GitHub Release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.5),
which provides the wheel, source archive, and checksum manifest.

This source tree declares unpublished `0.2.7.dev0`. A source declaration and the historical
private `0.2.6.dev0` candidate do not establish public availability or final artifact identity.
The permanent native v0.2.6 regression corpus is engineering evidence only and does not create
independent-use evidence, another release or Stage 3 credit.

The table and integration notes below preserve dated engineering references. They are not a
moving-head ledger. The PR #247 resulting-main baseline (`5b9860b`) has twenty-five browser checks: eleven installed-wheel
Chromium cases, eight constructed Streamlit selection checks, and six helper/capture checks.
Dated five-check CI results below remain
historical results, not current suite counts.

The [2026-10-28 browser maintenance investigation](docs/audits/2026-10-28-browser-maintenance.md)
separates reproduced helper/download defects from the original missing-dropdown trigger, which
remains unexplained. That bounded maintenance did not change stage or release status.

The [2026-10-30 JUnit selection follow-up](docs/audits/2026-10-30-junit-browser-recovery.md)
records the recurring multiselect verification failure and bounded helper recovery. It adds no
product milestone or genuine-use evidence; the original popup-disappearance cause remains unproven.

The [2026-10-28 CI maintenance slice](docs/audits/2026-10-28-ci-required-gate.md) addresses
documented skipped-dependency gate risk and observed serial verification delay. The unchanged
engineering workload runs independently; the final required `verify` check accepts only success
from all five engineering lanes. This does not reduce verification or create a feature queue.

The owner-authorized [CSV decision-handoff slice](docs/superpowers/specs/2026-10-29-csv-decision-handoff-design.md)
addresses a reproduced product gap: CSV previously omitted the review-level reason and next action
when accepted criteria still required final acceptance. Six appended JSON-array columns preserve
the existing gate context on each criterion row. This is included in published v0.2.4 and remains
engineering evidence only; it does not advance Stage 3 or change the historical v0.2.3 package.

The [candidate-selection completeness slice](docs/superpowers/specs/2026-10-29-candidate-selection-completeness-design.md)
discloses eligible, shown and omitted candidate counts around the unchanged eight-candidate
selector. Historical counts remain unknown. This adds explanation across the workbench and
exports without changing retrieval, gate decisions, frozen research or stage status.

<details>
<summary>Release baseline and dated integration references</summary>

The rows below preserve dated integration and pre-v0.2.4 preparation snapshots. Their source
versions and availability statements are historical; use the candidate guide and GitHub Releases
for the current source identity and publication availability.

| Area | Snapshot state |
|---|---|
| Published install | v0.2.3 GitHub Release with wheel, source archive, and checksum manifest |
| Active source line | Unreleased `0.2.4.dev0`; no v0.2.4 release, tag, or package publication exists |
| Post-PR #207 resulting-main snapshot (2026-10-27) | `8f01cf237b75da30796d1879f3fbde7b8a5ef6d5`; [CI run 40431365174](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40431365174) passed 2,581 tests, 2 intentional skips, 95.0534% unrounded coverage, and 5/5 packaged-browser checks. Pages did not run or create a deployment for this merge. See the [dated engineering record](docs/portfolio/2026-10-27/verification.md). |
| Post-PR #202 resulting-main snapshot (2026-10-26) | `e1f798a05940c39f9aea1f7fbf62ece5f4f7b73e`; [CI run 40204676870](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40204676870) succeeded with 2,523 passed, 2 intentional skips, 95.06% coverage, and 5/5 packaged-browser checks |
| 2026-10-25 observed main | `f586d90b72a14fd19d5a0add01f3d05532a88955`; integrity and portfolio draft work remains separate from the published v0.2.3 release |
| Post-PR #193 resulting-main snapshot (2026-08-13) | PR #193 product-source baseline at `432371c4faec0b790f70fec32b4d3fc4d5132cfa` (PR head `8bb407079a0ff7098d2fc18af3d75b216725df2e`, base `9426e8714ffd2c3742bb074ae26fc788f1049c63`) |
| Post-PR #196 resulting-main snapshot (2026-08-17) | Exact PR #196 head `5a6a25a6dff23cdfa8dcb4023b83144078620610` landed in merge `8387156fd6f6e90eef7caf58881b0cc5bb62b111`; hosted resulting-main CI run [`32093041685`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/32093041685) succeeded as the exact-head engineering record |
| Post-PR #197 resulting-main snapshot (2026-08-18) | Exact PR #197 head `5a69af4e92e2720adc524a32ea8c4eb94d013cb8`, base `8387156fd6f6e90eef7caf58881b0cc5bb62b111`, and merge `789950dc63d80ec24d8bca5974a3ae52955b1c4f`; resulting-main CI [`32194734107`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/32194734107), CodeQL [`32194733033`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/32194733033), Pages [`32194734125`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/32194734125), and base-advance [`32194734440`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/32194734440) succeeded as the dated engineering record. PR #197 owner workflow consolidation is complete and does not claim customer validation. |
| Verified product baseline | PR #184 release integration landed on `main` at `448c42758ea139bf9203cbf1bb04b02b02ae412c` |
| Product verification | Full product-code verification is bound to `fb74d4bbb402f4de3e2fabb56ce28c948214f8c2`; package, install, installed-benchmark, and health artifacts are bound to `81598899fcd85df58ab22f9212f2e8382f4a5e5f`. |
| Release integration evidence | PR #184 release integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`; exact-main CI, CodeQL, and Pages all succeeded, and `origin/main` matched at the 2026-08-08 branch-start snapshot |
| Integration authority | PR #184 exact-main CI run `30854382641`, CodeQL run `30854382413`, and Pages run `30854382659` verify the release integration |
| Historical source integration | PR #183 integrity/reviewer-loop source merge at `cd362a85a558645a0f56d6540f6bf035e5821809`; runs `30847416893`, `30847415556`, and `30847417705` remain historical source-integration evidence |
| Snapshot verification | Hosted resulting-main CI run [`31704668247`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668247) at exact PR #193 tree `432371c4faec0b790f70fec32b4d3fc4d5132cfa` recorded 2,251 passed, 2 intentional skips, and 95.22% coverage |
| Snapshot engineering checks | Resulting-main CI run [`31704668247`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668247) covers Python 3.11, Python 3.13, Windows, installed-wheel, deterministic benchmark, and packaged-browser checks; CodeQL run [`31704666031`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704666031) and Pages run [`31704668164`](https://github.com/YuzeJ21/Scope-Proof/actions/runs/31704668164) also succeeded |
| Product validation | Stage 1 closed as not pursued with every count at zero; owner-led Stage 2 is active without customer-validation claims |

Verify live GitHub and current release records before relying on publication state. Engineering
milestones may proceed through owner-led Stage 2, but they remain engineering evidence rather than
customer validation.

After the v0.2.3 release, PR #185 merged core-backed CLI lifecycle parity and packaged Chromium
proof at `30177733ef312ced22e6a2e57e3df6fdb1e92507`; PR #187 merged Python 3.13 plus bounded
keyboard/focus and zoom engineering evidence at `c548759b5464ad5bb98baf1e996397f241dfc455`; and
PR #188 merged verified-public provenance enforcement at
`077f9351283b319b82854ad1df95eac7ce614e21`. CLI lifecycle parity is implemented;
verified-public provenance enforcement is implemented. These changes form the `0.2.4.dev0`
development line and earn no Stage 1 credit.

PRs [#199](https://github.com/YuzeJ21/Scope-Proof/pull/199) through
[#202](https://github.com/YuzeJ21/Scope-Proof/pull/202) merged the bounded JUnit adapter,
urllib3 and GitPython lock updates, and the integrity work. The resulting-main
[CI run 40204676870](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40204676870)
succeeded at `e1f798a05940c39f9aea1f7fbf62ece5f4f7b73e` with 2,523 tests passed,
2 intentional skips, 95.06% coverage, and 5/5 packaged-browser checks. The
[2026-10-25 integration disposition](docs/audits/2026-10-25-integrity-integration-disposition.md)
remains a historical pre-merge review. These changes are on the unreleased `0.2.4.dev0`
development line and provide engineering evidence only.

PR #189 established the post-release development identity; PR #190 preserved comparison
relationship integrity; PR #191 remediated the GitPython dependency and security issue; PR #192
bounded same-origin GitHub pagination; and PR #193 hardened cross-platform identity-bound alpha
storage. The dated post-PR #193 resulting-main snapshot at
`432371c4faec0b790f70fec32b4d3fc4d5132cfa` is the PR #193 product-source baseline, not a
declaration of perpetually current `main`. These are engineering changes on `0.2.4.dev0`, not a
new published release; v0.2.3 remains the published release and none earns Stage 1 credit.

PR #194 aligned the dated status record without turning it into a moving-head claim; PR #195 closed
Stage 1 as not pursued and activated owner-led Stage 2 without customer-validation claims; PR #196
added the exact-head informational Check lifecycle with bounded default-base repair; and PR #197
completed owner workflow consolidation. PR #198 adds blocker-first decision-handoff ordering and
places the selected criterion evidence and controls before the secondary evidence matrix as a
bounded Stage 2 follow-up. This remains Stage 2 engineering work and does not claim customer
validation.

The current bounded JUnit adapter slice adds the first separately typed, non-executing evidence
adapter across the core, CLI, local workbench, saved records, exports, comparison, and installed
browser proof. It accepts only bounded local bytes, stores sanitized exact-head and criteria-bound
context, requires explicit human mapping, and never changes gate inputs or creates E1–E4, CI,
runtime, decision, acceptance, correctness, or customer-validation claims.

</details>

### Verification and evidence boundaries

- Engineering checks do not prove acceptance-criteria correctness.
- CI Windows evidence is not a real Windows desktop workflow.
- Browser automation is not screen-reader or WCAG-conformance evidence.
- Reviewer identity remains asserted, not authenticated.
- The GitHub Action remains opt-in and informational. Its neutral-only
  `ScopeProof evidence summary (informational)` is exact-head and criteria-source bound, is not a
  required branch-protection check, and does not create customer validation. It does not prove
  correctness, does not prove runtime behavior, does not prove accessibility, and does not prove
  demand or adoption. Stage 1 remains at 0/5 qualifying reviews, 0/3 independent practitioners,
  0/3 public repositories, 0/3 independently observed under-ten-minute completions, and 0/2
  reuse-intent signals.
- ScopeProof never executes target-repository code.

### Storage-maintenance boundary

`atomic_files.py` is large and transactionally complex, and its existing regression coverage is
strong. Portable storage may fail closed on filesystems without required hard-link behavior, and
ambiguous filesystem ownership must be preserved rather than deleted. Future filesystem-behavior
changes require a separate design, test-first decomposition, and owner approval; do not weaken
identity-bound cleanup or atomicity to simplify the implementation.

## Stage 0 — Reviewer-first product reset

Status: prior PR #177 repairs remain historical engineering evidence. PR #180
merged the exact-head runtime-evidence repair, PR #181 aligned the
documentation, PR #182 merged product convergence, and PR #183 merged the
integrity/reviewer-loop source work. PR #184 then merged the v0.2.3 release
integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`; the peeled tag and
release baseline resolve to the same commit. `origin/main` also matched at the
2026-08-08 branch-start snapshot. The GitHub Release record is
authoritative for publication availability. None of this engineering evidence
advances Stage 1, which remains at zero.

- [x] Acceptance-coverage vocabulary separates candidate strength from reviewer decisions.
- [x] Standard flow is public PR → confirmed criteria → coverage → decisions → export.
- [x] Live reviews and genuine-alpha records require an explicit verified-public repository fact;
  private, ambiguous, and legacy-unverified sources fail closed for Stage 1.
- [x] Enforce at the core boundary that manual verification records runtime
  evidence and its decision atomically, and reject unpaired reconstructed
  bundles or states at every trusted boundary.
- [x] Enforce at the core boundary that final acceptance requires complete
  ingestion, passing observed CI, and a current accepted decision for every
  criterion.
- [x] Encode unchanged-candidate paths, transmit the exact head SHA separately,
  and reject malformed or unanchored candidate responses.
- [x] Bind every effective E3/E4 manual decision to one immutable runtime
  evidence ID and matching repository, PR, head, criterion, reviewer, and level.
- [x] Migrate version 1/2 records to version 3 without inventing manual links;
  legacy-unlinked decisions remain auditable and require reconfirmation.
- [x] Bind each new criteria confirmation to an immutable source URI, optional
  revision, exact source-text digest, ordered normalized-criteria digest,
  confirmer, and timestamp. Version 1–3 records migrate to version 4 without
  invented provenance and remain fail-closed until reconfirmed.
- [x] Project runtime identity through the workbench and JSON, Markdown, CSV,
  and HTML exports while retaining Pydantic validation.
- [x] Project criteria-source provenance through the CLI, advanced Action,
  workbench, alpha record, local persistence, and all validated exports.
- [x] Reject malformed or cross-object gate input deterministically before it
  can be evaluated, including duplicate identifiers, coverage mismatches,
  foreign resolution identifiers, and provenance-digest contradictions.
- [x] Bind qualifying alpha outcomes to a fully revalidated saved review,
  genuine public-GitHub origin, exact PR head, criteria snapshot, and immutable
  one-time outcome; fixture, demo, research, and legacy-unknown origins remain
  ineligible.
- [x] Provide an offline confirmation-preparation command that calculates
  exact requirement hashes, refuses overwrite, and never needs a paid API.
- [x] Simplify the workbench and public-alpha surfaces with supported theme
  settings and progressive disclosure while preserving safety copy, focus
  treatment, and deterministic gate behavior.
- [x] Clean the public product page for desktop and narrow screens, including a
  readable mobile header and a valid local favicon without changing the
  evidence boundary.
- [x] Optional alpha feedback stays separate, local, consent-controlled, and off by default.
- [x] Re-review comparison preserves both bundles and reports head, evidence, decision, and status
  changes.
- [x] The GitHub Action remains an advanced, non-default preview.
- [x] **Software license decision:** the evaluation-only use policy remains unchanged and no
  open-source license is granted.

## Completed engineering evidence — does not advance Stage 1

- [x] R-001 records a hash-bound public-PR engineering comparison with corrected observed-CI
  aggregation and explicit E2 eval-definition intent. It does not establish test execution,
  runtime verification, acceptance, or Stage 1 credit.
- [x] R-002 records a deterministic 20-case, 12-repository static baseline with frozen
  benchmark-owner research criteria and labels, immutable references, zero unexpected Ready
  outcomes, and two identical offline runs.
- [x] R-002 executed 20/20 cases with zero failures, skipped cases, or rerun mismatches. It
  recorded 18/22 benchmark-label candidate precision, 5/20 criterion candidate coverage, and
  41/41 missing-evidence explanation completeness.

These cases, repositories, outcomes, and timing contribute zero genuine Alpha reviews,
participants, repositories, timing observations, False Ready rate evidence, or reuse signals.
R-002 is engineering evidence only. It contributes to owner-led engineering work but not customer
validation or optional external-discovery evidence.

## Current engineering track — v0.2.3 Evidence Quality

Status: the earlier candidate and PR #177 repairs remain merged history. PR #179
merged the first workbench UX change, PR #180 merged exact-head runtime-evidence
hardening, PR #181 aligned post-merge documentation, PR #182 merged product
convergence, and PR #183 merged the integrity/reviewer-loop source work at
`cd362a85a558645a0f56d6540f6bf035e5821809`. PR #184 merged the published
v0.2.3 release integration at `448c42758ea139bf9203cbf1bb04b02b02ae412c`.
The GitHub Release record is authoritative for publication availability. This
engineering and release work earns zero Stage 1 credit.

- [x] Add validated retrieval outcomes and one deterministic diagnostic per criterion.
- [x] Record searched terms, identifiers, paths, evidence types, inspected-line counts, filtering
  counts, and accepted-candidate counts without changing retrieval behavior.
- [x] Persist diagnostics in new reviews while preserving historical reviews without inventing
  diagnostics.
- [x] Render diagnostics in the workbench, CLI-created reviews, constructed demo, and Markdown,
  JSON, CSV, and HTML exports.
- [x] Prove existing evidence IDs, scores, references, findings, and gate decisions are unchanged.
- [x] Prove the completed R-002 canonical inputs and result remain byte-identical.
- [x] Classify R-002 misses only after diagnostics exist. Convert genuine retrieval defects into
  separate constructed regression fixtures.
- [x] Reject ineligible final-acceptance and unpaired manual-verification
  events in the core lifecycle, with regression coverage.
- [x] Preserve exact-head candidate retrieval across URL metacharacters and
  Unicode paths, with request-level regression coverage.
- [x] Require immutable runtime identity for new E3/E4 records and fail closed
  on duplicate, missing, foreign-repository, wrong-PR, wrong-head, or mismatched
  resolution links.
- [x] Keep legacy runtime history visible while deterministically requiring
  active-head reconfirmation instead of guessing an association.
- [x] Show complete passing CI observations with skipped checks as an explicit
  visible limitation without changing their deterministic check state.
- [x] Restore autosave recovery for bundle-less revised reviews with stale
  criterion-detail drafts, without mutating review state or enabling exports
  before reanalysis.
- [x] Require an exact, typed criteria-source snapshot before new analysis,
  automated review, export, alpha outcome, or final acceptance can proceed.
- [x] Preserve legacy version 1–3 records without fabricating provenance and
  require explicit source reconfirmation before they can regain eligibility.
- [x] Reduce first-use and public-alpha page density without hiding evidence,
  limitations, labels, controls, or the reviewer confirmation step.
- [x] Fail closed when GitHub provides no inspectable changed-file patch instead
  of treating a missing patch as a complete empty file.
- [x] Restore saved-review source identity for a one-click current-head check,
  connect matrix cards to criterion detail, and require a note for acceptance
  below the required candidate-evidence level.
- [x] Make all five re-review candidate classes inspectable in the workbench and
  add validated comparison Markdown and JSON downloads.
- [ ] Freeze a new holdout before using it to evaluate a retrieval algorithm change. R-003 design
  is complete; cohort generation and later criteria and label confirmations remain distinct
  evidence-integrity gates.
- [x] Complete fresh packaging, clean-install, and a bounded accessibility and platform audit in
  the available environment before calling v0.2.3 an internal release candidate; unsupported
  environments and interactions remain explicitly unverified.
- [x] Keep publication as a separate owner-controlled decision.

Do not retune against the frozen R-002 cohort, weaken thresholds, add model-generated verdicts, or
promote search diagnostics into evidence or correctness claims.

The [earlier status audit](docs/releases/v0.2.3-status-and-next-stages.md) retains the feature
ledger before v0.2.5. See [current priorities](#current-priorities--2026-11-07) for the next stage.
Current official-source
competitive research is maintained separately in the
[current official-source market comparison](docs/commercialization/market-comparison-2026-11-02.md).
Historical current-main package, security, and environment evidence is recorded
in the [post-merge release-readiness audit](docs/releases/v0.2.3-post-merge-release-readiness.md).
The merged product-tree evidence is recorded in the
[exact-head verification audit](docs/audits/exact-head-runtime-evidence/verification.md).
The merged PR #182 convergence source and its deliberately separated
historical-candidate exact-target evidence are recorded in the
[product-convergence verification audit](docs/audits/v0.2.3-product-convergence/verification.md).
The merged PR #183 ingestion and reviewer-loop source evidence is recorded in the
[integrity and reviewer-loop verification audit](docs/audits/v0.2.3-integrity-reviewer-loop/verification.md).

## Stage 1 — Genuine public alpha

Status: `closed_not_pursued_by_owner`.

Stage 1 did not pass. On 2026-08-14, the owner chose not to pursue the external public-alpha
program. Closure changes no measured count, satisfies none of the former exit conditions, and
creates no customer, adoption, usability, timing, reuse, demand, pricing, or willingness-to-pay
evidence.

Current measured state:

- 0/5 qualifying reviews.
- 0/3 independent practitioners.
- 0/3 public repositories.
- 0/3 independently observed under-ten-minute completions.
- 0/2 reuse-intent signals.
- Zero participant False Ready observations across zero participant reviews; this is
  not a validated False Ready rate.

Former exit conditions, preserved as unmet historical targets:

- [ ] Five completed reviews on genuine public pull requests.
- [ ] At least three independent practitioners across product, QA, or engineering roles.
- [ ] At least three public repositories.
- [ ] At least three participants reach an inspectable coverage report within ten minutes.
- [ ] Misleading candidate matches and material friction are recorded, not hidden.
- [ ] Zero confirmed False Ready outcomes.
- [ ] At least two independent participants state an intent to use ScopeProof again.

Only source-owner-confirmed criteria from public requirements, a genuine public pull request, an exact reviewed head SHA, a saved
review, and a validated local outcome record count. Constructed demos, owner-authored synthetic
cases, technical smokes, release downloads, and GitHub activity do not count.

The [concierge host checklist](docs/alpha/concierge-host-checklist.md) remains available only for
optional voluntary external feedback. Using it does not reopen Stage 1 or create stage credit.

### Archived external-evidence distinctions

These distinctions remain binding if optional external research is separately authorized:

- Preparation is not outreach: prepare public, source-safe materials and qualification records
  before contacting anyone, but do not contact, recruit, or message a participant without that
  separate authorization.
- Inbound submissions are not recruited participants: retain the source and authorization path for
  each case and do not count an inbound lead as recruited use.
- Observed completion evidence is not self-reported timing: independently observe the complete
  review-to-inspectable-coverage-report interval before crediting the under-ten-minute count.
- Qualifying reviews are not demos, tests, maintainers, bots, or repository activity: only the
  documented non-owner, public-PR, source-owner-confirmed, exact-head, saved-review, validated-
  outcome path can credit a count.

## Stage 2 — Owner-led productization

Status: `owner_led_productization_active`.

The owner authorized owner-led productization on 2026-08-14 and on 2026-10-30 delegated the move
from maintenance to a short product-development queue. This status does not claim customer
validation. Each milestone addresses an inspectable gap in the implemented reviewer workflow,
with a user outcome and automated completion evidence. A gap in the implementation is a reason
for a bounded engineering improvement, not proof that practitioners need or will adopt it.

| Order and status | Reviewer outcome and current gap | Automated finish line |
| --- | --- | --- |
| M1 — implemented in source: scope-aware re-review | Explain changed-file scope across reviewed heads. Candidate-only comparison previously omitted the changed-file inventory, so an uncited file could appear without a corresponding candidate delta. | Deterministic, Pydantic-validated scope comparison in the workbench and comparison JSON/Markdown; constructed regressions for inventory differences, explicit rename metadata, unresolved paths and historical unknown inventory; relevant full-suite, coverage, lint, package/browser and exact-head CI checks. Keep gate semantics and reviewer decisions unchanged. |
| M2 — implemented in source: durable saved comparison | Reopen a saved review and explicitly select another saved record or a retained compatible historical analysis. Changed heads can live in distinct saved records. | Validated read-only selection bound to both saved-state fingerprints; explicit compatibility checks; stale selection/download invalidation; unchanged saved JSON bytes and decisions; core, AppTest and installed-browser restart/reopen/download regressions. |
| M3 — implemented in source: reviewer-selected references | Explicitly cite an already-ingested exact-head static location omitted by conservative matching, with criterion mapping, reviewer and rationale, and audited correction/withdrawal. Usefulness remains unvalidated. | Separate non-gating, Pydantic-validated references/events; source/fingerprint/provenance checks; bounded selection/history; safe v7 persistence and legacy rejection; core, report, AppTest and installed-browser save/restart/reopen/download regressions. Preserve automatic findings, confidence, scope coverage, decisions and runtime truth. |

M1 is implemented by [PR #222](https://github.com/YuzeJ21/Scope-Proof/pull/222); its review and
exact-head integration checks are recorded there. Finish its outcome, regression coverage,
required checks and documentation, then stop that slice. M2's source implementation now restores
explicit saved-baseline access without reanalysis or a record-format change. M3 adds separately
attributed non-gating static references under its [bounded design](docs/superpowers/specs/2026-10-30-reviewer-selected-evidence-design.md).
Saved references remain viewable/exportable after reopen; new selections require matching loaded
source. They do not resolve missing automatic evidence or uncited changed files. Do not expand the queue or repeat candidate preparation to
manufacture progress. Required defect and dependency upkeep may interrupt the sequence when
needed. Do not make the owner test the product, recruit qualifying reviews or reopen Stage 1.

The verified engineering foundation includes confirmed criteria, immutable candidate references,
explicit missing evidence, fail-closed scope gates, reviewer decisions, local persistence and
exports. Independent usefulness, operator/recipient fit, repeat use and demand remain unknown.
None of these milestones supplies genuine independent-use evidence or advances Stage 3.

After PR #226, the owner authorized one bounded follow-on: **recorded selected-reference context
in saved re-review comparisons**. M3 deliberately excluded that context from comparisons; the new
source adds a separate attributed previous/current view and exact full-record presence distinctions
to the workbench and comparison JSON/Markdown. It never infers cross-head equivalence, carries a
decision forward, or changes automatic counts, findings, scope or gates. Missing historical
comparison projections stay unavailable rather than becoming invented empty snapshots. See the
[bounded follow-on design](docs/superpowers/specs/2026-10-30-selected-reference-comparison-design.md).
This completes this selected outcome, not an open-ended fourth-milestone queue. The owner then
explicitly selected **historical baselines from other saved reviews**. Unreleased source now adds a
per-record active/history selector, with record/head/revision identity and whole-record fingerprint
binding through locked preparation and downloads. Historical-only records and compatible histories
beneath incompatible active analyses remain selectable; changed records require explicit reselection,
without falling back to another analysis. See the [bounded history design](docs/superpowers/specs/2026-10-30-foreign-history-baseline-design.md).
After PR #228, the owner selected **file-scoped source reference paging**. Unreleased source now
uses an eligible-file catalog and pages of 100 eligible lines per selected file, reaching beyond
the legacy global first 1,000. Explicit line choice, exact-source/fingerprint revalidation, the
4,096-byte line and 32-reference limits, and existing source exclusions remain in force. Switching
file/page clears the line choice; static references remain non-gating. See the [bounded paging
assessment](docs/audits/2026-10-30-paged-source-references.md). This completes that selected outcome;
broader adapters, accounts, hosted processing and external validation retain separate gates.

The next owner-delegated gap review selected **continue a reopened saved analysis with matching
source**. The prior current-head reload reset the analysis even when source identity was unchanged.
Unreleased source now provides a separate explicit source attachment, preserving confirmation,
decisions, producer identity and saved bytes while enabling further static-reference selection.
Complete source/CI facts, bounded recorded unchanged paths and optimistic saved-state checks must
match. Newly observed contradictions suppress current workbench authority and exports without
rewriting the historical gate; current-head re-review remains explicit. See the
[bounded continuation assessment](docs/audits/2026-10-30-resume-reviewed-source.md).
This is the selected outcome, not a new standing queue or evidence of independent usefulness.

The owner next selected **audited correction and withdrawal of selected references**. The
unreleased source retains immutable original records and appends attributed terminal events.
Correction links a fresh source-validated replacement; withdrawal works on a reopened record
without source. Workbench, reports and saved comparisons show lifecycle status and history,
separately from original-record presence counts. New records use version 7; older records gain
no invented events and load without rewriting. Limits are 32 active references, 128 retained
records and 128 events per analysis. See the [bounded audit design](docs/superpowers/specs/2026-10-30-selected-reference-audit-design.md)
and [engineering assessment](docs/audits/2026-10-30-selected-reference-audit.md).
This completes a correction/review outcome; it creates no standing feature queue or Stage 3 credit.

The next owner-delegated gap review selected **find saved reviews by validated recorded details**.
Unreleased source now offers explicitly loaded ten-record pages and page-scoped search by
repository, PR, head, revision or ID, shared by reopen and foreign-comparison selection.
Preview work is capped at 1 MiB per record and 10 MiB per request. Unavailable previews retain
ID-only access; direct reopen keeps full validation. Filename/owner identity and preview-state
checks prevent retargeted or stale choices. History selection, evidence, gates and record v7
remain unchanged. See the [bounded discovery assessment](docs/audits/2026-10-30-saved-review-discovery.md).
This completes another selected reviewer outcome without a persistent index, release or Stage 3 claim.

The next owner-delegated gap review selected **inspect recorded reviewer decision and runtime
context in compatible comparisons**. Previously, comparison reduced criterion resolutions to
decision labels, hiding same-label changes in notes, attribution or linked observations. Unreleased
source now provides separately validated previous/current snapshots in the workbench and comparison
JSON/Markdown, with complete latest criterion resolutions and retained runtime records. Complete
record distinctions remain separate from existing enum deltas, candidate changes, decision-review
logic and gates. Explicit runtime links are preserved; legacy links remain unknown. Review-level
final acceptance and full event history are outside this slice. See the [bounded assessment](docs/audits/2026-10-30-decision-context-comparison.md).
This completes the selected reporting outcome without changing record v7, release status or Stage 3.

The next owner-delegated gap review selected **inspect and hand off one retained historical
analysis without a compatible active analysis**. Saved data was intact, but comparison-only access
excluded pending records with no active bundle and changed criteria. Unreleased source now provides
an explicit read-only history selector, historical-only JSON/Markdown and separate producer/current
validation identities. Full-record/history-position/analysis fingerprints and callback leases reject
stale or retargeted choices. Unknown revisions remain unknown; missing historical provenance keeps
reports unavailable under existing policy. Current drafts, active analysis, decisions, gates,
comparison compatibility and record v7 stay unchanged. See the [bounded assessment](docs/audits/2026-10-31-historical-analysis-inspection.md).
This completes one inspection/handoff outcome without a new release, standing queue or Stage 3 claim.

The next owner-delegated gap review selected **inspect saved requirements changes**. Revising
requirements archives the analysis, while evidence comparison correctly refuses changed criteria.
Unreleased source now compares one explicitly selected retained analysis's criteria with the current
saved revision, even while unconfirmed. Complete field/position/source/provenance distinctions and
requirements-only JSON/Markdown remain separate from evidence comparison. Same IDs are recorded
keys, not semantic continuity; unknown provenance stays unknown. Exact saved-state and both snapshot
fingerprints plus deferred leases reject stale selections. No decision carry-forward, criteria
confirmation, analysis, storage mutation or gate change occurs. See the
[bounded assessment](docs/audits/2026-10-31-criteria-revision-changes.md).
This completes one requirements-inspection outcome; publication and Stage 3 retain separate gates.

The next owner-delegated gap review selected **find static references by source content before
choosing a line**. The existing chooser exposed line numbers before excerpts. Unreleased source
now supports literal, case-insensitive search across eligible lines of one explicitly selected,
already-ingested file. Counts and bounded 100-line physical-coordinate previews precede explicit
selection; no match selects nothing, and query/file/page/context changes clear dependent choices.
Existing eligibility, exact-head append checks, attribution, static/non-gating boundaries, record
v7 and frozen research remain unchanged. This is source navigation, not a retrieval algorithm or
repository-search claim. See the [bounded assessment](docs/audits/2026-10-31-source-reference-search.md).
This completes one source-selection outcome without a release, standing queue or Stage 3 advance.

The next owner-delegated gap review selected **headless retained-analysis handoff**. The local
workbench could inspect/export retained history, while CLI export required current criteria and
could not select a historical position. Unreleased source now provides a typed `history` metadata
catalog and explicit `export-history` JSON/Markdown with a mandatory saved-state fingerprint and
one-based position. Existing historical services recheck owner, full state and analysis identity;
the consumer lock covers rendering/publication. Pending criteria stay unconfirmed, missing
historical provenance still blocks full reports, output creation is atomic/no-overwrite, and saved
bytes, decisions and gates stay unchanged. See the [bounded handoff assessment](docs/audits/2026-10-31-cli-historical-analysis.md).
This completes one automatic-workflow outcome without publication, a standing queue or Stage 3 credit.

The following owner-delegated review selected **headless saved requirements-change handoff**.
After historical CLI export, scripts still could not explain the old-versus-current saved criteria
when evidence comparison correctly refused changed or pending requirements. Unreleased source now
adds `export-criteria-changes`, reusing the existing history catalog, explicit position/full-state
fingerprint, requirements-only services and JSON/Markdown policy. Missing provenance remains
unknown without relaxing full acceptance reports; pending criteria stay unconfirmed. Lock-bound
publication and atomic no-overwrite output preserve saved bytes, decisions and gates. See the
[bounded requirements handoff assessment](docs/audits/2026-10-31-cli-criteria-changes.md).
This finishes one selected script-recipient outcome, not an ongoing parity queue or Stage 3 claim.

The next owner-delegated review selected **recorded final acceptance in comparisons**. Existing
gate labels and criterion-decision context did not expose the recorded review-level flag; two
Conditional analyses can differ in acceptance. Unreleased source now adds separate typed
previous/current values with owning identities and derived change status to the workbench and
comparison JSON/Markdown. Older missing context remains unavailable. Analysis snapshots do not
retain acceptance actors, times, rationale or event association, so those stay explicitly unknown;
No is never translated into revoked or never accepted. Gates, decisions, v7 records and frozen
research remain unchanged. See the [bounded inspection assessment](docs/audits/2026-11-01-recorded-final-acceptance.md).
This completes one informational outcome without a release, standing queue or Stage 3 advance.

The next owner-delegated gap review selected **inspect loaded changes before a file-scope
decision**. The existing form showed names and prior decisions but no source beside its explicit
within/outside choice. Unreleased source now provides a source-bound, read-only diff preview with
base/head coordinates, rename metadata and bounded 100-record pages. Skipped/truncated or
ambiguous content remains unavailable; overlong records have explicit omissions. Switching files
clears dependent decision drafts, and review/source changes clear the target. Reopened records
without source retain explicit unavailability and the existing matching-source attachment path.
This changes no saved decision, citation, gate, record version or frozen research. See the
[bounded assessment](docs/audits/2026-11-01-scope-file-inspection.md). This completes a direct scope
inspection outcome, not a standing parity queue or evidence of genuine independent usefulness.

The next owner-delegated gap review selected **map one JUnit artifact to multiple criteria before
one import**. The prior workbench mapped every selected scope only to the inspected criterion,
while duplicate-artifact protection correctly prevented importing that report again. Unreleased
source now stages explicit target/scope choices, previews the canonical assignments and supports
criterion-group removal/clear before one unchanged lifecycle append. Complete review/artifact
binding expires stale choices, overlapping ownership is rejected without changing the prior
draft, and unsubmitted choices block Save. Existing parser, duplicate protection, saved imports,
record v7, gates, decisions, runtime truth and frozen research remain unchanged. See the
[bounded assessment](docs/audits/2026-11-01-junit-multi-criterion-draft.md). Saved-import correction
is a separate future lifecycle decision; this is one completed import outcome, not a standing
adapter/parity queue or genuine-use evidence.

The next owner-delegated gap review selected **readable decision-audit handoff**. Markdown
previously reduced resolution history to target/outcome/note, and HTML omitted that history.
Unreleased source now preserves recorded event IDs, asserted actors/times, revision and
Current/Superseded/Prior revision status, evidence declarations and runtime links in both readable
formats. Append order determines applicability; timestamp order does not. Bundle-only and retained
analysis exports explicitly lack complete event history, and no historical head/provenance or
acceptance-event association is inferred. Existing validation, JSON/CSV, record v7, gates,
decisions, runtime truth and frozen R-002 stay unchanged. See the
[bounded assessment](docs/audits/2026-11-01-readable-resolution-audit.md). This completes one report
recipient outcome, without a release, ongoing format-parity queue or Stage 3 credit.

The owner next selected **consistent workbench decision-audit display** for schema-valid mixed
legacy events. The workbench and readable reports now share the same target-based field projection:
review flags stay explicit `final_acceptance=true/false`, criterion decisions retain their own
meaning, and extra recorded fields are visible as not applied to that target. Event identity,
asserted metadata, missing/empty values and timezone uncertainty remain inspectable without
reinterpreting stored history. Append order and existing deterministic status classification stay
unchanged. The [bounded assessment](docs/audits/2026-11-01-workbench-resolution-audit.md) records
isolated AppTest and installed-browser verification, including reopening/download without record
writes. This closes the concrete display discrepancy found during PR #242; it does not create a
parity queue, new release, genuine-use evidence or Stage 3 advancement.

The next owner-delegated gap review selected **retire a mistaken saved JUnit import with audit**.
Two independent source assessments reproduced that saved imports lacked a recovery action, while
draft edits only affected unsaved mappings. Unreleased source now offers whole-import withdrawal
after source-free reopening and through fingerprint-bound CLI commands. Immutable original results
and mappings remain inspectable with asserted withdrawal attribution. Workbench, readable/JSON/CSV
reports and previous/current comparisons distinguish Active/Withdrawn; withdrawal is a recorded
context change, never deletion or new runtime evidence. Existing duplicate-artifact protection and
the20-retained-import limit remain; replacement, reactivation and same-byte remapping are excluded.
That withdrawal milestone introduced v8 with explicit bounded audit arrays and v1–7 read
compatibility without fabricated events. Decisions, final flags, gates and frozen research stay unchanged. See the
[bounded assessment](docs/audits/2026-11-01-junit-import-withdrawal.md). This closes one selected
recovery outcome, without a standing adapter queue, publication or Stage 3 credit.


The owner next selected **correct mistaken saved JUnit mappings with audit**, extending recovery
beyond whole-import withdrawal. Unreleased source retains the complete original import and appends
explicit replacement mapping snapshots in the same ordered audit stream. Source-free workbench
staging and fingerprint-bound CLI commands use confirmed criteria and retained cases, with explicit
whole-import confirmation. All consumers distinguish original/effective mappings and preserve
removed/intermediate-group audit; comparison detects mapping cycles as context changes. Gates,
runtime, recorded decisions/final flags, duplicate protection and frozen research stay unchanged.
Current saves use v9; v1–8 remain readable without invented correction events or load-time writes.
Twenty retained corrections per analysis are bounded separately from twenty imports/withdrawals,
so saturated correction history cannot prevent terminal withdrawal. The
[bounded assessment](docs/audits/2026-11-01-junit-mapping-correction.md) records migration,
consumer, installed and integration evidence. No reparse/replacement/reactivation, release,
qualifying-use evidence or Stage3 advancement is included.


The next owner-delegated gap review selected **continue a reopened review after confirmed criteria
edits**. Archiving the old analysis correctly removed its current verdict, but also disabled source
attachment and prevented fresh analysis in the same review. Unreleased source now supports an explicit
matching-source continuation for confirmed pending revisions, retaining the review ID, revised
criteria, old analyses and audit. Full-state/source leases and locked completion reject stale or
conflicting input. New analysis carries no prior manual/runtime/import context or acceptance; known
complete source and bounded recorded unchanged paths remain required. See the
[bounded assessment](docs/audits/2026-11-02-pending-analysis-continuation.md). Typed CLI criteria input
and portable record transfer were considered and deferred as distinct later outcomes. This closes one
existing lifecycle workflow without creating a parity queue, release or Stage3 credit.

The [automatic source-coordinate repair](docs/audits/2026-10-30-git-source-coordinates.md)
addresses the concrete non-LF separator defect found during M3 review. It corrects new automatic
references while preserving historical evidence and frozen research; it is bounded defect upkeep,
not a fourth product milestone or a retrieval-performance claim.

PR #197 owner workflow consolidation is complete: public PR and constructed-demo entry remain
clear, explicit criteria confirmation remains unmistakable, and stable unresolved-criteria queue
actions select the matching criterion. PR #198 adds blocker-first unresolved decisions and places
the selected criterion evidence and controls before the secondary evidence matrix. This bounded
Stage 2 follow-up preserves every evidence boundary and keeps optional external research
secondary.

The bounded JUnit adapter is the first implemented non-executing adapter. Its locally supplied
results remain exact-head/provenance-bound, separately rendered, explicitly mapped, and
non-gating. Coverage summaries, contract reports, deployment records, and other adapter families
remain separately scoped future decisions.

The 2026-10-26 changed-file scope integrity work on the unreleased `0.2.4.dev0` source carries an
exact-head inventory into the deterministic gate. An uncited inspected file stays unresolved until
an attributable reviewer decision explicitly places it outside confirmed criteria, while skipped
files remain partial and historical unknown inventories fail closed. The original constructed
scope-expansion label and frozen R-002 record remain unchanged. See the
[Stage 3 readiness assessment](docs/releases/2026-10-26-stage3-readiness-assessment.md) for the
engineering evidence boundary and missing independent-use gate.

The [Stage 2 productization packet](docs/commercialization/stage2-readiness-packet.md) is the
operating boundary. External commercial discovery is optional and separate from owner-led
productization. It is not required to continue Stage 2 and needs separate owner authorization
before outreach or participant contact.

Stage 2 status does not authorize a merge, release, tag, package publication, outreach, participant
contact, R-002 retuning, R-003 generation, billing, accounts, private-repository support, hosted
source processing, generic code review, security scanning, automatic fixes, or paid APIs. Existing
explicit merge authorization remains in force; Stage 2 status itself grants no new integration
authority. Deployment is also a separate owner decision.

The [30-day Design Partner Sprint](docs/commercialization/design-partner-sprint.md) is an optional
research protocol, not a productization gate. The
[market-positioning hypotheses](docs/commercialization/market-positioning-hypotheses.md) remain
unvalidated hypotheses unless genuine attributable evidence is later collected.

## Stage 3 — Limited beta

Status: dormant and gated by a separate owner decision after Stage 2 engineering evidence is reviewed.

The 2026-10-26 readiness assessment is an engineering review only. No genuine independent repeat
use has been observed, so Stage 3 has not started.

On 2026-10-27 the owner reaffirmed that qualifying participant reviews and personal product
testing are not being pursued. Automated reviewers, browser journeys, and constructed cases must
not stand in for independent use. Stage 3 therefore remains gated under the current direction;
do not initiate outreach, a beta, or a release to manufacture progress.

Stage 3 may define a bounded release candidate or beta only through a new owner-authorized plan.
Owner-led productization cannot be presented as customer validation, and no release, tag, or
publication is implied by Stage 2 progress.

Exit conditions:

- Repeat use occurs on a later PR without project-owner prompting.
- Reviewers can explain and act on candidate status without mistaking it for correctness.
- Re-review comparison is used to inspect a changed head rather than relying on stale evidence.
- Repeated friction is classified by source loading, criteria, coverage, decisions, export, or
  integration.
- Product changes are traceable to genuine observations and have regression coverage.
- Confirmed False Ready remains zero.

## Stage 4 — Evidence-guided expansion decision

Status: gated by a separate owner decision and evidence appropriate to the proposed expansion.

Only recurring behavior can justify broader scope. Candidate directions include clearer
requirements intake, better evidence explanations, and narrower collaboration handoffs. Private
repositories, billing, accounts, and paid LLM APIs require a separate owner decision and are not
implied by beta progress. Generic code review, security scanning, and auto-fix features remain
excluded under [AGENTS.md](AGENTS.md).

Stage 4 requires a named constraint, evidence appropriate to that constraint, and separate owner
approval. Missing external evidence remains missing; engineering work does not turn into customer
evidence.

## Honest stop and pivot rules

- Stop the current slice after its named reviewer outcome and required checks are complete.
  Select subsequent work from the bounded order above; do not invent a follow-up feature, repeat
  a closed investigation or rebuild the completed candidate merely because checks are green.
- Unsupported platform rows may remain unsupported; absence of an environment is not a mandate
  for repeated attempts or for personal testing.

- Do not create synthetic validation or present constructed fixtures as human validation;
  do not invent users and outcomes.
- Do not create recurring external-evidence monitors merely to manufacture activity.
- Do not execute pull-request code or promote implementation evidence to test or runtime proof.
- Do not weaken deterministic gates to improve apparent completion.
- Do not broaden the evaluation-only use policy without a new explicit owner decision.
- If optional genuine sessions occur, preserve negative and incomplete results without rewriting
  them as productization success.
