# ScopeProof Beta-Entry Activation Design

## Objective

Move ScopeProof from an engineering-complete public alpha to a state where a real participant can
complete a supervised public-PR trial with minimal ambiguity, while preserving the roadmap's two
external beta-entry gates: source-owner-confirmed criteria and a human-recorded outcome.

The implementation improves readiness for that evidence. It does not manufacture a participant,
publish a LinkedIn post, infer consent, or mark Stage 1 complete without a genuine case.

## Product boundaries

- Public GitHub pull requests only.
- No paid or LLM API, billing, private repository, organization, fork test, automated outreach,
  email, GitHub comment, synthetic participant, synthetic validation, or invented evidence.
- ScopeProof never executes pull-request code.
- Users explicitly confirm normalized acceptance criteria before analysis.
- Static implementation and test candidates never become runtime verification.
- The evaluation-only use policy and absence of an open-source license remain unchanged.
- No report, participant outcome, or quote is publishable without explicit consent recorded for
  that exact publication category.

## Delivery sequence

The work is split into three independently reviewable implementation plans and one external
closeout condition:

1. Alpha activation records and first-use onboarding.
2. Reproducible development environment with continuing newest-supported compatibility checks.
3. Free GitHub Pages presentation and a 60-second captioned constructed-demo video.
4. Issue #3 cleanup only after the LinkedIn post is genuinely public.

All repository changes travel through one protected pull request unless an external GitHub Pages
configuration step requires the merged workflow to exist first.

## Alpha participant kit

The repository gains four copy-ready participant documents:

- `docs/alpha/participant-quickstart.md`: a ten-minute sequence from qualification to outcome;
- `docs/alpha/public-pr-qualification-checklist.md`: public PR, source-owner authority, public
  requirements source, and no-confidential-information checks;
- `docs/alpha/acceptance-criteria-confirmation-template.md`: one atomic criterion per line plus an
  explicit confirmation statement;
- `docs/alpha/outcome-form.md`: exactly three primary outcomes: `found_useful_gap`,
  `showed_only_known_information`, and `created_friction`.

The documents never request names, email addresses, private source, credentials, customer data,
or confidential requirements. They distinguish a technical smoke from a confirmed dogfood case.

## Validated alpha-case domain

### Models

`scopeproof_core.alpha.models` defines Pydantic contracts independent of Streamlit:

- `ParticipantRole`: `product_manager`, `qa`, `engineering`, or `other`;
- `AlphaOutcome`: the three required outcomes;
- `AlphaFrictionStage`: `qualification`, `criteria`, `evidence`, `decisions`, `outcome`, `export`,
  or `integration`;
- `AlphaPublicationConsent`: separate report and quote booleans, both false by default;
- `AlphaCaseRecord`: public PR identity, public requirements source, source-owner-confirmed role,
  confirmed criteria, no-confidential-information literal, optional review linkage, optional
  outcome, consent, and timestamps;
- `AlphaCasePublicSummary`: a deliberately reduced export that contains no local notes or quote.

Every model uses `extra="forbid"`. The PR URL must match a public GitHub pull-request shape. The
requirements source must use HTTPS. Criteria must be non-empty, trimmed, unique, and atomic input
owned by the user. The schema contains no participant name, profile, email, or direct-message
field.

An outcome requires a real local review ID and a 40-character reviewed head SHA. A friction stage
is required only for `created_friction` and forbidden for the other outcomes. Completion time is
set only when an outcome is recorded. Report and quote consent remain independent.

### Service and storage

`scopeproof_core.alpha.service` creates immutable model updates for initialization and outcome
recording. It produces a public summary only when report publication consent is true; quote
consent alone is insufficient to publish the report.

`scopeproof_core.alpha.storage` stores one validated JSON object per case under
`.scopeproof/alpha-cases` by default. It follows the existing local review-store protections:
case IDs have a restricted shape, the root must be a regular directory rather than a symlink, all
loaded objects are revalidated, and writes refuse to overwrite an existing record unless the
operation is the explicit outcome update for the same case.

### CLI

The existing `scopeproof` CLI gains a nested `alpha` command:

```text
scopeproof alpha init
scopeproof alpha outcome
scopeproof alpha show
```

`init` requires a public PR URL, HTTPS requirements-source URL, participant role, one-criterion-
per-line file, and an explicit no-confidential-information flag. It stores the validated case and
prints Pydantic-validated JSON metadata.

`outcome` requires the case ID, real ScopeProof review ID, reviewed head SHA, one of the three
outcomes, and separate report/quote consent flags. Friction also requires a friction stage. It
updates only that case and preserves the qualification inputs.

`show` returns the full local record by default. `--public-summary` refuses unless report
publication consent is true and returns only `AlphaCasePublicSummary`. None of the commands contact
GitHub, publish content, send email, or emit comments.

## Guided real-public-PR onboarding

The local workbench retains the deliberately constructed demo path and adds a preflight panel for
the real public-PR path before ingestion. The preflight asks the reviewer to confirm:

