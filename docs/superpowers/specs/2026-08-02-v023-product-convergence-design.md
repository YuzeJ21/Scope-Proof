# ScopeProof v0.2.3 Product Convergence Design

Date: 2026-08-02
Status: approved for implementation by the owner request to follow the latest roadmap,
fix the known product issues, clean the product pages, and merge the resulting version to
`main`.

## Context

The current `main` is a strong Stage 0 engineering alpha. Its deterministic evidence
engine, exact-head runtime-evidence integrity, five-step workbench, local persistence,
exports, benchmarks, packaging checks, and public Pages site are already implemented.
The full current test baseline is 1,753 passing tests with one intentional skip.

The remaining work is not a frontend rewrite and it cannot manufacture Stage 1 product
validation. The audited product issues in scope are:

1. the local workbench still looks and feels like a default, dense Streamlit utility;
2. optional matrix filters occupy primary space before a reviewer asks for them;
3. the public-alpha page presents five equal-weight actions instead of one clear path;
4. confirmation records the copied requirements text, but not a deterministic identity for
   the source snapshot, its confirmer, or its confirmation time;
5. the copyable GitHub Action is pinned before the latest exact-head integrity repair; and
6. the v0.2.3 status documents still describe the already-merged alignment PR as future work.

The public release remains v0.2.1. This design prepares and merges the latest v0.2.3 source
to `main`; it does not create a tag or GitHub Release. Publication still requires exact
release-tree assets, checksums, and a separate publication decision.

## Product boundary

ScopeProof remains an evidence assistant, not a correctness oracle.

- Candidate implementation or test references never become runtime verification.
- The application never executes untrusted repository code.
- Criteria still require explicit human confirmation before analysis.
- Gates remain deterministic and fail closed; False Ready remains the higher-cost error.
- Legacy records remain readable, but missing source provenance cannot newly support
  `Ready`.
- No paid API, account, billing, private-repository, generic code-review, security-scanning,
  auto-fix, outreach, notification, or fork-testing capability is added.
- Engineering and constructed evidence created by this work contributes zero Stage 1 credit.

## Chosen approach

Use one coordinated, reviewable convergence branch with three independently tested slices:

1. a restrained visual and information-hierarchy cleanup;
2. deterministic criteria-source snapshot provenance; and
3. release/documentation alignment.

The existing five-step workflow and widget identities remain stable. The implementation
uses Streamlit's supported theme configuration plus a small documented presentation layer;
it does not replace the application framework or couple the core engine to Streamlit.

## Slice 1: product-page cleanup

### Workbench visual system

Align the local workbench with the existing public Pages palette:

- background `#0d0f12`;
- secondary surface `#171a1f`;
- text `#f7f7f2`;
- primary lime `#d8ff63`;
- secondary cyan `#8cecff`;
- warning orange `#ffad66`.

The packaged launcher passes supported Streamlit theme settings so an installed
`scopeproof-web` session has the same visual system regardless of the caller's working
directory. A repository `.streamlit/config.toml` supplies the same defaults for the
documented source-development command.

The existing accessibility focus ring remains visible. A bounded CSS layer improves the
main content width, vertical rhythm, headings, expanders, buttons, and status panels. It
must not hide Streamlit controls, evidence warnings, gate reasons, or mobile content. It
must respect reduced-motion preferences and retain readable contrast.

### Workbench hierarchy

The four evidence-matrix filters retain their current keys, defaults, options, and
behavior, but move into one collapsed expander labelled `Filter evidence matrix
(optional)`. CI limitations and all fail-closed warnings remain visible above it.

No confirmation, evidence, decision, external-verification, persistence, or export field is
removed merely for appearance. Necessary evidence inputs stay available; secondary and
advanced controls are progressively disclosed.

### Public Pages hierarchy

The public-alpha card retains every current URL and safety boundary, but presents:

1. one primary action: `Submit a public alpha case`;
2. one secondary action: `Open the ten-minute quickstart`; and
3. three visibly tertiary, inline resources for qualification, research/stop gates, and the
   post-review outcome form.

The no-private-code/credentials/confidential-information boundary remains immediately
adjacent to the primary path. The completed-outcome link is explicitly labelled as a
post-review resource.

## Slice 2: criteria-source snapshot provenance

### Model

Add one immutable Pydantic `CriteriaSourceProvenance` object containing:

- `source_uri`: a bounded, non-blank source reference;
- `source_revision`: an optional non-blank human-supplied revision identifier;
- `source_text_sha256`: the lowercase SHA-256 of the exact confirmed source text;
- `normalized_criteria_sha256`: the lowercase SHA-256 of the canonical confirmed criterion
  payload;
- `confirmed_by`: a non-blank human attribution; and
- `confirmed_at`: a timezone-aware timestamp normalized to UTC.

`source_uri` accepts a public HTTPS source or one explicit built-in ScopeProof URI for the
constructed demo. Normal standard reviews require the reviewer to identify the requirements
source; ScopeProof does not guess it from the PR URL. `source_revision` is optional because
the exact source-text digest is always present. The model is frozen and rejects extra fields.

Pure core helpers compute and validate both digests without network access. A changed source
text, changed normalized criteria, or mismatched observed revision invalidates the snapshot
with a stable error. This is capture-time staleness detection, not live monitoring of a
remote page.

### Lifecycle

The active `Review` and `CriteriaRevision` carry the same provenance object.

- New analysis bundles require a validated provenance snapshot.
- Revising criteria clears active confirmation and its provenance.
- Confirming a pending revision requires a newly created provenance snapshot.
- Attaching analysis requires exact provenance equality between the active revision and the
  bundle's review.
