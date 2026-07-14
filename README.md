# ScopeProof

**Prove the PR matches the product intent.**

ScopeProof reviews a public GitHub pull request against user-confirmed product requirements. It maps each atomic acceptance criterion to auditable code and test candidates, makes missing or partial evidence visible, records human decisions, and produces a deterministic release recommendation.

ScopeProof is an evidence assistant. It does not replace QA, engineering review, runtime testing, or human acceptance.

## Why this exists

AI coding agents can produce pull requests quickly, but a green CI check does not establish that every ticket promise was implemented. Product reviewers still need to answer questions such as:

- Did export include every active filter?
- Is the failure state visible to the user?
- Was the required analytics event added?
- Does a test exercise the requested behavior, or does a similarly named test merely exist?
- Did the pull request expand scope beyond the approved requirement?

ScopeProof turns that review into a requirement-to-evidence matrix. It shows why each candidate matched and what remains unverified.

## MVP boundaries

- No paid LLM API and no model-generated verdicts.
- Supports public repositories only.
- Anonymous GitHub access works without a token.
- An optional GitHub token can increase free rate limits; it remains in Streamlit session memory and is never exported or saved.
- Users author and confirm criteria. ScopeProof does not invent product requirements.
- Pull-request code is never executed.
- Static candidates cannot be presented as runtime verification.
- General bug review, security scanning, automatic fixes, private repositories, Jira, billing, and team accounts are outside this release.

## Evidence and verdict language

| Level | Meaning in this MVP |
|---|---|
| E0 | No candidate evidence found |
| E1 | Candidate implementation or contract evidence |
| E2 | Candidate test evidence that still requires reviewer confirmation |
| E3 | Runtime verification recorded manually from an external check |
| E4 | Explicit human acceptance |

Criterion findings are `Evidence Found`, `Partial`, `Missing`, or `Needs Review`. These are provisional findings, not correctness claims.

The release gate uses explicit precedence:

1. `Blocked` for failed checks, change-required decisions, or unresolved must-have gaps.
2. `Needs Review` for unconfirmed criteria, partial ingestion, unavailable checks, ambiguous evidence, or unresolved required decisions.
3. `Conditional` for resolved must-haves with should-have gaps or accepted exceptions.
4. `Ready` only after all requirements, checks, ingestion, resolution, and final human-acceptance conditions are met.

## Quickstart

Python 3.11 or newer is required.

Install the verified v0.1.16 release wheel in an isolated environment. This path does not require
cloning the repository.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install \
  https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.1.16/scopeproof-0.1.16-py3-none-any.whl
scopeproof benchmark
scopeproof-web --host 127.0.0.1 --port 8501
```

To verify the release bytes before installation, download the wheel and its checksum:

```bash
curl -LO https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.1.16/scopeproof-0.1.16-py3-none-any.whl
curl -LO https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.1.16/scopeproof-0.1.16-py3-none-any.whl.sha256
```

Use the command for your platform, then install the verified local file:

```bash
# macOS
shasum -a 256 -c scopeproof-0.1.16-py3-none-any.whl.sha256

# Linux
sha256sum -c scopeproof-0.1.16-py3-none-any.whl.sha256

python -m pip install ./scopeproof-0.1.16-py3-none-any.whl
```

A matching checksum verifies the downloaded bytes against the digest published with this release.
It does not provide code-signing or product-correctness assurance.

The offline benchmark verifies that the installed package and bundled regression corpus execute.
It is not runtime evidence for any pull request. `scopeproof-web` starts the packaged local
workbench; stop it with `Ctrl+C`. Continue with the public-PR CLI workflow below to review
reviewer-confirmed criteria against a real public PR.

### Public PR CLI workflow

After installation, the CLI provides the same read-only public-PR ingestion and deterministic
core without starting Streamlit. First create `requirements.txt` with one atomic criterion per
line. Every line must contain reviewer-confirmed criteria; running the command is an explicit
confirmation that this normalized set is ready for analysis.

```bash
scopeproof review --pr https://github.com/OWNER/REPOSITORY/pull/123 \
  --requirements requirements.txt \
  --storage-dir .scopeproof/reviews \
  --report scopeproof-review.md
