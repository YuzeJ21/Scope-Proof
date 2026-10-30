# Automatic candidate source coordinates — 2026-10-30

## Baseline and defect

The starting main was `7cffb6c50d15c4b83b92c76682a3aa32c6e09a67`, with clean local checkouts,
green hosted CI and no open PR. The owner requested an automated correction, independent review
and checked merge without personal testing or qualifying reviews. Source remains unreleased
0.2.5; public download remains v0.2.4.

Changed-patch parsing and unchanged-file enumeration used Python's broad `splitlines()`. Git
source coordinates follow LF. Embedded CR, VT, FF, FS/GS/RS, NEL or Unicode LS/PS could truncate
a source record or shift subsequent candidate links. Embedded hunk/+/- text could be treated as
diff protocol; a deleted record containing a separator followed by `+target_identifier()` could
produce a nonexistent current-head candidate.

## Bounded correction

A pure shared LF splitter preserves complete records, internal blanks and final unterminated
content. It drops only the terminal empty sentinel and explicitly handles CRLF. Changed-patch
parsing retains raw CR until checking Git's following no-final-newline marker: a protocol LF
must not erase a real final source CR. GitHub can omit the final protocol LF for a normal
CRLF-terminated source; its absence does not imply an unterminated source line. The following
marker governs CR preservation, and ordinary CRLF presentation remains unchanged.

Only production source coordinate boundaries use the helper. Matching terms, thresholds,
candidate limit, source typing, schema/version 6, gate policy/ruleset 2.0.0, reviewer decisions
and dependencies are unchanged. Correct records supply the existing bounded context renderer.
M3 retains its conservative ambiguity guard; this fix does not expand selectable sources.

New analyses record their new core source identity. Loading/exporting old saved evidence neither
reparses nor renumbers it, including archived analyses and producer metadata. Historical locations
are not retroactively verified; corrected locations come from a fresh analysis. The historical
producer identity remains available to distinguish those results.

## Frozen research and constructed regressions

All seven tracked files under `evals/r002` and `docs/research/r002-swebench-verified` retain their
baseline bytes. Existing ignored R-002 cache/results are not rewritten. Research-specific
normalization and redaction logic remain untouched. Frozen inputs, labels, metrics and recorded
scores are not retuned or rescored; no current-engine R-002 score is claimed.

New cases are separate tests: all nine separators, changed/unchanged routes, fake diff markers,
removed-to-added promotion, real LF line-two links, complete neighbor context and E1/E2 typing.
Thirty-six checks compare inert bytes from a disposable Git repository's immutable blobs/diffs.
Git configuration/hooks/filter execution are isolated; no source or tests from that repository
are executed. A separate real-Git EOF-CR case failed while its ordinary CRLF control passed,
then drove marker-aware handling. Helper edge cases cover empty/internal-blank/trailing-newline
boundaries. Saved/exported historical coordinate tests assert no silent rewriting.

The pre-fix independent matrix had 108 assertion failures. The first LF correction passed those
108 cases. Subsequent EOF-CR and complete verification results belong to their exact PR head;
the PR and resulting-main CI are the integration authority. Failed and passing evidence are
retained separately in the private version-bound audit packet.

Independent review identified one minor CRLF presentation inconsistency in the initial fix:
the final API patch record could retain a CR when GitHub omitted its protocol LF. An offline
API-shaped regression reproduced the extra character before the marker-based correction;
changed and unchanged candidates must now have identical normalized context. The real-Git EOF-CR
regression continues to require preservation of actual final source content. No comparison
classification or gate impact is claimed for this minor finding.

## Verification boundary

Run full original coverage targets with the unrounded 95% floor, lint/lock, unchanged deterministic
acceptance/comparison benchmarks, clean installed wheel/browser checks and Python/Windows lanes.
The existing seventeen browser checks remain three installed journeys, eight constructed
selection checks and six helper/capture checks. Add targeted coordinate tests to the existing
Windows lane without replacing its existing checks. Independent review and an expected-head
merge are followed by resulting-main checks.

No source-owner confirmation, real participant use, qualifying-review credit, accessibility
conformance, runtime correctness, release, deployment, outreach or Stage 3 advancement follows.
Implementation references remain candidates, and test definitions remain intent rather than
execution evidence.
