# CI context comparison review and boundary

## Project review

The November 27 review found the existing three CI handoff priorities implemented:
CLI export and follow-up summaries in #304, and the maintained no-install journey in
#305. PR #305 remains open and unmerged at this review. Its source tree is
`1a6dad79c774645b629c77e745e2ad2eba5fa0a4`; the isolated development baseline was
verified against that exact tree before the follow-on change.

Core workflow, storage, comparisons, exports and extensive engineering tests exist.
The unresolved product questions remain independent usefulness, retrieval performance
outside the frozen research, repeat use and demand. These engineering outcomes supply
no customer validation. The owner asked for continued roadmap progress; no outreach,
personal testing, release or deployment was requested.

## Reproduced reviewer gap

The evaluation guide instructed a reviewer to download separate before/after CI
snapshots and compare them manually. The current CLI and workbench project only one
supplied manifest at a time. A read-only replay of the existing frozen B inputs showed:

| Test | Initial B | B after targeted context | Effective supplying run after update |
| --- | --- | --- | --- |
| category_filter | Failed | Failed | B |
| row_entitlement | Explicitly skipped | Failed | B-targeted |
| csv_header | Passed | Passed | B |

The saved gate remained blocked and final acceptance remained false. This is a
constructed context replay, not new source analysis or execution of target PR code.

## Implemented outcome

An explicit `--previous-manifest` flag on `ci-snapshot` renders one offline report.
Both inputs must match the active saved review, confirmed criteria and exact head.
The core comparison uses strict Pydantic models and the existing CI status projection;
test and run rows are derived rather than accepted as externally asserted deltas.
The renderer revalidates, including nested inputs changed after construction.
Independent review reproduced a provenance drift: a valid nested outcome edit could
retain the old raw-file digest. Failing regressions reproduced that edit and a valid
URL edit. The corrected model retains immutable input bytes, derives its digests from
them, and rejects any semantic disagreement between those bytes and parsed fields.

The report separates effective result changes, changed test mappings and run-record
assertions. Reused IDs with different source data are changed records. Added runs do
not imply new execution time. Explicit skips do not erase earlier same-head pass/fail
under existing projection rules, and conflicts remain unknown. Both byte digests,
mapping gaps and supplying runs remain visible. Saved acceptance is labelled as an
unchanged record, not a new assessment of external CI data.

The existing single-snapshot CLI behavior remains available without the flag. Inputs
remain bounded local files, loading retains the existing saved-review lock, and output
creation remains atomic and refuses replacement. No gate, evidence rule, record format,
workbench state, dependency, frozen example or research result changes.

## Verification scope

Baseline focused checks passed before implementation. Core, renderer and CLI tests
were written and observed failing before their respective implementation. Coverage
includes retained vs introduced results, altered/reused run IDs, mapping changes,
stale and conflicting reports, changed file order, invalid context, pending reviews,
input-byte preservation and refusal of output replacement.

The final focused run passed 248 checks with two intentional browser skips.
Repository Ruff, whitespace and frozen-artifact checks passed. These local results
do not substitute for the pending installed-package and browser CI cases.

The installed CLI rehearsal now exercises the comparison from the built wheel. The
existing browser CI invocation includes a new offline desktop/phone case with fragment
citations, contained tables, keyboard scrolling and no automatic external requests.
Windows compatibility also runs the comparison contracts.

Local package building was unavailable: Hatchling is absent from the active environment,
and the offline uv cache could not be initialized under the current filesystem policy.
Installed-package and browser results must therefore come from exact-head hosted CI;
source checks and the prior PR's CI must not be substituted for those results.

The follow-on is reviewed and synced separately against #305. Integration, evaluation
distribution, workbench comparison, limited beta and broader access remain distinct
next-stage decisions as recorded in the current roadmap.
