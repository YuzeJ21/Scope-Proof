# Microsoft R-001 Evidence-Quality Design

## Problem

The first ScopeProof public engineering research case, Microsoft `hve-core` issue 2148 and pull
request 2149 at head `8e5277e88f0ca650549d41255eb24d74afc74772`, exposed two product defects.
GitHub's empty combined-status response reports `pending` even when it contains no statuses, so it
can incorrectly override completed successful check runs. Candidate selection also takes the first
eight globally ranked line matches, allowing one high-volume documentation file to hide a relevant
test or eval definition.

The case remains blocked because candidate evidence and observed CI do not replace runtime
verification or human acceptance. It is public engineering research, not an Alpha participant,
customer, or Stage 1 result.

## Chosen approach

Use three small, independent core changes:

1. Aggregate GitHub checks from real observations. Failure wins, then real pending observations,
   then successful completed runs, otherwise unavailable. An empty legacy `pending` aggregate has
   no authority. Persist a validated CI summary containing the deterministic reason, counts, and
   skipped check names so reports can explain the state and explicitly show skipped execution.
2. Classify changed test and eval definitions as E2 test-intent candidates and select evidence with
   a deterministic diversity-first pass. The best relevant candidate from each represented static
   evidence type is selected before remaining slots are filled by the existing global rank. Existing
   matching thresholds, the eight-item bound, immutable links, and gate rules do not change.
3. Add an optional validated research-case context to the review bundle. When present, exports,
   CLI metadata, and Streamlit state identify the case as engineering research with zero Stage 1
   credit. Ordinary reviews remain unchanged.

Existing manually recorded `RuntimeEvidence` remains the only E3/E4 path. CI summaries remain
observed workflow metadata and never become criterion-level runtime evidence automatically.

## Alternatives rejected

1. Ignore legacy status whenever check runs exist. This would hide a real non-empty legacy pending
   or failing status and could create False Ready.
2. Lower matching thresholds or reserve slots for every evidence type. This would increase noisy
   matches and force irrelevant evidence into results.
3. Convert passing CI into E3 runtime evidence. A workflow can only prove the checks it actually
   ran, and R-001's eval execution/report jobs were skipped.
4. Hard-code Microsoft file paths, check names, PR numbers, or SHA values. The defect and selection
   rules must be repository-independent.

## Data model

Add `CIObservation`, a Pydantic model containing the aggregate `state`, a nonblank `reason`, counts
for total, successful, pending, failing, neutral, and skipped check runs, the count of concrete
legacy statuses, and bounded skipped-check names. `PullRequestSnapshot` and `Review` carry this
object alongside `check_state`; validators require both states to agree. Defaults represent an
unavailable observation so old fixtures and records remain readable.

Add optional `ResearchContext` to `ReviewBundle` with a stable case ID, the fixed classification
`public_engineering_research`, `stage1_credit = false`, and a nonblank boundary note. Validation
prevents any research bundle from claiming Stage 1 credit.

## CI aggregation

Normalize every check run by `status` and `conclusion`, and treat the concrete legacy `statuses`
array as the source of legacy observations. The aggregate order is:

1. any failing check conclusion or failing/error legacy observation -> `failing`;
2. any queued/in-progress check run or concrete pending legacy observation -> `pending`;
3. any successful completed check run or concrete successful legacy observation -> `passing`;
4. otherwise -> `unavailable`.

Neutral and skipped runs are counted but never prove passing. The top-level legacy `state` is used
only when at least one concrete legacy status exists. The reason string is derived from the same
normalized input, not written by an adapter caller.

## Evidence classification and selection

The static evidence classifier recognizes conventional test paths and explicit `eval`/`evals`
path segments as `test`. Test and eval definitions remain E2 and receive the limitation: they show
test intent, not execution. Documentation and instruction markdown remain documentation E1;
implementation and contract rules remain unchanged.

For each criterion, matching and score thresholds run exactly as today. After deterministic global
sorting, selection takes the first item for each represented evidence type in first-seen order,
then fills the remaining slots from the sorted candidates without duplication. This guarantees
diversity only when another relevant type already passed the existing filters.

## Product surfaces

- Markdown and HTML show observed CI state, reason, counts, and skipped check names near review
  identity, then preserve the candidate-not-correctness boundary.
- CSV repeats validated CI fields per criterion and retains formula neutralization.
- JSON includes the validated models directly.
- CLI metadata prints CI state/reason and research classification without credentials.
- Streamlit shows CI reason and skipped-check guidance for fetched or reopened reviews, labels E2
  test/eval definitions as intent rather than execution, and displays the research/Stage boundary.
- Reports distinguish missing runtime evidence and unresolved reviewer decisions from static
  candidate coverage. Existing manual runtime records remain separate.

## R-001 research record

Store only requirements, generated ScopeProof reports, hashes, and an engineering summary under
`docs/research/r001-microsoft-hve-core/`. Do not copy unnecessary Microsoft source content. Record
the original and current SHA, anonymous/authenticated comparison, check aggregation before/after,
candidate-type distribution, gate outcome, limitations, and zero Stage 1 credit. No Microsoft code
is executed and no Microsoft repository state is changed.

## Verification

Use RED-GREEN-REFACTOR tests for aggregation, schema integrity, diverse selection, exports, CLI,
and Streamlit. Then run focused tests, Ruff, repository contracts, the complete suite with the
repository coverage threshold, both deterministic benchmarks, locked dependency sync, build,
wheel metadata and clean installation, installed benchmarks, public-review smoke, report link and
schema validation, and `git diff --check`.

R-001 is rerun anonymously and, only when a session token is already available, authenticated.
Allowed timestamp and review identity fields are normalized before comparing results. A skipped
eval execution must remain skipped/unavailable runtime verification, and the deterministic gate
must remain conservative when evidence or human decisions are missing.
