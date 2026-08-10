# Post-v0.2.3 Development Identity Design

## Context

ScopeProof v0.2.3 is published from the immutable release commit
`448c42758ea139bf9203cbf1bb04b02b02ae412c`. The current development tree contains later merged
engineering work for CLI lifecycle parity, strict saved-record validation, installed-wheel browser
coverage, Python 3.13, bounded keyboard/focus and zoom checks, and verified-public provenance. The
single checked-in version source still reports `0.2.3`, and the Unreleased changelog section is
empty. A wheel built from current `main` can therefore have different bytes and behavior while
presenting the same final version as the published release.

This work restores package and documentation identity only. It does not alter evidence evaluation,
gate behavior, persistence, exports, GitHub ingestion, or the published v0.2.3 tag and assets.

## Decision

Advance the single development version source to `0.2.4.dev0`. That is the next PEP 440
development line after the published `0.2.3` release and matches ScopeProof's established
post-release convention.

Add a repository contract that binds every final version named in its published-release ledger to
the exact Git tree recorded for that release. When the working tree reports a published final
version, the committed tree must match the corresponding release tag tree. A later committed tree
that still reports `0.2.3` therefore fails closed; a development version such as `0.2.4.dev0` is not
mistaken for a published final release.

Reconcile current-facing documentation so it distinguishes:

- the immutable, publicly installable v0.2.3 release;
- the current `0.2.4.dev0` source line and its post-release engineering evidence;
- historical audits bound to their named commits and versions; and
- unsupported real-environment and external-validation claims.

## Version and release contract

`scopeproof_core/version.py` remains the only package-version source. Hatch metadata, imported
module identity, both CLI version commands, and new review provenance continue to derive from it.

The repository contract keeps an explicit mapping from published final version `0.2.3` to tag
`v0.2.3`. It resolves the current committed tree and release-tag tree with Git and requires equality
only when the current source identifies as that published final version. The contract also requires
the expected release constants and the development version, making a silent reuse of the final
version fail in CI before packaging can be accepted.

The tag, GitHub Release, checksums, and historical candidate/audit artifacts remain unchanged. This
branch does not create or publish a `0.2.4` artifact.

## Documentation model

The authoritative active surfaces are updated together:

- `CHANGELOG.md` records all work merged after v0.2.3 under `Unreleased`.
- `README.md` names v0.2.3 as the public install and `0.2.4.dev0` as unreleased source.
- `ROADMAP.md` records completed post-release engineering separately from Stage 1 progress.
- `docs/development-environment.md` describes the development identity and verified Python 3.11,
  3.12, and 3.13 engineering lanes without implying desktop-platform support.
- The v0.2.3 status page and platform/package matrix retain historical release evidence while adding
  a dated post-release status boundary.
- The market comparison removes CLI lifecycle parity and keyboard/focus from current gaps, while
  preserving screen-reader, Windows desktop, Linux desktop, non-Chromium, and WCAG limitations.
- Superseded verification audits receive explicit historical-boundary notices where a reader could
  otherwise mistake their version or unsupported-environment statements for current truth. Their
  original measurements, hashes, and commit-specific conclusions are not rewritten.

All active surfaces retain the exact Stage 1 counts at zero and state that engineering evidence
earns no Stage 1 credit.

## Alternatives considered

- Keep `0.2.3`: rejected because post-release source and wheel bytes would remain ambiguous with the
  published final release.
- Use `0.2.3.post1`: rejected because no post-release distribution is being published and the tree
  is the next development line, not a corrective published artifact.
- Use `0.2.4`: rejected because that would present the branch as a final release before an owner
  release gate.
- Assert only the literal expected version in a test: insufficient by itself because the same
  ambiguity could recur after a future release. The release-tree binding makes the invariant
  reusable.
- Rewrite historical audits to current wording: rejected because that would destroy exact-head
  provenance. Additive supersession notes preserve both historical evidence and current clarity.

## Verification

Start with a focused repository-contract regression that fails while current source still reports
`0.2.3`, then change the version and make it pass. Add documentation contracts for the development
identity, Unreleased ledger, completed engineering evidence, unsupported environments, and unchanged
Stage 1 counts.

The final head must pass Ruff, the complete suite with at least 95 percent combined coverage,
repository contracts, both deterministic benchmarks, two reproducible wheel builds with identical
SHA-256, artifact-inventory inspection, clean installation and dependency validation, installed and
source version equality, both CLI versions, installed benchmarks, exact loopback health, the
installed-wheel Chromium regression, every currently supported Python/CI lane, diff and commit
audit, independent review, and all available GitHub checks.

These results are controlled engineering evidence only. They do not execute target-repository code,
prove correctness, establish accessibility conformance or desktop-platform support, or advance
Stage 1.

## Boundaries

No release, tag, package publication, merge, issue mutation, participant contact, outreach, R-002
retuning, R-003 generation, beta activation, private-repository support, paid API, or product-scope
expansion is authorized. The GitHub Action remains opt-in and informational. Reviewer and
source-owner identity remain asserted, not authenticated. Real screen-reader operation, Windows
desktop, Linux desktop, non-Chromium browsers, and WCAG conformance remain unsupported.