1. the PR is public;
2. a source owner can confirm the criteria;
3. the requirements source is public HTTPS;
4. no confidential information will be entered.

The real public-alpha fetch button remains disabled until the PR URL and every preflight field are
valid. A separate technical-smoke choice remains available but is visibly labeled as not product
validation and does not satisfy Stage 1.

A stable progress cue is always visible:

```text
PR → Criteria → Evidence → Decisions → Outcome
```

The active stage is derived from session state rather than user-entered status. Criteria
confirmation receives an explicit source-owner confirmation cue. Finding guidance remains
non-prescriptive and is also rendered in a copyable code block for `Missing`, `Partial`, and
`Needs Review` findings. The Outcome stage links to the alpha quickstart and shows the exact local
CLI command pattern for recording one of the three outcomes after a review.

Qualification values remain session-only in the workbench. The optional local alpha-case record
is created by the CLI, preventing the Streamlit layer from becoming a second persistence system.

## Reproducible development environment

The repository gains `uv.lock`, generated with `uv 0.11.29`, and documents this known-good path:

```text
python3 -m pip install uv==0.11.29
uv sync --extra dev --locked
uv run python -m pytest -q
```

The lock is a reproducibility surface, not the only compatibility target. Existing Python 3.11
and Python 3.12 jobs continue installing the newest versions allowed by `pyproject.toml`. CI adds
a separate locked-environment job that installs exactly `uv==0.11.29`, verifies `uv.lock` is
unchanged, and runs repository contracts plus the deterministic benchmark. There is no schedule,
monitor, or notification workflow.

The known-good documentation records Streamlit 1.59.2 as the tested baseline and notes that 1.57.0
had a testing-interface regression. It does not claim all future versions are compatible.

## GitHub Pages presentation

### Static site

`site/` contains a dependency-free static page with:

- the narrow product question and evidence-assistant boundary;
- the deliberately constructed demo disclosure;
- a five-stage workflow matching the workbench;
- links to the v0.1.22 release, repository, participant quickstart, and LinkedIn DM call to action;
- the existing 1200x1200 alpha image;
- the 60-second captioned demo;
- a clear statement that likes, views, stars, and impressions are not product validation;
- no analytics, cookies, forms, trackers, remote fonts, customer logos, testimonials, or outcome
  claims.

The page is responsive, keyboard navigable, uses semantic HTML, has visible focus styles, and
respects reduced-motion preferences.

### Demo video

`site/assets/scopeproof-captioned-demo.mp4` is exactly 60 seconds, has no audio dependency, and
uses the deliberately constructed demo only. On-screen captions follow `docs/launch/demo-script.md`
and keep the required disclosure visible at the beginning and end. The video never shows private
tabs, tokens, local paths, participant data, or a real incident.

`site/assets/scopeproof-captioned-demo.vtt` contains equivalent captions for the HTML video
element. The page includes a poster image and a text transcript link.

### Deployment

`.github/workflows/pages.yml` deploys only `site/` on pushes to `main` and through a manual
dispatch. Every third-party Action is pinned to an immutable commit SHA. The workflow has only
`contents: read`, `pages: write`, and `id-token: write` permissions and does not run untrusted
repository code.

After merge, GitHub Pages is configured to use GitHub Actions and the repository homepage is set
to the resulting `https://yuzej21.github.io/Scope-Proof/` URL. This is a free public-repository
deployment and introduces no billing service.

## Feedback-channel cleanup

Issue #3 receives no further release comments. Once a genuine public LinkedIn post URL is known,
the owner-approved closeout is:

1. edit the issue body once to point to v0.1.22, the participant quickstart, and the public
   LinkedIn post;
2. close the issue without adding a new comment;
3. use LinkedIn DM as the only recruitment inbox.

If the LinkedIn post is not yet public, this external action remains pending. The repository must
not invent a LinkedIn URL or close the issue while claiming that the condition was satisfied.

## Verification and completion evidence

Completion requires all of the following:

- red/green unit tests for every alpha schema rule, storage operation, service transition, and CLI
  command;
- Streamlit AppTest coverage for preflight gating, technical-smoke labeling, progress, criteria
  confirmation, copyable next actions, and outcome guidance;
- repository contracts for participant documents, lockfile, known-good documentation, site copy,
  video/VTT duration and disclosure, Pages workflow pins, and no tracking scripts;
- original-resolution visual review of the landing page on desktop and mobile;
- rendered video inspection at beginning, middle, and end plus an automated 60-second duration
  check;
- full Ruff, pytest with at least 95 percent coverage, deterministic benchmark, dependency check,
  wheel install, CLI smoke, web health, and `git diff --check`;
- protected pull-request CI and CodeQL on the reviewed head SHA;
- successful Pages deployment from the exact merged main SHA;
- local and remote `main` equality and a clean worktree.

Stage 1 is not marked complete unless a genuine source owner confirms criteria and records a real
outcome. A successful implementation and Pages deployment prove readiness only.
