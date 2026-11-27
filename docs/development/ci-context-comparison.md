# Compare supplied CI context for one reviewed commit

The development-source CLI can explain a CI update in one offline handoff. It uses
the same status projection as existing snapshots and does not reanalyze the pull
request or change its saved acceptance decision.

```sh
scopeproof ci-snapshot REVIEW_ID ./current.json \
  --previous-manifest ./previous.json \
  --storage-dir ./reviews --output ./comparison.html
```

Supply an existing active saved review, two explicit local manifests up to 1 MiB
each, and a new `.html` path. Both manifests must match the repository, PR, confirmed
criteria and exact reviewed commit. Missing or pending reviews, incompatible inputs,
malformed data and existing output files are refused under
the existing bounded-file and storage boundaries. Original input bytes are preserved.

## Reading the report

- **Test rows:** one per test ID, with prior/current criterion mappings, effective
  CI status, reasons and links to supplying run records. A changed row can reflect
  source or mapping changes even if its effective status stays the same.
- **Run records:** retained, introduced, absent or changed assertions. Each side
  retains its own reported head, source URL and outcomes. Reusing an ID with changed
  data does not make that record retained evidence.
- **Mapping gaps:** criteria without a supplied mapping remain explicit. Removing
  a test mapping does not turn it into a pass or an explicit skip.
- **Saved acceptance:** the unchanged recorded status and final-acceptance flag are
  separate from the new supplied context. They are not a new assessment of those
  external results.

Previous/current refer to input-file order. Manifests contain no authenticated
chronology, and ScopeProof does not establish which run actually happened later.
It does not authenticate producers, execute target tests or upgrade runtime evidence.
Both raw manifest SHA-256 values identify the exact supplied byte sequences.

## Existing constructed example

Use the B review emitted by the documented simulated-workbench setup. After
publishing its targeted run, export:

```sh
scopeproof ci-snapshot B_REVIEW_ID ./simulated-ci-output/B-targeted-scopeproof-manifest.json \
  --previous-manifest ./simulated-ci-output/B-scopeproof-manifest.json \
  --storage-dir ./simulated-ci-output/reviews --output ./b-ci-comparison.html
```

The report shows row access changing from explicitly skipped to failed. The filter
failure and header pass retain initial B's supplying run. The targeted run record
reports explicit skips for the other checks; those skips do not erase earlier
exact-build results under the existing projection. Both snapshots use the same B
commit and unchanged saved review. Conflicting exact-build pass/fail reports remain
unknown. An older-build-only result remains stale.

The comparison model is strict Pydantic and derives rows from validated inputs.
It retains the immutable supplied bytes and computes both digests from those bytes.
The renderer rejects parsed fields that drift from the original bytes, even when a
changed outcome or URL is otherwise valid. The output uses no scripts, remote styles or automatic network
requests. Tables support horizontal keyboard scrolling on narrow screens.

No saved-record migration, evidence-rule or gate change follows. Cross-head
comparison, workbench history, authentication and package/site publication remain
outside this change. The existing frozen walkthrough and R-002 results are unchanged.
