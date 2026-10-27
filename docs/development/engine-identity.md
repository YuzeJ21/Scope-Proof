# Policy and analysis source identity

ScopeProof records three different identifiers. None is a signature or a correctness guarantee.

| Identifier | Meaning | Limits |
| --- | --- | --- |
| `tool_version` | Package version declared by the analysis producer | Multiple unreleased builds can share `0.2.4.dev0`. |
| `ruleset_version` | Declared evidence/gate policy generation | Current `2.0.0` names the already-merged changed-file scope policy. It does not change a gate predicate. Historical `1.0.0` covered more than one behavior and cannot identify an exact historical engine. |
| `analysis_source_identity` | Source fingerprint explicitly observed when a new analysis was created | Covers only installed core Python source; excludes UI, dependencies, Python/platform, configuration, target repository, Git status and runtime behavior. |

The new analysis field is a strict, frozen Pydantic object containing `scheme` and `sha256`.
Its scheme is `core-python-source-v1`. Its digest must be exactly 64 lowercase hexadecimal
characters. Unknown fields and malformed values are rejected. It is informational provenance,
not a new gate input or permission to accept any criterion or file.

## Exact source algorithm

1. Read only `.py` files below the installed `scopeproof_core` directory. Reject missing/empty
   source trees and symlinks; unreadable source fails explicitly. Never execute those files or
   target repository code to calculate identity.
2. Replace each file's CRLF byte pairs with LF. Other bytes remain unchanged.
3. For each source, calculate SHA-256 of the normalized bytes and pair the digest with the
   relative POSIX path. Sort by relative path.
4. Serialize the array of `[relative_path, lowercase_file_digest]` pairs using
   `json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")`.
5. Calculate SHA-256 of those canonical bytes. Store it with the scheme.

This excludes timestamps, absolute installation paths and bytecode. A wheel installed from the
same core source should have the same identity as the checkout. The digest includes core
reporting/CLI/research code as well as gate and retrieval code; a changed digest does not prove
a changed policy. A matching digest does not identify dependency or configuration behavior.
Source-less packages are unsupported for this capture. Do not modify installed source during a
running process: disk bytes are an observation, not proof of which bytecode was already imported.

## Creation, reopening and reanalysis

New CLI, workbench and constructed-demo analyses explicitly capture the current core source.
Parsing `Review` has no capture default: missing identity remains `None`, rendered as
`Not captured` in human-readable exports. Opening, saving, validating, recording a decision or
migrating an old record must not replace unknown identity with today's build. Historical tool
and ruleset strings remain recorded values. The frozen R-002 inputs/results are unchanged and
are not retroactively assigned this identity.

A genuinely new analysis after explicit criteria reconfirmation adopts its producer's source,
tool and policy metadata in the active review. Other review identity checks remain exact.
Archived analysis bundles keep their prior metadata, including unknown identity.

## Gate validation is a separate operation

The installed evaluator checks stored gate output against current deterministic rules.
Older-record migration can recompute gates under current policy, as documented by the existing
record migrations. That is current reassessment, not a replay of the historical producer.
It does not rewrite analysis-source identity or turn that field into attribution for every later
gate calculation or reviewer decision. The application does not preserve executable versions of
every historical engine. Keep historical exports if an original serialized outcome is needed.

Before future gate/evidence semantics change, declare a new policy version, document the migration
and comparison behavior, and add regression coverage. Do not silently reuse a policy identifier
to imply identical behavior. A future full build attestation or historical replay system would
require a separate design; neither is implemented here.
