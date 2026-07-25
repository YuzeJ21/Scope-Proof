# R-002 SWE-bench Verified Static Research Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a deterministic, offline 20-case SWE-bench Verified research benchmark that measures ScopeProof's static evidence retrieval without executing target-repository code or claiming Alpha/customer validation.

**Architecture:** Keep the public research pack separate from both constructed benchmarks and from product UI/CLI flows. The GET-only `prepare` command has two fail-closed phases: `criteria-sources` validates the immutable Parquet identity and materializes only the 20 selected problem statements; after Owner Gate 1, `evidence` redownloads the same pinned file, validates the full selected rows and public GitHub metadata/head-file bytes, and atomically publishes the complete ignored cache. A separate offline path parses the prepared evidence, passes validated snapshots through the unchanged retrieval/findings/gate pipeline, maps every result to an owner-confirmed annotation universe, and emits only strict redacted results. Criteria and candidate labels are two explicit owner-confirmation gates between those phases and scoring.

**Tech Stack:** Python 3.11/3.12, Pydantic 2, httpx, pyarrow 25.0.0 as the exact `research` extra, pytest, pytest-cov, Ruff, uv, Hatchling.

## Global Constraints

- ScopeProof is an evidence assistant, not a correctness oracle; every criterion verdict cites explicit evidence or states what is missing.
- R-002 is always `public_engineering_research`, `eligible_for_stage_1: false`, `does_not_advance_stage_1: true`, and `target_repository_code_executed: false`.
- Never describe R-002 as customer validation, a genuine Alpha review, runtime verification, acceptance, correctness proof, or a measured real False Ready rate.
- Never clone, check out, apply, import, compile, install, test, or execute code from a benchmark target repository.
- Do not modify retrieval thresholds, evidence levels, finding semantics, gate rules, comparison rules, the Streamlit flow, or the GitHub Action.
- Treat False Ready as more harmful than False Blocked. Every R-002 case must finish `blocked` or `needs_review`; `ready` is a hard failure.
- The existing 12-case benchmark and two-case comparison benchmark remain byte-for-byte behaviorally unchanged.
- Users must confirm all normalized criterion fields before patch/test-patch inspection; design approval is not criterion approval.
- Candidate labels must cover the full independent criterion-by-line universe and be owner-confirmed before any scored run.
- Every persisted or exported R-002 object uses a Pydantic model with `ConfigDict(extra="forbid")`.
- Raw problem statements, patches, test patches, hints, test names, source text, evidence excerpts, context excerpts, credentials, timestamps, generated review IDs, HTTP metadata, absolute paths, and local cache paths never enter tracked R-002 JSON or Markdown.
- Checked-in data may contain only IDs, public URLs, SHAs/hashes, factual bounded metadata, ScopeProof-authored criterion paraphrases, paths, line numbers, enums, reason codes, counts, metrics, and limitations.
- Cache raw research material only beneath ignored `.scopeproof/research/r002/`; reject symlink roots and destinations.
- `prepare --phase criteria-sources` and `prepare --phase evidence` are GET-only, free, bounded, hash-verified, and the only paths that import the direct `pyarrow` dependency or use the network. The evidence phase requires confirmed criteria before reading patch/test-patch columns or contacting GitHub.
- `annotate` and `run` are offline. `run` rejects missing, incomplete, drifted, or unconfirmed inputs and never silently skips a case.
- Do not add paid APIs, LLM APIs, `datasets`, Docker, the SWE-bench harness, accounts, private repositories, billing, outreach, email, DM, comments, releases, tags, or monitoring.
- Do not push, open a PR, merge, or release during this plan unless the owner gives a later explicit GitHub authorization.
- If a real case exposes a core rule defect, reduce it to a minimal ScopeProof-authored constructed fixture and fix it in a separate approved slice; do not tune this cohort, its criteria, labels, thresholds, or gates after observing a score.

---

## File map

- `scopeproof_core/evals/r002_models.py`: strict source, cache, annotation, result, metric, and determinism contracts plus canonical hashing helpers.
- `scopeproof_core/evals/r002_source.py`: criteria-only projected-row decoding, exact 13-field full-row validation, Parquet metadata validation, canonical row hashes, and deterministic 20-case cohort recomputation.
- `scopeproof_core/evals/r002_diff.py`: bounded evaluation-only unified-diff parser and `PullRequestSnapshot` changed-file adapter.
- `scopeproof_core/evals/r002_verify.py`: immutable head-file line verification, exact permalink checks, evidence-to-annotation-key mapping, and implementation/test provenance checks.
- `scopeproof_core/evals/r002_cache.py`: symlink-safe `0600`, fsync, atomic, reopen-and-revalidate bytes/JSON persistence.
- `scopeproof_core/evals/r002_prepare.py`: allowlisted streaming GET client, problem-only preparation before Gate 1, and confirmed-criteria-gated source/PR/head-file preparation after Gate 1.
- `scopeproof_core/evals/r002_runner.py`: criteria proposal, annotation-universe construction, review construction, scoring, metrics, redaction, and determinism.
- `scopeproof_core/evals/r002_swebench.py`: installed-package-aware `prepare --phase criteria-sources|evidence | annotate | run` command dispatcher only.
- `scopeproof_core/retrieval/engine.py`: expose the existing path classifier as a pure public helper without changing classification behavior.
- `evals/r002/source_manifest.json`: exact source pin, selected cohort, base/head SHAs, row indices, and content hashes; no raw dataset text.
- `evals/r002/criteria.json`: all 20 confirmed ScopeProof-authored criterion sets; created only after the first owner gate.
- `evals/r002/candidate_labels.json`: complete confirmed label universe hashes and expected-missing records; created only after the second owner gate.
- `tests/evals/conftest.py`: small ScopeProof-authored R-002 rows/diffs/manifests used by tests; no third-party source bodies.
- `tests/evals/test_r002_models.py`: schema, pin, cross-file identity, research literals, and strictness tests.
- `tests/evals/test_r002_source.py`: Parquet metadata, row hashing, size bounds, and deterministic selection tests.
- `tests/evals/test_r002_diff.py`: valid and adversarial parser tests.
- `tests/evals/test_r002_verify.py`: head-file, line, permalink, and evidence-type integrity tests.
- `tests/evals/test_r002_cache.py`: atomic-write, permissions, symlink, partial-write, and revalidation tests.
- `tests/evals/test_r002_prepare.py`: controlled `httpx.MockTransport` source/redirect/GitHub preparation tests, including proof that the pre-confirmation phase never reads patch/test-patch columns.
- `tests/evals/test_r002_annotation.py`: two-pass criteria/annotation completeness and drift tests.
- `tests/evals/test_r002_runner.py`: offline review, scoring, gate, redaction, and determinism tests.
- `tests/test_repository_contracts.py`: exact packaged inputs, raw-content exclusions, optional dependency, CI, docs, and installed-wheel contracts.
- `pyproject.toml`, `uv.lock`: exact free `research = ["pyarrow==25.0.0"]` dependency and reproducible lock.
- `.github/workflows/ci.yml`: install the research extra for controlled fixture tests only; never call live `prepare` or use target code.
- `README.md`, `ROADMAP.md`, `CHANGELOG.md`, `docs/development-environment.md`: truthful opt-in usage and engineering-only status after a successful real run.
- `docs/research/r002-swebench-verified/result.json`: validated redacted first-run result after both owner gates.
- `docs/research/r002-swebench-verified/summary.md`: concise method, baseline, limits, and exact Stage 1 boundary after both owner gates.

## Fixed interfaces and constants

The following names are shared contracts across tasks; do not rename them in one task without updating every consumer in this plan.

```python
# scopeproof_core/evals/r002_models.py
def validate_r002_logical_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("invalid R-002 logical path")
    return value

def validate_r002_source_span(value: str) -> str:
    match = re.fullmatch(r"problem_statement:L([1-9]\d*)-L([1-9]\d*)", value)
    if match is None or int(match.group(1)) > int(match.group(2)) or len(value) > 64:
        raise ValueError("invalid R-002 source span")
    return value

R002CaseId = Annotated[str, Field(pattern=r"^R002-\d{3}$")]
GitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
R002LogicalPath = Annotated[
    str,
    Field(min_length=1, max_length=512),
    AfterValidator(validate_r002_logical_path),
]
R002SourceSpan = Annotated[str, AfterValidator(validate_r002_source_span)]

class R002DiffStream(StrEnum):
    PATCH = "patch"
    TEST_PATCH = "test_patch"

class R002MetricState(StrEnum):
    VALUE = "value"
    NOT_APPLICABLE = "not_applicable"

class R002RequestKind(StrEnum):
    DATASET = "dataset"
    PR_METADATA = "pr_metadata"
    HEAD_FILE = "head_file"

R002_REQUEST_LIMITS = {
    R002RequestKind.DATASET: 4,
    R002RequestKind.PR_METADATA: 20,
    R002RequestKind.HEAD_FILE: 128,
}

R002_COMMAND_FAILURE_CODES = (
    "source_manifest_missing",
    "criteria_missing",
    "labels_missing",
    "prepared_cache_missing",
    "criteria_not_confirmed",
    "labels_not_confirmed",
    "input_validation_failed",
    "network_policy_failed",
    "network_unavailable",
    "source_integrity_failed",
    "preparation_integrity_failed",
    "annotation_required",
    "reannotation_required",
    "benchmark_gate_failed",
    "filesystem_failed",
    "internal_error",
)

R002_RESULT_LIMITATIONS = (
    "Criteria and relevance labels are benchmark-owner research judgements, not source-owner confirmation.",
    "Only static historical diff and immutable PR-head evidence was evaluated.",
    "No target code or tests were executed and current CI was not observed.",
    "Candidate evidence does not prove correctness or criterion satisfaction.",
    "R-002 is engineering evidence only and contributes zero Stage 1 validation credit.",
)

R002_ANNOTATION_UNIVERSE_MAX_BYTES = 256 * 1024 * 1024
R002_ANNOTATION_REVIEW_MAX_BYTES = 512 * 1024 * 1024
R002_REDACTION_RAW_VALUE_MAX_BYTES = 1024 * 1024 * 1024
R002_REDACTION_TRACKED_FILE_MAX_BYTES = 512 * 1024 * 1024

R002_STATIC_EVIDENCE_TYPES = (
    EvidenceType.IMPLEMENTATION,
    EvidenceType.TEST,
    EvidenceType.DOCUMENTATION,
    EvidenceType.CONTRACT,
)
```

The expected-missing universe is exactly those four path-classified static candidate types. CI, runtime, and human evidence are excluded because R-002 deliberately records none and never treats them as diff-line candidates.

The exact callable signatures are:

- `R002Error(reason_code: str)` stores one stable allowlisted `reason_code`; subclasses never store raw bodies, URLs, credentials, or paths in exception args.
- `canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes`
- `canonical_sha256(value: BaseModel | dict[str, object]) -> str`
- `case_projection_sha256(cases: Sequence[R002CaseManifest]) -> str`
- `load_source_manifest(path: Path) -> R002SourceManifest`
- `load_confirmed_criteria(path: Path, manifest_sha256: str) -> R002CriteriaSet`
- `load_confirmed_labels(path: Path, manifest_sha256: str, criteria_sha256: str) -> R002CandidateLabelSet`
- `decode_criteria_source_rows(source: BinaryIO, pin: SWEbenchSourcePin) -> list[SWEbenchCriteriaSourceRow]`
- `decode_verified_parquet(source: BinaryIO, pin: SWEbenchSourcePin) -> list[SWEbenchVerifiedRow]`
- `select_r002_criteria_source_rows(rows: Sequence[SWEbenchCriteriaSourceRow], parquet_sha256: str) -> list[SWEbenchCriteriaSourceRow]`
- `select_r002_rows(rows: Sequence[SWEbenchVerifiedRow], parquet_sha256: str) -> list[SWEbenchVerifiedRow]`
- `validate_manifest_criteria_sources(manifest: R002SourceManifest, rows: Sequence[SWEbenchCriteriaSourceRow]) -> list[SWEbenchCriteriaSourceRow]`
- `validate_manifest_rows(manifest: R002SourceManifest, rows: Sequence[SWEbenchVerifiedRow]) -> list[SWEbenchVerifiedRow]`
- `parse_unified_diff(raw: bytes, *, stream: R002DiffStream, limits: R002DiffLimits = DEFAULT_R002_DIFF_LIMITS) -> R002ParsedDiff`
- `parse_case_diffs(*, case_id: R002CaseId, patch: str, test_patch: str, limits: R002DiffLimits = DEFAULT_R002_DIFF_LIMITS) -> R002ParsedCase`
- `parsed_case_to_changed_files(parsed: R002ParsedCase) -> list[ChangedFile]`
- `verify_case_head_files(*, case: R002CaseManifest, parsed: R002ParsedCase, head_file_bytes: Mapping[str, bytes], limits: R002HeadFileLimits = DEFAULT_R002_HEAD_LIMITS) -> R002VerifiedCaseLines`
- `verify_evidence_reference(*, case: R002CaseManifest, evidence: EvidenceItem, verified_lines: R002VerifiedCaseLines) -> R002CandidateLineKey`
- `R002Cache.__init__(root: Path) -> None`
- `R002Cache.write_bytes(relative_name: str, data: bytes) -> Path`
- `R002Cache.write_content_addressed_model(relative_name: str, value: T, model_type: type[T]) -> Path`
- `R002Cache.write_model(relative_name: str, value: BaseModel) -> Path`
- `R002Cache.replace_model(relative_name: str, value: BaseModel) -> Path`
- `R002Cache.read_bytes(relative_name: str, *, expected_sha256: str | None = None) -> bytes`
- `R002Cache.read_model(relative_name: str, model_type: type[T]) -> T`
- `R002Cache.open_unlinked_scratch() -> ContextManager[BinaryIO]`
- `R002Cache.publish_criteria_source_index(index: R002CriteriaSourceIndex) -> Path`
- `R002Cache.load_criteria_source_index() -> R002CriteriaSourceIndex`
- `R002Cache.publish_index(index: R002CacheIndex) -> Path`
- `R002Cache.load_index() -> R002CacheIndex`
- `R002Cache.write_annotation_universe(*, source_manifest_sha256: str, criteria_set_sha256: str, candidate_count: int, ordered_key_factory: Callable[[], Iterator[R002CandidateLineKey]]) -> R002AnnotationUniverse`
- `R002Cache.write_annotation_review(*, source_manifest_sha256: str, criteria_set_sha256: str, annotation_universe_sha256: str, candidate_count: int, ordered_item_factory: Callable[[], Iterator[R002AnnotationReviewItem]]) -> R002AnnotationReview`
- `validate_request_target(*, url: str, request_kind: R002RequestKind, case: R002CaseManifest | None = None, allow_signed_hf_query: bool = False) -> SplitResult`
- `R002ReadOnlyClient.download_dataset(source: SWEbenchSourcePin, cache: R002Cache) -> ContextManager[BinaryIO]`
- `R002ReadOnlyClient.validate_pr(case: R002CaseManifest) -> None`
- `R002ReadOnlyClient.fetch_head_file(case: R002CaseManifest, logical_path: str) -> bytes`
- `prepare_criteria_sources(*, manifest_path: Path, cache_root: Path, transport: httpx.BaseTransport | None = None) -> R002CriteriaSourcePreparationResult`
- `prepare_r002(*, manifest_path: Path, criteria_path: Path, cache_root: Path, transport: httpx.BaseTransport | None = None) -> R002PreparationResult`
- `build_criteria_proposal(manifest: R002SourceManifest, cache: R002Cache, criteria_by_case: Mapping[R002CaseId, Sequence[Criterion]]) -> R002CriteriaProposal`
- `build_annotation_universe(*, manifest: R002SourceManifest, criteria: R002CriteriaSet, cache: R002Cache) -> R002AnnotationUniverse`
- `annotate_r002(*, manifest_path: Path, criteria_path: Path, cache_root: Path) -> R002AnnotationUniverse`
- `run_r002(*, manifest_path: Path, criteria_path: Path, labels_path: Path, cache_root: Path, scopeproof_commit: str) -> R002BenchmarkResult`
- `resolve_scopeproof_commit(explicit: str | None, *, checkout_root: Path | None = None) -> GitSha`
- `audit_r002_redaction(*, cache_root: Path, candidate_paths: Sequence[Path]) -> R002RedactionAudit`

## Fixed source identity and manifest values

`SWEbenchSourcePin` and `R002SourceManifest` validate structure so controlled fixtures can use bounded test pins without third-party bodies. The production `load_source_manifest` function and tracked source-manifest repository contract must require these exact values rather than accepting equivalent aliases:

```python
R002_SCHEMA = (
    "repo", "instance_id", "base_commit", "patch", "test_patch",
    "problem_statement", "hints_text", "created_at", "version",
    "FAIL_TO_PASS", "PASS_TO_PASS", "environment_setup_commit", "difficulty",
)
R002_SOURCE = {
    "dataset_id": "SWE-bench/SWE-bench_Verified",
    "config": "default",
    "split": "test",
    "revision": "91aa3ed51b709be6457e12d00300a6a596d4c6a3",
    "source_url": "https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/91aa3ed51b709be6457e12d00300a6a596d4c6a3/data/test-00000-of-00001.parquet",
    "parquet_path": "data/test-00000-of-00001.parquet",
    "byte_length": 2_090_470,
    "sha256": "43ed5a3d1d98da36472c1ade65ddd2085d7b4ff694fcaf6a023a07c5c1f32f21",
    "row_count": 500,
    "repository_count": 12,
    "unique_instance_count": 500,
    "schema": list(R002_SCHEMA),
}
R002_APPROVED_CASES_SHA256 = (
    "ef091bb60e78abf9311112ff434f9e80613438915db198662aecd5f469cee336"
)
```

`R002_APPROVED_CASES_SHA256` is the SHA-256 of compact sorted-key UTF-8 JSON for the ordered list of all 20 `R002CaseManifest.model_dump(mode="json")` dictionaries, with no trailing newline. It therefore pins every case ID, instance, repository, PR number/URL, base SHA, verified head SHA, row index, difficulty, and four content hashes shown below—not merely the IDs.

Use the approved design table for every repository, PR number, PR URL, base SHA, and head SHA. The independently recomputed immutable row values are:

| Case | Row | Row SHA-256 | Problem SHA-256 | Patch SHA-256 | Test-patch SHA-256 |
|---|---:|---|---|---|---|
| R002-001 | 7 | `2ab9bc4442553756efedd9737e68d2c11a68954da353a12acb903c86ba414ec0` | `938971021e89cd882f6ea33d61202fe7aa0091d7be4748b100ddc7e164db90cd` | `57a810467af331eba7c3238bbcd78268a47e96ad75eed3e2aa8b908da99104bc` | `3a6a8ffc9c81264bccb9990b926bc6b1c2253a9aa7ce47810b5d28ad95c2596c` |
| R002-002 | 16 | `ba1ba98c4ec623be61f8f5efbe700a6afac5390a057f6d6a6fdc4ef254433eb8` | `70c79d6da0284ce81f9e951dbab5c77d94bf8a27cd156f54169b424d75d11e43` | `b720439fe90e5673cf5d75523a36c25927c9f78f785f280508433447293be578` | `b86ae285f129f2941e27ff5f3229511c58199ae4a9e93b2d32e05dd4c2766dd7` |
| R002-003 | 29 | `0469361e971f290aeafbd49942b2e8305400f8c337fe4f0c177ddc19a85204d8` | `9bd93972a91db1ad0e44e65720dd0f36f000de6264e770ffdaaeb06996a338f3` | `38dfd449272afdf7269e56d798668fd4167db5c34c775614ca0b2fb47eb25789` | `00c3a6c821fbf38e48279ab12d29b9f3edffe76295d1ca2a39bb500863a39a86` |
| R002-004 | 76 | `144160660b3e379ed645123e7ae4fff017e8cc3afee680eef9d58868b73c8fe5` | `eb0c9b99667bc7666a6ff518747eaa71c6d392f727583d3f90cabe5cf4afe994` | `9ec3e3ad1dd4c1993e6c0fb4698939f8f7eb192128fe0d696add4abb969e7037` | `769a15faf523189f8c37917ff3c002c381f0e5a517c481020ea71abe5ee58cf9` |
| R002-005 | 256 | `5cd6ca2a9b3f4cd1056da08095356d10d5073a93f26317615efd66d223b2aac7` | `c201ac5236b0a5eb57faa1768a12c67f0132074a5538d82feb717a62af9ad01d` | `2943065dce13dc7e0f4f5bacc13353a4fe4e3fc3398086c9421b1b4cf4012383` | `d39f439303c71d295be1d94a6f1d0501b7ffe7030bce1c6f5fc6845c990ce3eb` |
| R002-006 | 276 | `b12837067251cb70ae564442328e30d10aa23ebf5d0ba30eaefae1b290106da9` | `f9bbb7794506f072129a5e7941e265280853fd873550828d7a66e91baa611c7e` | `762993a12dfbd18ea1cd9b78c54a5d3262a2e011aa5c79bca562751ff2aba82a` | `86204b551acc12241d3bbb5618a57f44e8341deeb867a860d7cd45c9a3b59163` |
| R002-007 | 288 | `80aa45876204fa0a13ba2c7916e5723b61713622784ca260ebd40f7786abd9d0` | `72157e71b5c0ed5d58d66a7eeb30ed7b2fb237374183b9ebee200f5d58abd77b` | `578f98370810261561a8936dd7202e8c6644ef8d9ae52a54578a680f3cb4fc1f` | `580a0ee004bb0143ba24afcaf0e45ec309635fa4610049ed91a8a15f7e9e1fc8` |
| R002-008 | 289 | `5cc7ccbd782cf546cdded80c0811a572ba428ecace70022e5982477ad6a47489` | `f77d8eab7dd608172aa78b3b50dfa7e0e9b3a6a1c52d14a1cb02417eb5a0ab00` | `087d51d66413bfa35111ac0eca31f1db1636572702cfd967c428049b453f451d` | `e16f06b260b5169a49397e9d571b5af70317cd23792e1437232fabf718fe8871` |
| R002-009 | 292 | `35c5b9191de9f49b68c229d1af037792a54c1cdd418b7003bfc5527541c6eec6` | `90d541e87a05a5135b7ee242c82702e5cad1e2cae9e5571fcbc032d7d6d80682` | `fdf4dc67f564bc801f1fe74b1e6000a3186f19acec083f7585caef1b58671b12` | `8104cc2c46abb076affea41d2f19d40a908fbc696aee3115dfffc5b0354662b4` |
| R002-010 | 304 | `8b74893d1cc8df31c7ec8c4bcaf6b05f7dff93c23800f8e497266bb536576e92` | `d1cc08eec285573fc56f2a58a623e0b7adf33e6f75fd16b4214dd1db4b3e46a6` | `643f8e9f14148cb48741a09de7c02ec50175a2a63d8bef84821ad6ab12c4b141` | `ac49c8fe1085bfb95c0d5df8e513f7a0fa9299c9f18ce878be2362e08797517b` |
| R002-011 | 316 | `b2929496bc01afda4604941fb957f49b6cf64e0a8184e78c2b1bf993f3a8a6ac` | `2fd625e5f58b6b7b7c292b9ba90307e8583cad9d4ddb395fe9805bb06c74208b` | `2c9df82ff3c01c158b6cf1155a89b46da0d60f6705cd29ededd6bce02e9847e8` | `41f0aead689f02738cecae41605836cb9e6aceb17e1e6c0e4b7ffa57191763a8` |
| R002-012 | 327 | `25624f1c827f50c9cf055262a27ebb1a485ed0bd0305469a849d549d0926c26e` | `82319497af035b3cdcd4ee71b5fccd578074989dfa157dc54ecc5bf8ea76ceab` | `f908ad1f6d4b8df3755a634c6741abf8ae613bc59278a54c16560c16d255580f` | `7d42b9582d23667623d84307132d46e63588cbcfe63c35bccb7a52940bf5ca08` |
| R002-013 | 344 | `0cda868e19eb39388dde21e14ca951ef9d0deea5a32a8cbeab9149945e4e2408` | `9a5e8c33368dc3bbe9c5f03d3136a574cebede61fea6c575d39ddf108b92d947` | `88a7af7e123619306d887c6a9bd1f905acc4872b454df914094c038b71356e30` | `fe5323cfe9d6be9648be22ffb13a95079c6e17c13f09987f4c1b8589d27c690c` |
| R002-014 | 345 | `3fc86672e886cb8326e6729b9438d775a377d75f2e41d481e7d1934fb19f0a44` | `39f1953e5d5a7481355aa6109b16ecaebbb037957e473cc71e9ab1402d3aa9b9` | `e1f62165b6ecc14c60b08bb71a59b927adba0c3b9a8393394481cc6a4f0f8f0e` | `5d7b9e51ea700508725976f0643bd1c601afcb5373481118f8741e4660d64e59` |
| R002-015 | 363 | `b75c49d788db78afa25500c392c597a2107aed49c439549972836873e6a8ceee` | `d32c6ecdfaf0eeb42a35e7cb05bd03fc034571aaef7c7743a452422c2bcdc6bc` | `6faf85c3ffaaebff5458d13c730b28c4d6acfded07cc733b80278df6d2166cb4` | `fb96b7aa463a986df0b395398d07262b26ee71f60e84696d6e60932db59c7fc1` |
| R002-016 | 367 | `8f4615aae668d879679359f06220df42cd8d198653cfed4241724326075ac77b` | `7860d59abe6e6a85ed92cbc43c7b632982164bc89105df4df399793154bb15df` | `5f9a4088607136868645a435d919f0d07737643a2ab25ab11672234c01ca1853` | `ea556bb6d85c2d707dc36a6df92174f9b514c53a04e61c7f492a7dddf5086d9c` |
| R002-017 | 403 | `076da25d826502bcd19d69bcd9eb3a109f8b3e2dd4224482541f36dfc5ad64cc` | `5a7af99001528e86ff4d88a9bf03e4b87b08c1c4907ef4230d6dfa05a3375018` | `8bf406df3ba81a273c45b95b9c14c70ba7e4ae7c0a5e387c5544d0d608d4900d` | `7a3d56dc1bc60a57becc535d9032530e8703309049f50ff28a2ddb196171ea1f` |
| R002-018 | 413 | `3b12d82c5290396b3a7972957b15d302baf7686662eb0bf65b46c79a4e5c64d6` | `e814405fe0885a2284bec4dfdf1efa5bd0386117d02410e9ad0ec98c0e1712ab` | `e6cc08c8b1858c3d41964c220e396638c15e601f88fa9cb6493938e5fdd814c6` | `0971215a38b16f54484b9a2f11da137413f131dfc453fd9a08de1978d31360b0` |
| R002-019 | 478 | `754b459bdbb9a9f094572df632e40c980c09f7e08a25c8957d9f876f5c9f1db0` | `d97c4296d41c2a7cdf87b6e2de16dd10a5755318d9bde720c8677b8787c20ec3` | `dbec818a9a22bcfeaeeb2f292cf7bba7048f84bca05aa04f38870e483ec803d5` | `f84920fc71c885455f40e439ea052707b7936b1367ba6af67a2a7b9c3f626f9c` |
| R002-020 | 482 | `8a45d630025652ef97b71f933739e60ea6b5ee7768804f9062e20856f4cbb967` | `657b0dc782c25c6b54593dac7ccb7c4aaa95bd6da6e1a87b2e4b778f86d29b99` | `72e403affa86c748aad0332d53ef48a2bff26cad6ee96d5588c28c1b30982c3e` | `d199d4ee685de99f64461d66f3b8424c6544dd38c665812a6ff0d6f3ccfd6f6b` |

