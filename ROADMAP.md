# ScopeProof Roadmap

ScopeProof is a reviewer-first public-repository evidence assistant. The deterministic engine,
local workbench, CLI, exports, benchmark, packaging, and protected CI are engineering evidence only.
They do not prove
runtime correctness, adoption, or beta readiness.

This roadmap separates owner-led productization from external validation. Stage 1 is
`closed_not_pursued_by_owner` with all external-evidence counts at zero. Stage 2 is
`owner_led_productization_active`, following a short, outcome-driven development queue;
this owner decision does not create customer validation. Stage 3 is dormant and gated.
The owner is not pursuing personal testing or qualifying participant reviews.

## Current priorities — 2026-11-04

The product direction is **explain and revisit an acceptance decision**. Confirmed intent,
exact-head evidence, explicit gaps, recorded decisions and later comparison form the working
product; acceptance checking alone is not distinctive. The [current product and market decision](docs/commercialization/product-direction-2026-11-02.md)
documents direct overlap and adoption constraints without claiming superiority or demand.

| Stage and order | Concrete outcome | Finish line or boundary |
| --- | --- | --- |
| Stage 2 — completed on source | Carry complete normalized criteria from preparation into an automated CLI review without rebuilding intent. | Source-bound editable draft; explicit confirmation; stable IDs/order/priority/type/source metadata and required evidence levels; malformed/stale rejection before ingestion/writes; automated and independent agent review plus exact-head CI. See the [bounded assessment](docs/audits/2026-11-02-typed-criteria-handoff.md). |
| Stage 2 — completed on source | A recipient can transfer and safely reopen a saved review through supported CLI controls and the existing workbench. | Preserve complete record bytes, history and provenance; validate versions and gates; bounded regular files; atomic no-overwrite import under the original ID; installed reopening and independent automated review. See the [transfer assessment](docs/audits/2026-11-02-saved-review-transfer.md). |
| Stage 2 — completed on source, PR #250 | Complete sender-to-recipient saved-review handoff entirely in the local workbench. | Explicit saved-record download, upload inspection, byte-bound consent/import and existing guarded reopen; original history/provenance preserved, collisions and stale callbacks rejected. See the [workbench handoff assessment](docs/audits/2026-11-02-workbench-review-handoff.md). |
| Stage 2 — completed, PR #251 | Make the accumulated workflow coherent to evaluate. | One [evaluation entry](docs/evaluation-guide.md) with the release/source version map and a constructed handoff. |
| P0 — private distribution verified at `6b39fb4` | Package the accumulated reviewer workflow and verify an upgrade from the public writer. | Matching direct and source-built wheel bytes, isolated installs, artifact hashes and a constructed native v5-to-v9 upgrade on copies. Each packet names its source commit. |
| P1 — workbench folder selection on source | Run sender and recipient workbenches on one computer using separate review folders. | Explicit launch option, visible selected folder and installed browser handoff with both instances under one OS account. |
| P2 — publication, gated | Decide whether to distribute a new evaluation download. | Choose one reviewed artifact set and authorize publication before creating a tag or release. Public v0.2.4 remains available. |
| P3 — Stage 3 dormant | Determine whether independent practitioners find the acceptance handoff useful and reuse it. | Genuine independent-use evidence and separate authorization. |

No additional adapter family, accounts, hosted processing, billing or generic code review is
needed for the selected outcome. Public-only scope, evaluation-only licensing, local setup,
asserted actor identity and unknown independent usefulness remain material constraints.

Further feature work needs a named observable constraint and a bounded finish line. The
evaluation walkthrough identified the single-account storage constraint. The distribution
packet addresses the gap between the published download and the current reviewer workflow.

The dated implementation notes below preserve prior milestone context. This priority table is
the next-stage decision; those notes are not an instruction to reopen completed work or grow
an endless format-parity queue.

## Current operating decision

**v0.2.4 is published as a downloadable evaluation release.** Its public wheel, source archive
and checksums were automatically verified. The [dated public verification record](docs/releases/v0.2.4-public-verification.md)
binds those results to release source `11bcdc66f7d8f5a29055688208de1ed337eed07f`.
Current source/package identity is unreleased `0.2.5`.
[PR #221](https://github.com/YuzeJ21/Scope-Proof/pull/221) completed private candidate preparation:
direct/source-built distribution checks, isolated installs, a constructed native v0.2.4 review
upgrade, and an exact-main packet at `4f12ae02dee277705d17ac6ab94f0a74f99be346`.
The [candidate guide](docs/releases/v0.2.5-evaluation-candidate.md) retains the separate publication
gate. Those private archives and their original source binding remain unchanged; later development
does not update their evidence or trigger another candidate-preparation cycle or publication.
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
that incompatible older combination. PR #219 integrated the unreleased upload repair, letting the
full-size artifact reach the unchanged fail-closed parser limit, with unit and installed-browser
regressions. The [source declaration alignment](docs/audits/2026-10-29-dependency-baseline-alignment.md)
now enforces the maintained Pydantic, Streamlit and direct Pillow floors, retaining all resolved
lock versions. These are verified baseline choices, not proven earliest compatible versions.
The older-stack
browser observation remains partial because its saved-review selector differs from the current
test helper; it is not a full compatibility pass. The upload, dependency, CI and candidate
preparation questions are closed. The next work improves the existing reviewer workflow through
the [ordered Stage 2 milestones](#stage-2--owner-led-productization). This is evaluation
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
ScopeProof v0.2.4 is published. Public install: v0.2.4 is available from the
[v0.2.4 GitHub Release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.4),
which provides the wheel, source archive, and checksum manifest.

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

Current product, gap, and next-stage details are maintained in the
[v0.2.3 status audit](docs/releases/v0.2.3-status-and-next-stages.md). Current official-source
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

- Do not create synthetic validation, invented users, or constructed outcomes.
- Do not create recurring external-evidence monitors merely to manufacture activity.
- Do not execute pull-request code or promote implementation evidence to test or runtime proof.
- Do not weaken deterministic gates to improve apparent completion.
- Do not broaden the evaluation-only use policy without a new explicit owner decision.
- If optional genuine sessions occur, preserve negative and incomplete results without rewriting
  them as productization success.
