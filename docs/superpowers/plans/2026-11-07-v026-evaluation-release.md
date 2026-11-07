# ScopeProof v0.2.6 Evaluation Release Plan

**Goal:** Finalize and publish the authorized downloadable evaluation release, then verify public downloads automatically.

**Baseline:** Main `5d229419851273db29c65773cf1338fb580c180a` and its CI are verified. Public v0.2.5 remains the previous verified download. The private dev0 candidate is historical and must not be renamed into final artifacts.

**Design:** Change only the source version, current release/install guidance, and release-identity contracts. GitHub Releases determines availability and completed public verification, so documentation is accurate before and after publication. Preserve explicit known-final guards for v0.2.3–v0.2.5. For current final v0.2.6, exact local tag presence activates the same tree, dirty-input and untracked-input checks; only an absent tag permits prepublication, and Git inspection failures fail closed. This contract requires complete Git metadata (CI fetch-depth 0); local absence is not proof of remote publication status. Rerun it after creating the exact final tag.

**Constraints:** Follow AGENTS.md; preserve gate/schema/dependency behavior and frozen R-002. No target-code execution, personal testing, qualifying reviews, deployment or outreach. Stage 3 remains dormant.

## Verification and execution

1. Finalize version 0.2.6 and phase-neutral guidance. Observe failing version/tag-guard cases before implementing their supported treatment. Run repository contracts, lint, lock and link checks; obtain independent review.
2. Merge only after exact-head CI passes. Verify resulting main. Build wheel, source archive and checksums from that exact clean merged commit; compare direct/source-built wheels and package/source identities.
3. Verify locked clean wheel/source installations, Python compatibility, installed CLI/browser journeys, actual public-v0.2.5 writer compatibility on copied constructed records, and deterministic benchmarks. Any earlier preview evidence applies to final artifacts only after exact byte equality is established.
4. Create the annotated v0.2.6 tag at the final source. Create a private release draft with exactly three assets. Locate the draft by explicit release ID, verify tag/source/notes and all uploaded bytes, and abort on any failed preflight. Do not treat a failed draft-by-tag lookup as success.
5. Publish only the verified draft. Anonymously fetch the release page, latest-release identity, wheel, source archive and checksum manifest. Check HTTP outcomes, bytes/digests, fresh installations, benchmarks and launcher/installed journeys. Record actual results in a strict Pydantic manifest and the GitHub release notes. Verify main remains clean and report limits.
