# Post-release truth, packaged-browser, and CLI lifecycle parity design

## Context and objective

ScopeProof v0.2.3 is publicly available from GitHub Release tag `v0.2.3`, and
`main`, the peeled tag, and the release integration merge all resolve to
`448c42758ea139bf9203cbf1bb04b02b02ae412c`. The current repository still has
three independent post-release gaps:

1. current-state documentation still describes PR #183 and its source merge as
   the final release boundary;
2. the packaged workbench has health and component-level coverage but lacks a
   durable real-browser primary-path regression; and
3. the CLI can create and export a review but cannot perform the reviewer
   lifecycle already supported by the core and workbench.

This slice aligns public truth, adds bounded packaged-browser evidence, and
exposes the existing lifecycle through a core-backed CLI. It must not alter
retrieval thresholds, evidence levels, gate precedence, alpha counts, the
evaluation-only license, or the prohibition on executing target-repository
code.

## Selected approach

Implement one protected `codex/*` pull request with four independently
reviewable tasks:

1. release-truth and public-intake alignment;
2. CLI lifecycle parity;
3. packaged-browser regression and an honest zoom evidence boundary; and
4. safe local worktree hygiene.

CLI parity is selected ahead of R-003 because it completes a real reviewer
workflow using already validated core transitions. R-003 remains design-only
and receives no cohort generation, label confirmation, scoring, or Stage 1
credit in this slice.

## Alternatives rejected

### Documentation and manual browser review only

This would remove stale copy but leave the CLI unable to record the decisions
needed to complete a review. It is too small to address the observed workflow
gap.

### R-003 before lifecycle parity

R-003 would add research coverage but stop at its separate human label gate. It
would not improve the user-facing review loop, so it remains deferred.

### Synthetic browser zoom presented as native zoom

CSS `zoom`, device-pixel-ratio changes, and viewport resizing are not browser
zoom. They must not be reported as 200% browser-zoom evidence. Automated tests
may cover responsive layout and keyboard operation; native 200% zoom is recorded
only when a controlled browser can expose and verify the real zoom state.

## Release-truth and public-intake alignment

Update current-state surfaces so they distinguish the published release from
historical engineering snapshots:

- `ROADMAP.md` names PR #184 and merge `448c42758ea139bf9203cbf1bb04b02b02ae412c`
  as the current main and v0.2.3 release baseline and lists exact-main CI,
  CodeQL, and Pages runs `30854382641`, `30854382413`, and `30854382659`.
- `docs/releases/v0.2.3-status-and-next-stages.md` records the same integration
  target, public tag, three published assets, and unchanged Stage 1 counts.
- `README.md` preserves PR #183 as historical source evidence but adds an
  explicit current release statement bound to PR #184 and the peeled tag.
- `site/index.html` changes `Check for release v0.2.3` to a direct, truthful
  `Download v0.2.3` action linked to the release page, not directly to an asset.
- Current-state contracts reject wording that makes PR #183 the present main or
  claims v0.2.3 is unpublished. Historical audit files retain their dated
  evidence and are not rewritten.

Issue #3 remains the passive inbound Alpha location. Its body is edited once to
name v0.2.3, link the current participant path, state that historical owner
comments are superseded, and retain the zero-validation boundary. No new issue
comment, email, DM, post, label change, recurring monitor, or participant claim
is created.

## CLI lifecycle parity

### Commands

Add four commands to `scopeproof_core.cli`:

1. `scopeproof resolve REVIEW_ID`
   - required: `--criterion-id`, `--decision`, `--reviewer`;
   - optional: `--comment-file`, `--evidence-url`;
   - allowed decisions exclude `manually_verified`, which belongs only to the
     atomic verification command;
   - the command loads one validated record, constructs a `ResolutionEvent`,
     calls `append_resolution`, atomically saves the validated state, and prints
     deterministic JSON metadata.

2. `scopeproof verify-runtime REVIEW_ID`
   - required: `--criterion-id`, `--level` (`E3` or `E4`), `--reviewer`,
     `--artifact-reference`, `--scenario`, `--environment`, `--result`, and
     `--comment-file`;
   - repeatable `--limitation` records bounded human limitations;
   - the command derives a new UUID, binds repository, PR, and head from the
     loaded review, constructs matching `RuntimeEvidence` and `ResolutionEvent`
     objects, calls `append_external_verification`, and saves only the resulting
     validated state;
   - no static evidence is promoted and no target code is run.

3. `scopeproof final-acceptance REVIEW_ID`
   - mutually exclusive required flags: `--accept` or `--revoke`;
   - required: `--reviewer`; optional: `--comment-file`;
   - `--accept` succeeds only through `append_resolution` and
     `can_record_final_acceptance`; `--revoke` appends a false final event;
   - failed prerequisites leave the saved record byte-for-byte unchanged.

