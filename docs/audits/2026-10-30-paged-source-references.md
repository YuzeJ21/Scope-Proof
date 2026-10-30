# File-scoped source reference paging — 2026-10-30

The owner selected this bounded follow-on after PR #228. Baseline main was
`af1423eab4a57f120d21fd4d172dcc9934df2c8a`; its CI, CodeQL and base-advance workflows passed.
Both local main and the reused managed worktree were clean and synchronized before this work.
This assessment applies to the unreleased `0.2.5` source change, not published v0.2.4 or the
private candidate archives prepared at `4f12ae02dee277705d17ac6ab94f0a74f99be346`.

## Reproduced gap and treatment

The legacy selector built its file list from the global first 1,000 eligible source lines.
A large earlier file could hide every later file, and the save transition rejected any line
outside that prefix. New constructed core and AppTest regressions reproduced the missing APIs
and absent controls before implementation (24 and 3 expected failures respectively).

One shared source-policy iterator now supplies a file catalog, file-scoped 100-line pages,
the compatible legacy prefix API and source revalidation on save. Catalogs retain counts and
identity, not every excerpt. A page retains at most 100 eligible raw lines, preserving their
physical Git coordinates. Invalid, unavailable and out-of-range requests fail closed. File/page
switches clear the line selection; page defaults never implicitly choose a line. Existing
draft/export/conflict controls remain active. Session paging requires no stored-schema migration.

The core is independent of Streamlit. The workbench lists all eligible already-ingested files;
it does not fetch additional source or execute source code. Changed, renamed, generated, unrelated
and unchanged candidate locations use the existing static evidence rules. Deleted, skipped,
truncated, ambiguous, duplicate and noncanonical sources retain their existing exclusions.
The M3 separator guard remains conservative. Append still validates the full review fingerprint,
confirmed criterion, head/inventory, exact line value, reviewer and rationale.

## Verification and limits

Focused verification of the core and workbench selection paths passed 92 tests, including the
new file/page regressions. The installed-wheel journey uses a visibly constructed large-source
fixture to select beyond the legacy prefix, then save, restart, reopen and export. Its fixture
injection is test harness setup, not genuine independent use or a production source adapter.
Full-suite, browser, lint, benchmark, independent review and exact-head/resulting-main evidence
are recorded with the integration result. The private audit folder is
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-10-30-paged-source-references`.

Frozen R-002 input and result files retain their original bytes. Automatic findings, confidence,
file scope, decisions, gate, runtime evidence and acceptance remain unchanged by selected
references. Each raw line remains limited to 4,096 UTF-8 bytes and each analysis to 32 references.
The legacy prefix API intentionally retains its 1,000-line result bound for callers.

This completes the selected source-navigation outcome. Usefulness, independent repeat use and
demand remain unverified. The owner declines personal testing and qualifying reviews; automation
does not replace genuine evidence. Stage 3 remains dormant until genuine independent use and
separate authorization. No release, deployment, participant contact or public post is included.
