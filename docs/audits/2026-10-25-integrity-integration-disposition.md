# ScopeProof integration disposition — 2026-10-25

This is a source and hosted-check audit, not customer validation. The published v0.2.3 release is
at `448c42758ea139bf9203cbf1bb04b02b02ae412c`; `origin/main` was observed at
`f586d90b72a14fd19d5a0add01f3d05532a88955`. The separate `0.2.4.dev0` integrity draft is
not a release. Stage 1 remains `closed_not_pursued_by_owner`, with zero qualifying external cases.

## Open integration decisions

| Item | Exact reviewed head and evidence | Disposition |
| --- | --- | --- |
| [PR #200](https://github.com/YuzeJ21/Scope-Proof/pull/200), urllib3 | `a772e184989a1b710f1610f62f0101816d04aea1`; lockfile-only 2.7 to 2.8; [five CI jobs succeeded](https://github.com/YuzeJ21/Scope-Proof/actions/runs/38032902632). [Maintainer advisories](https://github.com/urllib3/urllib3/security/advisories) identify the fixed version. | Retain the narrow update for review. No direct ScopeProof urllib3/proxy/streaming path was found; exploitability here is unproven. Three unrelated workflows were skipped, so they are not passing checks. Recheck exact-head CI and combined lockfile after integration. |
| [PR #201](https://github.com/YuzeJ21/Scope-Proof/pull/201), GitPython | `58de9e4160b8d167cf06704cf743578d3a408f3b`; lockfile-only 3.1.59 to 3.2.1; [five CI jobs succeeded](https://github.com/YuzeJ21/Scope-Proof/actions/runs/40068370411). [Maintainer advisory GHSA-83vg-56qc-22m7](https://github.com/gitpython-developers/GitPython/security/advisories/GHSA-83vg-56qc-22m7) names the fixed version. | Retain the narrow update for review. The affected submodule-create path is not called directly by ScopeProof; GitPython is indirect through Streamlit. Raise `tests/test_repository_contracts.py`'s minimum GitPython version to 3.2.1 when the lock change is integrated. Recheck the combined lockfile because both PRs edit `uv.lock`; the three skipped workflows are not passing checks. |
| [PR #199](https://github.com/YuzeJ21/Scope-Proof/pull/199), JUnit adapter | The initial review found two P1/P2 defects at `fc2f17cf4434b6f7b11c73ec8d4a2e12a9dba3fb`: `<testcase name="t" status="failed"/>` was displayed as passed, and changed sanitized outcomes/warnings could be labelled unchanged. Follow-up review found namespace-qualified suite attributes and `success="false"` false-pass shapes. Repairs are at draft head `8f8fa9e22f6d41e246773cf688c77be8462d0c07`. The parser now rejects namespace-qualified attributes throughout the XML tree and unsupported outcome attributes; comparison hashes validated sanitized context and distinguishes context and mapping changes. Current-head focused importer/comparison/export tests: 92 passed. The earlier `37186b8` PR-branch non-UI suite passed 2,258 with 1 intentional skip; its temporary combined merge passed 2,275 with 1 intentional skip. A new uncommitted merge of `8f8fa9e` with the integrity draft passed 339 targeted tests. | Retain as a separate integration review. Exact-head hosted CI is pending; earlier broad local runs and the targeted combined rehearsal are not exact-head full-suite evidence. Imported XML remains externally supplied, non-gating context, not ScopeProof-executed tests or proof of runtime behavior at a SHA. |

These are review and merge decisions; no PR above was merged by this audit. A previously passing
hosted run does not prove compatibility with the new integrity draft or with another lockfile PR.

## Divergent archival work

The archival branch `codex/evidence-integrity-hotfix` was inspected commit by commit. It is not
safe to merge wholesale, and none of its material was deleted.

| Commit or file | Disposition | Reason |
| --- | --- | --- |
| `f99dc72` candidate-file SHA binding | Already represented | Current source binds candidate-file requests to an exact head. Its pull metadata and mutable-list order do not repair an A→B→A mixed-revision race; the integrity draft uses a SHA-addressed comparison for those lists. |
| `fa8d257` bundle SHA/permalink checks | Adapted narrowly | The integrity draft validates candidate head and live-public permalink relationships at the shared Pydantic `ReviewBundle` boundary. Historical/constructed links stay inert and readable under existing migration rules. |
| `b19fc33` bounded saved-record reads | Narrow follow-up | Main still has unbounded review/alpha JSON reads. The archived descriptor helper is not portable across the supported storage paths; design a cross-platform cap with explicit size and error behavior before adapting it. |
| `02c3c59` alpha outcome binding | Already represented | Current alpha service revalidates saved review identity and origin before one-time outcome capture. |
| `bdabbd4` participant rollup | Obsolete for current stage | Owner closed Stage 1 without qualifying external cases; constructed or historical work cannot revive it. |
| `8d54c23`, `c8aa360` changed-file inventory and uncited-scope acknowledgement | Unresolved product/gate design | A new Ready prerequisite needs a focused schema, migration, and deterministic gate design with regressions; it is outside this integrity repair. |
| `f96eafa` Action policy | Superseded | Current exact-head informational Check is neutral-only and does not claim a required gate. |
| Untracked `.worktrees/scopeproof-rereview-evidence-integrity/scopeproof_core/reviews/comparison 2.py` | Obsolete content, preserve file | It is byte-identical to ancestor `f5e361f`'s comparison implementation; current source has later semantic comparison and validation. The file remains untouched for the owner to reconcile in normal workspace cleanup. |

The present draft does not demonstrate customer adoption, accessibility conformance, demand,
retrieval accuracy beyond the existing constructed benchmarks, or hosted behavior until its own
exact-head checks complete.
