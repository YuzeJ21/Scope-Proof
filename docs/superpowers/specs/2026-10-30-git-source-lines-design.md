# Git source line coordinates

## Defect and chosen repair

Automatic changed-patch and unchanged-file retrieval use Python `splitlines()`, which accepts
CR, VT, FF, FS/GS/RS, NEL and Unicode LS/PS as separators. Git source coordinates follow LF.
This can truncate excerpts, shift later source permalinks or reinterpret embedded diff markers.

Use a tiny pure `split_git_source_lines(text: str, *, strip_crlf: bool = True) -> list[str]` helper in
`scopeproof_core/source_lines.py` at only those two production coordinate boundaries. Each LF
terminates a record; remove one CR only when immediately before that LF, preserving existing
CRLF presentation. Preserve every other character, including lone/final CR. Drop only the final
empty split sentinel. Empty content has zero records; internal blank records and an unterminated
final record remain. No stripping, broad Unicode splitting or global newline replacement.

Patch parsing requests raw CR retention until it inspects the following Git no-final-newline
marker. Git adds a protocol LF even after an unterminated source line; a CR before that LF is
real content when the marker follows. Ordinary CRLF records retain existing normalization.

Two inline fixes would duplicate subtle CRLF/EOF handling. Globally replacing every splitlines
would alter requirement parsing and frozen research normalization. The shared narrow helper is
the implementer's choice under the owner's delegated routine design authority.

## Integration and invariants

`github.client._parse_patch` consumes complete LF records before reading hunk or +/-/context
prefixes. `retrieval.engine._candidate_file` numbers the same complete records from one. Existing
matching scores, candidate limits, source typing, findings/gate logic and reviewer decisions
remain unchanged. Correct upstream records also correct existing bounded context construction.

M3 source-selection guards remain conservative and unchanged. Do not relax its rejected-source
policy as part of this defect repair. Do not alter schemas, record version 6, ruleset 2.0.0,
dependencies, criteria confirmation, export sanitization or historical evidence. New analyses
capture their current core source identity; saved old coordinates/source identities remain as
recorded and are not silently repaired during load/export.

## Frozen evidence

Preserve all tracked `evals/r002` and `docs/research/r002-swebench-verified` bytes, their labels,
metrics and recorded score. Do not modify ignored R-002 caches/results or rerun/rescore that
frozen study. Leave `r002_diff`, `r002_verify` normalization and runner redaction splitting alone.
Record new constructed separator cases in separate regression tests/audit evidence. Existing
deterministic acceptance/comparison benchmarks run against their unchanged inputs/expectations.

## Verification

Observe RED before correction for changed and unchanged sources, all nine uncommon separators,
embedded fake hunk/+/- prefixes, removed-to-added promotion, later true LF line/permalink and
whole-record context. Include ordinary LF/CRLF, internal blanks, empty input and final newline
boundaries. Independent tests compare raw bytes from a disposable Git commit/diff without
executing source or hooks. Historical saved/exported coordinates remain unchanged.

Run targeted tests, full original 95% coverage, lint/lock, deterministic benchmarks, installed
wheel/browser and available Python/Windows checks. Independent review, supported-finding fixes,
exact-head checked merge and resulting-main verification are required. No human testing,
qualifying review, publication/deployment/outreach, target execution or Stage 3 claim.
