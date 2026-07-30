# R-002 SWE-bench Verified Static Research Benchmark Design

## Goal

Create a separate 20-case public engineering research benchmark that exercises ScopeProof's
criteria-to-evidence workflow against real, historical pull-request material from SWE-bench
Verified. The benchmark measures static evidence retrieval quality, evidence-type separation,
missing-evidence explanations, immutable-reference integrity, conservative gating, and
determinism without cloning, applying, importing, compiling, or executing code from a benchmark
target repository.

R-002 is engineering evidence only. Every result is classified as
`public_engineering_research`, is permanently ineligible for Stage 1 credit, and cannot be
described as customer validation, a genuine Alpha review, runtime verification, acceptance, or
proof that a pull request is correct.

## Why this benchmark

The existing 12-case benchmark and two-case comparison benchmark are deliberately constructed
regression corpora. Microsoft R-001 adds one deep public research case. They provide strong local
determinism and targeted failure coverage, but they do not show how the same static matching path
behaves across a broader set of real issue-and-patch shapes.

The [official SWE-bench dataset guide](https://www.swebench.com/SWE-bench/guides/datasets/)
describes SWE-bench Verified as 500 expert-verified solvable cases. That makes it suitable for this
bounded research job across established Python repositories. Its gold implementation patch and
test patch offer a public reference for static candidate coverage. They do not provide ScopeProof
with source-owner-confirmed acceptance criteria, participant decisions, current runtime execution,
or permission to claim a PR is Ready.

## Options considered

### 1. Separate static public research pack

Pin a small, outcome-blind SWE-bench Verified cohort; decode only its public data; adapt unified
diffs into ScopeProof's existing static review path; and preserve a permanent research boundary.
This is the selected approach because it adds real multi-repository input breadth without changing
the product's evidence or gate rules.

### 2. Run the official SWE-bench harness

The harness checks patches by building containers and executing target repositories. That answers a
software-solving question, not ScopeProof's evidence-assistance question, and directly conflicts
with the rule against executing untrusted repository code. It is rejected.

### 3. Fold the cases into the constructed benchmark

This would mix public third-party research inputs with ScopeProof-authored regression fixtures and
change the exact packaged 12-case contract. It is rejected so each evidence class remains clear.

### 4. Select convenient live GitHub PRs

Live hand-picked cases would be easier to ingest but would invite outcome cherry-picking, drift,
and unsupported assumptions about requirements authority. The pinned, deterministic cohort is
preferred.

## Source-of-record pin

R-002 uses this immutable source:

- dataset: `SWE-bench/SWE-bench_Verified`;
- config and split: `default/test`;
- dataset repository revision: `91aa3ed51b709be6457e12d00300a6a596d4c6a3`;
- file: `data/test-00000-of-00001.parquet`;
- immutable source URL:
  `https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/91aa3ed51b709be6457e12d00300a6a596d4c6a3/data/test-00000-of-00001.parquet`;
- exact byte length: `2,090,470`;
- file SHA-256: `43ed5a3d1d98da36472c1ade65ddd2085d7b4ff694fcaf6a023a07c5c1f32f21`;
- expected rows: `500`;
- expected repositories: `12`;
- expected unique instance IDs: `500`.

The
[pinned dataset card](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/blob/91aa3ed51b709be6457e12d00300a6a596d4c6a3/README.md)
and the decoded Parquet have exactly these 13 string fields:

`repo`, `instance_id`, `base_commit`, `patch`, `test_patch`, `problem_statement`, `hints_text`,
`created_at`, `version`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `environment_setup_commit`, and
`difficulty`.

The generalized SWE-bench documentation shows URL fields for some datasets, but this exact
snapshot does not contain `issue_url`, `pr_url`, or `issue_id`. R-002 validates the real pinned
schema and never invents missing fields. A PR URL may be derived only after the instance suffix is
validated as the PR number for the row's repository. An original issue URL is optional enrichment
only when it can be verified from a public source; it is never inferred.

The dataset card does not state a dataset-level license. ScopeProof therefore does not commit or
redistribute raw problem statements, patches, test patches, hints, or test-name lists. The checked-in
corpus contains only IDs, public URLs, immutable hashes and SHAs, bounded factual metadata,
ScopeProof-authored criterion paraphrases, and expected engineering labels. Raw rows remain in the
already ignored `.scopeproof/research/r002/` cache.

## Deterministic 20-case selection

Selection is fixed before ScopeProof produces any result:

1. Validate the exact source revision, file size, file hash, schema, 500 rows, 12 repositories,
   and 500 unique IDs.
2. Give every repository one case.
3. Give eight additional slots to repositories ordered by `(case_count DESC, repo ASC)`.
4. Within each repository, order rows by the lowercase hexadecimal value of
   `SHA256("<pinned-file-sha256>:<instance_id>")` and take the repository quota.
5. Order the final manifest by `(repo, instance_id)` and assign stable case IDs `R002-001` through
   `R002-020`.

This algorithm covers all 12 repositories, caps any repository at two cases, and does not inspect
ScopeProof output, normalized criteria, patch complexity, expected matches, or gate results.

The selected cohort is:

| Case | SWE-bench instance / public PR | Dataset base commit | Verified PR head SHA |
|---|---|---|---|
| `R002-001` | [`astropy__astropy-14096`](https://github.com/astropy/astropy/pull/14096) | `1a4462d72eb03f30dc83a879b1dd57aac8b2c18b` | `271b2875d9aae0a5875acba0b1b27dc4885fd6e5` |
| `R002-002` | [`astropy__astropy-7166`](https://github.com/astropy/astropy/pull/7166) | `26d147868f8a891a6009a25cd6a8576d2e1bd747` | `3306a25dee0dc9c7583f9ede5155ad9a416279d8` |
| `R002-003` | [`django__django-11087`](https://github.com/django/django/pull/11087) | `8180ffba21bf10f4be905cb0d4890dc2bcff2788` | `f110de5c04818b8f915dcf65da37a50c1424c6e6` |
| `R002-004` | [`django__django-12262`](https://github.com/django/django/pull/12262) | `69331bb851c34f05bc77e9fc24020fe6908b9cd5` | `e3d546a1d986f83d8698c32e13afd048b65d06eb` |
| `R002-005` | [`matplotlib__matplotlib-20676`](https://github.com/matplotlib/matplotlib/pull/20676) | `6786f437df54ca7780a047203cbcfaa1db8dc542` | `5c08ff65b884bd03d80eba0a6de01a9d24599299` |
| `R002-006` | [`matplotlib__matplotlib-25287`](https://github.com/matplotlib/matplotlib/pull/25287) | `f8ffce6d44127d4ea7d6491262ab30046b03294b` | `264e7d37d2ee89c6019af4e5743653f4748448e1` |
| `R002-007` | [`mwaskom__seaborn-3187`](https://github.com/mwaskom/seaborn/pull/3187) | `22cdfb0c93f8ec78492d87edb810f10cb7f57a31` | `9372112ea432a8b3d5bd9e11051a999b63905e86` |
| `R002-008` | [`pallets__flask-5014`](https://github.com/pallets/flask/pull/5014) | `7ee9ceb71e868944a46e1ff00b506772a53a4f1d` | `b8b410014d85f9861acc87c5f21c9a55a42d09c9` |
| `R002-009` | [`psf__requests-1766`](https://github.com/psf/requests/pull/1766) | `847735553aeda6e6633f2b32e14ba14ba86887a4` | `92d3616b02fc0ce5b1a89d884a4b1c7d602cb364` |
| `R002-010` | [`pydata__xarray-4075`](https://github.com/pydata/xarray/pull/4075) | `19b088636eb7d3f65ab7a1046ac672e0689371d8` | `5650db2b9076787d848fa180e4b752aa578629c4` |
| `R002-011` | [`pydata__xarray-6992`](https://github.com/pydata/xarray/pull/6992) | `45c0a114e2b7b27b83c9618bc05b36afac82183c` | `ca01949cb889ee38aae33560b02de1f7625fd921` |
| `R002-012` | [`pylint-dev__pylint-7080`](https://github.com/pylint-dev/pylint/pull/7080) | `3c5eca2ded3dd2b59ebaf23eb289453b5d2930f0` | `c744a5357abfd30b84de9d171c901de4d555669b` |
| `R002-013` | [`pytest-dev__pytest-7490`](https://github.com/pytest-dev/pytest/pull/7490) | `7f7a36478abe7dd1fa993b115d22606aa0e35e88` | `ccad10a82908d7a12cd6024e00be11af413edf1c` |
| `R002-014` | [`pytest-dev__pytest-7521`](https://github.com/pytest-dev/pytest/pull/7521) | `41d211c24a6781843b174379d6d6538f5c17adb9` | `8616a5f1d989eec5e2c5f2129040149fe4cf4347` |
| `R002-015` | [`scikit-learn__scikit-learn-13779`](https://github.com/scikit-learn/scikit-learn/pull/13779) | `b34751b7ed02b2cfcc36037fb729d4360480a299` | `2ca0e6c7958a8c217a4788cad08768249d6a0522` |
| `R002-016` | [`scikit-learn__scikit-learn-14496`](https://github.com/scikit-learn/scikit-learn/pull/14496) | `d49a6f13af2f22228d430ac64ac2b518937800d0` | `8e8a34535f8f8743aedf88553d62e66423118423` |
| `R002-017` | [`sphinx-doc__sphinx-8459`](https://github.com/sphinx-doc/sphinx/pull/8459) | `68aa4fb29e7dfe521749e1e14f750d7afabb3481` | `333e7a447edfcb3092032ac801116e1eec193e44` |
| `R002-018` | [`sphinx-doc__sphinx-9230`](https://github.com/sphinx-doc/sphinx/pull/9230) | `567ff22716ac258b9edd2c1711d766b440ac0b11` | `9a132b4f8114f1652a9bc494b740b6632c3545a9` |
| `R002-019` | [`sympy__sympy-20801`](https://github.com/sympy/sympy/pull/20801) | `e11d3fed782146eebbffdc9ced0364b223b84b6c` | `b5424dd3d0484087ae9d175c014e9a803e91a875` |
| `R002-020` | [`sympy__sympy-21612`](https://github.com/sympy/sympy/pull/21612) | `b4777fdcef467b7132c055f8ac2c9a5059e6a145` | `305d1300055245c26c0261ffaf77575fb2e9f9d9` |

All 20 PRs were read-only verified as public, closed, and merged on 2026-07-21. Each live PR base
SHA matched its dataset `base_commit`. The actual PR head SHA above, not the dataset base commit or
a synthetic digest, is the only candidate evidence commit allowed for that case. Implementation
must verify that every parsed candidate-eligible new-side line, both added and context, is
inspectable at that head before accepting a permalink.

## Criteria and label protocol

The dataset `problem_statement` is public research text, not a set of source-owner-confirmed
acceptance criteria. R-002 therefore uses this strict two-pass protocol:

1. Read only the problem statement and produce 1–16 small, atomic ScopeProof-authored criteria per
   case, including at least one `MUST_HAVE`. Do not inspect the gold patch, test patch, test names,
   or ScopeProof output while normalizing.
2. Freeze each source hash and every criterion's ID, text, priority, criterion type, criterion
   source, source span, and required evidence level in a review artifact. The benchmark owner must
   explicitly confirm the complete normalized criterion objects before any patch inspection or
   real-case analysis runs.
3. Record `benchmark_owner_confirmed: true` and `source_owner_confirmed: false`. An unconfirmed
   case is rejected before retrieval; it is never silently treated as confirmed.
4. Only after confirmation, inspect the gold implementation and test patches. Independently of
   ScopeProof retrieval, build the complete annotation universe as the cross-product of every
   confirmed criterion and every parsed candidate-eligible new-side line (`added` and `context`)
   from both streams. Freeze each pair under `(case_id, criterion_id, stream, path,
   new_line_number, normalized_line_sha256)`.
5. Author a relevant/irrelevant label for every pair in that independent universe and obtain one
   batch owner confirmation. Expected-missing `(criterion_id, evidence_type)` labels are derived
   where the confirmed universe has no relevant pair of that type. The label artifact stores
   hashes, paths, line numbers, booleans, and reason codes, not raw lines.
6. Only after labels are frozen, run ScopeProof and map each retrieved candidate back to one exact
   annotation key. A candidate outside the frozen universe or a missing annotation invalidates
   scoring and requires a new labelled revision; it is never guessed or labelled after the score
   is known.

The approval of the R-002 design and cohort does not by itself confirm criterion wording that has
not yet been written. Criteria confirmation is a deliberate review gate in the implementation
plan, not a reason to weaken the product rule.

After owner confirmation, the product-facing criterion may use the existing
`CriterionSource.USER_CONFIRMED` value because the benchmark operator confirmed the wording. The
R-002 manifest and `ResearchContext` must still make clear that this operator is not the source
owner and that the case is ineligible for Stage 1.

## Architecture and data flow

R-002 remains independent from the existing constructed benchmarks:

```text
pinned dataset bytes + pinned manifest
                |
                v
read-only preparation and hash validation
                |
                v
ignored, Pydantic-validated local cache
                |
                v
bounded static unified-diff adapter
                |
                v
validated PullRequestSnapshot + confirmed criteria
                |
                v
existing retrieval -> findings -> deterministic gate
                |
                v
validated R-002 case results and aggregate research report
```

Use the dedicated module `scopeproof_core/evals/r002_swebench.py` and three packaged, separately
validated inputs:

- `evals/r002/source_manifest.json` for the source pin, cohort, SHAs, and row/content hashes;
- `evals/r002/criteria.json` for source hashes, criteria, provenance, and owner confirmation;
- `evals/r002/candidate_labels.json` for the frozen independent annotation-universe hash, relevance labels,
  expected-missing labels, and owner confirmation.

The explicit entry points are:

- `python -m scopeproof_core.evals.r002_swebench prepare`;
- `python -m scopeproof_core.evals.r002_swebench annotate`;
- `python -m scopeproof_core.evals.r002_swebench run`.

Do not add the 20 cases to `scopeproof benchmark` or `scopeproof comparison-benchmark`; their
12-case and two-case constructed contracts remain exact and unchanged. The module locates the
three `evals/r002/` inputs with the same installed-package-root pattern as the existing runners, so
the commands work from a clean wheel installation rather than relying on the source checkout.

Preparation and execution are separate:

- `prepare` performs GET-only access to the pinned Hugging Face source and public GitHub PR
  metadata, verifies all hashes and SHAs, and atomically materializes only the selected cases under
  `.scopeproof/research/r002/`;
- `run` is fully offline and rejects absent, incomplete, changed, or unconfirmed cached inputs;
- no command clones a target repository, checks out a target commit, applies a target patch,
  imports modules from a benchmark repository, starts Docker, installs a target project, or
  executes any target command or test;
- no paid API, LLM API, account creation, outreach, comment, issue, email, release, or scheduled
  monitor is involved.

`prepare` accepts only the exact HTTPS `huggingface.co` source URL above, at most three HTTPS
redirects whose hosts are `huggingface.co` or end in `.hf.co`, GitHub metadata GETs under
`api.github.com/repos/<manifest-repo>/pulls/<manifest-number>`, and immutable file GETs under
`raw.githubusercontent.com/<manifest-repo>/<manifest-head>/<manifest-path>`. It rejects credentials
in URLs, redirects to IP literals or other hosts, and every non-GET method.

The Parquet download must advertise and produce exactly 2,090,470 bytes; streaming stops on the
first excess byte and SHA-256 is calculated while writing. Before rows become Python objects,
Parquet metadata must declare exactly 500 rows, the expected schema, at most 16 MiB total
uncompressed column data, and no nested values. Selected rows are limited to 1 MiB canonical JSON,
128 KiB problem text, and 512 KiB for each patch stream.

Cache handling rejects a symlink cache root or symlink destination. It writes a mode-`0600`
temporary file in the same directory, flushes and syncs it, atomically replaces the destination,
then reopens and revalidates the persisted bytes and Pydantic object. Logical third-party paths
never become cache paths; cached head files use content-addressed SHA-256 filenames referenced by a
validated index.

The first implementation does not add `datasets`, Docker, or SWE-bench's evaluation harness.
Direct decoding of the hash-verified Parquet uses `pyarrow` as a free, preparation-only optional
dependency pinned through a `research` extra and `uv.lock`; it is not imported by ScopeProof's
normal runtime or the offline `run` command. `prepare` reads the exact downloaded Parquet directly
and never uses the unversioned dataset row service.

For each row, canonical bytes are UTF-8 JSON produced from the exact 13 string fields with sorted
keys, `ensure_ascii=false`, separators `(",", ":")`, and no trailing newline or Unicode
normalization. The manifest pins each selected row's canonical SHA-256 plus separate hashes for
`problem_statement`, `patch`, and `test_patch`. This creates a direct, reproducible chain from the
pinned Parquet bytes to every cached selected row.

## Validated contracts

Every checked-in manifest, cached row, label, case result, and aggregate result uses a Pydantic
model with `extra="forbid"`.

### Source pin

`SWEbenchSourcePin` contains the dataset ID, config, split, revision, immutable source URL, Parquet
path, exact byte length, SHA-256, row count, repository count, unique-ID count, and exact ordered
schema.

### Source and case manifest

`R002SourceManifest` contains the source pin and exactly 20 ordered `R002CaseManifest` records.
Each case contains:

- stable case ID and instance ID;
- repository, validated PR number, HTTPS PR URL, dataset base commit, and verified PR head SHA;
- canonical full-row, problem-statement, implementation-patch, and test-patch hashes;
- bounded factual metadata such as difficulty and row index;
- no raw source text, criteria, or candidate labels.

The source manifest rejects duplicate case IDs, duplicate instance IDs, invalid repository names,
URLs outside the approved sources, non-40-character Git SHAs, non-64-character SHA-256 values, rows
not in deterministic order, or any count other than 20.

`R002CriteriaSet` requires all 20 source hashes; 1–16 fully specified criteria per case; at least
one `MUST_HAVE` criterion per case; stable ordering; benchmark-owner confirmation; and
`source_owner_confirmed: false`. `R002CandidateLabelSet` requires the pinned
source manifest hash, criteria-set hash, complete independent annotation-universe hash, one label
per stable annotation key, explicit expected-missing labels, and benchmark-owner confirmation.
`prepare` needs only the source manifest; `annotate` additionally requires the confirmed criteria
set; `run` requires all three inputs, records the exact ScopeProof commit being scored, and rejects
cross-file hash or revision drift.
The criteria set rejects any attempt to claim source-owner confirmation.

### Pack and results

`R002Manifest`, `R002CachedCase`, `R002CaseResult`, and `R002BenchmarkResult` preserve these literal
boundaries:

- `pack_id: "R-002"`;
- `classification: "public_engineering_research"`;
- `eligible_for_stage_1: false`;
- `does_not_advance_stage_1: true`;
- `target_repository_code_executed: false`.

Every generated `ReviewBundle` includes the existing `ResearchContext` with its case ID and zero
Stage 1 credit. It contains no `RuntimeEvidence`, no `HumanResolution`, and no final acceptance.
Its required `check_state` is `unavailable`; its validated `CIObservation` has reason code
`no_observations`, complete collection, zero successful/pending/failing/neutral/skipped check runs,
and zero concrete legacy statuses. Dataset test names, a gold test patch, a merged PR, or historical
SWE-bench verification never become E3/E4 evidence, a reviewer decision, or a current CI
observation.

A complete `ReviewBundle` necessarily contains source text and evidence excerpts, so it is written
only to the ignored local cache. `R002CaseResult` never embeds a `ReviewBundle`. Tracked JSON and
Markdown may contain only case/criterion/candidate IDs, hashes, repository-relative paths, line
numbers, counts, enum states, reason codes, aggregate metrics, and limitations. They exclude raw
problem statements, patches, test names, source text, evidence excerpts, and context excerpts.

## Static diff adapter

The research adapter parses only unified-diff text already present in the selected row. It records
whether every path came from the gold `patch` or `test_patch` stream, then passes the validated
snapshot to the unchanged core. The core still classifies candidate evidence from the path. R-002
compares that observed classification with stream provenance: a candidate from `test_patch` must
remain E2 test intent, and any disagreement is a hard separation error rather than an adapter
override.

The parser is evaluation infrastructure, not a general patch application engine. It must:

- support multiple files and multiple hunks while preserving new-side line numbers;
- never treat removed lines as current candidate evidence;
- reject duplicate logical paths, absolute paths, `..` segments, NULs, backslashes, malformed hunk
  counts, overlapping hunks, path/header disagreement, binary content, or unsupported rename/copy
  constructs, including a path duplicated across the implementation and test streams;
- enforce fixed byte, file, hunk, and line limits before allocation;
- keep third-party logical paths as data and never use them as local write paths;
- require the implementation and test streams to remain distinguishable;
- fail the case instead of guessing when the input is ambiguous.

Concrete parser limits are 32 logical files, 256 hunks, 50,000 diff lines, a 512-character logical
path, and 64 KiB per diff line for one case. Counters are enforced during line iteration before
building unbounded lists.

Diff and immutable-file bytes decode as strict UTF-8. CRLF and lone CR line endings normalize to
LF; the single unified-diff marker byte is removed; all remaining leading and trailing whitespace
is preserved; and the terminal line break is excluded. `normalized_line_sha256` is the SHA-256 of
those UTF-8 content bytes. No case folding, Unicode normalization, trimming, or tab expansion is
allowed.

Criteria are bounded to 1–16 per case and require at least one `MUST_HAVE`. The independent
annotation universe is capped at 250,000 criterion-line pairs for the pack and is streamed to a
temporary validated artifact before atomic replacement. Exceeding either limit fails annotation
and requires an explicit design change; it does not truncate the universe or silently reduce
coverage.

Every new-side candidate-eligible line, both `added` and `context`, is verified against the
immutable raw file at the pinned PR head. `prepare` may fetch at most 4 MiB per head file, 16 MiB
per case, 128 MiB for the pack, and 128 head-file requests. It stores the verified file bytes only
under the ignored content-addressed cache and records their hashes in the cache index. The offline
runner rechecks path, new-side line number, normalized line bytes, file hash, head SHA, and the exact
GitHub blob permalink before admitting a candidate. Removed lines are never candidate eligible.

Runner sidecar provenance maps each logical path to `patch` or `test_patch`. Before analysis it
requires every `test_patch` path to satisfy the existing core's TEST classification and rejects a
path present in both streams. The adapter never overrides the core evidence type or level. Any
test-stream result other than TEST/E2 is a hard separation error.

The current 20-case cohort contains ordinary text diffs without rename, copy, binary, new-file, or
deleted-file records. Negative constructed parser fixtures still cover those failure paths without
committing third-party patch bodies.

## Metrics and gates

The first 20-case result records:

- executed, failed, and skipped case counts;
- confirmed criterion and candidate counts;
- owner-confirmed research-label candidate precision and criterion candidate coverage;
- candidate-to-gold-file and candidate-to-gold-hunk coverage;
- implementation/test-intent separation errors;
- missing-evidence explanation completeness;
- invalid or stale immutable-reference count;
- parse, schema, source-hash, and source-SHA errors;
- `unexpected_ready_count`;
- normalized rerun mismatches.

The metric formulas are fixed before scoring:

- owner-confirmed research-label candidate precision = retrieved candidates labelled relevant /
  all retrieved candidates in the frozen labelled universe;
- criterion candidate coverage = confirmed criteria with at least one retrieved relevant candidate
  / confirmed criteria whose frozen universe contains at least one relevant candidate;
- candidate-to-gold-file coverage = unique parsed `patch` or `test_patch` paths referenced by at
  least one retrieved candidate / all unique parsed paths;
- candidate-to-gold-hunk coverage = unique parsed hunks containing at least one retrieved candidate
  / all parsed hunks;
- missing-evidence explanation completeness = expected-missing `(criterion_id, evidence_type)`
  pairs present with an explicit missing reason / all frozen expected-missing pairs;
- immutable-reference integrity errors = admitted candidates whose cached head-file hash, path,
  new-side line number, normalized line hash, head SHA, or permalink does not match the source pin;
- normalized rerun mismatches = case IDs whose `R002DeterminismProjection` canonical SHA-256 differs
  between two consecutive offline runs.

Every denominator and zero-denominator case is reported explicitly. A zero denominator produces a
`not_applicable` metric state, never an invented 100 percent.

Do not call these results customer precision, a real False Ready rate, semantic correctness, or
acceptance accuracy. `owner-confirmed research-label candidate precision` is allowed only after
every candidate has a frozen research label that the benchmark owner reviewed and confirmed.
Before that, report only structural gold-file/hunk coverage.

The hard integrity gates for the first run are:

- exactly 20 cases execute; zero are silently skipped;
- all persisted objects validate;
- every source and row hash matches;
- every case uses its pinned, publicly inspectable PR head SHA;
- implementation and test intent remain separated with zero E3/E4 promotion;
- every missing expected evidence type has an explicit explanation;
- every case has `check_state=unavailable`, no resolutions, and `final_acceptance=false`; the exact
  expected gate is either `blocked` with `blocking_criteria` or `needs_review` with
  `checks_not_passing` and `unresolved_criteria`, so `unexpected_ready_count` is zero;
- normalized consecutive offline runs are byte-identical after removing only documented generated
  IDs, timestamps, and absolute cache paths;
- existing 12-case and two-case benchmark outputs remain unchanged.

`R002DeterminismProjection` contains only stable manifest identity, criteria hashes, candidate
keys, evidence classifications, finding/gate enums, reference hashes, limitations, and metrics. It
does not contain `Review` UUIDs, generated timestamps, HTTP metadata, or local paths. Canonical
result bytes use Pydantic JSON values encoded as UTF-8 with sorted keys, compact separators, and no
trailing newline. Determinism compares the SHA-256 of that projection rather than deleting
arbitrary fields from a full `ReviewBundle`.

Candidate precision and coverage are baseline observations in R-002's first run, not arbitrary
release gates chosen before seeing the baseline. Any later threshold must be proposed from the
saved baseline and approved without weakening gate rules or hiding poor matches.

## Test-driven implementation

1. Add failing schema and repository-contract tests for the exact source pin, exact 20-case cohort,
   stable ordering, research literals, criteria-confirmation boundary, and absence of third-party
   raw content from tracked files.
2. Add failing constructed parser tests for multi-file/multi-hunk line accounting,
   implementation/test separation, removed lines, malformed counts, traversal, duplicate paths,
   binary and rename records, UTF-8 handling, and resource limits.
3. Implement the smallest Pydantic contracts and bounded static adapter needed to make those tests
   pass without changing core evidence or gate rules.
4. Add failing preparation tests for hostname/redirect restrictions, exact content length/hash,
   direct pinned-Parquet decoding, canonical row hashes, base/head SHA mismatch, added/context line
   verification, symlink rejection, incomplete atomic cache writes, and offline reuse.
5. Implement GET-only preparation using controlled ScopeProof-owned HTTP fixtures in CI. Never make
   CI depend on live SWE-bench or GitHub availability.
6. Normalize criteria from problem statements alone, freeze their hashes, and produce the 20-case
   criterion review artifact. Stop real-case analysis until the benchmark owner confirms it.
7. After confirmation, independently build and hash the full criterion-by-line annotation universe,
   add owner-confirmed relevance and expected-missing labels for that complete universe, then run
   all 20 cases offline twice. Write a Pydantic-validated redacted JSON result plus a concise
   Markdown engineering summary that excludes raw third-party content.
8. Run focused tests, repository contracts, Ruff, the full coverage-gated suite, both existing
   deterministic benchmarks, package build/content inspection, and a clean installed execution of
   the new opt-in runner.

If a real case exposes a general evidence-rule defect, first reduce the behavior to the smallest
ScopeProof-authored constructed regression fixture. Fix it in a separate, reviewable slice with a
failing test. Do not tune matching thresholds, labels, selected cases, expected outcomes, or gate
rules inside R-002 merely to improve the benchmark result.

## Failure handling

- A missing network source during `prepare` is an explicit preparation failure; it does not produce
  a partial benchmark. A previously complete, hash-valid cache remains usable by `run`.
- A changed remote dataset at another revision is ignored. A mismatch at the pinned revision fails
  closed and requires a new design decision; the manifest is not silently regenerated.
- A missing or changed PR head, base mismatch, uninspectable candidate-eligible new-side line, or
  invalid permalink fails that case and therefore the 20-case integrity gate.
- An unconfirmed criterion set prevents analysis for that case.
- An annotation-universe hash change, an unlabelled candidate, or a missing frozen annotation prevents
  precision scoring. It produces an explicit `reannotation_required` state rather than silently
  counting the candidate as relevant or irrelevant.
- Unsupported or malformed diff input fails with a bounded explanation; no repository code is
  fetched as a fallback and no case is replaced after the manifest is frozen.
- A poor matching score is reported honestly. It does not authorize changing criteria wording,
  expected labels, retrieval thresholds, or gates after seeing the result.
- Raw cached third-party content, credentials, local paths, timestamps, and generated review IDs
  are excluded from committed reports.

## Scope

Expected implementation is limited to:

- a dedicated R-002 source/manifest/result model and offline runner under
  `scopeproof_core/evals/r002_swebench.py`;
- a bounded evaluation-only unified-diff adapter;
- the packaged `evals/r002/source_manifest.json`, `criteria.json`, and `candidate_labels.json`
  containing the 20-case metadata, confirmed criteria, and engineering labels without raw
  third-party text or patches;
- a locked `research` optional dependency group used only to decode the pinned Parquet during
  preparation;
- ignored local preparation/results data under `.scopeproof/research/r002/`;
- focused tests, repository contracts, and a concise `docs/research/r002-swebench-verified/`
  summary after the real run.

## Explicit non-goals

R-002 does not:

- modify the core retrieval thresholds, evidence levels, finding semantics, gate decisions,
  lifecycle, exports, comparison rules, Streamlit flow, or GitHub Action;
- add generic code review, bug solving, patch generation, security scanning, auto-fix, or a
  SWE-bench agent;
- run the SWE-bench harness, Docker, repository tests, or any code from a benchmark target
  repository;
- add accounts, private repositories, billing, paid APIs, LLM APIs, hosted processing, or external
  communication;
- create a release, tag, public post, issue, comment, email, DM, or monitoring task;
- count any case, repository, timing result, outcome, or reuse signal toward Stage 1;
- start Stage 2, Stage 3, or Stage 4.

## Acceptance criteria

- The source pin, schema, selection algorithm, exact 20 cases, base commits, and real PR head SHAs
  are explicit and reproducible.
- Cohort selection and criterion wording are frozen before annotation, and confirmed relevance
  labels cannot change after any scored ScopeProof result is known.
- Raw third-party problem statements and patches remain outside tracked project files.
- All checked-in, cached, and exported R-002 objects have strict Pydantic validation.
- Complete criterion objects are normalized from problem statements only and explicitly confirmed
  before patch inspection or analysis; each case has at least one `MUST_HAVE`, and source-owner
  confirmation remains false.
- Preparation is read-only, free, bounded, hash-verified, and separate from offline execution.
- No code from a benchmark target repository is cloned, applied, imported, compiled, installed, or
  executed.
- Test patches remain E2 test intent; current CI remains explicitly unavailable with zero observed
  statuses, while runtime evidence, human resolutions, and final acceptance remain absent.
- With unavailable checks, no resolutions, false final acceptance, and at least one `MUST_HAVE`,
  every case is exactly `blocked` or `needs_review` with the documented reason codes and never
  Ready.
- The first benchmark executes exactly 20 cases with zero silent skips and produces deterministic,
  validated JSON and a truthful aggregate Markdown summary.
- Existing product behavior and both constructed benchmark contracts remain unchanged.
- R-002 remains engineering evidence only; Stage 1 stays
  `waiting_for_inbound_public_alpha_submission`, and Stages 2–4 remain gated.
