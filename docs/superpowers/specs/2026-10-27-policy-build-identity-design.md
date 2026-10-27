# Policy and core-source identity

The owner authorized this bounded adjustment without personal testing or routine design input.
It records the core source used when an analysis is created. It does not establish runtime
correctness, authenticated authorship, or customer validation.

## Approach

Keep package version, declared policy version, and observed core-source identity distinct.
The current declared ruleset becomes `2.0.0`, identifying the already-merged changed-file scope
policy. This is a metadata correction; no gate predicate, threshold, or precedence changes.
Older `1.0.0` values remain untouched and cannot uniquely identify historical policy behavior.

Add an optional Pydantic `CoreSourceIdentity` to `Review.analysis_source_identity`.
It contains a fixed `core-python-source-v1` scheme and a strict lowercase SHA-256 digest.
The digest covers a canonical sorted manifest of relative paths and SHA-256 digests of all
`.py` files under the installed `scopeproof_core` package. Normalize CRLF to LF; exclude
bytecode, absolute paths, timestamps, UI code, dependencies, environment and Git metadata.
Read only ScopeProof-owned source, never target repository files. A missing/unreadable source
must fail explicitly rather than invent an identity.

Explicitly capture identity at new CLI, workbench and constructed-demo analysis entry points.
The field defaults to `None`, so validation and reopening cannot relabel historical records.
The historical R-002 runner and frozen inputs/results are unchanged. Saved objects and JSON
preserve typed identity; Markdown, CSV and HTML expose the scheme/digest or `Not captured`.

When an explicitly confirmed revised criteria set receives a new analysis, adopt that analysis's
tool version, declared policy and source identity into the active lifecycle review and bundle.
Compare all other review fields exactly as before; preserve the archived analysis identities.
Ordinary decisions, validation and migration must not update analysis identity.

Validation checks a stored result against the installed evaluator; older-record migration may
recompute gates. Neither action rewrites analysis identity. This field identifies the source
snapshot observed at analysis creation, not the producer of every later lifecycle transition.
There is no promise of historical engine replay. Source modified during a running process is
unsupported; the fingerprint is not an attestation of imported bytecode or dependency behavior.

## Alternatives

Documentation alone would leave new analyses without a source record. An embedded Git commit
would misidentify dirty builds and require special wheel-build injection. A complete execution
attestation and historical policy replay system exceeds this task. The additive source record
provides inspectable provenance without expanding trust or gate authority.

## Verification and limits

Test source/wheel identity equivalence, path/ordering/newline independence, source-change
sensitivity, strict schema rejection, new analysis capture, unknown historical records,
save/reopen/export preservation and unchanged deterministic gate behavior. Keep the full suite's
95% coverage floor. No licensing, target code execution, R-003, participant, release or beta work.