4. `scopeproof compare PREVIOUS_REVIEW_ID CURRENT_REVIEW_ID`
   - `--format` is `json` or `markdown`, default `json`;
   - both reviews come from one `--storage-dir` and are fully validated;
   - the command calls `compare_reviews` and the existing validated comparison
     exporters;
   - optional `--output` refuses overwrite; without it the export is written to
     stdout;
   - comparison never copies a prior decision into the current review.

All mutation commands use the existing `--storage-dir` default
`.scopeproof/reviews`. Successful mutation output contains the review ID,
record path, current head SHA, event ID, gate verdict, and reason codes. Errors
remain bounded argparse errors without a traceback, and a failed command must
not partially persist an event or runtime record.

### Acceptance-note parity

The workbench currently requires a note when a reviewer accepts below the
criterion's required candidate-evidence level. Move that decision into one pure
core helper used by both the workbench and CLI. The helper never raises evidence
level or changes the gate; it only determines whether an attributable comment is
required. This prevents CLI operation from bypassing a workbench-only guard.

### Persistence and validation

Do not add a new record version. `ResolutionEvent`, `RuntimeEvidence`,
`ReviewState`, `ReviewBundle`, and comparison output remain Pydantic-validated.
`JsonReviewStore.save` remains the only persistence operation. Credentials,
tokens, target code, environment output, and private repository data are never
read or stored by these commands.

## Packaged-browser regression

Add Playwright as a development-only dependency and a `browser` pytest marker.
The package wheel must not gain a Playwright runtime dependency. A dedicated
test builds and installs the current wheel into a temporary environment, starts
`scopeproof-web` on loopback with a temporary `HOME`, and drives Chromium
against the installed application.

The durable browser path must:

1. load the deliberately constructed demo without GitHub networking;
2. reach confirmed criteria and run deterministic analysis;
3. expose criterion evidence, missing evidence, and the conservative summary;
4. confirm Markdown, JSON, and CSV export controls are reachable;
5. complete the primary controls with keyboard activation where Streamlit
   exposes stable accessible controls;
6. repeat at 1280x720 and 390x844 and assert document width does not exceed the
   viewport; and
7. fail on browser console errors or unhandled page errors.

The CI `verify` path installs the pinned Chromium version owned by the locked
Playwright dependency and runs the browser marker after the existing installed
wheel smoke. Third-party Actions remain SHA-pinned, no hosted browser service is
introduced, and the required `verify` context name is unchanged.

Native 200% browser zoom is a separate evidence row. If the available local
browser exposes a verifiable native zoom level, perform the same primary path
and record the exact environment and result in the audit. Otherwise keep the row
`unavailable`; responsive 640px or device-scale tests must not substitute for
native zoom. Screen-reader, Windows, Linux desktop, and Python 3.13 claims remain
unsupported unless those real environments are exercised.

## Safe local worktree hygiene

Cleanup is limited to registered project-local worktrees whose branch tips are
ancestors of current `main`, whose remote branch is gone, and whose
`git status --porcelain` is empty. For each eligible worktree, remove the
worktree normally, prune stale registrations, and delete the merged local branch
with non-force `git branch -d`.

Preserve without modification:

- the root `.coverage 2` file;
- the R-002 worktree containing `.coverage 2`;
- the re-review worktree containing `scopeproof_core/reviews/comparison 2.py`;
- every unmerged branch, including `codex/evidence-integrity-hotfix`; and
- the standalone nested `v023-post-merge-overnight` checkout, which is not a
  registered worktree owned by this cleanup.

No `git reset --hard`, `git clean`, force branch deletion, or bulk filesystem
deletion is allowed.

## Testing strategy

Every product behavior follows RED-GREEN TDD:

- repository contracts fail on stale current-release wording before docs are
  changed;
- focused CLI tests fail because each new command is absent, then cover success,
  malformed inputs, atomic failure, no-overwrite output, and fail-closed gate
  behavior;
- the acceptance-note core helper is tested before moving the UI decision;
- browser contracts fail before the Playwright harness and CI steps exist;
- existing lifecycle, storage, export, Streamlit, CLI, benchmark, and release
  contracts remain green.

Before integration run the locked environment, Ruff, the full coverage gate,
both deterministic benchmarks, repository contracts, build, installed-wheel
smoke, and the packaged-browser regression. A reviewer must inspect the complete
diff before the pull request is merged. The resulting `main` SHA must then pass
required `verify`, CodeQL, and Pages checks.

## Evidence and product boundaries

- This work creates engineering evidence only and adds zero Stage 1 credit.
- Stage 1 remains 0/5 qualifying reviews, 0/3 practitioners, 0/3 repositories,
  0/3 independently observed under-ten-minute completions, and 0/2 reuse-intent
  signals.
- No paid API, LLM verdict, account, billing, private repository, fork test,
  telemetry, generic code review, security scan, automatic fix, synthetic user,
  or invented validation is added.
- The GitHub Action remains advanced and informational; this slice does not
  promote it to a required product check.
- Candidate evidence remains evidence for inspection, never proof of
  correctness, test execution, runtime behavior, or acceptance.
