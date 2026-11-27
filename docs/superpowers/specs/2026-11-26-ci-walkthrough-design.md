# Offline CI handoff walkthrough

## Goal and execution prompt

Make ScopeProof's existing two-build CI handoff understandable before installation.
An evaluator opens one offline walkthrough, sees what changed from Build A to
Build B and the targeted rerun, follows the exact-build snapshots and manifests,
and understands what still requires reviewer action. Reuse the existing simulator,
validated saved reviews, CI projection, and installed exporter. Preserve input bytes,
acceptance decisions, and deterministic gates. Verify provenance, offline reading,
desktop/mobile layout, and the complete generated example. Finish this milestone;
do not imply customer validation or create another feature queue.

The user requested review, a next-goal prompt, and its execution in this session.
Implementation choices below are the agent's choices within that authorization.

## Review and approach

PR #304 implements CLI CI snapshots and shared follow-up summaries. The tracked
no-install report is the frozen v0.2.6 example; it cannot explain the newer CI
lifecycle. The private candidate was found in the separate ScopeProof Evaluations
folder. It already contains installed-package reports and verification evidence.
Reuse its exact report and input bytes; do not rebuild that completed candidate.
The repository lacks that evaluation path and its permanent regression contract.

Chosen approach: a reproducible presentation packager for the existing candidate's
exact reports and validated inputs. Extending the product UI
would add application scope without resolving access before installation. Replacing
the v0.2.6 example would destroy its historical producer boundary. Keep it intact.

## Deliverable

- A builder consumes frozen copies of the existing candidate's three reports,
  original producer record, manifests, raw fixture results and two saved reviews.
  It executes no target code and rebuilds no package or CI candidate.
- Strict Pydantic models validate the exported walkthrough/provenance. Record the
  original version, source commit, recorded wheel digest, presentation recipe digest,
  and exact input/output artifact digests. Producer assertions are not signatures.
- Three unmodified exporter snapshots show A passed/passed/passed, B failed/skipped/
  passed, and targeted B failed/failed/passed at the same B SHA.
- An offline index explains the change, links each exact snapshot and supplied
  manifest, shows recorded review status separately, and states next reviewer
  actions without accepting or upgrading evidence. Every page has an upfront
  constructed-example disclosure; preserve raw snapshot bytes by adding that
  disclosure only to the presentation copy.
- A deterministic ZIP contains the index, snapshots, manifests, saved input records,
  and validated provenance. No scripts, remote resources, or automatic network calls.
- Repackaging identical inputs produces identical bytes. Reject a mismatched original
  producer, changed reports or inputs, pending reviews, and existing output paths.
- Link the new example from current evaluation docs while retaining the public
  v0.2.8 / unpublished 0.2.9.dev0 distinction.

## Boundaries and finish line

No gate/evidence-rule change, record migration, retrieval retuning, dependency,
connector, authentication, private-repository support, release, Pages deployment,
outreach, or independent-use claim. Keep frozen R-002 and v0.2.6 assets unchanged.
Use source tests for failure boundaries, verify the original wheel/source binding, and
offline Chromium checks at desktop and phone widths. Review the final diff
independently, address material findings, and share a reviewable GitHub branch/PR.
