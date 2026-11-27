# CI run outcomes and consolidated evaluation candidate

The owner requested execution of the next stages after #305–#307. Their merged main
`b1d142da4f73075189348714160b8d48068876ef` has tree
`755b09c422593af9a417a8d76aad7c2f6480b78d` and passed full main verification.

## Reviewer outcome

The workbench's run comparison currently labels a changed assertion but omits its outcomes.
Show previous/current reported outcome maps in that same run table, including changes which
do not change the effective test result. Use deterministic ordering, literal identifiers,
explicit absent-record labels and separate rows for introduced/removed records. Reuse the
existing validated core comparison; do not change evidence rules, gates, saved decisions,
input bindings or download guards.

## Evaluation preparation

Prepare a fresh unpublished `0.2.9.dev0` candidate containing the accumulated CI handoff
source. Preserve the old private candidate, frozen examples, released-writer corpus and R-002.
Do not rename development archives as final-version assets. Public v0.2.8 remains current;
no tag, Release, Pages deployment, promotion or participant contact is part of this task.

Local build tooling is unavailable. Extend the existing engineering CI job to retain a
candidate after its source, installed CLI and browser checks. Build wheel/sdist using the
existing Hatchling backend through the CI's already maintained uv version. Require the direct
wheel, wheel rebuilt from sdist, installed-CLI wheel and every browser-fixture wheel to be
byte-identical. A source-wheel package probe must import from its installation, match the
version/core fingerprint and pass the existing constructed benchmarks. Runtime dependencies
may be inherited from the tested CI environment; describe that limit explicitly.

Persist a strict Pydantic-validated candidate manifest, both archives, SHA256SUMS and a short
README as a GitHub Actions artifact. The manifest records actual checked-out Git SHA/tree,
version, archive hashes/sizes, core fingerprint, run URL, source/browser pytest JUnit counts,
the wheel bindings and source-install probe. Validate source and wheel Python inventories.
Failed checks, mismatched archives, invalid probe/results or existing output must fail closed.
Keep candidate output outside the checkout. A PR merge checkout is labelled `pr-merge`;
only the artifact rebuilt after integration is labelled `main`. This is engineering evidence,
not signed provenance, publication, independent usefulness or beta validation.

Chosen approach: add a focused preparation helper under `scripts`, reuse existing installed
CLI and browser runs and bind their exact wheels. A separate release service or new browser
fixture override would duplicate established execution. Local cache workarounds and manual
archive construction would not verify the requested distribution.

## Completion

Observe outcome-display and packet-validation regressions failing before implementation.
Exercise outcome-only changes with unchanged effective results, absent/empty run records and
literal identifiers. Test packet hashes, archive parity, source inventory, failure results,
probe binding and create-only output with controlled own-package fixtures. Obtain one fresh
branch review and fix important findings with regressions. Sync and integrate only protected,
verified heads, verify resulting main and link its candidate artifact and exact-source CI.
The candidate is reviewable for a later publication decision; independent-use counts remain zero.