The exact selected-row difficulty strings are:

```python
R002_DIFFICULTY_BY_CASE = {
    "R002-001": "15 min - 1 hour",
    "R002-002": "<15 min fix",
    "R002-003": "15 min - 1 hour",
    "R002-004": "15 min - 1 hour",
    "R002-005": "<15 min fix",
    "R002-006": "<15 min fix",
    "R002-007": "15 min - 1 hour",
    "R002-008": "<15 min fix",
    "R002-009": "<15 min fix",
    "R002-010": "<15 min fix",
    "R002-011": ">4 hours",
    "R002-012": "15 min - 1 hour",
    "R002-013": "15 min - 1 hour",
    "R002-014": "<15 min fix",
    "R002-015": "<15 min fix",
    "R002-016": "<15 min fix",
    "R002-017": "<15 min fix",
    "R002-018": "<15 min fix",
    "R002-019": "15 min - 1 hour",
    "R002-020": "15 min - 1 hour",
}
```

The exact identity table used with those hashes is:

| Case | Instance | Dataset base SHA | Verified PR head SHA |
|---|---|---|---|
| R002-001 | `astropy__astropy-14096` | `1a4462d72eb03f30dc83a879b1dd57aac8b2c18b` | `271b2875d9aae0a5875acba0b1b27dc4885fd6e5` |
| R002-002 | `astropy__astropy-7166` | `26d147868f8a891a6009a25cd6a8576d2e1bd747` | `3306a25dee0dc9c7583f9ede5155ad9a416279d8` |
| R002-003 | `django__django-11087` | `8180ffba21bf10f4be905cb0d4890dc2bcff2788` | `f110de5c04818b8f915dcf65da37a50c1424c6e6` |
| R002-004 | `django__django-12262` | `69331bb851c34f05bc77e9fc24020fe6908b9cd5` | `e3d546a1d986f83d8698c32e13afd048b65d06eb` |
| R002-005 | `matplotlib__matplotlib-20676` | `6786f437df54ca7780a047203cbcfaa1db8dc542` | `5c08ff65b884bd03d80eba0a6de01a9d24599299` |
| R002-006 | `matplotlib__matplotlib-25287` | `f8ffce6d44127d4ea7d6491262ab30046b03294b` | `264e7d37d2ee89c6019af4e5743653f4748448e1` |
| R002-007 | `mwaskom__seaborn-3187` | `22cdfb0c93f8ec78492d87edb810f10cb7f57a31` | `9372112ea432a8b3d5bd9e11051a999b63905e86` |
| R002-008 | `pallets__flask-5014` | `7ee9ceb71e868944a46e1ff00b506772a53a4f1d` | `b8b410014d85f9861acc87c5f21c9a55a42d09c9` |
| R002-009 | `psf__requests-1766` | `847735553aeda6e6633f2b32e14ba14ba86887a4` | `92d3616b02fc0ce5b1a89d884a4b1c7d602cb364` |
| R002-010 | `pydata__xarray-4075` | `19b088636eb7d3f65ab7a1046ac672e0689371d8` | `5650db2b9076787d848fa180e4b752aa578629c4` |
| R002-011 | `pydata__xarray-6992` | `45c0a114e2b7b27b83c9618bc05b36afac82183c` | `ca01949cb889ee38aae33560b02de1f7625fd921` |
| R002-012 | `pylint-dev__pylint-7080` | `3c5eca2ded3dd2b59ebaf23eb289453b5d2930f0` | `c744a5357abfd30b84de9d171c901de4d555669b` |
| R002-013 | `pytest-dev__pytest-7490` | `7f7a36478abe7dd1fa993b115d22606aa0e35e88` | `ccad10a82908d7a12cd6024e00be11af413edf1c` |
| R002-014 | `pytest-dev__pytest-7521` | `41d211c24a6781843b174379d6d6538f5c17adb9` | `8616a5f1d989eec5e2c5f2129040149fe4cf4347` |
| R002-015 | `scikit-learn__scikit-learn-13779` | `b34751b7ed02b2cfcc36037fb729d4360480a299` | `2ca0e6c7958a8c217a4788cad08768249d6a0522` |
| R002-016 | `scikit-learn__scikit-learn-14496` | `d49a6f13af2f22228d430ac64ac2b518937800d0` | `8e8a34535f8f8743aedf88553d62e66423118423` |
| R002-017 | `sphinx-doc__sphinx-8459` | `68aa4fb29e7dfe521749e1e14f750d7afabb3481` | `333e7a447edfcb3092032ac801116e1eec193e44` |
| R002-018 | `sphinx-doc__sphinx-9230` | `567ff22716ac258b9edd2c1711d766b440ac0b11` | `9a132b4f8114f1652a9bc494b740b6632c3545a9` |
| R002-019 | `sympy__sympy-20801` | `e11d3fed782146eebbffdc9ced0364b223b84b6c` | `b5424dd3d0484087ae9d175c014e9a803e91a875` |
| R002-020 | `sympy__sympy-21612` | `b4777fdcef467b7132c055f8ac2c9a5059e6a145` | `305d1300055245c26c0261ffaf77575fb2e9f9d9` |

## Exact persisted-model field map

Task 1 implements every model below. Types such as `R002CaseId`, `GitSha`, and `Sha256` are the strict aliases above; every model inherits `R002StrictModel` unless it is an enum.

| Model | Exact fields |
|---|---|
| `R002StrictModel` | No data fields; `ConfigDict(extra="forbid", frozen=True, strict=True)` is inherited by every R-002 persisted/exported model. |
| `R002Manifest` | `pack_id: Literal["R-002"]`, `classification: Literal["public_engineering_research"]`, `eligible_for_stage_1: Literal[False]`, `does_not_advance_stage_1: Literal[True]`, `target_repository_code_executed: Literal[False]`. |
| `SWEbenchSourcePin` | `dataset_id`, `config`, `split`, `revision`, `source_url`, `parquet_path`, `byte_length`, `sha256`, `row_count`, `repository_count`, `unique_instance_count`, ordered `schema`; structural constraints accept controlled fixture values, while `load_source_manifest` pins the production constant. |
| `R002CaseManifest` | `case_id`, `instance_id`, `repository`, `pr_number`, `pr_url`, `dataset_base_commit`, `verified_pr_head_sha`, `row_index`, `difficulty`, `row_sha256`, `problem_statement_sha256`, `patch_sha256`, `test_patch_sha256`. |
| `R002SourceManifest` | all five fixed research-boundary fields, `source`, and exactly 20 ordered `cases`. |
| `SWEbenchVerifiedRow` | The exact 13 required string fields in `R002_SCHEMA`; no aliases, nulls, or extra keys. |
| `SWEbenchCriteriaSourceRow` | `repo`, `instance_id`, `base_commit`, `problem_statement`, and `difficulty`; it is created by a projected Parquet read that never requests patch, test-patch, hint, test-name, or other non-criteria columns. |
| `R002DiffLimits` | `files: Literal[32]`, `hunks: Literal[256]`, `diff_lines: Literal[50000]`, `path_characters: Literal[512]`, `line_bytes: Literal[65536]`. |
| `R002HeadFileLimits` | `bytes_per_file: Literal[4194304]`, `bytes_per_case: Literal[16777216]`, `bytes_per_pack: Literal[134217728]`, `request_count: Literal[128]`. |
| `R002ParsedLine` | `change_type`, `old_line_number`, `new_line_number`, `content`, `normalized_line_sha256`. |
| `R002ParsedHunk` | `hunk_id`, `old_start`, `old_count`, `new_start`, `new_count`, `lines`. |
| `R002ParsedFile` | `stream`, `path: R002LogicalPath`, `hunks`, `additions`, `deletions`. |
| `R002ParsedDiff` | `stream`, `files`, `file_count`, `hunk_count`, `diff_line_count`. |
| `R002ParsedCase` | `case_id`, `files`, `file_count`, `hunk_count`, `diff_line_count`. |
| `R002VerifiedLine` | `stream`, `path: R002LogicalPath`, `hunk_id`, `new_line_number`, `normalized_line_sha256`, `head_file_sha256`, `head_sha`, `permalink`. |
| `R002VerifiedCaseLines` | `case_id`, `head_sha`, `lines`; method `by_path_and_line(path, number)` requires exactly one match. |
| `R002CachedHeadFile` | `logical_path: R002LogicalPath`, `head_sha`, `byte_length`, `content_sha256`. |
| `R002CachedCase` | `case_id`, `row_sha256`, `problem_statement_sha256`, `patch_sha256`, `test_patch_sha256`, `parsed_case_sha256`, ordered `verified_lines: tuple[R002VerifiedLine, ...]`, ordered `head_files: tuple[R002CachedHeadFile, ...]`. |
| `R002CriteriaSourceCase` | `case_id`, `problem_statement_sha256`, `byte_length`; ordered exactly like the source manifest. |
| `R002CriteriaSourceIndex` | all five fixed research-boundary fields, `source_sha256`, `manifest_sha256`, `complete: Literal[True]`, and exactly 20 ordered `cases`. |
| `R002CacheIndex` | all five fixed research-boundary fields, `source_sha256`, `manifest_sha256`, `criteria_set_sha256`, `complete: Literal[True]`, and exactly 20 ordered `cases`. |
| `R002CriteriaSourcePreparationResult` | all five research-boundary fields, `phase: Literal["criteria_sources"]`, `complete: Literal[True]`, `executed_case_count`, `failed_case_count`, `skipped_case_count`, ordered case IDs, `errors`, and `hard_gate_errors`. |
| `R002PreparationCaseResult` | `case_id`, `status: Literal["prepared"]`, `head_file_count`, `candidate_line_count`. |
| `R002PreparationResult` | all five research-boundary fields, `phase: Literal["evidence"]`, `complete: Literal[True]`, `criteria_set_sha256`, `executed_case_count`, `failed_case_count`, `skipped_case_count`, `head_file_count`, `candidate_line_count`, `cases`, `errors`, `hard_gate_errors`. |
| `R002CommandFailure` | all five research-boundary fields, `ok: Literal[False]`, `operation_failed: Literal[True]`, `command: Literal["prepare", "annotate", "run"]`, `reason_code` restricted to one value from `R002_COMMAND_FAILURE_CODES`, and a one-item bounded `errors` tuple containing only that same stable reason code; it makes no partial case-count claim. |
| `R002RedactionAudit` | all five research-boundary fields, `passed: Literal[True]`, `tracked_file_count`, `raw_value_count`, and ordered `checked_value_sha256`; it contains no raw value or local path. |
| `R002CriterionCase` | `case_id`, `problem_statement_sha256`, `criteria`. |
| `R002CriterionReviewCase` | the same fields plus local-only `problem_statement`. |
| `R002CriteriaProposal` | all five research-boundary fields, `source_manifest_sha256`, both confirmation flags fixed false, and exactly 20 ordered `R002CriterionReviewCase` values. |
| `R002CriteriaSet` | all five research-boundary fields, `source_manifest_sha256`, `source_owner_confirmed: Literal[False]`, `benchmark_owner_confirmed: Literal[True]`, and exactly 20 ordered `R002CriterionCase` values. |
| `R002CandidateLineKey` | `case_id`, `criterion_id`, `stream`, `path: R002LogicalPath`, `new_line_number`, `normalized_line_sha256`. |
| `R002CandidateLabel` | `key`, `relevant`, `reason_code` restricted to the five codes in Task 11. |
| `R002ExpectedMissing` | `case_id`, `criterion_id`, one of the four static evidence types, `reason_code: Literal["no_owner_labelled_relevant_candidate"]`. |
| `R002AnnotationUniverse` | all five research-boundary fields, `source_manifest_sha256`, `criteria_set_sha256`, `candidate_count`, and ordered `candidate_keys`. |
| `R002AnnotationReviewItem` | local-only `key`, marker-free `line_content`, optional `previous_line`, optional `next_line` (each enforcing the 64 KiB UTF-8 line bound and permitting an empty line), `relevant: bool | None`, `reason_code: str | None`. |
| `R002AnnotationReview` | all five research-boundary fields, both upstream hashes, `annotation_universe_sha256`, and ordered local-only `items`. |
| `R002CandidateLabelProposal` | all five research-boundary fields, both upstream hashes, `annotation_universe_sha256`, `annotation_count`, `benchmark_owner_confirmed: Literal[False]`, ordered complete `labels`, and derived `expected_missing`. |
| `R002CandidateLabelSet` | the same fields with `benchmark_owner_confirmed: Literal[True]`. |
| `R002Metric` | `state`, `numerator`, `denominator`, `value`; zero denominator is only `not_applicable/None`. |
| `R002RetrievedCandidate` | `key`, `evidence_type`, `evidence_level`, `hunk_id`, `head_file_sha256`, `matching_rule`, `relevance_score`, `owner_label_relevant`. |
| `R002MissingExplanation` | `case_id`, `criterion_id`, `evidence_type`, `source: Literal["scopeproof_finding", "r002_retrieval_comparison"]`, `finding_status`, and one of the three fixed reason codes in Task 8. |
| `R002CaseResult` | `case_id`, `repository`, `pr_number`, `head_sha`, `criterion_count`, `annotation_candidate_count`, `retrieved_candidates`, `missing_explanations`, `gate_verdict`, `gate_reason_codes`, `blocking_criteria`, `conditional_criteria`, `unresolved_criteria`, `check_state`, `ci_reason_code`, `runtime_evidence_count`, `resolution_count`, `final_acceptance`, `separation_errors`, `reference_errors`, `limitations`. |
| `R002Metrics` | the five `R002Metric` ratios plus integer `implementation_test_separation_errors`, `immutable_reference_integrity_errors`, `parse_errors`, `schema_errors`, `source_hash_errors`, `source_sha_errors`, `unexpected_ready_count`, `normalized_rerun_mismatches`. |
| `R002DeterminismProjection` | all five research-boundary fields, the three packaged-input hashes, `scopeproof_commit`, the already redacted ordered `R002CaseResult` values, metrics, and limitations; no UUID/time/HTTP/local path. |
| `R002BenchmarkResult` | all five research-boundary fields, the three packaged-input hashes, `scopeproof_commit`, `executed_case_count`, `failed_case_count`, `skipped_case_count`, `confirmed_criterion_count`, `annotation_candidate_count`, `case_results`, `metrics`, mirrored integer `unexpected_ready_count`, `normalized_rerun_mismatches`, `hard_gate_errors`, and `limitations`. |

Model validators enforce these exact rules:

- `SWEbenchVerifiedRow` limits canonical UTF-8 JSON to 1 MiB, `problem_statement` to 128 KiB, and each patch stream to 512 KiB.
- Parsed lines require exactly the old/new number combination implied by their marker; hunks recalculate counts; parsed files/cases recalculate all declared counts and stable order.
- Every `test_patch` path remains distinguishable from every `patch` path; duplicates across or within streams fail.
- Criteria-source indexes bind the exact manifest order and problem hashes but contain no row, patch, test-patch, hint, test-name, parsed-diff, or GitHub material. Full cache cases/indexes bind exact case order, confirmed-criteria hash, row hashes, head-file identities, complete state, and the five immutable research literals.
- Criteria proposal/set cases bind exact manifest case order/problem hashes; criteria fields are complete; IDs are consecutive; every case has 1–16 criteria and at least one `MUST_HAVE`.
- Annotation and label models require stable key order, exact unique keys, exact counts, matching upstream hashes, the 250,000 cap, and no source-owner-confirmation field.
- `direct_static_candidate`, `supporting_static_candidate`, and `test_intent_candidate` require `relevant=true`; `unrelated_candidate` and `insufficient_context` require `relevant=false`; `test_intent_candidate` additionally requires `stream=test_patch`.
- Result models preserve observed gate/evidence states and exact error counters so a failed run remains inspectable; the success predicate adds hard-gate errors for any Ready verdict, E3/E4 candidate, nonzero runtime/resolution/final-acceptance state, non-unavailable CI state, or missing counter.
- `R002CaseResult` permits only actual core gate reason codes, requires reason/criterion IDs to be sorted and unique, requires exact `blocked + blocking_criteria` or `needs_review + checks_not_passing + unresolved_criteria` shape, and fixes check state/reason, runtime/resolution/final acceptance, separation errors, and reference errors to the approved successful-run boundary.
- Every case result, determinism projection, and aggregate result requires the exact ordered `R002_RESULT_LIMITATIONS`; free-form limitations cannot carry raw source text into tracked output.

### Task 1: Add strict R-002 contracts and exact source-manifest guards

**Files:**
- Create: `scopeproof_core/evals/r002_models.py`
- Create: `tests/evals/conftest.py`
- Create: `tests/evals/test_r002_models.py`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: `Criterion`, `EvidenceType`, `GateVerdict`, and `LineChangeType` from `scopeproof_core.schemas.models`.
- Produces: every R-002 type named in **Fixed interfaces and constants**, including strict draft/confirmed criteria and label types used by Tasks 6–10.

- [ ] **Step 1: Write failing strict-model and manifest tests**

Add JSON-shaped fixtures containing exactly `R002-001` through `R002-020`, exactly 12 repositories, at most two cases per repository, and the fixed research literals. Because `R002StrictModel` is strict, validate those dictionaries with `model_validate_json(json.dumps(payload))`; use `model_validate` only when the fixture already contains tuples, enum instances, and nested model instances. Mutate copied JSON dictionaries for invalid cases so every intended Pydantic validator executes.

```python
def test_source_manifest_requires_exact_research_boundary(r002_manifest_payload):
    manifest = R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))
    assert manifest.pack_id == "R-002"
    assert manifest.classification == "public_engineering_research"
    assert manifest.eligible_for_stage_1 is False
    assert manifest.does_not_advance_stage_1 is True
    assert manifest.target_repository_code_executed is False
    assert [case.case_id for case in manifest.cases] == [
        f"R002-{number:03d}" for number in range(1, 21)
    ]
    assert len({case.repository for case in manifest.cases}) == 12
    assert case_projection_sha256(manifest.cases) == R002_APPROVED_CASES_SHA256

@pytest.mark.parametrize(
    ("field", "value"),
    [("classification", "alpha"), ("eligible_for_stage_1", True),
     ("does_not_advance_stage_1", False),
     ("target_repository_code_executed", True)],
)
def test_research_boundary_cannot_be_promoted(r002_manifest_payload, field, value):
    r002_manifest_payload[field] = value
    with pytest.raises(ValidationError):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))

def test_case_identity_binds_instance_repository_pr_and_url(r002_manifest_payload):
    r002_manifest_payload["cases"][0]["pr_url"] = "https://github.com/other/repo/pull/1"
    with pytest.raises(ValidationError, match="case identity fields disagree"):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))

def test_confirmed_criteria_reject_source_owner_confirmation(r002_criteria_payload):
    r002_criteria_payload["source_owner_confirmed"] = True
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(json.dumps(r002_criteria_payload))

def test_every_persisted_model_forbids_extra_fields(r002_manifest_payload):
    r002_manifest_payload["unexpected"] = "not allowed"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))

@pytest.mark.parametrize("value", ["", ".", "..", "a/../b", "/absolute", "a\\b"])
def test_r002_logical_path_rejects_empty_current_parent_and_platform_paths(value):
    with pytest.raises(ValueError, match="invalid R-002 logical path"):
        validate_r002_logical_path(value)
```

Also cover duplicate IDs/URLs/instances, non-consecutive case IDs, wrong ordering, 19/21 cases, 11 repositories, three cases for one repository, malformed Git/SHA-256 strings, zero criteria, 17 criteria, no `MUST_HAVE`, unstable criterion ordering, unconfirmed confirmed-set models, incomplete/duplicate annotation keys, invalid metric zero-denominator representation, and extra fields on every persisted model family.
Add loader-boundary tests proving structural `R002SourceManifest.model_validate_json` accepts a controlled 20-case/12-repository fixture, while `load_source_manifest` rejects (a) its non-production source pin and (b) any one-field mutation of each approved case-projection field, including `verified_pr_head_sha`. A final test proves the exact `R002_SOURCE` plus exact `R002_APPROVED_CASES_SHA256` file loads. This keeps fixture flexibility out of the installed production boundary.

- [ ] **Step 2: Run the model tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_models.py \
  tests/test_repository_contracts.py::test_r002_packaged_inputs_are_redacted_and_strict
```

Expected: collection fails because `scopeproof_core.evals.r002_models` and `evals/r002/` do not exist.

- [ ] **Step 3: Implement the strict base and source models**

Use strict annotated IDs and literal research boundaries. Canonical bytes are compact UTF-8 JSON with sorted keys, `ensure_ascii=False`, and no trailing newline.

```python
class R002StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

class R002Error(Exception):
    allowed_reason_codes: ClassVar[frozenset[str]]

    def __init__(self, reason_code: str) -> None:
        if reason_code not in self.allowed_reason_codes:
            raise RuntimeError("unregistered R-002 reason code")
        self.reason_code = reason_code
        super().__init__(reason_code)

class R002Manifest(R002StrictModel):
    pack_id: Literal["R-002"] = "R-002"
    classification: Literal["public_engineering_research"] = "public_engineering_research"
    eligible_for_stage_1: Literal[False] = False
    does_not_advance_stage_1: Literal[True] = True
    target_repository_code_executed: Literal[False] = False

class SWEbenchSourcePin(R002StrictModel):
    dataset_id: str = Field(min_length=1)
    config: str = Field(min_length=1)
    split: str = Field(min_length=1)
    revision: GitSha
    source_url: str = Field(pattern=r"^https://huggingface\.co/.+\.parquet$")
    parquet_path: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.parquet$")
    byte_length: StrictInt = Field(gt=0)
    sha256: Sha256
    row_count: StrictInt = Field(gt=0)
    repository_count: StrictInt = Field(gt=0)
    unique_instance_count: StrictInt = Field(gt=0)
    schema: tuple[str, ...] = Field(min_length=1)

class R002CaseManifest(R002StrictModel):
    case_id: R002CaseId
    instance_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-\d+$")
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    pr_url: str = Field(pattern=r"^https://github\.com/.+/.+/pull/\d+$")
    dataset_base_commit: GitSha
    verified_pr_head_sha: GitSha
    row_index: StrictInt = Field(ge=0, lt=500)
    difficulty: str = Field(min_length=1, max_length=64)
    row_sha256: Sha256
    problem_statement_sha256: Sha256
    patch_sha256: Sha256
    test_patch_sha256: Sha256

    @model_validator(mode="after")
    def bind_identity(self) -> Self:
        expected_instance = self.repository.replace("/", "__") + f"-{self.pr_number}"
        expected_url = f"https://github.com/{self.repository}/pull/{self.pr_number}"
        if self.instance_id != expected_instance or self.pr_url != expected_url:
            raise ValueError("case identity fields disagree")
        return self