```

The command prints JSON containing the local `review_id`, record path, head SHA, and provisional
gate verdict, plus the requested report path. ScopeProof refuses to overwrite an existing report.
Use the review identifier later to repeat the export or choose another format:

```bash
scopeproof export REVIEW_ID \
  --storage-dir .scopeproof/reviews \
  --format markdown
```

Anonymous public-repository access is the default. `--token` is optional and can increase GitHub's
free rate limit, but it is not required or persisted. The CLI never comments on the pull request,
executes its code, or converts static candidates into runtime verification.

## Contributor setup

Clone the repository to run the Streamlit workbench or contribute changes:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run apps/web/app.py
```

Open the displayed local URL, then choose either path:

1. Select **Load deliberately constructed demo** for a complete offline walkthrough.
2. Enter a public GitHub PR URL, optionally add a token, fetch the PR, paste one criterion per line, and confirm the criteria.

The five review steps are:

1. Start Review.
2. Confirm Criteria.
3. Evidence Matrix.
4. Criterion Detail and human resolution.
5. Summary and Markdown, JSON, or CSV export.

### Durable local review workflow

The workbench keeps criteria revisions and append-only resolution history. Adding, removing,
splitting, reordering, or editing criteria invalidates the previous analysis and requires explicit
reconfirmation before another review run. Human decisions and final acceptance are recorded as
history rather than silently replacing earlier decisions.

### Local review storage

The workbench stores versioned JSON records under `~/.scopeproof/reviews`. The reopen panel lists
safe local record IDs in deterministic order, while an empty store retains manual ID recovery.
The app validates the selected record when it is opened and refuses a configured review path that
is a symbolic link or another existing non-directory. This app-owned local directory prevents a
browser input from selecting arbitrary file paths. Records preserve the review SHAs, criteria
revisions, evidence, findings, resolution history, and gate decision. They never contain the
optional GitHub token. A reopened review reports a changed head SHA rather than silently reusing
old evidence.

## Deliberately constructed demo

The bundled CSV export case is a deliberately constructed demo, not a real incident. Its PR-shaped fixture implements CSV export, one active filter, and a happy-path test. It intentionally omits another filter, the error state, and the `research_exported` event.

Expected output:

| Criterion | Expected finding |
|---|---|
| AC-01 Export CSV | Evidence Found |
| AC-02 Respect all active filters | Partial |
| AC-03 Show export failure | Missing |
| AC-04 Record `research_exported` | Missing |

The deterministic gate is `Blocked` because must-have gaps remain.

## Verification

Run lint and all offline tests:

```bash
python -m ruff check .
python -m pytest -q
```

Run the labeled regression benchmark:

```bash
python -m scopeproof_core.evals.runner
```

The benchmark executes 12 executable benchmark cases, rather than treating a static category list
as coverage. It reports executed case and criterion counts, False Ready, False Blocker,
case-level mismatches, immutable evidence-link errors, and unexecuted required categories. It exits
nonzero when a known must-have False Ready, label mismatch, evidence-link error, or unexecuted
category is present.

Run the opt-in live public GitHub smoke test:

```bash
RUN_LIVE_GITHUB_TESTS=1 python -m pytest tests/github/test_live_public_pr.py -q
```

Check the running Streamlit server:

```bash
curl --fail http://127.0.0.1:8501/_stcore/health
```

## Architecture

```text
Public GitHub PR
      ↓
Read-only ingestion
      ↓
User-confirmed criteria
      ↓
Deterministic candidate retrieval
      ↓
Provisional findings + human resolution
      ↓
Deterministic gate
      ↓
Markdown / JSON / CSV
```

`scopeproof_core` contains Pydantic contracts, ingestion, retrieval, verification, gates, reporting, fixtures, and evaluation. It has no Streamlit dependency. `apps/web/app.py` is a thin local interface over those core services.

Every evidence item contains a file, line, immutable head SHA, GitHub permalink, excerpt, matching rule, relevance reason, deterministic score, and limitations. Deleted lines cannot become current implementation evidence. Partial ingestion cannot produce Ready.

