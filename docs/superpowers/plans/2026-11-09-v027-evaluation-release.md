# Final v0.2.7 evaluation release

> Execute the owner-authorized release inline with independent engineering review. No owner testing or qualifying review is required.

**Goal:** Publish final v0.2.7 downloads containing the accumulated historical-report and saved-history validation corrections, with exact-source and exact-artifact evidence.

**Architecture:** Keep the existing package/release architecture and all product behavior. Finalize the checked-in version/guidance, review and merge only after exact-head CI, then rebuild from the verified merged main. Bind fresh final archives to that commit and keep the prior private development candidate immutable. Use a verified GitHub draft for uploaded bytes, publish under existing owner authorization, and verify anonymous public downloads separately.

**Alternatives:** Renaming development archives would misrepresent their version/core identity. Adding a feature or architecture rewrite lacks a selected new constraint. Publishing without fresh final builds and checks would not verify the requested release.

## Constraints

- Follow AGENTS.md; preserve Pydantic validation, explicit confirmation, exact-head rules, deterministic gates and reviewer decisions. No untrusted target code executes.
- Freeze R-002 inputs/results and actual released-writer corpus. Reuse copies, preserving producer/history and original bytes; no new corpus, rescore or implicit acceptance.
- Keep ruleset 2.0.0, saved format 9, dependencies and policy unchanged. Final version changes reader build identity, not historical producer identity.
- No Pages deployment, outreach, personal testing, qualifying reviews, customer validation, accessibility conformance or Stage 3 advancement.
- Release record is authoritative for publication and verification; repository guidance must remain truthful before and after publication.

## Sequence

1. Verify live clean main, tag/release absence and private candidate identities. Finalize version/changelog/guidance without changing the prior packet.
2. Run affected tests/lint/benchmarks, obtain independent whole-branch review, create PR and require exact-head full CI with the existing unrounded 95% floor and all Python/Windows/installed-browser lanes.
3. Merge reviewed head and verify resulting main separately. Rebuild final wheel/sdist from that exact main; require source-built wheel parity and source/core/artifact digests.
4. Verify fresh isolated final installs, existing installed CLI and eight browser cases, copied native v0.2.6 preservation/report checks and the existing PR #277 large constructed input. Independently review final artifact bindings. Reuse valid same-byte evidence only with explicit source/identity binding.
5. Create only the authorized v0.2.7 annotated tag/draft with three verified assets. Verify uploaded draft bytes, then publish. Download anonymously with curl configuration disabled, verify official/local SHA-256 identities, and freshly install both public archives with benchmarks and native-record preservation checks.
6. Record final source, assets, exact-head/main checks, command results, public verification and limits in the Release entry and strict private manifests. Confirm clean synchronized main, then stop.

Integration and publication evidence is recorded in the PR, GitHub Release and private release packet; this plan does not itself assert that any pending check or publication succeeded.