class R002SourceManifest(R002Manifest):
    source: SWEbenchSourcePin
    cases: tuple[R002CaseManifest, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def validate_cohort(self) -> Self:
        expected_ids = [f"R002-{number:03d}" for number in range(1, 21)]
        if [case.case_id for case in self.cases] != expected_ids:
            raise ValueError("case IDs must be consecutive R002-001 through R002-020")
        if list(self.cases) != sorted(self.cases, key=lambda case: (case.repository, case.instance_id)):
            raise ValueError("cases must be ordered by repository and instance ID")
        for values, label in (
            ([case.instance_id for case in self.cases], "instance IDs"),
            ([case.pr_url for case in self.cases], "PR URLs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        counts = Counter(case.repository for case in self.cases)
        if len(counts) != 12 or max(counts.values()) > 2:
            raise ValueError("cohort must cover 12 repositories with at most two cases each")
        return self

def canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")

def canonical_sha256(value: BaseModel | dict[str, object]) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()

def case_projection_sha256(cases: Sequence[R002CaseManifest]) -> str:
    payload = [case.model_dump(mode="json") for case in cases]
    return sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()

def load_source_manifest(path: Path) -> R002SourceManifest:
    value = R002SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source.model_dump(mode="json") != R002_SOURCE:
        raise R002SourceError("source_pin_mismatch")
    if case_projection_sha256(value.cases) != R002_APPROVED_CASES_SHA256:
        raise R002SourceError("approved_cohort_mismatch")
    return value

def load_confirmed_criteria(path: Path, manifest_sha256: str) -> R002CriteriaSet:
    value = R002CriteriaSet.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source_manifest_sha256 != manifest_sha256:
        raise R002AnnotationError("criteria_manifest_drift")
    return value

def load_confirmed_labels(
    path: Path, manifest_sha256: str, criteria_sha256: str
) -> R002CandidateLabelSet:
    value = R002CandidateLabelSet.model_validate_json(path.read_text(encoding="utf-8"))
    if (
        value.source_manifest_sha256 != manifest_sha256
        or value.criteria_set_sha256 != criteria_sha256
    ):
        raise R002AnnotationError("candidate_label_upstream_drift")
    return value
```

Define `R002SourceError` and `R002AnnotationError` beside the loaders in `r002_models.py` to avoid import cycles; define closed reason-code sets for `R002DiffError`, `R002ReferenceError`, `R002CacheError`, `R002NetworkPolicyError`, `R002PreparationError`, and `R002RunError` in their owning modules. Tests enumerate every raise site and fail if a literal code is absent from its subclass allowlist. Exceptions carry only the stable code; diagnostic bodies stay in local test assertions, never CLI output.

Place the three loader functions after all model class definitions in the real file so every return type is defined at import time.

- [ ] **Step 4: Implement criteria, annotation, cache, and result contracts**

Add these exact model families to the same file. Draft models permit `benchmark_owner_confirmed=False`; final packaged models require `Literal[True]`. `R002CriteriaSet` rejects `source_owner_confirmed=True`, binds all 20 problem hashes, enforces 1–16 criteria with at least one `MUST_HAVE`, unique ordered IDs, and complete non-default serialized criterion fields. `R002CandidateLabelSet` binds both upstream hashes, sorted unique keys, exact universe count/hash, complete labels, derived expected-missing records, and owner confirmation.

```python
class R002CriterionCase(R002StrictModel):
    case_id: R002CaseId
    problem_statement_sha256: Sha256
    criteria: tuple[Criterion, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_criteria(self) -> Self:
        ids = [item.criterion_id for item in self.criteria]
        if ids != [f"AC-{number:02d}" for number in range(1, len(ids) + 1)]:
            raise ValueError("criterion IDs must be ordered and consecutive")
        if not any(item.priority is Priority.MUST_HAVE for item in self.criteria):
            raise ValueError("every case requires at least one MUST_HAVE criterion")
        if any(item.criterion_source is not CriterionSource.USER_CONFIRMED for item in self.criteria):
            raise ValueError("R-002 criteria must use the operator-confirmed source value")
        if any(
            item.source_span is None
            or validate_r002_source_span(item.source_span) != item.source_span
            for item in self.criteria
        ):
            raise ValueError("every R-002 criterion requires a bounded problem-statement span")
        if any(len(item.text) > 512 or "\n" in item.text or "\r" in item.text
               for item in self.criteria):
            raise ValueError("R-002 criteria must be bounded single-line paraphrases")
        return self

class R002CriterionReviewCase(R002CriterionCase):
    problem_statement: str = Field(min_length=1, max_length=131_072)

class R002CriteriaProposal(R002Manifest):
    source_manifest_sha256: Sha256
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[False] = False
    cases: tuple[R002CriterionReviewCase, ...] = Field(min_length=20, max_length=20)

class R002CriteriaSet(R002Manifest):
    source_manifest_sha256: Sha256
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[True]
    cases: tuple[R002CriterionCase, ...] = Field(min_length=20, max_length=20)

class R002CandidateLineKey(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    stream: R002DiffStream
    path: R002LogicalPath
    new_line_number: StrictInt = Field(ge=1)
    normalized_line_sha256: Sha256

class R002CandidateLabel(R002StrictModel):
    key: R002CandidateLineKey
    relevant: bool
    reason_code: Literal[
        "direct_static_candidate",
        "supporting_static_candidate",
        "test_intent_candidate",
        "unrelated_candidate",
        "insufficient_context",
    ]

class R002ExpectedMissing(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=r"^AC-\d{2,}$")
    evidence_type: Literal[
        EvidenceType.IMPLEMENTATION, EvidenceType.TEST,
        EvidenceType.DOCUMENTATION, EvidenceType.CONTRACT,
    ]
    reason_code: Literal["no_owner_labelled_relevant_candidate"]

class R002AnnotationUniverse(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_count: StrictInt = Field(ge=1, le=250_000)
    candidate_keys: tuple[R002CandidateLineKey, ...] = Field(min_length=1, max_length=250_000)

class R002CandidateLabelSet(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    annotation_count: StrictInt = Field(ge=1, le=250_000)
    benchmark_owner_confirmed: Literal[True]
    labels: tuple[R002CandidateLabel, ...] = Field(min_length=1, max_length=250_000)
    expected_missing: tuple[R002ExpectedMissing, ...]

class R002CandidateLabelProposal(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    annotation_count: StrictInt = Field(ge=1, le=250_000)
    benchmark_owner_confirmed: Literal[False] = False
    labels: tuple[R002CandidateLabel, ...] = Field(min_length=1, max_length=250_000)
    expected_missing: tuple[R002ExpectedMissing, ...]

class R002Metric(R002StrictModel):
    state: R002MetricState
    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    value: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_ratio(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("metric numerator cannot exceed denominator")
        if self.denominator == 0:
            if self.state is not R002MetricState.NOT_APPLICABLE or self.value is not None:
                raise ValueError("zero denominator must be not_applicable")
        elif self.state is not R002MetricState.VALUE or self.value != self.numerator / self.denominator:
            raise ValueError("nonzero denominator must report the exact ratio")
        return self
```

Implement every remaining class in **Exact persisted-model field map** with those exact names and fields. Apply every validator in the rule list immediately below that table; use tuples with explicit `Field` bounds for persisted collections and reject unknown, duplicate, missing, or unsorted cross-references.

- [ ] **Step 5: Add the initial repository redaction contract**

Add this test before the real input files exist; it permits an absent/partial directory only until Task 12 replaces it with the exact three-file contract.

```python
def test_r002_packaged_inputs_are_redacted_and_strict() -> None:
    root = Path("evals/r002")
    allowed = {"source_manifest.json", "criteria.json", "candidate_labels.json"}
    assert not root.is_symlink()
    if not root.exists():
        return
    assert root.is_dir()
    entries = tuple(root.rglob("*"))
    assert all(path.is_file() and not path.is_symlink() for path in entries)
    assert all(path.parent == root for path in entries)
    assert {path.relative_to(root).as_posix() for path in entries} <= allowed
    forbidden_keys = {
        "problem_statement", "patch", "test_patch", "hints_text",
        "FAIL_TO_PASS", "PASS_TO_PASS", "source_text", "excerpt", "context_excerpt",
    }
    for path in entries:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stack = [payload]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                assert forbidden_keys.isdisjoint(value)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
```

- [ ] **Step 6: Run tests and verify GREEN**

Run the Step 2 command. Expected: all R-002 model tests and the initial redaction contract pass.

- [ ] **Step 7: Commit the contracts slice**

```bash
git add scopeproof_core/evals/r002_models.py tests/evals/conftest.py \
  tests/evals/test_r002_models.py tests/test_repository_contracts.py
git commit -m "feat: define strict R-002 research contracts"
```

### Task 2: Decode, validate, hash, and deterministically select source rows

**Files:**
- Create: `scopeproof_core/evals/r002_source.py`
- Create: `tests/evals/test_r002_source.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: `SWEbenchSourcePin`, `SWEbenchCriteriaSourceRow`, `SWEbenchVerifiedRow`, `R002SourceManifest`, `canonical_json_bytes`, and `canonical_sha256` from Task 1.
- Produces: `decode_criteria_source_rows(source, pin)`, `decode_verified_parquet(source, pin)`, the criteria-source and full-row `select_r002_*` functions, `manifest_case_from_row(case_id, row_index, row, verified_pr_head_sha)`, and both `validate_manifest_*` functions.

- [ ] **Step 1: Add the exact free research dependency**

Add the group without changing normal application dependencies:

```toml
[project.optional-dependencies]
dev = [
  "pytest>=9.0.3,<10",
  "pytest-cov>=6,<7",
  "ruff>=0.5,<1",
]
research = [
  "pyarrow==25.0.0",
]
```

Run:

```bash
uv lock
uv sync --extra dev --extra research --locked
```

Expected: both commands exit zero, `uv.lock` contains `pyarrow` 25.0.0, and the ScopeProof package records `research` as an optional dependency. The implementation must describe this as R-002's direct preparation dependency; it must not claim that normal Streamlit dependency resolution can never include pyarrow transitively.

- [ ] **Step 2: Write failing Parquet/source tests**

Construct a tiny valid Parquet file in `tmp_path` with the exact 13 string columns and use a structurally valid test-only pin whose row/repository counts and file hash match the fixture. Test strict schema order/type, nested-type rejection, row/null/unique-instance/repository counts, 16 MiB metadata bound, selected-row 1 MiB canonical bound, 128 KiB problem bound, 512 KiB per patch stream, canonical Unicode preservation, and outcome-blind selection. Add a recording Parquet wrapper proving `decode_criteria_source_rows` requests only `repo`, `instance_id`, `base_commit`, `problem_statement`, and `difficulty`; any access to `patch`, `test_patch`, `hints_text`, `FAIL_TO_PASS`, or `PASS_TO_PASS` before criteria confirmation fails the test.

```python
def test_canonical_row_hash_preserves_unicode_and_field_order(tmp_path):
    row = swebench_row(problem_statement="café", patch="+  value\t", test_patch="+test")
    path, pin = write_parquet_and_pin(tmp_path, [row])
    with path.open("rb") as source:
        decoded = decode_verified_parquet(source, pin)
    assert canonical_json_bytes(decoded[0]).decode("utf-8") == (
        '{"FAIL_TO_PASS":"[]","PASS_TO_PASS":"[]","base_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        '"created_at":"2024-01-01T00:00:00Z","difficulty":"<15 min fix",'
        '"environment_setup_commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
        '"hints_text":"","instance_id":"scopeproof__fixture-1","patch":"+  value\\t",'
        '"problem_statement":"café","repo":"scopeproof/fixture","test_patch":"+test","version":"1"}'
    )

def test_selection_is_repository_balanced_and_hash_ranked(full_selection_rows):
    selected = select_r002_rows(full_selection_rows, R002_SOURCE["sha256"])
    assert len(selected) == 20
    assert len({row.repo for row in selected}) == 12
    assert max(Counter(row.repo for row in selected).values()) == 2
    assert [row.instance_id for row in selected] == APPROVED_INSTANCE_IDS
```

- [ ] **Step 3: Run source tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_source.py
```

Expected: FAIL because `r002_source.py` is absent.

- [ ] **Step 4: Implement canonical row validation and selection**

Keep the `pyarrow` imports inside the two decode functions. Both take a seekable binary handle produced by the secure downloader, validate the complete file size/hash and Parquet metadata before calling `read()`, and sum every row-group column's `total_uncompressed_size`. `decode_criteria_source_rows` then reads only the five allowlisted projected columns and validates repository/instance counts and deterministic selection without constructing `SWEbenchVerifiedRow`; `decode_verified_parquet` alone reads all 13 columns, and it is never called before confirmed criteria load succeeds.

```python
def _validate_parquet_container(source: BinaryIO, pin: SWEbenchSourcePin):
    import pyarrow as pa
    import pyarrow.parquet as pq

    source.seek(0)
    digest = sha256()
    length = 0
    while chunk := source.read(64 * 1024):
        length += len(chunk)
        digest.update(chunk)
    if length != pin.byte_length or digest.hexdigest() != pin.sha256:
        raise R002SourceError("parquet_bytes_mismatch")
    source.seek(0)
    parquet = pq.ParquetFile(source)
    metadata = parquet.metadata
    if metadata.num_rows != pin.row_count:
        raise R002SourceError("parquet_row_count_mismatch")
    if tuple(parquet.schema_arrow.names) != pin.schema:
        raise R002SourceError("parquet_schema_mismatch")
    if any(not pa.types.is_string(field.type) for field in parquet.schema_arrow):
        raise R002SourceError("parquet_field_type_mismatch")
    uncompressed = sum(
        metadata.row_group(group).column(column).total_uncompressed_size
        for group in range(metadata.num_row_groups)
        for column in range(metadata.num_columns)
    )
    if uncompressed > 16 * 1024 * 1024:
        raise R002SourceError("parquet_uncompressed_limit")
    return parquet

def decode_verified_parquet(
    source: BinaryIO, pin: SWEbenchSourcePin
) -> list[SWEbenchVerifiedRow]:
    parquet = _validate_parquet_container(source, pin)
    rows = [SWEbenchVerifiedRow.model_validate(item) for item in parquet.read().to_pylist()]
    validate_row_collection(rows, pin)
    return rows

def decode_criteria_source_rows(
    source: BinaryIO, pin: SWEbenchSourcePin
) -> list[SWEbenchCriteriaSourceRow]:
    parquet = _validate_parquet_container(source, pin)
    projected = parquet.read(columns=R002_CRITERIA_SOURCE_COLUMNS).to_pylist()
    rows = [SWEbenchCriteriaSourceRow.model_validate(item) for item in projected]
    validate_criteria_source_collection(rows, pin)
    return rows

def select_r002_rows(
    rows: Sequence[SWEbenchVerifiedRow], parquet_sha256: str
) -> list[SWEbenchVerifiedRow]:
    grouped: dict[str, list[SWEbenchVerifiedRow]] = defaultdict(list)
    for row in rows:
        grouped[row.repo].append(row)
    repository_order = sorted(grouped, key=lambda repo: (-len(grouped[repo]), repo))
    quotas = {repo: 1 for repo in grouped}
    for repo in repository_order[:8]:
        quotas[repo] += 1
    chosen = []
    for repo, candidates in grouped.items():
        ranked = sorted(
            candidates,
            key=lambda row: sha256(
                f"{parquet_sha256}:{row.instance_id}".encode("utf-8")
            ).hexdigest(),
        )
        chosen.extend(ranked[: quotas[repo]])
    return sorted(chosen, key=lambda row: (row.repo, row.instance_id))

def validate_row_collection(
    rows: Sequence[SWEbenchVerifiedRow], pin: SWEbenchSourcePin
) -> None:
    if len(rows) != pin.row_count:
        raise R002SourceError("row_count_mismatch")
    instance_ids = [row.instance_id for row in rows]
    if len(set(instance_ids)) != pin.unique_instance_count:
        raise R002SourceError("unique_instance_count_mismatch")
    if len({row.repo for row in rows}) != pin.repository_count:
        raise R002SourceError("repository_count_mismatch")

def manifest_case_from_row(
    case_id: R002CaseId,
    row_index: int,
    row: SWEbenchVerifiedRow,
    verified_pr_head_sha: GitSha,
) -> R002CaseManifest:
    match = re.fullmatch(
        re.escape(row.repo.replace("/", "__")) + r"-(\d+)", row.instance_id
    )
    if match is None:
        raise R002SourceError("instance_pr_suffix_mismatch")
    pr_number = int(match.group(1))
    row_bytes = canonical_json_bytes(row)
    return R002CaseManifest(
        case_id=case_id,
        instance_id=row.instance_id,
        repository=row.repo,
        pr_number=pr_number,
        pr_url=f"https://github.com/{row.repo}/pull/{pr_number}",
        dataset_base_commit=row.base_commit,
        verified_pr_head_sha=verified_pr_head_sha,
        row_index=row_index,
        difficulty=row.difficulty,
        row_sha256=sha256(row_bytes).hexdigest(),
        problem_statement_sha256=sha256(row.problem_statement.encode("utf-8")).hexdigest(),
        patch_sha256=sha256(row.patch.encode("utf-8")).hexdigest(),
        test_patch_sha256=sha256(row.test_patch.encode("utf-8")).hexdigest(),
    )

def validate_manifest_rows(
    manifest: R002SourceManifest,
    rows: Sequence[SWEbenchVerifiedRow],
) -> list[SWEbenchVerifiedRow]:
    selected = select_r002_rows(rows, manifest.source.sha256)
    if [row.instance_id for row in selected] != [case.instance_id for case in manifest.cases]:
        raise R002SourceError("manifest_selection_mismatch")
    row_indexes = {row.instance_id: index for index, row in enumerate(rows)}
    for case, row in zip(manifest.cases, selected, strict=True):
        observed = manifest_case_from_row(
            case.case_id,
            row_indexes[row.instance_id],
            row,
            case.verified_pr_head_sha,
        )
        if observed != case:
            raise R002SourceError("manifest_row_mismatch")
    return selected
```

The shared private `_validate_parquet_container` returns a `ParquetFile` over the still-open handle. `decode_criteria_source_rows` must never request, compute, return, log, or persist patch/test-patch/hint/test-name values. Implement `select_r002_criteria_source_rows` with the exact same repository quotas and hash ranking as `select_r002_rows`, using only `repo` and `instance_id`. `validate_manifest_criteria_sources` compares exact selected order, base commit, difficulty, row index, and problem-statement hash against the manifest and returns only the selected 20 projected rows.

`validate_manifest_rows` must recompute the complete selection, compare exact instance order, compare every fixed row index/hash/base commit, and return the 20 selected rows only after every comparison passes.

The closed `R002SourceError` allowlist is exactly: `source_pin_mismatch`, `approved_cohort_mismatch`, `parquet_bytes_mismatch`, `parquet_row_count_mismatch`, `parquet_schema_mismatch`, `parquet_field_type_mismatch`, `parquet_uncompressed_limit`, `row_count_mismatch`, `unique_instance_count_mismatch`, `repository_count_mismatch`, `instance_pr_suffix_mismatch`, `manifest_selection_mismatch`, and `manifest_row_mismatch`. The criteria-only validator reuses `manifest_selection_mismatch` and `manifest_row_mismatch`; no source exception includes a case ID or prose in its args. Tests enumerate the raise literals and require exact equality with this allowlist.

- [ ] **Step 5: Run source tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_models.py tests/evals/test_r002_source.py
uv run ruff check scopeproof_core/evals/r002_models.py scopeproof_core/evals/r002_source.py \
  tests/evals/test_r002_models.py tests/evals/test_r002_source.py
```

Expected: all tests pass and Ruff reports no findings.

- [ ] **Step 6: Commit the source slice**

```bash
git add pyproject.toml uv.lock scopeproof_core/evals/r002_source.py \
  tests/evals/test_r002_source.py
git commit -m "feat: validate pinned R-002 source rows"
```

### Task 3: Parse bounded unified diffs and expose unchanged path classification

**Files:**
- Create: `scopeproof_core/evals/r002_diff.py`
- Create: `tests/evals/test_r002_diff.py`
- Modify: `scopeproof_core/retrieval/engine.py`
- Modify: `tests/retrieval/test_engine.py`

**Interfaces:**
- Consumes: `R002DiffStream`, parsed models, `ChangedFile`, `ChangedLine`, and `LineChangeType`.
- Produces: `parse_unified_diff`, `parse_case_diffs`, `parsed_case_to_changed_files`, and `classify_changed_path_evidence_type(path: str) -> EvidenceType`.

- [ ] **Step 1: Write failing path-classification and valid-parser tests**

Use ScopeProof-authored diff bytes containing two files, three hunks, CRLF, lone CR, tabs, blank added lines, removed lines, and context lines. Assert exact old/new line numbers and hashes of the marker-free, newline-free UTF-8 content.

```python
def test_parser_preserves_new_side_identity_and_whitespace():
    parsed = parse_unified_diff(
        b"diff --git a/src/a.py b/src/a.py\r\n--- a/src/a.py\r\n+++ b/src/a.py\r\n"
        b"@@ -2,2 +2,3 @@\r\n keep\r+\tadded  \r\n-old\r\n+\r\n",
        stream=R002DiffStream.PATCH,
    )
    lines = parsed.files[0].hunks[0].lines
    assert [(line.change_type.value, line.old_line_number, line.new_line_number, line.content) for line in lines] == [
        ("context", 2, 2, "keep"),
        ("added", None, 3, "\tadded  "),
        ("removed", 3, None, "old"),
        ("added", None, 4, ""),
    ]
    assert lines[1].normalized_line_sha256 == sha256(b"\tadded  ").hexdigest()

def test_test_patch_path_uses_existing_test_classification():
    assert classify_changed_path_evidence_type("tests/test_widget.py") is EvidenceType.TEST
```

- [ ] **Step 2: Write failing adversarial parser tests**

Parameterize exact rejected forms: invalid UTF-8; absolute, `..`, NUL, backslash, blank, or >512-character paths; `rename from/to`, `copy from/to`, binary markers, new-file/deleted-file modes, `/dev/null`; mismatched `diff --git`/`---`/`+++` paths; malformed/overlapping hunk ranges; hunk count mismatch; duplicate path inside one stream or across streams; >32 files, >256 hunks, >50,000 diff lines, and >64 KiB marker-free line bytes. Add a cross-stream case with individually valid streams whose combined lines exceed 50,000 and require `case_diff_line_limit`. Each test asserts `R002DiffError` with a stable reason code rather than partial output.

```python
@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        (b"diff --git a/../x b/../x\n", "invalid_path"),
        (b"diff --git a/x b/x\nrename from x\nrename to y\n", "unsupported_rename"),
        (b"diff --git a/x b/x\nBinary files a/x and b/x differ\n", "binary_diff"),
    ],
)
def test_parser_rejects_ambiguous_or_unsafe_records(raw, reason):
    with pytest.raises(R002DiffError, match=reason):
        parse_unified_diff(raw, stream=R002DiffStream.PATCH)
```

- [ ] **Step 3: Run parser tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_diff.py tests/retrieval/test_engine.py
```

Expected: FAIL because the R-002 parser and public path-classification helper do not exist.

- [ ] **Step 4: Extract the existing classifier without changing behavior**

Move only the path-based body from `_evidence_type` into a public pure function and keep `_evidence_type` as a wrapper so existing call sites and outputs remain unchanged.

```python
def classify_changed_path_evidence_type(path_value: str) -> EvidenceType:
    path = PurePosixPath(path_value)
    normalized_parts = tuple(part.casefold() for part in path.parts)
    lower_path = path_value.casefold()
    name = path.name.casefold()
    if (
        any(part in {"test", "tests", "eval", "evals"} for part in normalized_parts)
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    ):
        return EvidenceType.TEST
    if path.suffix.casefold() in {".md", ".rst"} or "docs" in normalized_parts:
        return EvidenceType.DOCUMENTATION
    if "migration" in lower_path or "alembic" in lower_path:
        return EvidenceType.CONTRACT
    if any(marker in lower_path for marker in ("openapi", "schema", "contract")):
        return EvidenceType.CONTRACT
    return EvidenceType.IMPLEMENTATION

def _evidence_type(file: ChangedFile) -> EvidenceType:
    return classify_changed_path_evidence_type(file.path)
```

- [ ] **Step 5: Implement the bounded parser and adapter**

Normalize bytes with `raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")`, decode strict UTF-8, split only on `"\n"`, count and reject before appending, and require exact file/hunk state transitions. The hunk loop must use marker-specific counters and reject any observed count that differs from its header.

```python
def _parsed_line(marker: str, content: str, old_line: int, new_line: int) -> R002ParsedLine:
    if len(content.encode("utf-8")) > 64 * 1024:
        raise R002DiffError("line_limit")
    if marker == " ":
        kind, old_number, new_number = LineChangeType.CONTEXT, old_line, new_line
    elif marker == "+":
        kind, old_number, new_number = LineChangeType.ADDED, None, new_line
    elif marker == "-":
        kind, old_number, new_number = LineChangeType.REMOVED, old_line, None
    else:
        raise R002DiffError("invalid_line_marker")
    return R002ParsedLine(
        change_type=kind,
        old_line_number=old_number,
        new_line_number=new_number,
        content=content,
        normalized_line_sha256=sha256(content.encode("utf-8")).hexdigest(),
    )

def parse_case_diffs(
    *, case_id: R002CaseId, patch: str, test_patch: str,
    limits: R002DiffLimits = DEFAULT_R002_DIFF_LIMITS,
) -> R002ParsedCase:
    parsed = [
        parse_unified_diff(patch.encode("utf-8"), stream=R002DiffStream.PATCH, limits=limits),
        parse_unified_diff(test_patch.encode("utf-8"), stream=R002DiffStream.TEST_PATCH, limits=limits),
    ]
    files = tuple(file for diff in parsed for file in diff.files)
    paths = [file.path for file in files]
    if len(paths) != len(set(paths)):
        raise R002DiffError("duplicate_path_across_streams")
    if len(files) > limits.files or sum(len(file.hunks) for file in files) > limits.hunks:
        raise R002DiffError("case_limit")
    if sum(diff.diff_line_count for diff in parsed) > limits.diff_lines:
        raise R002DiffError("case_diff_line_limit")
    return R002ParsedCase(case_id=case_id, files=files)

def parsed_case_to_changed_files(parsed: R002ParsedCase) -> list[ChangedFile]:
    return [
        ChangedFile(
            path=file.path,
            status="modified",
            additions=file.additions,
            deletions=file.deletions,
            changes=file.additions + file.deletions,
            patch="",
            lines=[
                ChangedLine(
                    change_type=line.change_type,
                    line_number=(line.old_line_number if line.change_type is LineChangeType.REMOVED else line.new_line_number),
                    content=line.content,
                )
                for hunk in file.hunks for line in hunk.lines
            ],
        )
        for file in parsed.files
    ]
```

Complete `parse_unified_diff` with this only accepted file grammar: `diff --git a/<path> b/<path>`, one optional `index <hex>..<hex>[ <mode>]` line, exact `--- a/<path>`, exact `+++ b/<path>`, then one or more hunks. Reject every other file metadata line, including mode changes. Use hunk grammar `^@@ -old_start[,old_count] +new_start[,new_count] @@(?: .*)?$`, default omitted count `1`, stable `hunk_id = "<stream>:<path>:H<one-based-index>"`, strict count reconciliation, and every rejection listed in Step 2. Accept `\ No newline at end of file` only immediately after a hunk content line, do not count it as content, and reject it elsewhere. Require successive old-side and new-side hunk ranges to be non-overlapping. Do not call the simpler `_parse_patch` in `github/client.py`.

- [ ] **Step 6: Run parser tests and both existing benchmarks**

Run:

```bash
uv run pytest -q tests/evals/test_r002_diff.py tests/retrieval/test_engine.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
```

Expected: focused tests pass; the constructed benchmark executes exactly 12 cases with no mismatches; comparison executes exactly two cases with counts `unchanged=1`, `relocated=1`, `modified=1`, `added=3`, `removed=3` and no mismatches.

- [ ] **Step 7: Commit the parser slice**

```bash
git add scopeproof_core/evals/r002_diff.py scopeproof_core/retrieval/engine.py \
  tests/evals/test_r002_diff.py tests/retrieval/test_engine.py
git commit -m "feat: parse bounded R-002 diffs"
```

### Task 4: Verify every candidate line against immutable PR-head files

**Files:**
- Create: `scopeproof_core/evals/r002_verify.py`
- Create: `tests/evals/test_r002_verify.py`

**Interfaces:**
- Consumes: `R002CaseManifest`, `R002ParsedCase`, `R002VerifiedLine`, `R002VerifiedCaseLines`, `R002CandidateLineKey`, `EvidenceItem`, and `classify_changed_path_evidence_type`.
- Produces: `verify_case_head_files`, `verify_evidence_reference`, `candidate_permalink`, and `assert_test_stream_separation`.

- [ ] **Step 1: Write failing immutable-line tests**

Create one parsed implementation file and one parsed test file from ScopeProof-authored diffs, then provide head-file bytes keyed by repository-relative path. Cover both added and context lines and prove removed lines are ignored.

```python
def test_added_and_context_lines_are_bound_to_head_bytes(r002_case_manifest):
    parsed = parse_case_diffs(
        case_id=r002_case_manifest.case_id,
        patch=IMPLEMENTATION_DIFF,
        test_patch=TEST_DIFF,
    )
    verified = verify_case_head_files(
        case=r002_case_manifest,
        parsed=parsed,
        head_file_bytes={
            "src/widget.py": b"before\nadded  \nafter\n",
            "tests/test_widget.py": b"def test_added():\n    assert True\n",
        },
    )
    assert {(line.stream.value, line.path, line.new_line_number) for line in verified.lines} == {
        ("patch", "src/widget.py", 1),
        ("patch", "src/widget.py", 2),
        ("patch", "src/widget.py", 3),
        ("test_patch", "tests/test_widget.py", 1),
        ("test_patch", "tests/test_widget.py", 2),
    }
    assert all(line.head_sha == r002_case_manifest.verified_pr_head_sha for line in verified.lines)

def test_evidence_mapping_uses_sidecar_line_not_trimmed_excerpt(
    r002_case_manifest, verified_case_lines
):
    evidence = evidence_item(
        criterion_id="AC-01", file_path="src/widget.py", line_start=2,
        excerpt="added", commit_sha=r002_case_manifest.verified_pr_head_sha,
    )
    key = verify_evidence_reference(
        case=r002_case_manifest, evidence=evidence, verified_lines=verified_case_lines
    )
    assert key.normalized_line_sha256 == sha256(b"added  ").hexdigest()
```

- [ ] **Step 2: Write failing integrity and separation tests**

Assert fail-closed errors for missing head file, non-UTF-8 bytes, file >4 MiB, case total >16 MiB, line number beyond EOF, changed whitespace/content, wrong head SHA, wrong permalink, duplicate `(path,new_line_number)`, test-stream path classified as non-test, implementation/test path collision, and evidence not present in the verified sidecar.

```python
@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda files: files.pop("src/widget.py"), "head_file_missing"),
        (lambda files: files.__setitem__("src/widget.py", b"before\nchanged\nafter\n"),
         "head_line_mismatch"),
        (lambda files: files.__setitem__("src/widget.py", b"\xff"), "head_file_not_utf8"),
    ],
)
def test_head_verification_fails_closed(r002_case_manifest, parsed_case, head_files, mutation, reason):
    mutation(head_files)
    with pytest.raises(R002ReferenceError, match=reason):
        verify_case_head_files(
            case=r002_case_manifest, parsed=parsed_case, head_file_bytes=head_files
        )

def test_test_patch_never_becomes_implementation(r002_case_manifest):
    parsed = parse_case_diffs(
        case_id=r002_case_manifest.case_id,
        patch=IMPLEMENTATION_DIFF,
        test_patch=TEST_DIFF.replace("tests/test_widget.py", "src/not_a_test.py"),
    )
    with pytest.raises(R002ReferenceError, match="test_stream_not_test_evidence"):
        assert_test_stream_separation(parsed)
```

- [ ] **Step 3: Run verifier tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_verify.py
```

Expected: FAIL because `r002_verify.py` does not exist.

- [ ] **Step 4: Implement line normalization, verification, and permalink binding**

Normalize file bytes with the same CRLF/lone-CR rule as the parser, split only on LF, retain all whitespace, and index lines from one. Keep removed lines out of the verified candidate set.

```python
def _normalized_file_lines(raw: bytes, *, max_bytes: int) -> list[str]:
    if len(raw) > max_bytes:
        raise R002ReferenceError("head_file_limit")
    try:
        text = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").decode("utf-8")
    except UnicodeDecodeError as error:
        raise R002ReferenceError("head_file_not_utf8") from error
    values = text.split("\n")
    if values and values[-1] == "":
        values.pop()
    return values

def candidate_permalink(case: R002CaseManifest, path: str, line_number: int) -> str:
    repository = quote(case.repository, safe="/")
    head = quote(case.verified_pr_head_sha, safe="")
    logical_path = quote(path, safe="/")
    return (
        f"https://github.com/{repository}/blob/{head}/{logical_path}"
        f"#L{line_number}-L{line_number}"
    )

def verify_case_head_files(
    *, case: R002CaseManifest, parsed: R002ParsedCase,
    head_file_bytes: Mapping[str, bytes],
    limits: R002HeadFileLimits = DEFAULT_R002_HEAD_LIMITS,
) -> R002VerifiedCaseLines:
    assert_test_stream_separation(parsed)
    if sum(len(value) for value in head_file_bytes.values()) > limits.bytes_per_case:
        raise R002ReferenceError("head_case_limit")
    verified: list[R002VerifiedLine] = []
    for parsed_file in parsed.files:
        raw = head_file_bytes.get(parsed_file.path)
        if raw is None:
            raise R002ReferenceError("head_file_missing")
        file_hash = sha256(raw).hexdigest()
        lines = _normalized_file_lines(raw, max_bytes=limits.bytes_per_file)
        for hunk in parsed_file.hunks:
            for line in hunk.lines:
                if line.change_type is LineChangeType.REMOVED:
                    continue
                number = line.new_line_number
                if number is None or number > len(lines):
                    raise R002ReferenceError("head_line_out_of_range")
                if lines[number - 1] != line.content:
                    raise R002ReferenceError("head_line_mismatch")
                verified.append(R002VerifiedLine(
                    stream=parsed_file.stream,
                    path=parsed_file.path,
                    hunk_id=hunk.hunk_id,
                    new_line_number=number,
                    normalized_line_sha256=line.normalized_line_sha256,
                    head_file_sha256=file_hash,
                    head_sha=case.verified_pr_head_sha,
                    permalink=candidate_permalink(case, parsed_file.path, number),
                ))
    return R002VerifiedCaseLines(
        case_id=case.case_id,
        head_sha=case.verified_pr_head_sha,
        lines=tuple(sorted(verified, key=lambda item: (
            item.stream.value, item.path, item.new_line_number
        ))),
    )

def verify_evidence_reference(
    *, case: R002CaseManifest, evidence: EvidenceItem,
    verified_lines: R002VerifiedCaseLines,
) -> R002CandidateLineKey:
    matches = [
        line for line in verified_lines.lines
        if line.path == evidence.file_path and line.new_line_number == evidence.line_start
    ]
    if len(matches) != 1 or evidence.line_end != evidence.line_start:
        raise R002ReferenceError("evidence_not_in_verified_universe")
    line = matches[0]
    if evidence.commit_sha != case.verified_pr_head_sha:
        raise R002ReferenceError("evidence_head_mismatch")
    if evidence.permalink != line.permalink:
        raise R002ReferenceError("evidence_permalink_mismatch")
    return R002CandidateLineKey(
        case_id=case.case_id,
        criterion_id=evidence.criterion_id,
        stream=line.stream,
        path=line.path,
        new_line_number=line.new_line_number,
        normalized_line_sha256=line.normalized_line_sha256,
    )
```

`assert_test_stream_separation` calls `classify_changed_path_evidence_type(file.path)` and requires every `test_patch` file to be `EvidenceType.TEST`; it never overwrites a classification. `verify_evidence_reference` also checks that test-stream evidence is exactly TEST/E2 and that no item is E3 or E4.

- [ ] **Step 5: Run verifier tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_verify.py tests/evals/test_r002_diff.py \
  tests/retrieval/test_engine.py
uv run ruff check scopeproof_core/evals/r002_verify.py tests/evals/test_r002_verify.py
```

Expected: all tests pass and Ruff reports no findings.

- [ ] **Step 6: Commit the immutable-reference slice**

```bash
git add scopeproof_core/evals/r002_verify.py tests/evals/test_r002_verify.py
git commit -m "feat: bind R-002 evidence to immutable lines"
```

### Task 5: Add a symlink-safe, atomic, content-addressed research cache

**Files:**
- Create: `scopeproof_core/evals/r002_cache.py`
- Create: `tests/evals/test_r002_cache.py`

**Interfaces:**
- Consumes: `R002CriteriaSourceIndex`, `R002CacheIndex`, `R002CachedCase`, `R002CachedHeadFile`, `R002StrictModel`, `canonical_json_bytes`, and `canonical_sha256`.
- Produces: every `R002Cache` method defined in **Fixed interfaces and constants**, including the two reserved completion-marker publication pairs, the two typed streamed annotation writers, and the secure unlinked scratch-descriptor context used by the downloader.

- [x] **Step 1: Write failing safe-cache tests**

Cover mode `0700` cache directories, mode `0600` files, same-directory temporary files, fsync before replace, content-addressed object reuse, rejection of changed existing objects, and index publication as the sole completion marker.

```python
def test_cache_publishes_0600_file_and_reopens_validated_model(tmp_path):
    cache = R002Cache(tmp_path / "r002")
    proposal = criteria_proposal()
    path = cache.replace_model("criteria-proposal.json", proposal)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cache.read_model("criteria-proposal.json", R002CriteriaProposal) == proposal

def test_failed_index_replace_preserves_previous_complete_index(tmp_path, monkeypatch):
    cache = R002Cache(tmp_path / "r002")
    first = cache_index(revision=1)
    cache.publish_index(first)
    monkeypatch.setattr(os, "replace", raising_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        cache.publish_index(cache_index(revision=2))
    assert cache.load_index() == first

def test_existing_content_addressed_object_must_match(tmp_path):
    cache = R002Cache(tmp_path / "r002")
    digest = sha256(b"expected").hexdigest()
    cache.write_bytes(f"head-files/{digest}", b"expected")
    with pytest.raises(R002CacheError, match="content_address_collision"):
        cache.write_bytes(f"head-files/{digest}", b"changed")

def test_content_address_name_must_equal_data_digest(tmp_path):
    with pytest.raises(R002CacheError, match="content_address_digest_mismatch"):
        R002Cache(tmp_path / "r002").write_bytes(
            f"head-files/{'0' * 64}", b"different digest"
        )

@pytest.mark.parametrize("reserved", ["criteria-source-index.json", "cache-index.json"])
def test_completion_markers_reject_generic_writes(tmp_path, reserved):
    cache = R002Cache(tmp_path / "r002")
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.write_bytes(reserved, b"{}")
    with pytest.raises(R002CacheError, match="completion_marker_requires_publish"):
        cache.write_model(reserved, cache_index())

@pytest.mark.parametrize(
    "control",
    ["criteria-proposal.json", "criteria-review.json", "annotation-review.json",
     "candidate-label-proposal.json", "result.json", "reviews/R002-001.json"],
)
def test_raw_bytes_cannot_bypass_control_model_validation(tmp_path, control):
    with pytest.raises(R002CacheError, match="raw_write_requires_content_namespace"):
        R002Cache(tmp_path / "r002").write_bytes(control, b"{}")
```

- [x] **Step 2: Write failing filesystem-attack tests**

Create symlinks at the cache root, an existing ancestor, destination, and temporary-file candidate; create non-regular destinations; pass `../`, absolute, backslash, NUL, and non-hash object names. Each must fail before reading or writing through the unsafe path.

```python
@pytest.mark.parametrize("relative", ["../escape", "/tmp/escape", "rows\\escape", "rows/\x00"])
def test_cache_rejects_nonlocal_names(tmp_path, relative):
    with pytest.raises(R002CacheError, match="unsafe_relative_name"):
        R002Cache(tmp_path / "cache").write_bytes(relative, b"value")

def test_cache_rejects_symlink_root(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(R002CacheError, match="symlink"):
        R002Cache(linked).write_bytes("criteria-proposal.json", b"{}")
```

- [x] **Step 3: Run cache tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_cache.py
```

Expected: FAIL because `r002_cache.py` is absent.

- [x] **Step 4: Implement safe path creation and atomic persistence**

Allow only the literal control filenames in `_SAFE_RELATIVE` plus content-addressed selected `rows`, `criteria-sources`, and `head-files` objects and `reviews/<R002-case>.json`. The complete 500-row Parquet is a descriptor-backed temporary download, never a persisted cache object. Never derive a local filename from a repository path.

```python
_SAFE_RELATIVE = re.compile(
    r"^(?:criteria-source-index\.json|cache-index\.json|"
    r"criteria-proposal\.json|criteria-review\.json|"
    r"annotation-universe\.json|annotation-review\.json|candidate-label-proposal\.json|"
    r"result\.json|"
    r"rows/[0-9a-f]{64}|criteria-sources/[0-9a-f]{64}|"
    r"head-files/[0-9a-f]{64}|"
    r"reviews/R002-\d{3}\.json)$"
)

```

Implement every path operation descriptor-relative from a root directory descriptor opened with `O_DIRECTORY | O_NOFOLLOW`. Create each allowlisted child directory one segment at a time with `dir_fd`, reopen it with `O_DIRECTORY | O_NOFOLLOW`, and reject platforms that cannot provide those guarantees. Never use path-based `exists`, `is_symlink`, `open`, `read_bytes`, `mkdir`, `chmod`, `unlink`, or `os.replace` after the root descriptor is established.

`write_bytes` accepts only raw `criteria-sources/<digest>` and `head-files/<digest>` objects. `write_content_addressed_model` accepts only `rows/<digest>`, requires `model_type is SWEbenchVerifiedRow`, canonicalizes the already validated row, and reopens it through that exact type. For every immutable object, require the last path segment to equal `sha256(data)`, open existing destinations with `O_RDONLY | O_NOFOLLOW`, require a regular `0600` file owned by the current user, and compare its bytes. For a new object, create an unpredictable same-directory temporary name using `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW` and mode `0600`, write/flush/fsync, reopen by descriptor and byte-compare, then publish without overwriting an existing name. If another process wins the race, reopen and require identical bytes/model. Fsync the containing directory after publication.

For replaceable local controls, use the same descriptor-relative temporary sequence and call `os.replace` with explicit source name, destination name, `src_dir_fd`, and `dst_dir_fd`, then reopen the destination with `O_RDONLY | O_NOFOLLOW`. `write_bytes`, `write_model`, and `replace_model` must reject both reserved completion markers. `write_model`/`replace_model` accept only a filename-to-model allowlist: criteria proposal/review → `R002CriteriaProposal`, candidate-label proposal → `R002CandidateLabelProposal`, local result → `R002BenchmarkResult`, and `reviews/<case-id>.json` → `ReviewBundle`. Both `annotation-universe.json` and raw `annotation-review.json` are exclusive to their separate streamed typed writers; generic model methods reject them. Generic methods reject a mismatched model class, canonicalize the supplied validated model, reopen through the mapped class, and compare the validated value—not merely raw bytes.

`publish_criteria_source_index` is the sole writer for `criteria-source-index.json`; it verifies the exact 20 referenced `criteria-sources/<problem-hash>` objects, their byte lengths and hashes, atomically replaces the marker, reopens it as `R002CriteriaSourceIndex`, and fsyncs the root. `publish_index` is the sole writer for `cache-index.json`; it requires the confirmed-criteria hash, verifies every referenced selected row and head-file digest plus the already complete criteria-source index, atomically replaces the marker, reopens it as `R002CacheIndex`, and fsyncs the root. Failed publication leaves any earlier complete marker usable.

`write_annotation_review` uses the same streamed-array/atomic-replace discipline as `write_annotation_universe`, but serializes `R002AnnotationReviewItem` values and enforces `R002_ANNOTATION_REVIEW_MAX_BYTES`. It loads the just-written universe through its strict type, requires its exact hash and candidate count, counts items while streaming, reopens the complete review through `R002AnnotationReview`, and requires its ordered item keys to equal the universe keys before publication. A failed review write leaves any prior review bytes unchanged; that prior artifact cannot be used because its universe hash must differ from the newly written universe. The annotate operation fails and returns no success object until both current artifacts match.

The downloader obtains a secure scratch descriptor from the cache using the same dirfd policy, immediately unlinks its random name while keeping the descriptor open, writes and rewinds through that descriptor, and passes a duplicate seekable binary handle to `pyarrow`. Closing the context removes the only remaining reference. No full-source filename appears in the cache index or survives either preparation phase.

- [x] **Step 5: Run cache tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_cache.py
uv run ruff check scopeproof_core/evals/r002_cache.py tests/evals/test_r002_cache.py
```

Expected: all tests pass and Ruff reports no findings.

- [x] **Step 6: Commit the cache slice**

Task 5 exact-head verification before the local commit: 1,439 tests passed with one intentional
live-GitHub skip; the repository coverage gate reached 95.00% without exclusions or threshold
changes; Ruff, diff hygiene, the offline locked resolution, dependency compatibility, the 12-case
benchmark, and the two-case comparison benchmark passed. These are local engineering checks only
and do not advance Stage 1.

```bash
git add scopeproof_core/evals/r002_cache.py tests/evals/test_r002_cache.py
git commit -m "feat: persist R-002 cache atomically"
```

### Task 6: Implement bounded two-phase GET-only preparation with controlled HTTP tests

**Files:**
- Create: `scopeproof_core/evals/r002_prepare.py`
- Create: `tests/evals/test_r002_prepare.py`

**Interfaces:**
- Consumes: Tasks 1–5, `httpx.Client`, the fixed source manifest, and the ignored `R002Cache`.
- Produces: `R002ReadOnlyClient`, `prepare_criteria_sources(manifest_path, cache_root, transport=None) -> R002CriteriaSourcePreparationResult`, `prepare_r002(manifest_path, criteria_path, cache_root, transport=None) -> R002PreparationResult`, `R002CriteriaSourceIndex`, and the final validated `R002CacheIndex`.

- [x] **Step 1: Write failing URL and redirect tests**

Use only `httpx.MockTransport`; install a guard that raises if any request escapes the transport. Test the exact query-free source URL, at most three HTTPS redirects, allowed `huggingface.co`/`.hf.co` redirect hosts, and rejections for HTTP, credentials, non-default ports, IP literals, other hosts, fragments, GitHub redirects, metadata paths outside the manifest PR, raw paths outside the manifest repo/head/path, and any method other than GET. Allow an opaque provider-supplied query only on an already validated Hugging Face redirect target; never accept a query on the initial URL or any GitHub URL, persist it, print it, or carry it to another host.

```python
@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/source",
        "https://user:secret@huggingface.co/source",
        "https://127.0.0.1/source",
        "https://example.com/source",
        "https://api.github.com/repos/other/repo/pulls/1",
    ],
)
def test_read_only_client_rejects_unapproved_urls(url, r002_case_manifest):
    with pytest.raises(R002NetworkPolicyError):
        validate_request_target(
            url=url,
            request_kind=R002RequestKind.PR_METADATA,
            case=r002_case_manifest,
        )

def test_dataset_redirect_limit_is_three(source_url, tmp_path):
    transport = redirect_chain_transport(redirects=4, host_suffix=".hf.co")
    with pytest.raises(R002NetworkPolicyError, match="redirect_limit"):
        with R002ReadOnlyClient(transport).download_dataset(
            source_pin(source_url=source_url), R002Cache(tmp_path / "cache")
        ):
            pytest.fail("fourth redirect must not be followed")
```

- [x] **Step 2: Write failing download, PR metadata, and head-file tests**

Cover response content encoding, missing/wrong `Content-Length`, streamed byte excess at byte 2,090,471, truncated body, SHA mismatch, wrong Parquet metadata, wrong 20-case selection, PR 404, PR not closed/merged, base mismatch, head mismatch, repository/number mismatch, JSON metadata bodies over 1 MiB, raw-file request count >128, 4 MiB/file, 16 MiB/case, and 128 MiB/pack limits. The success fixture uses constructed data and exact fake hashes; CI must use zero live network. Put the implementation in private `_prepare_criteria_sources_from_manifest(manifest, ...)` and `_prepare_evidence_from_inputs(manifest, criteria, ...)` helpers that accept already validated models. Controlled tests call those helpers with structural fixtures; public `prepare_criteria_sources`/`prepare_r002` wrappers always call the non-injectable exact production loader first, and wrapper tests prove test pins are rejected before HTTP. Instrument Parquet column reads and assert the criteria-source phase never requests patch/test-patch/hint/test-name columns and performs no GitHub request.

```python
def test_prepare_rejects_pr_base_or_head_drift(preparation_fixture, tmp_path):
    transport = preparation_fixture.transport(
        pr_overrides={"base": {"sha": "0" * 40}}
    )
    with pytest.raises(R002PreparationError, match="pr_base_sha_mismatch"):
        _prepare_evidence_from_inputs(
            manifest=preparation_fixture.manifest,
            criteria=preparation_fixture.confirmed_criteria,
            cache_root=tmp_path / "cache",
            transport=transport,
        )

def test_prepare_publishes_index_only_after_all_cases_verify(preparation_fixture, tmp_path):
    result = _prepare_evidence_from_inputs(
        manifest=preparation_fixture.manifest,
        criteria=preparation_fixture.confirmed_criteria,
        cache_root=tmp_path / "cache",
        transport=preparation_fixture.transport(),
    )
    assert result.executed_case_count == 20
    assert result.failed_case_count == 0
    assert result.skipped_case_count == 0
    assert R002Cache(tmp_path / "cache").load_index().complete is True

def test_evidence_prepare_rejects_unconfirmed_criteria_before_network_or_patch_read(
    preparation_fixture, tmp_path
):
    transport = recording_transport()
    with pytest.raises(R002PreparationError, match="criteria_not_confirmed"):
        prepare_r002(
            manifest_path=preparation_fixture.production_manifest_path,
            criteria_path=preparation_fixture.unconfirmed_criteria_path,
            cache_root=tmp_path / "cache",
            transport=transport,
        )
    assert transport.requests == []
    assert preparation_fixture.parquet_columns_read == []

def test_criteria_source_phase_publishes_only_problem_sources(preparation_fixture, tmp_path):
    result = _prepare_criteria_sources_from_manifest(
        manifest=preparation_fixture.manifest,
        cache_root=tmp_path / "cache",
        transport=preparation_fixture.dataset_only_transport(),
    )
    assert result.executed_case_count == 20
    assert R002Cache(tmp_path / "cache").load_criteria_source_index().complete is True
    assert not (tmp_path / "cache" / "cache-index.json").exists()
    assert preparation_fixture.parquet_columns_read == list(R002_CRITERIA_SOURCE_COLUMNS)
```

- [x] **Step 3: Run preparation tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_prepare.py
```

Expected: FAIL because `r002_prepare.py` does not exist.

- [x] **Step 4: Implement the allowlisted GET client**

The client owns `httpx.Client(follow_redirects=False, timeout=15.0)`, exposes no generic request method, and validates every URL before each GET. Every response stays streaming from request creation through bounded consumption; never call buffered `client.get()`.

```python
class R002ReadOnlyClient:
    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=15.0,
            transport=transport,
            headers={
                "User-Agent": "ScopeProof-R002/1",
                "Accept": "application/json, application/octet-stream;q=0.9",
                "Accept-Encoding": "identity",
            },
        )
        self.request_count_by_kind = Counter()

    @contextmanager
    def _stream_once(
        self, url: str, request_kind: R002RequestKind
    ) -> Iterator[httpx.Response]:
        self.request_count_by_kind[request_kind] += 1
        if self.request_count_by_kind[request_kind] > R002_REQUEST_LIMITS[request_kind]:
            raise R002NetworkPolicyError("request_limit")
        request = self._client.build_request("GET", url)
        response = self._client.send(request, stream=True)
        try:
            yield response
        finally:
            response.close()
```

`validate_request_target` enforces HTTPS, no credentials, port 443/default only, no fragment, no IP literal, and the exact request-kind path/host rules. `_stream_once` is private and is called only after validation. `R002_REQUEST_LIMITS` is exact: four dataset requests including redirects, 20 PR-metadata requests, and 128 head-file requests; a phase-local client cannot exceed 152 requests in total. Callers inspect 3xx status and a single bounded `Location` header before `raise_for_status`; they never buffer or read a redirect body. Error serialization records only stable reason codes and status classes, never response bodies, URLs containing queries, headers, or credentials.

`download_dataset` accepts only the exact query-free `manifest.source.source_url`, manually follows at most three redirects, and permits redirect hosts only when equal to `huggingface.co` or ending in `.hf.co`. An allowed redirect may include an opaque signed query, but it is used only for that GET and is never persisted, printed, included in an exception, or carried to another host. On the final 200 response, require no `Content-Encoding`, parse one exact decimal `Content-Length`, and stream `iter_raw()` chunks into the cache's open unlinked `0600` scratch descriptor while updating SHA-256. Abort on the first byte beyond the pin, require the exact final length/hash, rewind, yield a duplicate seekable binary handle, and destroy the descriptor at context exit. Do not publish `source/<hash>` or any equivalent full-source object.

`fetch_pr_metadata` permits exactly `https://api.github.com/repos/<repository>/pulls/<pr_number>` with no redirects/query. Require a final 200, identity/no content encoding, a decimal `Content-Length` no greater than 1 MiB when present, and always enforce the same 1 MiB streaming cap before JSON parsing. Validate `state == "closed"`, `merged is True`, repository full name, PR number, base SHA, and head SHA against the case manifest.

`fetch_head_file` permits exactly `https://raw.githubusercontent.com/<repository>/<verified-head>/<percent-encoded-logical-path>`, no redirect/query, a final 200, identity/no content encoding, 4 MiB per file, 16 MiB per case, 128 MiB across the pack, and 128 total head-file requests. A declared length cannot exceed the applicable bounds, and streamed bytes enforce them even when length is absent or false. It returns bytes only; logical paths remain index data and never local filesystem paths.

- [x] **Step 5: Implement criteria-source and post-confirmation evidence preparation**

The first phase downloads and validates the exact Parquet but projects only the five criteria-source columns. It recomputes the fixed selection, validates each selected problem hash, writes exactly 20 problem bodies, publishes `criteria-source-index.json` last, closes and destroys the full-source scratch descriptor, and never contacts GitHub or calls the full-row/diff parser.

```python
def prepare_criteria_sources(
    *, manifest_path: Path, cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002CriteriaSourcePreparationResult:
    return _prepare_criteria_sources_from_manifest(
        manifest=load_source_manifest(manifest_path),
        cache_root=cache_root,
        transport=transport,
    )

def _prepare_criteria_sources_from_manifest(
    *, manifest: R002SourceManifest, cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002CriteriaSourcePreparationResult:
    cache = R002Cache(cache_root)
    client = R002ReadOnlyClient(transport)
    with client.download_dataset(manifest.source, cache) as source:
        projected_rows = decode_criteria_source_rows(source, manifest.source)
    selected = validate_manifest_criteria_sources(manifest, projected_rows)
    cases = []
    for case, row in zip(manifest.cases, selected, strict=True):
        body = row.problem_statement.encode("utf-8")
        cache.write_bytes(f"criteria-sources/{case.problem_statement_sha256}", body)
        cases.append(R002CriteriaSourceCase(
            case_id=case.case_id,
            problem_statement_sha256=case.problem_statement_sha256,
            byte_length=len(body),
        ))
    index = R002CriteriaSourceIndex(
        source_sha256=manifest.source.sha256,
        manifest_sha256=canonical_sha256(manifest),
        complete=True,
        cases=tuple(cases),
    )
    cache.publish_criteria_source_index(index)
    return R002CriteriaSourcePreparationResult(
        phase="criteria_sources",
        complete=True,
        executed_case_count=len(index.cases),
        failed_case_count=0,
        skipped_case_count=0,
        case_ids=tuple(case.case_id for case in index.cases),
        errors=(),
        hard_gate_errors=(),
    )

def prepare_r002(
    *, manifest_path: Path, criteria_path: Path, cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002PreparationResult:
    manifest = load_source_manifest(manifest_path)
    manifest_hash = canonical_sha256(manifest)
    criteria = load_confirmed_criteria(criteria_path, manifest_hash)
    return _prepare_evidence_from_inputs(
        manifest=manifest,
        criteria=criteria,
        cache_root=cache_root,
        transport=transport,
    )

def _prepare_evidence_from_inputs(
    *, manifest: R002SourceManifest, criteria: R002CriteriaSet,
    cache_root: Path, transport: httpx.BaseTransport | None = None,
) -> R002PreparationResult:
    manifest_hash = canonical_sha256(manifest)
    if criteria.source_manifest_sha256 != manifest_hash:
        raise R002PreparationError("criteria_manifest_drift")
    criteria_hash = canonical_sha256(criteria)
    cache = R002Cache(cache_root)
    criteria_source_index = cache.load_criteria_source_index()
    validate_criteria_source_index(criteria_source_index, manifest)
    client = R002ReadOnlyClient(transport)
    with client.download_dataset(manifest.source, cache) as source:
        rows = decode_verified_parquet(source, manifest.source)
    selected = validate_manifest_rows(manifest, rows)
    cached_cases = []
    for case, row in zip(manifest.cases, selected, strict=True):
        client.validate_pr(case)
        parsed = parse_case_diffs(
            case_id=case.case_id, patch=row.patch, test_patch=row.test_patch
        )
        head_files = {
            path: client.fetch_head_file(case, path)
            for path in sorted({file.path for file in parsed.files})
        }
        verified = verify_case_head_files(
            case=case, parsed=parsed, head_file_bytes=head_files
        )
        cache.write_content_addressed_model(
            f"rows/{case.row_sha256}", row, SWEbenchVerifiedRow
        )
        cached_heads = []
        for path, content in sorted(head_files.items()):
            digest = sha256(content).hexdigest()
            cache.write_bytes(f"head-files/{digest}", content)
            cached_heads.append(R002CachedHeadFile(
                logical_path=path, head_sha=case.verified_pr_head_sha,
                byte_length=len(content), content_sha256=digest,
            ))
        cached_cases.append(R002CachedCase(
            case_id=case.case_id,
            row_sha256=case.row_sha256,
            problem_statement_sha256=case.problem_statement_sha256,
            patch_sha256=case.patch_sha256,
            test_patch_sha256=case.test_patch_sha256,
            parsed_case_sha256=canonical_sha256(parsed),
            verified_lines=verified.lines,
            head_files=tuple(cached_heads),
        ))
    index = R002CacheIndex(
        source_sha256=manifest.source.sha256,
        manifest_sha256=manifest_hash,
        criteria_set_sha256=criteria_hash,
        complete=True,
        cases=tuple(cached_cases),
    )
    cache.publish_index(index)
    return R002PreparationResult(
        phase="evidence",
        complete=True,
        criteria_set_sha256=criteria_hash,
        executed_case_count=len(index.cases),
        failed_case_count=0,
        skipped_case_count=0,
        head_file_count=sum(len(case.head_files) for case in index.cases),
        candidate_line_count=sum(len(case.verified_lines) for case in index.cases),
        cases=tuple(R002PreparationCaseResult(
            case_id=case.case_id,
            status="prepared",
            head_file_count=len(case.head_files),
            candidate_line_count=len(case.verified_lines),
        ) for case in index.cases),
        errors=(),
        hard_gate_errors=(),
    )
```

`prepare_r002` must load and validate the confirmed criteria file before constructing `R002ReadOnlyClient`, opening the Parquet scratch descriptor, decoding a patch column, reading a row object, or issuing any request. The full phase redownloads the exact 2 MB pin, decodes and validates all 500 rows, then materializes only the selected 20 full rows and their required head files. Do not catch a per-case error and continue. Any exception prevents a new full cache index from being published and leaves the earlier complete index unchanged; the shared CLI boundary later emits an operation-level failure object, never partial case counts. No replacement case is selected, and both full-source temporary downloads are destroyed on success or failure.

- [x] **Step 6: Run preparation tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_prepare.py tests/evals/test_r002_cache.py \
  tests/evals/test_r002_source.py tests/evals/test_r002_verify.py
uv run ruff check scopeproof_core/evals/r002_prepare.py tests/evals/test_r002_prepare.py
```

Expected: all controlled fixture tests pass with zero live HTTP requests.

Local engineering verification on 2026-07-24: 36 focused preparation tests and
355 related R-002 tests passed using controlled transports with socket-level DNS and connect
guard. Ruff, diff hygiene, the offline lock, installed dependency compatibility, and both
existing deterministic benchmarks passed. The full suite passed with 1,477 tests, one
pre-existing skip, and 95.04% line coverage after cleanup hardening; the focused cleanup
regressions were rerun after the last review correction. This remains constructed engineering
evidence and does not advance Stage 1.

- [x] **Step 7: Commit the preparation slice**

```bash
git add scopeproof_core/evals/r002_prepare.py tests/evals/test_r002_prepare.py
git commit -m "feat: prepare R-002 sources read only"
```

### Task 7: Enforce the two-pass criteria and complete annotation protocol

**Files:**
- Create: `scopeproof_core/evals/r002_runner.py`
- Create: `tests/evals/test_r002_annotation.py`
- Modify: `scopeproof_core/evals/r002_cache.py`
- Modify: `scopeproof_core/evals/r002_models.py`

**Interfaces:**
- Consumes: the problem-only criteria-source index for proposal authoring; after confirmation, the complete evidence cache, source-manifest hash, and owner-authored criteria supplied without any pre-gate patch/test-patch reads.
- Produces: `build_criteria_proposal(manifest, cache, criteria_by_case)`, `confirmed_criteria_from_proposal(proposal)`, `build_annotation_universe(manifest, criteria, cache)` with its matching local raw review artifact, `derive_expected_missing(criteria, universe, labels)`, `validate_complete_label_proposal(criteria, universe, labels)`, and `validate_complete_labels(criteria, universe, labels)`.

- [x] **Step 1: Write failing criteria-isolation tests**

Use a recording cache double and assert that criteria proposal construction reads only each selected row's `problem_statement` and its pinned hash. It must not return or inspect `patch`, `test_patch`, hints, test-name fields, ScopeProof evidence, or prior output.

```python
def test_criteria_proposal_reads_problem_statements_only(
    constructed_manifest, recording_cache, criteria_by_case
):
    proposal = build_criteria_proposal(
        constructed_manifest, recording_cache, criteria_by_case
    )
    assert proposal.benchmark_owner_confirmed is False
    assert proposal.source_owner_confirmed is False
    assert recording_cache.criteria_source_reads == {
        case.problem_statement_sha256 for case in constructed_manifest.cases
    }
    assert recording_cache.row_reads == 0
    assert all(1 <= len(case.criteria) <= 16 for case in proposal.cases)
    assert all(any(item.priority is Priority.MUST_HAVE for item in case.criteria)
               for case in proposal.cases)

def test_design_approval_cannot_confirm_criteria(r002_criteria_proposal):
    with pytest.raises(ValidationError):
        R002CriteriaSet.model_validate_json(canonical_json_bytes(r002_criteria_proposal))
```

Also assert every criterion explicitly serializes `criterion_id`, `text`, `priority`, `criterion_type`, `criterion_source`, `source_span`, and `required_evidence_level`; only `CriterionSource.USER_CONFIRMED` is accepted in a final set; text is a single line of at most 512 characters; and source spans match `^problem_statement:L[1-9]\d*-L[1-9]\d*$`, have start ≤ end, and stay within the actual normalized problem-statement line count, never copied source text.

- [x] **Step 2: Write failing annotation-universe and label tests**

Build the exact cross-product of each confirmed criterion and every added/context line from both streams. Assert removed lines are absent, order is stable, the tuple key is exact, the pack hard-fails above 250,000 pairs without truncation, universe JSON fails before exceeding 256 MiB, annotation-review JSON fails before exceeding 512 MiB, and any missing/extra/duplicate/changed key forces reannotation. Mutate each top-level source/manifest/criteria/universe hash in turn and mutate case IDs, problem hashes, row hashes, and criterion IDs on both sides of every zip; each must fail before a candidate is written or a label is accepted.

```python
def test_annotation_universe_is_complete_cross_product(
    constructed_manifest, confirmed_criteria, prepared_cache
):
    universe = build_annotation_universe(
        manifest=constructed_manifest,
        criteria=confirmed_criteria,
        cache=prepared_cache,
    )
    expected_count = sum(
        len(cached_case.verified_lines) * len(criteria_case.criteria)
        for cached_case, criteria_case in zip(
            prepared_cache.load_index().cases,
            confirmed_criteria.cases,
            strict=True,
        )
    )
    assert universe.candidate_count == expected_count
    assert list(universe.candidate_keys) == sorted(
        universe.candidate_keys,
        key=lambda key: (
            key.case_id, key.criterion_id, key.stream.value, key.path,
            key.new_line_number, key.normalized_line_sha256,
        ),
    )

    review = prepared_cache.read_model(
        "annotation-review.json", R002AnnotationReview
    )
    assert review.annotation_universe_sha256 == canonical_sha256(universe)
    assert tuple(item.key for item in review.items) == universe.candidate_keys
    assert all(isinstance(item.line_content, str) for item in review.items)
    assert all(item.relevant is None and item.reason_code is None for item in review.items)

def test_labels_must_equal_the_full_frozen_universe(
    confirmed_criteria, annotation_universe, confirmed_labels
):
    missing_one = confirmed_labels.model_copy(update={"labels": confirmed_labels.labels[:-1]})
    with pytest.raises(R002AnnotationError, match="reannotation_required"):
        validate_complete_labels(confirmed_criteria, annotation_universe, missing_one)
```

- [x] **Step 3: Run annotation tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_annotation.py
```

Expected: FAIL because the proposal and annotation functions do not exist.

- [x] **Step 4: Implement criteria proposal and confirmation transformation**

Change the fixed signature to accept explicitly authored criteria; there is no automatic criterion generator in the product.

```python
def build_criteria_proposal(
    manifest: R002SourceManifest,
    cache: R002Cache,
    criteria_by_case: Mapping[R002CaseId, Sequence[Criterion]],
) -> R002CriteriaProposal:
    index = cache.load_criteria_source_index()
    if (
        index.source_sha256 != manifest.source.sha256
        or index.manifest_sha256 != canonical_sha256(manifest)
        or tuple(item.case_id for item in index.cases)
        != tuple(case.case_id for case in manifest.cases)
        or tuple(item.problem_statement_sha256 for item in index.cases)
        != tuple(case.problem_statement_sha256 for case in manifest.cases)
        or set(criteria_by_case) != {case.case_id for case in manifest.cases}
        or not index.complete
    ):
        raise R002AnnotationError("criteria_source_cache_manifest_mismatch")
    cases = []
    for case in manifest.cases:
        row = cache.read_bytes(
            f"criteria-sources/{case.problem_statement_sha256}",
            expected_sha256=case.problem_statement_sha256,
        ).decode("utf-8")
        if sha256(row.encode("utf-8")).hexdigest() != case.problem_statement_sha256:
            raise R002AnnotationError("problem_statement_hash_mismatch")
        normalized_source_lines = row.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        validate_criterion_spans(
            criteria_by_case[case.case_id], line_count=len(normalized_source_lines)
        )
        cases.append(R002CriterionReviewCase(
            case_id=case.case_id,
            problem_statement_sha256=case.problem_statement_sha256,
            problem_statement=row,
            criteria=tuple(criteria_by_case[case.case_id]),
        ))
    return R002CriteriaProposal(
        source_manifest_sha256=canonical_sha256(manifest),
        cases=tuple(cases),
    )

def confirmed_criteria_from_proposal(proposal: R002CriteriaProposal) -> R002CriteriaSet:
    return R002CriteriaSet(
        source_manifest_sha256=proposal.source_manifest_sha256,
        source_owner_confirmed=False,
        benchmark_owner_confirmed=True,
        cases=tuple(R002CriterionCase(
            case_id=case.case_id,
            problem_statement_sha256=case.problem_statement_sha256,
            criteria=case.criteria,
        ) for case in proposal.cases),
    )
```

`validate_criterion_spans` requires every span to match `R002SourceSpan`, end within the normalized problem-statement line count, criterion text to be one nonblank line of at most 512 characters, and every field to be explicitly present in `Criterion.model_fields_set`. `R002CriterionReviewCase` and `R002CriteriaProposal` may contain raw problem text only because they are validated ignored-cache models. `R002CriteriaSet` cannot contain that field. Add `criteria-proposal.json` and `criteria-review.json` to the cache allowlist; never add either file to Git.

- [x] **Step 5: Implement streamed annotation-universe construction**

Read patch/test-patch only after `load_confirmed_criteria` succeeds. Perform one bounded count pass before writing any candidate; then stream canonical key objects into a same-directory temporary JSON array, fsync, reopen as `R002AnnotationUniverse`, verify the canonical SHA-256, and atomically publish `annotation-universe.json`. Do not retain raw line content in this hash-only artifact.

```python
@dataclass(frozen=True)
class _R002AnnotationMaterial:
    case: R002CaseManifest
    criterion_case: R002CriterionCase
    cached_case: R002CachedCase
    contexts: Mapping[_R002VerifiedLineIdentity, _R002RawLineContext]

def _load_annotation_material(
    case: R002CaseManifest, criterion_case: R002CriterionCase,
    cached_case: R002CachedCase, cache: R002Cache,
) -> _R002AnnotationMaterial:
    row = cache.read_model(f"rows/{case.row_sha256}", SWEbenchVerifiedRow)
    if (
        canonical_sha256(row) != case.row_sha256
        or sha256(row.problem_statement.encode("utf-8")).hexdigest()
        != case.problem_statement_sha256
        or sha256(row.patch.encode("utf-8")).hexdigest() != case.patch_sha256
        or sha256(row.test_patch.encode("utf-8")).hexdigest()
        != case.test_patch_sha256
    ):
        raise R002AnnotationError("prepared_cache_evidence_drift")
    parsed = parse_case_diffs(
        case_id=case.case_id, patch=row.patch, test_patch=row.test_patch
    )
    if canonical_sha256(parsed) != cached_case.parsed_case_sha256:
        raise R002AnnotationError("prepared_cache_evidence_drift")
    contexts = build_verified_raw_line_contexts(parsed, cached_case.verified_lines)
    if tuple(contexts) != tuple(
        verified_line_identity(line) for line in cached_case.verified_lines
    ):
        raise R002AnnotationError("prepared_cache_evidence_drift")
    return _R002AnnotationMaterial(
        case=case, criterion_case=criterion_case,
        cached_case=cached_case, contexts=contexts,
    )

def _annotation_pairs(
    material: _R002AnnotationMaterial,
) -> Iterator[tuple[R002CandidateLineKey, R002AnnotationReviewItem]]:
    for criterion in material.criterion_case.criteria:
        for verified_line in material.cached_case.verified_lines:
            identity = verified_line_identity(verified_line)
            context = material.contexts[identity]
            key = R002CandidateLineKey(
                case_id=material.case.case_id,
                criterion_id=criterion.criterion_id,
                stream=verified_line.stream,
                path=verified_line.path,
                new_line_number=verified_line.new_line_number,
                normalized_line_sha256=verified_line.normalized_line_sha256,
            )
            yield key, R002AnnotationReviewItem(
                key=key,
                line_content=context.line_content,
                previous_line=context.previous_line,
                next_line=context.next_line,
                relevant=None,
                reason_code=None,
            )

def build_annotation_universe(
    *, manifest: R002SourceManifest, criteria: R002CriteriaSet, cache: R002Cache
) -> R002AnnotationUniverse:
    manifest_hash = canonical_sha256(manifest)
    criteria_hash = canonical_sha256(criteria)
    manifest_case_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in manifest.cases
    )
    criteria_case_identity = tuple(
        (case.case_id, case.problem_statement_sha256) for case in criteria.cases
    )
    if (
        criteria.source_manifest_sha256 != manifest_hash
        or criteria_case_identity != manifest_case_identity
    ):
        raise R002AnnotationError("criteria_manifest_drift")
    index = cache.load_index()
    if (
        index.source_sha256 != manifest.source.sha256
        or index.manifest_sha256 != manifest_hash
        or index.criteria_set_sha256 != criteria_hash
        or tuple(case.case_id for case in index.cases)
        != tuple(case.case_id for case in manifest.cases)
        or tuple(case.row_sha256 for case in index.cases)
        != tuple(case.row_sha256 for case in manifest.cases)
    ):
        raise R002AnnotationError("prepared_cache_criteria_drift")
    triples = tuple(zip(
        manifest.cases, criteria.cases, index.cases, strict=True
    ))
    materials = tuple(
        _load_annotation_material(case, criterion_case, cached_case, cache)
        for case, criterion_case, cached_case in triples
    )
    candidate_count = sum(
        len(material.cached_case.verified_lines)
        * len(material.criterion_case.criteria)
        for material in materials
    )
    if candidate_count > 250_000:
        raise R002AnnotationError("annotation_pair_limit")
    universe = cache.write_annotation_universe(
        source_manifest_sha256=manifest_hash,
        criteria_set_sha256=criteria_hash,
        candidate_count=candidate_count,
        ordered_key_factory=lambda: (
            key
            for material in materials
            for key, _item in _annotation_pairs(material)
        ),
    )
    review = cache.write_annotation_review(
        source_manifest_sha256=manifest_hash,
        criteria_set_sha256=criteria_hash,
        annotation_universe_sha256=canonical_sha256(universe),
        candidate_count=candidate_count,
        ordered_item_factory=lambda: (
            item
            for material in materials
            for _key, item in _annotation_pairs(material)
        ),
    )
    if tuple(item.key for item in review.items) != universe.candidate_keys:
        raise R002AnnotationError("prepared_cache_evidence_drift")
    return universe
```

`build_verified_raw_line_contexts` walks each parsed file/hunk in stable order, considers only new-side added/context lines, removes only the diff marker already removed by the parser, and returns the current marker-free content plus the immediately adjacent new-side line within the same hunk. Its identity is `(stream, path, hunk_id, new_line_number, normalized_line_sha256)`. It rejects duplicates and requires exact equality with every cached verified-line identity before either streamed writer starts. Raw line/context fields enforce the existing 64 KiB per-line UTF-8 bound. Add `prepared_cache_evidence_drift` to the closed `R002AnnotationError` allowlist and cover row, parsed-hash, missing-line, extra-line, reordered-line, and neighboring-context mutations.

Implement the public offline wrapper explicitly so confirmation is validated before the full cache is opened:

```python
def annotate_r002(
    *, manifest_path: Path, criteria_path: Path, cache_root: Path
) -> R002AnnotationUniverse:
    manifest = load_source_manifest(manifest_path)
    manifest_hash = canonical_sha256(manifest)
    criteria = load_confirmed_criteria(criteria_path, manifest_hash)
    return build_annotation_universe(
        manifest=manifest,
        criteria=criteria,
        cache=R002Cache(cache_root),
    )
```

The wrapper imports no network module or `pyarrow`, rejects an absent/unconfirmed/drifted criteria file before `cache.load_index`, and writes the annotation universe/review only after all upstream identities pass.

`R002Cache.write_annotation_universe` writes the five literal research-boundary fields and both upstream hashes in canonical key order, opens `candidate_keys` as a JSON array, streams each already ordered canonical key with comma separators, counts bytes before every write, aborts before `R002_ANNOTATION_UNIVERSE_MAX_BYTES`, checks the emitted count, closes the object, fsyncs, reopens it through `R002AnnotationUniverse.model_validate_json`, verifies canonical bytes and SHA-256, atomically replaces `annotation-universe.json`, and reopens once more. `write_annotation_review` then separately streams the exact matching local-only item sequence, including marker-free raw line, one neighboring new-side line on each side within the hunk, and unset decision fields; it aborts before `R002_ANNOTATION_REVIEW_MAX_BYTES`, validates the complete strict model and universe-key equality, and atomically replaces `annotation-review.json`. These limits fail the whole annotation phase and require an explicit design revision—never truncation. The review artifact exists only to let the benchmark owner label content; the final label set strips all raw text.

- [x] **Step 6: Implement label completeness and expected-missing derivation**

Require exact ordered key equality between the universe and labels. Derive expected missing for the fixed static types from owner-confirmed relevant labels; do not let the author hand-edit this list.

```python
def derive_expected_missing(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: Sequence[R002CandidateLabel],
) -> tuple[R002ExpectedMissing, ...]:
    relevant_types: dict[tuple[str, str], set[EvidenceType]] = defaultdict(set)
    for label in labels:
        if label.relevant:
            relevant_types[(label.key.case_id, label.key.criterion_id)].add(
                classify_changed_path_evidence_type(label.key.path)
            )
    criterion_keys = [
        (case.case_id, criterion.criterion_id)
        for case in criteria.cases
        for criterion in case.criteria
    ]
    return tuple(
        R002ExpectedMissing(
            case_id=case_id,
            criterion_id=criterion_id,
            evidence_type=evidence_type,
            reason_code="no_owner_labelled_relevant_candidate",
        )
        for case_id, criterion_id in criterion_keys
        for evidence_type in R002_STATIC_EVIDENCE_TYPES
        if evidence_type not in relevant_types[(case_id, criterion_id)]
    )

def _validate_label_content(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelProposal | R002CandidateLabelSet,
) -> None:
    criteria_hash = canonical_sha256(criteria)
    if (
        universe.criteria_set_sha256 != criteria_hash
        or labels.criteria_set_sha256 != criteria_hash
        or labels.source_manifest_sha256 != criteria.source_manifest_sha256
        or universe.source_manifest_sha256 != criteria.source_manifest_sha256
    ):
        raise R002AnnotationError("label_upstream_hash_drift")
    criterion_identity = {
        (case.case_id, criterion.criterion_id)
        for case in criteria.cases
        for criterion in case.criteria
    }
    if any(
        (key.case_id, key.criterion_id) not in criterion_identity
        for key in universe.candidate_keys
    ):
        raise R002AnnotationError("annotation_criterion_drift")
    labelled_keys = tuple(label.key for label in labels.labels)
    if labelled_keys != universe.candidate_keys:
        raise R002AnnotationError("reannotation_required")
    if labels.annotation_count != universe.candidate_count:
        raise R002AnnotationError("reannotation_required")
    if labels.annotation_universe_sha256 != canonical_sha256(universe):
        raise R002AnnotationError("reannotation_required")
    expected = derive_expected_missing(criteria, universe, labels.labels)
    if labels.expected_missing != expected:
        raise R002AnnotationError("expected_missing_drift")

def validate_complete_label_proposal(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelProposal,
) -> None:
    if labels.benchmark_owner_confirmed is not False:
        raise R002AnnotationError("label_proposal_must_be_unconfirmed")
    _validate_label_content(criteria, universe, labels)

def validate_complete_labels(
    criteria: R002CriteriaSet,
    universe: R002AnnotationUniverse,
    labels: R002CandidateLabelSet,
) -> None:
    if labels.benchmark_owner_confirmed is not True:
        raise R002AnnotationError("candidate_labels_not_confirmed")
    _validate_label_content(criteria, universe, labels)
```

- [x] **Step 7: Run annotation tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_annotation.py tests/evals/test_r002_models.py \
  tests/evals/test_r002_cache.py
uv run ruff check scopeproof_core/evals/r002_runner.py tests/evals/test_r002_annotation.py
```

Expected: all tests pass and Ruff reports no findings.

Local engineering verification on 2026-07-24: 13 focused annotation tests passed,
including a concurrent-writer rollback regression, and the combined
annotation/model/cache suite passed 241 tests. The full suite passed 1,490 tests
with one pre-existing skip and 95.04% line coverage using coverage.py's Python 3.12
sysmon core; Ruff, diff hygiene, the offline lock, installed dependency compatibility,
and both existing deterministic benchmarks passed. All fixtures are ScopeProof-authored
controlled engineering evidence; no target repository code or live network was used,
and Stage 1 remains unchanged.

- [x] **Step 8: Commit the two-pass annotation slice**

```bash
git add scopeproof_core/evals/r002_runner.py scopeproof_core/evals/r002_cache.py \
  scopeproof_core/evals/r002_models.py tests/evals/test_r002_annotation.py
git commit -m "feat: freeze R-002 research annotations"
```

### Task 8: Run the unchanged ScopeProof path and compute redacted fixed metrics

**Files:**
- Modify: `scopeproof_core/evals/r002_runner.py`
- Create: `tests/evals/test_r002_runner.py`

**Interfaces:**
- Consumes: all confirmed packaged inputs and a complete cache; calls `retrieve_evidence`, `build_findings`, and `evaluate_gate` directly.
- Produces: `build_r002_review`, `evaluate_r002_case`, `metric`, `build_determinism_projection`, `run_r002`, and the local-only `audit_r002_redaction` helper.

- [ ] **Step 1: Write failing review-boundary and gate tests**

Use 20 generated ScopeProof-owned cached cases and confirmed labels. Assert exact unavailable CI, zero runtime evidence, zero resolutions, false final acceptance, research context, E1/E2 ceiling, test-patch TEST/E2 separation, and only the two allowed gate shapes.

```python
def test_r002_review_preserves_static_research_boundary(r002_review_bundle):
    bundle = r002_review_bundle
    assert bundle.research_context.classification == "public_engineering_research"
    assert bundle.research_context.stage1_credit is False
    assert bundle.review.check_state is CheckState.UNAVAILABLE
    assert bundle.review.ci_observation.reason_code is CIReasonCode.NO_OBSERVATIONS
    assert bundle.review.ci_observation.collection_complete is True
    assert bundle.review.ci_observation.total_check_runs == 0
    assert bundle.review.ci_observation.concrete_legacy_status_count == 0
    assert bundle.runtime_evidence == []
    assert bundle.resolutions == []
    assert bundle.review.final_acceptance is False
    assert all(item.evidence_level in {EvidenceLevel.E1, EvidenceLevel.E2}
               for item in bundle.evidence)
    assert bundle.gate.verdict in {GateVerdict.BLOCKED, GateVerdict.NEEDS_REVIEW}

def test_allowed_gate_reason_shapes_are_exact(r002_review_bundle):
    gate = r002_review_bundle.gate
    if gate.verdict is GateVerdict.BLOCKED:
        assert "blocking_criteria" in gate.reason_codes
        assert gate.blocking_criteria
    else:
        assert gate.verdict is GateVerdict.NEEDS_REVIEW
        assert {"checks_not_passing", "unresolved_criteria"}.issubset(gate.reason_codes)
        assert gate.unresolved_criteria

def test_needs_review_reason_codes_are_redacted_in_canonical_order(
    r002_needs_review_case_input,
):
    result = evaluate_r002_case(**r002_needs_review_case_input)
    assert result.gate_reason_codes == ("checks_not_passing", "unresolved_criteria")

def test_missing_explanations_are_derived_from_run_output_not_copied_labels(
    evaluated_case_input
):
    result = evaluate_r002_case(**evaluated_case_input)
    expected = evaluated_case_input["expected_missing"]
    assert len(result.missing_explanations) == len(expected)
    assert {item.reason_code for item in result.missing_explanations} <= {
        "scopeproof_finding_explicit_gap",
        "no_candidate_retrieved_for_type",
        "retrieved_only_owner_labelled_irrelevant",
    }
    mutated = without_one_retrieved_candidate(evaluated_case_input)
    changed = evaluate_r002_case(**mutated)
    assert changed.missing_explanations != result.missing_explanations
```

- [ ] **Step 2: Write failing metric, redaction, and determinism tests**

Cover every fixed numerator/denominator, `not_applicable` zero denominators, unlabelled/out-of-universe candidates, missing explanations derived from actual findings/retrieval, a deliberately omitted explanation producing completeness below 100% and a hard-gate failure, invalid references, `unexpected_ready_count`, exact 20/0/0 executed/failed/skipped, and projection stability across UUID/time/cache-root changes.

```python
def test_metric_zero_denominator_is_not_applicable():
    assert metric(0, 0) == R002Metric(
        state=R002MetricState.NOT_APPLICABLE,
        numerator=0,
        denominator=0,
        value=None,
    )

def test_metric_rejects_positive_numerator_with_zero_denominator():
    with pytest.raises(ValidationError, match="numerator cannot exceed denominator"):
        R002Metric.model_validate_json(
            '{"state":"not_applicable","numerator":1,"denominator":0,"value":null}'
        )

def test_projection_ignores_generated_and_local_fields(two_equivalent_local_runs):
    first_bundle, first_result, second_bundle, second_result = two_equivalent_local_runs
    assert first_bundle.review.review_id != second_bundle.review.review_id
    assert first_bundle.review.created_at != second_bundle.review.created_at
    assert canonical_sha256(build_determinism_projection(first_result)) == canonical_sha256(
        build_determinism_projection(second_result)
    )

def test_redacted_result_contains_no_third_party_bodies(r002_result):
    serialized = canonical_json_bytes(r002_result).decode("utf-8")
    for forbidden in THIRD_PARTY_BODY_SENTINELS:
        assert forbidden not in serialized

def test_redaction_audit_returns_hashes_not_raw_values(local_raw_pack, tracked_candidates):
    audit = audit_r002_redaction(
        cache_root=local_raw_pack.cache_root,
        candidate_paths=tracked_candidates,
    )
    assert audit.passed is True
    serialized = canonical_json_bytes(audit).decode("utf-8")
    assert all(raw not in serialized for raw in local_raw_pack.raw_values)
    assert audit.raw_value_count == len(local_raw_pack.raw_values)

def test_redaction_audit_streams_past_old_eight_mib_boundary(
    local_raw_pack, large_redacted_candidate
):
    assert large_redacted_candidate.stat().st_size > 8 * 1024 * 1024
    audit = audit_r002_redaction(
        cache_root=local_raw_pack.cache_root,
        candidate_paths=[large_redacted_candidate],
    )
    assert audit.passed is True

def test_redaction_audit_finds_forbidden_json_scalar_split_across_read_chunks(
    local_raw_pack, chunk_boundary_json_candidate
):
    with pytest.raises(R002RunError, match="redaction_boundary_failed"):
        audit_r002_redaction(
            cache_root=local_raw_pack.cache_root,
            candidate_paths=[chunk_boundary_json_candidate],
        )

def test_redaction_audit_allows_test_name_inside_approved_path(
    raw_pack_with_test_relational, candidate_labels_with_relational_path
):
    # Exact pinned collision: raw test name `test_relational` is a substring of
    # the allowed candidate path `tests/test_relational.py`, not a leaked scalar.
    audit = audit_r002_redaction(
        cache_root=raw_pack_with_test_relational.cache_root,
        candidate_paths=[candidate_labels_with_relational_path],
    )
    assert audit.passed is True
```

- [ ] **Step 3: Run runner tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_runner.py
```

Expected: FAIL because review construction, scoring, metrics, and determinism are incomplete.

- [ ] **Step 4: Implement exact offline review construction**

Read cached row and head files through validated cache methods, recheck every upstream hash, parse and reverify lines, and build the review without `demo.build_review` or `cli._build_bundle`.

```python
def build_r002_review(
    *, case: R002CaseManifest, row: SWEbenchVerifiedRow,
    criterion_case: R002CriterionCase, parsed: R002ParsedCase,
) -> ReviewBundle:
    snapshot = PullRequestSnapshot(
        repository=case.repository,
        pr_number=case.pr_number,
        title=f"R-002 {case.case_id}",
        description="",
        html_url=case.pr_url,
        base_sha=case.dataset_base_commit,
        head_sha=case.verified_pr_head_sha,
        check_state=CheckState.UNAVAILABLE,
        ci_observation=CIObservation(
            state=CheckState.UNAVAILABLE,
            reason="No check runs or concrete legacy statuses were observed.",
            reason_code=CIReasonCode.NO_OBSERVATIONS,
            collection_complete=True,
        ),
        ingestion_state=IngestionState.COMPLETE,
        files=parsed_case_to_changed_files(parsed),
    )
    review = Review(
        repository=case.repository,
        pr_number=case.pr_number,
        base_sha=case.dataset_base_commit,
        head_sha=case.verified_pr_head_sha,
        check_state=snapshot.check_state,
        ci_observation=snapshot.ci_observation,
        criteria_confirmed=True,
        ingestion_state=IngestionState.COMPLETE,
        final_acceptance=False,
    )
    criteria = list(criterion_case.criteria)
    evidence = retrieve_evidence(snapshot, criteria)
    findings = build_findings(criteria, evidence, IngestionState.COMPLETE)
    gate = evaluate_gate(review, criteria, findings, [])
    return ReviewBundle(
        review=review,
        source_text=row.problem_statement,
        criteria=criteria,
        evidence=evidence,
        runtime_evidence=[],
        findings=findings,
        resolutions=[],
        gate=gate,
        research_context=ResearchContext(
            case_id=case.case_id,
            boundary_note=(
                "Public engineering research only; this case is not customer or Alpha "
                "validation and does not advance Stage 1."
            ),
        ),
    )
```

- [ ] **Step 5: Implement candidate mapping and per-case redaction**

Map every retrieved item through `verify_evidence_reference`; require its key in the frozen label dictionary; attach only the key, evidence type/level, matching-rule code, score, hunk ID, head-file hash, and relevance boolean to `R002CaseResult`. Save the full bundle only as ignored `reviews/<case-id>.json`.

```python
def evaluate_r002_case(
    *, case: R002CaseManifest, bundle: ReviewBundle,
    verified: R002VerifiedCaseLines,
    label_by_key: Mapping[R002CandidateLineKey, R002CandidateLabel],
    expected_missing: Sequence[R002ExpectedMissing],
) -> R002CaseResult:
    retrieved = []
    for evidence in bundle.evidence:
        key = verify_evidence_reference(
            case=case, evidence=evidence, verified_lines=verified
        )
        label = label_by_key.get(key)
        if label is None:
            raise R002RunError("reannotation_required")
        line = verified.by_path_and_line(evidence.file_path, evidence.line_start)
        retrieved.append(R002RetrievedCandidate(
            key=key,
            evidence_type=evidence.evidence_type,
            evidence_level=evidence.evidence_level,
            hunk_id=line.hunk_id,
            head_file_sha256=line.head_file_sha256,
            matching_rule=evidence.matching_rule,
            relevance_score=evidence.relevance_score,
            owner_label_relevant=label.relevant,
        ))
    missing_explanations = build_missing_explanations(
        case=case,
        findings=bundle.findings,
        retrieved=tuple(retrieved),
        expected_missing=tuple(
            item for item in expected_missing if item.case_id == case.case_id
        ),
    )
    if len(bundle.gate.reason_codes) != len(set(bundle.gate.reason_codes)):
        raise R002RunError("benchmark_gate_failed")
    return R002CaseResult(
        case_id=case.case_id,
        repository=case.repository,
        pr_number=case.pr_number,
        head_sha=case.verified_pr_head_sha,
        criterion_count=len(bundle.criteria),
        annotation_candidate_count=sum(
            1 for key in label_by_key if key.case_id == case.case_id
        ),
        retrieved_candidates=tuple(retrieved),
        missing_explanations=missing_explanations,
        gate_verdict=bundle.gate.verdict,
        gate_reason_codes=tuple(sorted(bundle.gate.reason_codes)),
        blocking_criteria=tuple(bundle.gate.blocking_criteria),
        conditional_criteria=tuple(bundle.gate.conditional_criteria),
        unresolved_criteria=tuple(bundle.gate.unresolved_criteria),
        check_state=bundle.review.check_state,
        ci_reason_code=bundle.review.ci_observation.reason_code,
        runtime_evidence_count=len(bundle.runtime_evidence),
        resolution_count=len(bundle.resolutions),
        final_acceptance=bundle.review.final_acceptance,
        separation_errors=0,
        reference_errors=0,
        limitations=R002_RESULT_LIMITATIONS,
    )
```

`build_missing_explanations` must never copy `R002ExpectedMissing.reason_code`. For each frozen expected pair, inspect the actual `Finding` and actual mapped retrieved candidates of that evidence type:

- if the finding has a nonblank `missing_evidence` entry, emit `source="scopeproof_finding"` and `reason_code="scopeproof_finding_explicit_gap"` with its `FindingStatus`;
- otherwise, if no candidate of that type was retrieved, emit `source="r002_retrieval_comparison"` and `reason_code="no_candidate_retrieved_for_type"`;
- otherwise, require every retrieved candidate of that type to have `owner_label_relevant=false` and emit `source="r002_retrieval_comparison"` and `reason_code="retrieved_only_owner_labelled_irrelevant"`;
- if any retrieved candidate is owner-labelled relevant while the pair is frozen as expected-missing, raise `R002RunError("expected_missing_label_conflict")`.

The helper rejects duplicate findings, stable-sorts explanations by case/criterion/evidence type, and returns no entry when the expected criterion has no finding. That omission lowers the completeness numerator and is then a hard integrity failure; it is never backfilled from labels.

- [ ] **Step 6: Implement the fixed aggregate metrics**

Use these exact numerator/denominator definitions, counting unique stable candidate keys, paths, and hunk IDs:

```python
def metric(numerator: int, denominator: int) -> R002Metric:
    if denominator == 0:
        return R002Metric(
            state=R002MetricState.NOT_APPLICABLE,
            numerator=numerator,
            denominator=0,
            value=None,
        )
    return R002Metric(
        state=R002MetricState.VALUE,
        numerator=numerator,
        denominator=denominator,
        value=numerator / denominator,
    )

def calculate_metrics(
    cases: Sequence[R002CaseResult], universe: R002AnnotationUniverse,
    labels: R002CandidateLabelSet,
    parsed_cases: Mapping[R002CaseId, R002ParsedCase],
) -> R002Metrics:
    retrieved = {item.key: item for case in cases for item in case.retrieved_candidates}
    relevant_keys = {label.key for label in labels.labels if label.relevant}
    criteria_with_gold = {(key.case_id, key.criterion_id) for key in relevant_keys}
    criteria_with_retrieved_gold = {
        (key.case_id, key.criterion_id) for key in retrieved if key in relevant_keys
    }
    all_paths = {(case_id, file.stream, file.path)
                 for case_id, parsed in parsed_cases.items() for file in parsed.files}
    hit_paths = {(key.case_id, key.stream, key.path) for key in retrieved}
    all_hunks = {(case_id, hunk.hunk_id)
                 for case_id, parsed in parsed_cases.items()
                 for file in parsed.files for hunk in file.hunks}
    hit_hunks = {(item.key.case_id, item.hunk_id) for item in retrieved.values()}
    explanations = {(item.case_id, item.criterion_id, item.evidence_type)
                    for case in cases for item in case.missing_explanations}
    expected = {(item.case_id, item.criterion_id, item.evidence_type)
                for item in labels.expected_missing}
    return R002Metrics(
        owner_confirmed_label_candidate_precision=metric(
            len(set(retrieved) & relevant_keys), len(retrieved)
        ),
        criterion_candidate_coverage=metric(
            len(criteria_with_retrieved_gold), len(criteria_with_gold)
        ),
        candidate_to_gold_file_coverage=metric(len(hit_paths), len(all_paths)),
        candidate_to_gold_hunk_coverage=metric(len(hit_hunks), len(all_hunks)),
        missing_evidence_explanation_completeness=metric(
            len(explanations & expected), len(expected)
        ),
        implementation_test_separation_errors=sum(
            case.separation_errors for case in cases
        ),
        immutable_reference_integrity_errors=sum(
            case.reference_errors for case in cases
        ),
        parse_errors=0,
        schema_errors=0,
        source_hash_errors=0,
        source_sha_errors=0,
        unexpected_ready_count=sum(
            case.gate_verdict is GateVerdict.READY for case in cases
        ),
        normalized_rerun_mismatches=0,
    )
```

The four preflight integrity counters are zero here only because parsing, strict-schema loading, body/hash validation, and base/head-SHA validation abort `run_r002` before `_execute_r002_pass`; they are never inferred from an absent exception or used to hide a skipped case. Separation/reference counters are explicit sums of all case results, Ready is counted from observed gate verdicts, and the rerun counter starts at zero until both projections are compared. Add focused tests for every integer field and for the corresponding preflight abort path. Candidate precision/coverage values are baseline observations only, not pass thresholds.

Implement `audit_r002_redaction` as a local-only, offline, field-aware boundary check. Reopen every selected row and saved review through its strict Pydantic type. Build two deduplicated sets: body values (nonblank problem statements, patches, test patches, hints, review source text, evidence excerpts, and context excerpts) and exact scalar values (decoded individual `FAIL_TO_PASS`/`PASS_TO_PASS` test names, generated review IDs, generated/fetched timestamps, and the absolute cache-root string). Cap their combined UTF-8 bytes at `R002_REDACTION_RAW_VALUE_MAX_BYTES`; never print or persist them.

Open each allowlisted candidate with `O_RDONLY | O_NOFOLLOW`, require a regular file, and stream at most `R002_REDACTION_TRACKED_FILE_MAX_BYTES` per file. For JSON, use a bounded incremental UTF-8 JSON tokenizer whose key/string-scalar state survives chunk boundaries: reject every forbidden raw-content/HTTP-metadata key, any decoded scalar exactly equal to a body or scalar value, any body value of at least 32 bytes contained within a larger decoded scalar, and UUID/ISO-timestamp/absolute-cache-path content. For Markdown/text, incrementally emit complete logical scalars from full lines, table cells, fenced-code lines, inline-code spans, and lines after removing only Markdown container markers and matching quote/backtick pairs. Reject exact scalar equality, exact consecutive logical-line sequences for multiline bodies, long body values contained within a single logical scalar, UUID/ISO timestamp patterns, the absolute cache path, and HTTP-metadata field labels. Never scan short test names as arbitrary substrings inside allowed paths or prose.

There is no unrelated aggregate candidate-pack limit: the caller supplies a fixed, repository-contract-bounded file list, and each file uses the same 512 MiB ceiling as the largest approved persisted artifact. Return only checked file/value counts and sorted SHA-256 hashes. Tests cover a safe candidate above 8 MiB; a forbidden decoded JSON scalar split across chunks; Markdown scalar/body detection; symlink, non-regular, and per-file-limit failures; deterministic output under different chunk sizes; and the pinned-cohort collision where raw test name `test_relational` appears only inside allowed path `tests/test_relational.py`.

- [ ] **Step 7: Implement two-run determinism and hard integrity gates**

`run_r002` validates manifest/criteria/labels/cache hashes and performs the entire offline evaluation twice without a skip path. The first pass atomically saves each full local bundle to `reviews/<case-id>.json`; the second pass is read-only and does not overwrite those nondeterministic local bundles. Build one projection per pass containing only stable manifest identity, criteria/label hashes, candidate keys, evidence classifications/levels, finding/gate enums, reason codes, reference hashes, limitations, and metrics.

Implement the run as these exact fail-closed phases; do not wrap the per-case loop in a catch-and-continue block:

1. Load the exact production source manifest, confirmed criteria, and confirmed labels with the three fixed loaders. Compute their canonical hashes once. Load `cache-index.json` and `annotation-universe.json`; require the index source/manifest/criteria hashes, the universe manifest/criteria hashes, the label universe hash, and all five research-boundary literals to match. Require exact `R002-001` through `R002-020` order across manifest, criteria, cache index, and universe, then call `validate_complete_labels`. Build the label dictionary only after proving its ordered keys equal the complete universe exactly.
2. For each zipped manifest/criteria/index case, require matching case ID, problem hash, row hash, patch hash, and test-patch hash. Reopen `rows/<row_sha256>` as `SWEbenchVerifiedRow`; rehash the canonical row and all three bounded body fields; parse both diff streams again; require the parsed-case hash to equal the cached hash. Reopen each indexed `head-files/<content_sha256>` object with its expected digest, require its byte length/head SHA, re-run `verify_case_head_files`, and require the resulting ordered verified lines to equal the cached sidecar. Keep these validated in-memory inputs in manifest order; a single mismatch raises `R002RunError("run_input_drift")` before either evaluation pass.
3. `_execute_r002_pass(save_reviews: bool)` loops over all 20 prepared inputs in order. It calls `build_r002_review`, optionally writes the strict `ReviewBundle` to `reviews/<case-id>.json`, calls `evaluate_r002_case`, and appends exactly one redacted result. It then calculates metrics from all 20 case results and constructs an `R002BenchmarkResult` with explicit `20/0/0` counts, the three input hashes, confirmed criterion/candidate counts, zero initial rerun mismatches, fixed limitations, and hard-gate codes computed only from the observed result. It never substitutes an empty case, decrements the denominator, or returns a partial result.
4. Run `_execute_r002_pass(save_reviews=True)`, then reopen and validate all 20 saved bundles through `R002Cache.read_model`. Run `_execute_r002_pass(save_reviews=False)` without writing any file. Build one determinism projection from each result and compare both canonical projection hashes plus each ordered case-result hash. `normalized_rerun_mismatches` is exactly the number of case IDs whose ordered case-result projection differs; it never includes an aggregate-only increment. Independently compare the aggregate metrics and full projection hashes. Any nonzero case mismatch, aggregate-metric mismatch, or full-projection mismatch raises `R002RunError("normalized_rerun_mismatch")` and emits no benchmark result.
5. Rebuild the returned first result with `normalized_rerun_mismatches=0` mirrored in both the aggregate field and `R002Metrics`. Re-run all hard gates against that final strict object. If the sorted hard-gate code tuple is nonempty, raise `R002RunError("benchmark_gate_failed")`; otherwise require `hard_gate_errors == ()` and return the validated result.

Use only these additional `R002RunError` reason codes for this path: `run_input_drift`, `reannotation_required`, `expected_missing_label_conflict`, `redaction_boundary_failed`, `normalized_rerun_mismatch`, and `benchmark_gate_failed`, plus the five source-commit codes defined in Task 9. Add every literal to the closed allowlist and assert the complete set in tests. The CLI maps them to the bounded public failure codes `input_validation_failed`, `annotation_required`, or `benchmark_gate_failed`; it never emits a partial result or the underlying body/path/hash mismatch.

The pass builder is deliberately explicit:

```python
def _execute_r002_pass(
    *, prepared: Sequence[_R002PreparedRunCase], labels: R002CandidateLabelSet,
    universe: R002AnnotationUniverse, scopeproof_commit: GitSha,
    input_hashes: _R002InputHashes, cache: R002Cache, save_reviews: bool,
) -> R002BenchmarkResult:
    label_by_key = {label.key: label for label in labels.labels}
    case_results: list[R002CaseResult] = []
    parsed_by_case: dict[R002CaseId, R002ParsedCase] = {}
    for item in prepared:
        bundle = build_r002_review(
            case=item.case, row=item.row,
            criterion_case=item.criterion_case, parsed=item.parsed,
        )
        if save_reviews:
            cache.replace_model(f"reviews/{item.case.case_id}.json", bundle)
        case_results.append(evaluate_r002_case(
            case=item.case, bundle=bundle, verified=item.verified,
            label_by_key=label_by_key,
            expected_missing=labels.expected_missing,
        ))
        parsed_by_case[item.case.case_id] = item.parsed
    metrics = calculate_metrics(case_results, universe, labels, parsed_by_case)
    return R002BenchmarkResult(
        source_manifest_sha256=input_hashes.manifest,
        criteria_set_sha256=input_hashes.criteria,
        candidate_label_set_sha256=input_hashes.labels,
        scopeproof_commit=scopeproof_commit,
        executed_case_count=20,
        failed_case_count=0,
        skipped_case_count=0,
        confirmed_criterion_count=sum(
            len(item.criterion_case.criteria) for item in prepared
        ),
        annotation_candidate_count=universe.candidate_count,
        case_results=tuple(case_results),
        metrics=metrics,
        unexpected_ready_count=metrics.unexpected_ready_count,
        normalized_rerun_mismatches=0,
        hard_gate_errors=tuple(sorted(_hard_gate_codes(case_results, metrics))),
        limitations=R002_RESULT_LIMITATIONS,
    )
```

`_R002PreparedRunCase` and `_R002InputHashes` are private frozen in-memory dataclasses, not persisted models. `_hard_gate_codes` returns stable codes only and checks every condition listed below; it does not mutate results. Tests directly force each code, prove one corrupt case aborts the whole command, prove the second pass performs zero cache writes, and prove a changed stable field yields `normalized_rerun_mismatch` while UUID/time-only changes do not.

```python
def build_determinism_projection(result: R002BenchmarkResult) -> R002DeterminismProjection:
    return R002DeterminismProjection(
        pack_id=result.pack_id,
        source_manifest_sha256=result.source_manifest_sha256,
        criteria_set_sha256=result.criteria_set_sha256,
        candidate_label_set_sha256=result.candidate_label_set_sha256,
        scopeproof_commit=result.scopeproof_commit,
        case_results=result.case_results,
        metrics=result.metrics,
        limitations=result.limitations,
    )
```

Reject unless: executed/failed/skipped are exactly `20/0/0`; all objects validate; every source/hash/SHA/reference error count is zero; every test-stream candidate is TEST/E2; no evidence exceeds E2; all expected missing pairs have explanations; all cases have unavailable/empty CI, no runtime evidence/resolutions/final acceptance; every gate has an allowed shape; `unexpected_ready_count == 0`; both projection hashes match; and Task 3's two existing benchmark results remain exact.

- [ ] **Step 8: Run runner tests and verify GREEN**

Run:

```bash
uv run pytest -q tests/evals/test_r002_runner.py tests/evals/test_r002_annotation.py \
  tests/evals/test_r002_verify.py
uv run scopeproof benchmark
uv run scopeproof comparison-benchmark
uv run ruff check scopeproof_core/evals/r002_runner.py tests/evals/test_r002_runner.py
```

Expected: all focused tests pass; both existing benchmark outputs retain their exact counts and have no mismatches.

- [ ] **Step 9: Commit the offline runner slice**

```bash
git add scopeproof_core/evals/r002_runner.py tests/evals/test_r002_runner.py
git commit -m "feat: score R-002 research evidence offline"
```

### Task 9: Add the standalone module commands, packaging, CI fixture coverage, and docs skeleton

**Files:**
- Create: `scopeproof_core/evals/r002_swebench.py`
- Create: `tests/evals/test_r002_cli.py`
- Modify: `tests/test_repository_contracts.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/development-environment.md`

**Interfaces:**
- Consumes: `prepare_criteria_sources`, `prepare_r002`, `annotate_r002`, and `run_r002`; locates `evals/r002` with `Path(__file__).resolve().parents[2]`.
- Produces: the two explicit `prepare` phases plus `annotate` and `run`, deterministic bounded JSON stdout on post-parse domain success or failure, nonzero exit on an unmet gate, and an installed-wheel command surface. Standard `argparse` help and usage errors remain pre-dispatch stderr/`SystemExit` behavior and make no product-result claim.

- [ ] **Step 1: Write failing command tests**

Call `main(["prepare", "--phase", "criteria-sources", "--cache-dir", str(cache)], transport=mock_transport)` and the corresponding evidence/annotate/run argument lists directly. Assert the two prepare phases are the only network-capable paths, `annotate` rejects unconfirmed/missing criteria before reading patches, `run` works with networking disabled, no command imports `datasets`, and importing/running `run` does not import `pyarrow`.

```python
def test_run_is_offline_and_does_not_import_pyarrow(complete_r002_pack, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    monkeypatch.setattr(httpx.Client, "send", lambda *args, **kwargs: pytest.fail("network used"))
    monkeypatch.setattr(
        "scopeproof_core.evals.r002_swebench.resolve_scopeproof_commit",
        lambda *_args, **_kwargs: "a" * 40,
    )
    exit_code = main([
        "run", "--cache-dir", str(complete_r002_pack.cache_root),
        "--scopeproof-commit", "a" * 40,
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["executed_case_count"] == 20
    assert payload["unexpected_ready_count"] == 0

def test_success_stdout_is_exact_canonical_json(complete_r002_pack, monkeypatch, capsysbinary):
    monkeypatch.setattr(
        "scopeproof_core.evals.r002_swebench.resolve_scopeproof_commit",
        lambda *_args, **_kwargs: "a" * 40,
    )
    assert main(["run", "--cache-dir", str(complete_r002_pack.cache_root)]) == 0
    output = capsysbinary.readouterr().out
    result = R002BenchmarkResult.model_validate_json(output)
    assert output == canonical_json_bytes(result)
    assert not output.endswith(b"\n")

def test_annotate_rejects_unconfirmed_criteria_before_patch_access(
    prepared_pack, recording_cache, capsys
):
    exit_code = main(["annotate", "--cache-dir", str(prepared_pack.cache_root)])
    payload = R002CommandFailure.model_validate_json(capsys.readouterr().out)
    assert exit_code != 0
    assert payload.reason_code == "criteria_not_confirmed"
    assert recording_cache.patch_reads == 0

def test_evidence_prepare_failure_is_redacted_json(
    unconfirmed_pack, recording_transport, capsys
):
    exit_code = main([
        "prepare", "--phase", "evidence",
        "--cache-dir", str(unconfirmed_pack.cache_root),
    ], transport=recording_transport)
    output = capsys.readouterr().out
    payload = R002CommandFailure.model_validate_json(output)
    assert exit_code != 0
    assert payload.reason_code == "criteria_not_confirmed"
    assert recording_transport.requests == []
    assert str(unconfirmed_pack.cache_root) not in output

def test_checkout_commit_must_be_clean_head(clean_git_checkout):
    head = clean_git_checkout.head
    assert resolve_scopeproof_commit(head, checkout_root=clean_git_checkout.path) == head
    with pytest.raises(R002RunError, match="scopeproof_commit_mismatch"):
        resolve_scopeproof_commit("b" * 40, checkout_root=clean_git_checkout.path)
    clean_git_checkout.write_untracked("tracked-candidate.txt")
    with pytest.raises(R002RunError, match="scopeproof_checkout_dirty"):
        resolve_scopeproof_commit(head, checkout_root=clean_git_checkout.path)
```

- [ ] **Step 2: Run command tests and verify RED**

Run:

```bash
uv run pytest -q tests/evals/test_r002_cli.py \
  tests/test_repository_contracts.py::test_r002_module_commands_are_packaged_but_not_live_ci
```

Expected: FAIL because `r002_swebench.py` and the final command contract do not exist.

- [ ] **Step 3: Implement the standalone dispatcher**

Do not modify `scopeproof_core/cli.py`. Require `--phase criteria-sources|evidence` on `prepare`, permit `--cache-dir` on every command, and additionally permit `--scopeproof-commit` on `run` so a clean installed wheel can record its source commit. In a source checkout, default the commit from `git rev-parse HEAD`; outside a checkout, require the explicit 40-character lowercase SHA.

```python
def bundled_r002_root() -> Path:
    return Path(__file__).resolve().parents[2] / "evals" / "r002"

def default_cache_root() -> Path:
    return Path(".scopeproof/research/r002")

def _git_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise argparse.ArgumentTypeError("expected a 40-character lowercase Git SHA")
    return value

def resolve_scopeproof_commit(
    explicit: str | None, *, checkout_root: Path | None = None
) -> GitSha:
    root = checkout_root or Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        if explicit is None:
            raise R002RunError("scopeproof_commit_required_outside_checkout")
        return _git_sha(explicit)
    try:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise R002RunError("scopeproof_git_probe_failed") from error
    if status.stdout:
        raise R002RunError("scopeproof_checkout_dirty")
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise R002RunError("scopeproof_git_probe_failed") from error
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise R002RunError("scopeproof_head_invalid")
    if explicit is not None and explicit != head:
        raise R002RunError("scopeproof_commit_mismatch")
    return head

def main(
    argv: Sequence[str] | None = None,
    *, transport: httpx.BaseTransport | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m scopeproof_core.evals.r002_swebench")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "annotate", "run"):
        command = commands.add_parser(name)
        command.add_argument("--cache-dir", type=Path, default=default_cache_root())
        if name == "prepare":
            command.add_argument(
                "--phase", choices=("criteria-sources", "evidence"), required=True
            )
        if name == "run":
            command.add_argument("--scopeproof-commit", type=_git_sha)
    args = parser.parse_args(argv)
    root = bundled_r002_root()
    try:
        if args.command == "prepare" and args.phase == "criteria-sources":
            result = prepare_criteria_sources(
                manifest_path=root / "source_manifest.json",
                cache_root=args.cache_dir,
                transport=transport,
            )
        elif args.command == "prepare":
            result = prepare_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                cache_root=args.cache_dir,
                transport=transport,
            )
        elif args.command == "annotate":
            result = annotate_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                cache_root=args.cache_dir,
            )
        else:
            result = run_r002(
                manifest_path=root / "source_manifest.json",
                criteria_path=root / "criteria.json",
                labels_path=root / "candidate_labels.json",
                cache_root=args.cache_dir,
                scopeproof_commit=resolve_scopeproof_commit(args.scopeproof_commit),
            )
    except R002_EXPECTED_ERRORS as error:
        failure = command_failure(args.command, error)
        sys.stdout.buffer.write(canonical_json_bytes(failure))
        sys.stdout.buffer.flush()
        return 2
    except Exception:
        failure = internal_command_failure(args.command)
        sys.stdout.buffer.write(canonical_json_bytes(failure))
        sys.stdout.buffer.flush()
        return 3
    sys.stdout.buffer.write(canonical_json_bytes(result))
    sys.stdout.buffer.flush()
    if isinstance(result, (R002CriteriaSourcePreparationResult, R002PreparationResult)):
        return int(bool(result.hard_gate_errors or not result.complete))
    if isinstance(result, R002AnnotationUniverse):
        return 0
    return int(bool(result.hard_gate_errors))
```

Define `R002_EXPECTED_ERRORS` as the closed tuple of R-002 domain errors plus Pydantic validation and bounded filesystem errors. `command_failure` maps exception classes and their allowlisted internal reason-code attributes to `R002CommandFailure`; it never serializes `str(error)`, exception args, paths, URLs, HTTP bodies, or headers. The module `__main__` block exits with `main()`'s code and never prints a traceback for an expected validation failure. Unit tests cover every mapping and a fallback `internal_error` code at the boundary without disclosing the triggering message.

Argument parsing intentionally occurs before this domain-error boundary. Add tests proving `--help`, a missing subcommand, a missing `--phase`, and a malformed `--scopeproof-commit` retain ordinary bounded `argparse` help/usage behavior on stderr and never emit a misleading `R002CommandFailure`. JSON output guarantees begin only after a syntactically valid command has been dispatched.

- [ ] **Step 4: Strengthen repository and CI contracts**

Add the final exact packaged-name assertion only in Task 12, after both confirmation artifacts exist:

```python
root = Path("evals/r002")
entries = tuple(root.rglob("*"))
assert root.is_dir() and not root.is_symlink()
assert all(path.is_file() and not path.is_symlink() for path in entries)
assert all(path.parent == root for path in entries)
assert {path.relative_to(root).as_posix() for path in entries} == {
    "source_manifest.json", "criteria.json", "candidate_labels.json",
}
assert wheel["force-include"]["evals"] == "evals"
assert "python -m scopeproof_core.evals.r002_swebench prepare" not in workflow
assert "python -m scopeproof_core.evals.r002_swebench annotate" not in workflow
assert "python -m scopeproof_core.evals.r002_swebench run" not in workflow
```

At this task, retain the active absent/partial-directory redaction contract from Task 1 and add no skipped test. Do not weaken the raw-content scan.

Change CI installs to:

```yaml
run: python -m pip install -e '.[dev,research]'
```

for Python 3.11 and verify jobs, and:

```yaml
run: python -m uv sync --extra dev --extra research --locked
```

for the locked job. CI runs the controlled full pytest suite but never calls live R-002 preparation, GitHub, Hugging Face, Docker, or target-repository code. At this task add only the installed-wheel `python -m scopeproof_core.evals.r002_swebench --help` check; add the bounded missing-cache assertion after the source manifest is committed in Task 10 so the expected failure order is deterministic.

- [ ] **Step 5: Document the opt-in engineering command surface**

Add a development-guide section containing the four exact invocations (`prepare --phase criteria-sources`, `prepare --phase evidence`, `annotate`, and `run`), `uv sync --extra dev --extra research --locked`, the two required owner confirmations, the ignored cache location, and these exact boundaries:

```text
R-002 is public engineering research only. It does not execute target-repository code, prove
correctness, provide runtime verification, constitute customer/Alpha validation, or advance
Stage 1. Both explicit `prepare` phases are the only networked paths; `annotate` and `run` are offline.
```

Do not add first-run metrics or claim that the benchmark exists until Tasks 10–11 complete.

- [ ] **Step 6: Run command, repository, and CI-contract tests**

Run:

```bash
uv run pytest -q tests/evals/test_r002_cli.py tests/test_repository_contracts.py
uv run ruff check scopeproof_core/evals/r002_swebench.py tests/evals/test_r002_cli.py \
  tests/test_repository_contracts.py
uv lock --check
```

Expected: every test passes with no new skip; lock check succeeds; CI contains no live R-002 command.

- [ ] **Step 7: Commit the command and controlled-CI slice**

```bash
git add scopeproof_core/evals/r002_swebench.py tests/evals/test_r002_cli.py \
  tests/test_repository_contracts.py .github/workflows/ci.yml docs/development-environment.md
git commit -m "feat: expose opt-in R-002 research commands"
```

### Task 10: Materialize the exact source manifest, prepare problem-only inputs, and freeze criteria for owner review

**Files:**
- Create: `evals/r002/source_manifest.json`
- Modify: `tests/test_repository_contracts.py`
- Create only in ignored cache: `.scopeproof/research/r002/criteria-proposal.json`
- Create only in ignored cache: `.scopeproof/research/r002/criteria-review.json`

**Interfaces:**
- Consumes: the approved cohort table in the design, the exact row/hash table in this plan, `prepare --phase criteria-sources`, and the criteria-proposal path.
- Produces: one tracked source manifest, one complete problem-only criteria-source index, and one unconfirmed 20-case criteria proposal. This task performs no GitHub request, full-row decode, patch/test-patch inspection, head-file fetch, or ScopeProof retrieval.

- [ ] **Step 1: Add the complete redacted source manifest with `apply_patch`**

Create one canonical `R002SourceManifest` JSON object. Use the fixed source dictionary, identity table, difficulty mapping, and row/hash table above. Every case has this exact shape:

```json
{
  "case_id": "R002-001",
  "instance_id": "astropy__astropy-14096",
  "repository": "astropy/astropy",
  "pr_number": 14096,
  "pr_url": "https://github.com/astropy/astropy/pull/14096",
  "dataset_base_commit": "1a4462d72eb03f30dc83a879b1dd57aac8b2c18b",
  "verified_pr_head_sha": "271b2875d9aae0a5875acba0b1b27dc4885fd6e5",
  "row_index": 7,
  "difficulty": "15 min - 1 hour",
  "row_sha256": "2ab9bc4442553756efedd9737e68d2c11a68954da353a12acb903c86ba414ec0",
  "problem_statement_sha256": "938971021e89cd882f6ea33d61202fe7aa0091d7be4748b100ddc7e164db90cd",
  "patch_sha256": "57a810467af331eba7c3238bbcd78268a47e96ad75eed3e2aa8b908da99104bc",
  "test_patch_sha256": "3a6a8ffc9c81264bccb9990b926bc6b1c2253a9aa7ce47810b5d28ad95c2596c"
}
```

Repeat the same explicit field set for `R002-002` through `R002-020` using only the fixed tables in this plan; do not generate or infer an issue URL. Re-open the patched file with `load_source_manifest` and compare `canonical_json_bytes(reopened)` with the pre-patch canonical model bytes. The checked-in text may have the one conventional terminal newline added by `apply_patch`; identity hashes always use newline-free canonical model bytes.

- [ ] **Step 2: Strengthen the source-manifest repository contract**

Add exact source identity and redaction assertions:

```python
def test_r002_source_manifest_is_exact_and_redacted() -> None:
    path = Path("evals/r002/source_manifest.json")
    manifest = load_source_manifest(path)
    assert manifest.source.model_dump(mode="json") == R002_SOURCE
    assert [case.case_id for case in manifest.cases] == [
        f"R002-{number:03d}" for number in range(1, 21)
    ]
    assert len({case.repository for case in manifest.cases}) == 12
    raw = path.read_text(encoding="utf-8")
    for forbidden_key in (
        '"problem_statement":', '"patch":', '"test_patch":', '"hints_text":',
        '"FAIL_TO_PASS":', '"PASS_TO_PASS":',
    ):
        assert forbidden_key not in raw
```

- [ ] **Step 3: Validate and commit the source manifest before networking**

Run:

```bash
uv run pytest -q tests/evals/test_r002_models.py tests/evals/test_r002_source.py \
  tests/test_repository_contracts.py::test_r002_source_manifest_is_exact_and_redacted
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import load_source_manifest; load_source_manifest(Path("evals/r002/source_manifest.json"))'
git diff --check
git add evals/r002/source_manifest.json tests/test_repository_contracts.py
git commit -m "data: pin R-002 SWE-bench cohort"
R002_SMOKE_DIST="$(mktemp -d /tmp/scopeproof-r002-smoke-dist-XXXXXX)"
R002_SMOKE_VENV="$(mktemp -d /tmp/scopeproof-r002-smoke-venv-XXXXXX)"
R002_EMPTY_CACHE="$(mktemp -d /tmp/scopeproof-r002-empty-cache-XXXXXX)"
R002_SMOKE_COMMIT="$(git rev-parse HEAD)"
uv build --out-dir "$R002_SMOKE_DIST"
python3 -m venv "$R002_SMOKE_VENV"
"$R002_SMOKE_VENV/bin/python" -m pip install "$R002_SMOKE_DIST"/scopeproof-*.whl
set +e
(cd /tmp && "$R002_SMOKE_VENV/bin/python" -m \
  scopeproof_core.evals.r002_swebench run \
  --cache-dir "$R002_EMPTY_CACHE" \
  --scopeproof-commit "$R002_SMOKE_COMMIT" \
  > /tmp/scopeproof-r002-missing-input.json)
R002_SMOKE_EXIT=$?
set -e
test "$R002_SMOKE_EXIT" -ne 0
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import R002CommandFailure; value=R002CommandFailure.model_validate_json(Path("/tmp/scopeproof-r002-missing-input.json").read_text(encoding="utf-8")); assert value.reason_code == "criteria_missing"'
```

Expected: all validations pass, the diff contains no raw dataset body, and the commit succeeds. Build the wheel once here and assert its `run` command emits a validated bounded `R002CommandFailure` with `reason_code="criteria_missing"`; the documented run-preflight order is source manifest, confirmed criteria, confirmed labels, then complete cache, so this assertion is stable before the later two owner-gated inputs exist.

- [ ] **Step 4: Run the real problem-only preparation phase**

Run:

```bash
uv sync --extra dev --extra research --locked
uv run python -m scopeproof_core.evals.r002_swebench prepare \
  --phase criteria-sources
```

Expected: exact source size/hash/schema/500 rows/12 repositories/500 unique IDs; exact 20 selected cases; `executed_case_count=20`, `failed_case_count=0`, `skipped_case_count=0`; exactly 20 hash-addressed problem-statement objects and one complete validated `criteria-source-index.json`. The instrumentation/protocol guarantees zero reads of patch, test-patch, hint, test-name, or other non-criteria columns and zero GitHub requests. The full 500-row Parquet scratch descriptor is closed and gone. A network failure is a preparation failure, not a skipped case; retry the same immutable source without changing the manifest.

- [ ] **Step 5: Prove no third-party raw material became tracked**

Run:

```bash
git status --short
git check-ignore -v .scopeproof/research/r002/criteria-source-index.json
git ls-files .scopeproof evals/r002 docs/research/r002-swebench-verified
test ! -e .scopeproof/research/r002/cache-index.json
test ! -d .scopeproof/research/r002/rows
test ! -d .scopeproof/research/r002/head-files
```

Expected: `.scopeproof/research/r002/` is ignored; only `evals/r002/source_manifest.json` is tracked in the new pack; no problem statement or cache object appears in tracked files; and no full cache index, selected full-row object, head-file directory, patch, test patch, hint, test name, parsed diff, or source excerpt exists locally yet.

- [ ] **Step 6: Author the complete criteria proposal from problem statements only**

For cases in `R002-001` through `R002-020` order, read only the local `criteria-sources/<problem_statement_sha256>` object through `R002Cache.read_bytes`. There is no cached full-row object at this stage. Author 1–16 atomic criteria per case, including at least one `MUST_HAVE`, and explicitly set every field:

```json
{
  "criterion_id": "AC-01",
  "text": "One atomic ScopeProof-authored paraphrase",
  "priority": "must_have",
  "criterion_type": "behavior",
  "criterion_source": "user_confirmed",
  "source_span": "problem_statement:L1-L2",
  "required_evidence_level": "E1"
}
```

Do not open or search `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`, hints, raw head files, GitHub diff views, ScopeProof output, or earlier annotations. Pass the complete mapping into `build_criteria_proposal`, write the returned strict object to ignored `criteria-proposal.json`, and generate ignored `criteria-review.json` with the source text/hash and proposed fields for all 20 cases.

- [ ] **Step 7: Validate criteria isolation and proposal completeness**

Run:

```bash
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import R002CriteriaProposal; p=Path(".scopeproof/research/r002/criteria-proposal.json"); value=R002CriteriaProposal.model_validate_json(p.read_text(encoding="utf-8")); assert len(value.cases)==20; assert all(1 <= len(case.criteria) <= 16 for case in value.cases); assert value.benchmark_owner_confirmed is False; assert value.source_owner_confirmed is False'
uv run pytest -q tests/evals/test_r002_annotation.py::test_criteria_proposal_reads_problem_statements_only
```

Expected: proposal validates, all 20 cases are present, and the isolation test proves no patch/test/output access.

- [ ] **Step 8: Present the complete criteria review and stop at Owner Gate 1**

Present all 20 case IDs, public PR URLs, problem hashes, and complete criterion objects to the benchmark owner. State exactly:

```text
This confirms ScopeProof-authored research criteria only. The original source owners did not
confirm them; this is not Alpha/customer validation and does not advance Stage 1. No patch,
test patch, or ScopeProof result has been inspected for criterion authoring.
```

Required response: an explicit confirmation of the complete criterion wording and fields. Do not create `evals/r002/criteria.json`, call `annotate`, inspect patches, label candidates, or run ScopeProof until that confirmation exists. If the owner requests edits, revise the proposal from problem statements only, change its hash, and repeat this gate.

### Task 11: Freeze confirmed criteria, independently label the full universe, and stop for label approval

**Files:**
- Create after Owner Gate 1: `evals/r002/criteria.json`
- Modify: `tests/test_repository_contracts.py`
- Create only in ignored cache: `.scopeproof/research/r002/annotation-universe.json`
- Create only in ignored cache: `.scopeproof/research/r002/annotation-review.json`
- Create only in ignored cache: `.scopeproof/research/r002/candidate-label-proposal.json`

**Interfaces:**
- Consumes: the explicitly approved `R002CriteriaProposal`, exact source manifest/problem-only cache, and no ScopeProof scored output.
- Produces: one tracked confirmed criteria set, one complete criteria-bound evidence cache prepared only after that commit, and one complete unconfirmed candidate-label proposal for Owner Gate 2.

- [ ] **Step 1: Transform the approved proposal into the redacted confirmed criteria set**

Call `confirmed_criteria_from_proposal`; assert the result keeps `source_owner_confirmed=false`, sets `benchmark_owner_confirmed=true`, strips every raw problem statement, and preserves all approved criterion fields byte-for-byte. Add the canonical output with `apply_patch` to `evals/r002/criteria.json`.

```python
proposal = R002CriteriaProposal.model_validate_json(proposal_path.read_text(encoding="utf-8"))
confirmed = confirmed_criteria_from_proposal(proposal)
assert confirmed.source_owner_confirmed is False
assert confirmed.benchmark_owner_confirmed is True
assert "problem_statement" not in canonical_json_bytes(confirmed).decode("utf-8")
```

- [ ] **Step 2: Validate and commit the confirmed criteria before patch inspection**

Run:

```bash
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import R002CriteriaSet; R002CriteriaSet.model_validate_json(Path("evals/r002/criteria.json").read_text(encoding="utf-8"))'
uv run pytest -q tests/evals/test_r002_models.py tests/evals/test_r002_annotation.py \
  tests/test_repository_contracts.py
git diff --check
git add evals/r002/criteria.json tests/test_repository_contracts.py
git commit -m "data: freeze R-002 research criteria"
```

Expected: every test passes, no raw problem text is tracked, and criteria remain explicitly non-source-owner-confirmed.

- [ ] **Step 3: Run the post-confirmation evidence preparation phase**

Now—and only after the confirmed criteria commit exists—run:

```bash
uv run python -m scopeproof_core.evals.r002_swebench prepare \
  --phase evidence
```

Expected: the command first validates `criteria.json` and its manifest hash, then redownloads the exact source into a secure unlinked scratch descriptor, decodes the full rows, validates the 20 selected row/patch/test-patch hashes, verifies all 20 public closed merged PR base/head SHAs, parses the two diff streams, fetches and verifies the exact immutable head files, materializes only the selected 20 rows and referenced head files, and publishes `cache-index.json` last with the criteria-set hash. Expected counts are `20/0/0`, 47 immutable head files, zero source/hash/SHA/line/reference errors, and no target code execution. Network or integrity failure invalidates the new phase rather than skipping or replacing a case.

- [ ] **Step 4: Audit selected-only cache integrity before annotation**

Run a local cache audit through `R002Cache` and the strict models: revalidate `criteria-source-index.json` and `cache-index.json`; require the latter's source, manifest, and criteria hashes to equal the tracked inputs; enumerate exactly 20 `rows/<row_sha256>` objects and only the head-file digests referenced by the index; rehash every object; and prove no persistent Parquet source object, HTTP metadata, credentials, absolute paths, or unindexed raw file exists. Then run:

```bash
git status --short
git check-ignore -v .scopeproof/research/r002/cache-index.json
git ls-files .scopeproof evals/r002
```

Expected: all raw selected rows, patches, test patches, problem text, and head-file bodies remain ignored and local; tracked inputs remain only redacted manifest and confirmed criteria; the full 500-row Parquet no longer exists.

- [ ] **Step 5: Build the independent annotation universe offline**

Now—and only now—run:

```bash
uv run python -m scopeproof_core.evals.r002_swebench annotate
```

Expected: the command loads confirmed criteria, reads cached patch/test-patch and verified sidecars, builds the complete sorted criterion × added/context-line universe, enforces the 250,000-pair cap without truncation, and writes validated ignored `annotation-universe.json` plus raw ignored `annotation-review.json`. It must not call `retrieve_evidence`, `build_findings`, `evaluate_gate`, or any network function.

- [ ] **Step 6: Label every frozen pair independently**

Review each local annotation item using its criterion, stream, repository-relative path, new-side line number, raw marker-free line, and bounded neighboring context. Set exactly one boolean and one stable reason code for every key:

```json
{
  "key": {
    "case_id": "R002-001",
    "criterion_id": "AC-01",
    "stream": "patch",
    "path": "repository/relative/path.py",
    "new_line_number": 42,
    "normalized_line_sha256": "64-lowercase-hex"
  },
  "relevant": true,
  "reason_code": "direct_static_candidate"
}
```

Use `direct_static_candidate`, `supporting_static_candidate`, `test_intent_candidate`, `unrelated_candidate`, or `insufficient_context` as the only reason codes. Do not run ScopeProof, inspect its retrieved candidates, change criteria, change the cohort, or omit difficult pairs. Generate `expected_missing` solely through `derive_expected_missing` after all booleans are present.

- [ ] **Step 7: Validate the complete unconfirmed label proposal**

Write ignored `candidate-label-proposal.json` as a strict draft whose owner confirmation is false. Run:

```bash
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import R002CandidateLabelProposal,R002AnnotationUniverse,R002CriteriaSet; from scopeproof_core.evals.r002_runner import validate_complete_label_proposal; cache=Path(".scopeproof/research/r002"); criteria=R002CriteriaSet.model_validate_json(Path("evals/r002/criteria.json").read_text(encoding="utf-8")); universe=R002AnnotationUniverse.model_validate_json((cache/"annotation-universe.json").read_text(encoding="utf-8")); labels=R002CandidateLabelProposal.model_validate_json((cache/"candidate-label-proposal.json").read_text(encoding="utf-8")); validate_complete_label_proposal(criteria,universe,labels); assert labels.benchmark_owner_confirmed is False'
```

Expected: exact key equality, exact count and universe hash, no duplicates, no missing/extra keys, only allowed reason codes, derived expected-missing equality, and false confirmation.

- [ ] **Step 8: Present the frozen label summary and stop at Owner Gate 2**

Present per-case criterion count, candidate-line count, pair count, relevant/irrelevant counts by reason code, implementation/test path counts, expected-missing counts, and the exact universe/proposal hashes. Show a bounded sample of decisions from each reason code; keep raw content local and out of Git. State exactly:

```text
These are benchmark-owner research labels, not source-owner requirements, runtime results,
reviewer acceptance, or customer validation. ScopeProof has not been scored against them yet.
Confirming freezes this complete label universe before the first scored run.
```

Required response: explicit batch confirmation. Do not create `evals/r002/candidate_labels.json` or call `run` before it exists. If any label changes, regenerate the proposal hash and repeat the complete gate; never relabel after seeing a score.

### Task 12: Freeze labels, execute the real benchmark twice, publish redacted engineering evidence, and verify the branch

**Files:**
- Create after Owner Gate 2: `evals/r002/candidate_labels.json`
- Create: `docs/research/r002-swebench-verified/result.json`
- Create: `docs/research/r002-swebench-verified/summary.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/development-environment.md`
- Modify: `tests/test_repository_contracts.py`
- Create: `tests/fixtures/r002_redaction/sentinels.json` with ScopeProof-authored synthetic strings only

**Interfaces:**
- Consumes: the explicitly approved complete label proposal, the committed source/criteria inputs, and the complete immutable cache.
- Produces: one frozen label-set commit, one exact scored commit SHA, one deterministic redacted first-run result, truthful docs, full verification evidence, and a local handoff. It does not push, release, or advance Stage 1.

- [ ] **Step 1: Transform and add the confirmed label set**

Create `R002CandidateLabelSet` from the approved proposal with `benchmark_owner_confirmed=true`; preserve the source-manifest, criteria-set, universe hashes, every key/boolean/reason, and the derived expected-missing list exactly. Strip all raw line/context text. Add the canonical JSON with `apply_patch`.

- [ ] **Step 2: Remove the pre-materialization allowance and require all exact packaged files**

The final repository contract must require:

```python
root = Path("evals/r002")
entries = tuple(root.rglob("*"))
assert root.is_dir() and not root.is_symlink()
assert all(path.is_file() and not path.is_symlink() for path in entries)
assert all(path.parent == root for path in entries)
assert {path.relative_to(root).as_posix() for path in entries} == {
    "source_manifest.json",
    "criteria.json",
    "candidate_labels.json",
}
source = load_source_manifest(Path("evals/r002/source_manifest.json"))
criteria = load_confirmed_criteria(
    Path("evals/r002/criteria.json"), canonical_sha256(source)
)
labels = load_confirmed_labels(
    Path("evals/r002/candidate_labels.json"),
    canonical_sha256(source),
    canonical_sha256(criteria),
)
assert labels.benchmark_owner_confirmed is True
```

Keep the recursive forbidden-field/key scan. In this step create `tests/fixtures/r002_redaction/sentinels.json` with clearly artificial problem/patch/test-name/source/excerpt/context/UUID/timestamp/path/header strings and no third-party text. CI tests compare tracked R-002 outputs only with those ScopeProof-authored sentinels; they never depend on the ignored local cache. Add a separate one-off local audit command in Step 5 that extracts bounded hashes from the real ignored cache and compares them with tracked candidate bytes without copying raw sentinels into tests, logs, or Git.

- [ ] **Step 3: Validate and commit labels before any scored run**

Run:

```bash
uv run pytest -q tests/evals/test_r002_models.py tests/evals/test_r002_annotation.py \
  tests/test_repository_contracts.py
git diff --check
git add evals/r002/candidate_labels.json tests/test_repository_contracts.py \
  tests/fixtures/r002_redaction/sentinels.json
git commit -m "data: freeze R-002 candidate labels"
git rev-parse HEAD > /tmp/scopeproof-r002-scored-commit.txt
test "$(wc -c < /tmp/scopeproof-r002-scored-commit.txt | tr -d ' ')" -eq 41
```

Expected: the exact confirmed inputs are committed before scoring, all tests pass, and `R002_SCORED_COMMIT` is the lowercase 40-character commit that the result will record.

- [ ] **Step 4: Run the real 20-case benchmark offline**

Disable network at the process boundary if the platform supports it, then run:

```bash
export R002_SCORED_COMMIT="$(tr -d '\n' < /tmp/scopeproof-r002-scored-commit.txt)"
uv run python -m scopeproof_core.evals.r002_swebench run \
  --scopeproof-commit "$R002_SCORED_COMMIT" \
  > /tmp/scopeproof-r002-result.json
```

Expected: the internal two runs each execute exactly 20 cases with zero failed/skipped cases; every object/hash/SHA/permalink validates; every test-patch candidate stays TEST/E2; no E3/E4, concrete CI check/status observation, runtime evidence, resolution, or final acceptance appears; each validated CI observation remains exactly unavailable/`no_observations` with complete collection and all counts zero; every gate is exactly an allowed blocked/needs-review shape; missing-explanation completeness is 100% when applicable; `unexpected_ready_count=0`; normalized rerun mismatches are zero. Precision and coverage are reported as observed baselines with numerator/denominator or `not_applicable`, never used as retroactive thresholds.

- [ ] **Step 5: Re-open the result through Pydantic and audit redaction**

Run:

```bash
export R002_SCORED_COMMIT="$(tr -d '\n' < /tmp/scopeproof-r002-scored-commit.txt)"
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import R002BenchmarkResult; p=Path("/tmp/scopeproof-r002-result.json"); r=R002BenchmarkResult.model_validate_json(p.read_text(encoding="utf-8")); assert r.executed_case_count==20 and r.failed_case_count==0 and r.skipped_case_count==0 and r.unexpected_ready_count==0 and r.normalized_rerun_mismatches==0 and not r.hard_gate_errors'
uv run python -c 'import json,os; r=json.load(open("/tmp/scopeproof-r002-result.json")); assert r["scopeproof_commit"]==os.environ["R002_SCORED_COMMIT"]'
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import canonical_json_bytes; from scopeproof_core.evals.r002_runner import audit_r002_redaction; candidates=[*sorted(Path("evals/r002").glob("*.json")),Path("/tmp/scopeproof-r002-result.json")]; audit=audit_r002_redaction(cache_root=Path(".scopeproof/research/r002"),candidate_paths=candidates); assert audit.passed; print(canonical_json_bytes(audit).decode("utf-8"))'
```

The dedicated local-only helper reads the real ignored cache, checks typed raw values against the three packaged inputs plus the candidate result, and emits only pass/fail counters and value hashes. It asserts that no problem statement, patch, standalone decoded test-name scalar, source/excerpt/context body, absolute cache path, timestamp, UUID, or HTTP metadata field is present; a short test-name substring inside an otherwise allowed repository path is not misclassified as a leak. This command is not part of CI and never saves raw values.

- [ ] **Step 6: Build, inspect, and clean-install from the exact scored commit**

Do this while the checkout is still clean at the label commit, before adding result or documentation files:

```bash
export R002_SCORED_COMMIT="$(tr -d '\n' < /tmp/scopeproof-r002-scored-commit.txt)"
test "$(git rev-parse HEAD)" = "$R002_SCORED_COMMIT"
test -z "$(git status --porcelain --untracked-files=all)"
R002_DIST="$(mktemp -d /tmp/scopeproof-r002-dist-XXXXXX)"
R002_VENV="$(mktemp -d /tmp/scopeproof-r002-venv-XXXXXX)"
R002_CACHE="$(pwd)/.scopeproof/research/r002"
uv build --out-dir "$R002_DIST"
R002_WHEEL="$(find "$R002_DIST" -maxdepth 1 -type f -name 'scopeproof-*.whl' -print -quit)"
test -n "$R002_WHEEL"
uv run python -m zipfile -l "$R002_WHEEL" \
  > /tmp/scopeproof-r002-wheel-files.txt
R002_WHEEL="$R002_WHEEL" uv run python -c 'import os,zipfile; expected={"evals/r002/source_manifest.json","evals/r002/criteria.json","evals/r002/candidate_labels.json"}; z=zipfile.ZipFile(os.environ["R002_WHEEL"]); members={name for name in z.namelist() if name.startswith("evals/r002/")}; files={name for name in members if not name.endswith("/")}; directories=members-files; assert files==expected; assert directories<={"evals/r002/"}'
! rg '\.scopeproof|criteria-proposal|annotation-review|annotation-universe' \
  /tmp/scopeproof-r002-wheel-files.txt
shasum -a 256 "$R002_WHEEL" > /tmp/scopeproof-r002-wheel.sha256
python3 -m venv "$R002_VENV"
"$R002_VENV/bin/python" -m pip install "$R002_WHEEL"
(cd /tmp && "$R002_VENV/bin/python" -m \
  scopeproof_core.evals.r002_swebench run \
  --cache-dir "$R002_CACHE" \
  --scopeproof-commit "$R002_SCORED_COMMIT" \
  > /tmp/scopeproof-r002-installed-result.json)
cmp /tmp/scopeproof-r002-result.json /tmp/scopeproof-r002-installed-result.json
```

Expected: the wheel was built while tracked and untracked Git state was clean at exactly `R002_SCORED_COMMIT`; it contains exactly the three redacted inputs and no local/raw artifacts; its SHA-256 is retained; it installs outside the checkout; and it emits byte-identical output. The official result's provenance comes from the source-checkout resolver, which rejects dirty or mismatched HEAD. The outside-checkout explicit SHA is accepted only for this package-equivalence check and is not described as independent provenance verification.

- [ ] **Step 7: Add the exact redacted result with `apply_patch`**

Copy the validated canonical one-line result bytes—not raw local bundles—from `/tmp/scopeproof-r002-result.json` into `docs/research/r002-swebench-verified/result.json` using `apply_patch`, preserving compact sorted-key JSON with no trailing newline. Then run:

```bash
cmp /tmp/scopeproof-r002-result.json \
  docs/research/r002-swebench-verified/result.json
uv run python -c 'import os; from pathlib import Path; from scopeproof_core.evals.r002_models import R002BenchmarkResult,canonical_json_bytes; p=Path("docs/research/r002-swebench-verified/result.json"); raw=p.read_bytes(); result=R002BenchmarkResult.model_validate_json(raw); assert raw==canonical_json_bytes(result); assert result.scopeproof_commit==os.environ["R002_SCORED_COMMIT"]'
```

Expected: raw bytes are identical to the first validated run, including the absence of a terminal newline. A valid but transcribed, reformatted, reordered, or otherwise changed result is rejected.

- [ ] **Step 8: Write the truthful engineering summary and align product status**

The summary must include: immutable dataset revision/file SHA; deterministic selection algorithm; 20-case/12-repository scope; criteria and label confirmation hashes; no target-code execution; exact executed/failed/skipped counts; every metric with numerator/denominator/state; zero integrity/separation/Ready/rerun errors; gate distribution; fixed limitations; and a link to the redacted result. Use these exact claims:

```text
R-002 broadens static engineering coverage across 20 historical public PRs. It measures
owner-confirmed research-label candidate matching and immutable-reference integrity. It does not
measure customer precision, real False Ready rate, correctness, runtime behavior, or acceptance.
No target-repository code was executed.
```

Update README/CHANGELOG with one short engineering-research link. Update ROADMAP without changing its stage gate:

```text
Stage 1 remains waiting_for_inbound_public_alpha_submission. R-002 is engineering evidence only;
its 20 cases, 12 repositories, outcomes, and timing contribute zero genuine Alpha reviews,
participants, repositories, or reuse signals. Stages 2–4 remain gated.
```

Do not add a release, version bump, tag, external post, issue, comment, email, DM, or monitoring task.

- [ ] **Step 9: Run focused R-002 and repository verification**

Run:

```bash
uv run pytest -q tests/evals/test_r002_models.py tests/evals/test_r002_source.py \
  tests/evals/test_r002_diff.py tests/evals/test_r002_verify.py \
  tests/evals/test_r002_cache.py tests/evals/test_r002_prepare.py \
  tests/evals/test_r002_annotation.py tests/evals/test_r002_runner.py \
  tests/evals/test_r002_cli.py tests/test_repository_contracts.py
uv run ruff check .
uv lock --check
git diff --check
```

Expected: all tests and checks pass with zero R-002 skips or live network.

- [ ] **Step 10: Run the full regression and existing deterministic benchmarks**

Run:

```bash
uv run pytest --cov=scopeproof_core --cov=apps \
  --cov-report=term-missing:skip-covered --cov-fail-under=95 -q
uv run scopeproof benchmark > /tmp/scopeproof-constructed-result.json
uv run scopeproof comparison-benchmark > /tmp/scopeproof-comparison-result.json
uv run python -c 'import json; a=json.load(open("/tmp/scopeproof-constructed-result.json")); b=json.load(open("/tmp/scopeproof-comparison-result.json")); assert a["executed_case_count"]==12 and not a["mismatches"] and not a["unexecuted_declared_categories"]; assert b["executed_case_count"]==2 and not b["mismatches"] and b["actual_counts"]=={"unchanged":1,"relocated":1,"modified":1,"added":3,"removed":3}'
```

Expected: complete suite passes at or above 95% coverage; the existing constructed benchmark and comparison outputs remain exact.

- [ ] **Step 11: Audit branch scope and commit the verified research result**

Run:

```bash
git status --short
git diff --name-only origin/main...HEAD
R002_RG_STATUS=0
rg -n 'customer validation|genuine Alpha|proves correctness|runtime verified' \
  evals/r002 docs/research/r002-swebench-verified README.md ROADMAP.md CHANGELOG.md \
  || R002_RG_STATUS=$?
test "$R002_RG_STATUS" -le 1
git check-ignore -v .scopeproof/research/r002/cache-index.json
uv run python -c 'from pathlib import Path; from scopeproof_core.evals.r002_models import canonical_json_bytes; from scopeproof_core.evals.r002_runner import audit_r002_redaction; candidates=[*sorted(Path("evals/r002").glob("*.json")),*sorted(Path("docs/research/r002-swebench-verified").glob("*")),Path("README.md"),Path("ROADMAP.md"),Path("CHANGELOG.md"),Path("docs/development-environment.md")]; audit=audit_r002_redaction(cache_root=Path(".scopeproof/research/r002"),candidate_paths=candidates); assert audit.passed; print(canonical_json_bytes(audit).decode("utf-8"))'
```

Review every wording hit in context; allowed negative boundary statements remain, positive claims are removed. Confirm no unrelated main-worktree file, `.coverage 2`, cache body, credential, release artifact, or remote state changed. Then commit:

```bash
git add docs/research/r002-swebench-verified/result.json \
  docs/research/r002-swebench-verified/summary.md README.md ROADMAP.md CHANGELOG.md \
  docs/development-environment.md tests/test_repository_contracts.py
git commit -m "docs: record R-002 engineering benchmark"
git status --short --branch
```

Expected: the isolated branch is clean and ahead of `origin/main`; nothing is pushed, no PR/release exists, Stage 1 remains waiting, and Stages 2–4 remain gated.

## Execution checkpoints

The implementation can proceed continuously through Tasks 1–10 Step 7 and then present Task 10 Step 8. It must pause at exactly two evidence-integrity checkpoints:

1. **Owner Gate 1:** confirm every complete normalized criterion object before full-row decoding, patch/test-patch inspection, GitHub preparation, or evidence analysis. Before this gate, only the five projected criteria-source columns may be read and only problem statements may persist.
2. **Owner Gate 2:** confirm the complete independent label batch before the first scored ScopeProof run.

These are product-safety approvals, not technical blockers. While waiting, an executor may run existing tests, lint, package inspection, and documentation consistency checks, but may not cross the corresponding evidence boundary. No other external input, participant, paid service, outreach, fork, release, or billing step is required for R-002.