- Final acceptance is unavailable when provenance is absent or inconsistent.
- Comparison and changed-head re-review preserve historical provenance while the new review
  must reconfirm the current source snapshot.

The deterministic gate adds the stable reason code
`criteria_source_provenance_missing`. Missing provenance forces `Needs Review`; it can
never support `Ready`. A changed or contradictory source snapshot is rejected at the typed
validation or lifecycle boundary before a gate can be created, using a stable source-mismatch
error; ScopeProof does not persist a knowingly stale snapshot merely to attach a verdict to it.

### Legacy records

The local record format advances from version 3 to version 4. Versions 1–3 remain loadable.
Migration never invents a URL, digest, confirmer, revision, or timestamp. Legacy active and
historical bundles retain their original evidence and decisions, but their gates are
recomputed with missing provenance and therefore cannot be treated as current `Ready`
evidence. Reconfirmation and reanalysis are required before a new final acceptance or
export intended as a current review.

The user-facing reopen state explains this boundary rather than silently changing the old
facts.

### Workbench interaction

At criteria confirmation, show a compact `Criteria source` block:

- source URL/reference;
- optional source revision;
- confirmer name.

The exact text and normalized-criteria hashes plus confirmation time are computed, displayed
after confirmation, persisted, and included in exports. The deliberately constructed demo
preloads its checked-in demo source URI. Alpha mode reuses its already-qualified public
requirements URL rather than asking for it twice. Changing requirements, criteria, source
identity, revision, or confirmer invalidates prepared confirmation and requires explicit
reconfirmation.

### CLI and Action boundaries

The CLI review path may not silently manufacture confirmation. `scopeproof review` requires a
validated confirmation JSON file and passes the resulting provenance into the review bundle.
The existing validation command remains available and its confirmation schema gains source
identity plus the normalized criteria digest.

The trusted-base Action validates the checked-in requirements and confirmation artifacts,
then passes the validated provenance to the review command. It does not check out or execute
PR-head code. The Action stays informational and non-required.

### Exports and alpha records

JSON receives the typed fields from the model. Markdown and HTML show a compact criteria-source
table. CSV repeats the provenance columns on each criterion row. Every exporter revalidates
the object and refuses missing or contradictory current provenance.

New alpha case records reuse the same provenance and require its public source URI to match
the qualified requirements URL. Historical alpha records remain readable as legacy evidence
but cannot be newly completed as a qualifying outcome until their criteria are reconfirmed.

## Slice 3: release and roadmap alignment

Update the copyable Action's source pin and guide from the pre-integrity commit to the latest
verified merged product commit available before this branch. A repository contract keeps the
workflow pin and guide synchronized. After this convergence branch merges, a later release
publication must repin to the exact final release tree if that tree differs.

Update the v0.2.3 status, internal-candidate, post-merge readiness, and PR review-map documents
to record PR #181 and merge `eaa66c5979e2a71769d58f0699537da474094d06` as completed history.
Do not describe its docs tree as package or release-asset evidence.

The roadmap records this convergence work as engineering maturity with zero Stage 1 credit.
The next executable queue remains honest:

1. merge and verify this branch;
2. keep v0.2.3 publication separately gated;
3. run supported accessibility/platform checks when trustworthy tooling is available;
4. passively accept genuine Stage 1 cases without outreach or recurring monitoring; and
5. begin Stages 2–4 only when their evidence gates actually pass.

README, Pages, and quickstart continue pointing public installers to v0.2.1 until a real
v0.2.3 GitHub Release exists.

## Error handling

- Invalid provenance input does not mutate the active review.
- Digest or source mismatch produces a concise stable recovery message and leaves analysis
  disabled.
- CLI and Action failures return non-zero without publishing a misleading verdict.
- Legacy record migration is deterministic, idempotent, and never invents provenance.
- UI styling failures cannot affect core evaluation; no gate depends on CSS or presentation.

## Verification strategy

Implementation follows strict red-green-refactor cycles.

Required focused coverage includes:

- theme launcher/config contracts and preserved visible focus treatment;
- collapsed matrix-filter behavior with all existing widget keys and values;
- public Pages action hierarchy with all links and safety copy preserved;
- provenance model validation and deterministic digest helpers;
- lifecycle creation, revision, confirmation, analysis attachment, and final-acceptance guards;
- deterministic gate reason codes and no-provenance False Ready prevention;
- v1–v3 conservative migration and v4 round trip;
- CLI and Action propagation without target-code execution;
- JSON, Markdown, CSV, and HTML provenance plus tamper rejection;
- Streamlit source-input, confirmation invalidation, reopen, and alpha reuse behavior; and
- alpha-record compatibility and provenance matching.

Before integration, run formatting/lint, the complete locked test suite, both deterministic
benchmarks, build and clean-install checks, workbench health, repository contracts, diff checks,
and browser-based visual review at desktop and narrow viewport where the available browser can
produce trustworthy evidence. All claims remain classified as engineering evidence.

## Success criteria

This design is complete when:

1. reviewers see a coherent modern visual system across Pages and the local workbench;
2. optional controls no longer dominate the primary review path;
3. every new confirmed review has immutable source-snapshot provenance;
4. missing or changed source provenance cannot produce `Ready` or final acceptance;
5. provenance survives persistence, comparison, alpha qualification, CLI/Action flow, and every
   export without invention;
6. Action and release-status documentation reflect current merged truth;
7. the full verification matrix is green on the exact branch head;
8. the PR passes required GitHub checks and review; and
9. the branch is merged to protected `main`, with merged-main checks verified.

Stage 1 remains zero unless genuine non-owner evidence independently arrives.
