# Declared runtime dependency-floor assessment

Baseline main: `588dcb979c9f4900c32bfb959f70c8babc1921c0`. Public v0.2.4 is immutable;
current source is `0.2.5.dev0`. The owner delegated automatic work and declined routine input.

## Question and approach

Can the published v0.2.4 wheel operate on Python 3.11 with HTTPX 0.27.0, Pydantic 2.8.0 and
Streamlit 1.53.0, and does that allowed stack meet the documented maintained dependency baseline?
Current CI covers recent and locked dependencies, not this exact direct-floor combination.

Use one resolver transaction in a disposable external environment, verify public wheel bytes and
installed identities, then exercise existing constructed CLI/benchmark, persistence/export and
bounded workbench behavior. Check policy separately from compatibility: a passing older stack
must not be recommended if it conflicts with confirmed patch-policy evidence. In particular,
existing maintenance records identify Pillow 13 as the patched baseline.

Alternatives rejected: a new product feature or adapter lacks demonstrated need; another general
CI optimization would repeat a closed question. A permanent extra matrix is not justified before
the floor observation. Prefer a narrow existing-lane check only if findings justify ongoing cost.

## Conditional repair and finish line

If a product failure, metadata mismatch or confirmed dependency-policy contradiction is found,
make at most one narrow current-source/metadata/test/documentation repair. Distinguish old testing
interfaces from product APIs; do not weaken validation or rewrite expectations to obtain a pass.
Retain historical floor results and any new repaired-floor result separately. Existing public
assets are not repaired by changing development source; document that version boundary honestly.

Preserve explicit criteria/reviewer decisions, Pydantic validation, exact-head bindings,
deterministic fail-closed gates, source identity, all required CI suites and unrounded 95% coverage.
Run only trusted ScopeProof/constructed automation code; never execute target-repository code.
All activity is engineering evidence, with zero independent-use or qualifying-review credit.

Obtain independent automated review, pass exact-head tests/packaging/browser/compatibility/lint,
merge with a head guard and verify main. Preserve frozen R-002 and published assets/tags. No
personal testing, qualifying reviews, release, deployment, outreach, speculative features or
Stage 3 advancement. Stop when this compatibility/support question is resolved; return to maintenance.

## Observed findings and single repair selection

The historical direct floor installs and passes CLI/benchmarks/save/reopen/export on Python
3.11.15. It selects Pillow 12.3.0 because Streamlit 1.53 requires `<13`; this conflicts with
the documented patched baseline. Preserve that observation and document explicit maintained
install guidance. Do not promote the older combination as the recommended runtime or claim all
permitted combinations are patched. The old DOM also differs from the current browser helper;
that incomplete helper run is not a product-reopen defect.

The maintained public-wheel stack (Streamlit 1.66.1/Pillow 13, with the same other direct floors)
passes the primary and JUnit roundtrip helpers, but its uploader rejects exactly 1,048,576 bytes
before parsing. On the observed non-Windows browser, Streamlit's 1 MB widget cap is 1,000,000
bytes. **Select this exact-upload-boundary defect as the one code repair.** Withdraw the draft
metadata-floor change; dependency outcomes remain version-bound guidance in this assessment.

Give the widget a 2 MB transport envelope, retaining the current early `size > MAX_JUNIT_BYTES`
rejection and the independent core 1 MiB parser cap. Explain the payload/envelope distinction in
the uploader help. Regress exact 1 MiB acceptance, +1-byte pre-read rejection and unchanged
gate/decision/persisted context, including the installed-wheel browser path. The public v0.2.4
bytes retain the defect; current-source repair and public-wheel results must remain separate.