GitHub file and commit ingestion follows pagination and has explicit file, patch, and total-diff
limits. ScopeProof can also inspect a bounded unchanged candidate file when a caller explicitly
justifies it. This evidence is labeled `unchanged_candidate`, anchored to the head SHA, and never
means that the repository was scanned broadly.

## Repository layout

```text
apps/web/                 Streamlit review workbench
scopeproof_core/github/   Public GitHub ingestion
scopeproof_core/criteria/ Manual criterion preparation
scopeproof_core/retrieval/Deterministic evidence candidates
scopeproof_core/verification/Provisional findings
scopeproof_core/gates/    Release truth table
scopeproof_core/reporting/Markdown, JSON, and CSV exports
scopeproof_core/evals/    Regression runner
evals/                    Controlled fixtures and labels
tests/                    Unit, regression, AppTest, and live smoke tests
```

## Privacy and trust

The application does not persist credentials or execute repository code. Review exports contain the repository, PR number, head SHA, ruleset version, criteria, evidence, findings, resolutions, and gate reasons. They do not contain the optional GitHub token.

Large or truncated diffs are labeled partial and force human review. Missing GitHub checks are represented as unavailable, never passing. A parser or retrieval failure must fail safely rather than produce Ready.

The [privacy-readiness design](docs/privacy-readiness.md) documents current
local-only retention, deletion responsibility, fork protection, and the future
read-only private-repository boundary. It does not claim private support exists.

## Product status

This is a public-repository MVP for validating the requirement-to-evidence workflow. The next product decision should be based on repeat use with real pull requests and confirmed gaps found before merge—not the number of files scanned or comments generated.

For safe public-alpha operations, see the [public PR dogfood protocol](docs/dogfood/public-pr-protocol.md) and the [60-second demo script](docs/launch/demo-script.md). The protocol distinguishes deliberately constructed demos, technical smokes, and confirmed dogfood reviews so launch material does not overclaim validation.

The [launch evidence matrix](docs/launch/evidence-matrix.md) and
[review-before-posting LinkedIn draft](docs/launch/linkedin-draft.md) keep the
constructed-demo and technical-smoke boundaries explicit.

## GitHub Actions safe preview

The checked-in [GitHub Actions guide](docs/github-action.md) explains the local
starter workflow. It is non-blocking by default, needs an explicit checked-in
requirements file plus a hash-bound confirmation, runs the trusted base-branch
workflow through `pull_request_target`, and permits a scoped, idempotent
informational comment only for non-fork PRs with confirmed requirements. It
never checks out or executes pull-request head code. Its publication policy is
fixture-tested locally.

Use the [external validation runbook](docs/github-action-external-validation.md)
only in an authorized public demo repository. It records exact non-fork and
same-head rerun evidence before claiming a real Action run. Fork testing is
permanently excluded for this single-account public alpha; fork-safety remains
covered by local fixture tests without any external fork-run claim.

## Confirmed-action validation revision

This same-repository pull request validates that the current base branch's
hash-bound requirements confirmation controls ScopeProof's informational
publication.

The pinned-action technical smoke verifies that the safe-preview workflow uses
immutable third-party Action revisions without changing its non-blocking,
informational review boundary.

The Node-24 action smoke validates the upgraded immutable dependency revisions
through the same public, trusted-base workflow path.

## Explicit local Definition-of-Done packs

`scopeproof_core.rule_packs` offers opt-in local prompts for error, loading,
empty, analytics, authorization, API documentation, and migration coverage.
They are never inferred or added to a review automatically. Each is labelled
`Implicit local rule` and has an `implicit_rule_pack` source so it cannot
masquerade as a user-confirmed source requirement; a reviewer must explicitly
include and confirm it before analysis.

## Evidence-quality metrics

`scopeproof benchmark` emits `evidence_quality_metrics` alongside its executed
fixture results: immutable evidence-link precision, incorrect-line-citation
rate, criterion agreement, and False Ready/False Blocker totals. These measure
only the checked-in, executed labels; they do not prove runtime correctness or
market validation. Human override, accepted-exception, and unresolved-ambiguity
rates are intentionally `null` unless calculated from selected persisted review
histories.
