# Explicit multi-criterion JUnit draft — 2026-11-01

Baseline main `986229352bbeceea7490cf430f3a2b389d11af2b` after PR240. Live GitHub confirmed green
post-merge CI/CodeQL/base advance, no open PRs, and clean local source. Independent gap reviews
compared richer resolution-audit exports, persisted JUnit correction and pre-import mapping.
The selected direct workflow gap: the workbench mapped every scope to the inspected criterion,
but the immutable artifact digest could not be imported again for another criterion.

## Bounded outcome

The existing parser/builder already support multiple explicit targets and reject assigning a
test case to multiple criteria. A new typed session draft binds at most5,000 canonical selector
pairs to the full validated review fingerprint and computed artifact digest. Additions validate
the complete candidate through the existing builder and are transactional; removal/clear affect
only the draft. No raw XML or new saved object/event/schema is introduced.

The workbench independently chooses a mapping target, stages scopes, previews resolved case IDs,
and removes criterion groups or clears the draft before one existing import append. Only staged
choices can be saved; unsubmitted target/scopes block Save. Changed/removed/invalid uploads,
changed full review and existing global resets clear choices. The existing main criterion-change
reset remains; use the mapping target inside the import form for multiple criteria. Pending-input
guards include the typed draft even when selectors have been cleared after staging.

Saved imports remain immutable. Duplicate artifacts, parser limits, no-overlap policy, source
and criteria confirmation, record v7, gates, automatic findings, decisions and runtime truth are
unchanged. Persisted correction/withdrawal of an existing import is intentionally a separate
lifecycle/migration/reporting decision. This slice neither runs target code nor retrieves artifacts.

## Automated evidence

Root core RED6 and independent safety RED19 missing-feature cases preceded implementation.
New core/safety plus existing importer regressions:73passed. Component RED5 preceded the renderer;
the expanded six-case AppTest file also exercises the actual workbench saving both mappings once,
validated export and unchanged gate/decision/runtime truth. Three original single-target save
flows add explicit target/stage actions while keeping their assertions. An initial fixture used a
nonexistent decision enum, and provenance mutation attempted a frozen field; fixtures were
corrected without weakening production validation or rewriting historical records.

The existing installed-wheel primary journey is extended for two suites/two criteria, explicit
staging/reset/save guards, restart/reopen/export, sanitized output and unchanged remaining bundle
truth. No journey/server generation is added; collection remains17 checks (3 installed journeys,
8 selection and6 helper/capture checks). The1MiB boundary and discarded-output assertions remain.
Windows verification includes the31 new core/safety/AppTest cases.

Full-suite95% unrounded coverage, lint/lock, deterministic benchmarks, installed package/browser,
independent whole-branch review and exact-head/resulting-main integration outcomes are recorded
in the external version-bound packet:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-01-junit-multi-criterion-draft`.
The packet retains commands, actual outcomes and failures; this source document is not a moving
main ledger. Seven frozen R-002 inputs/results remain unchanged; new cases are separate fixtures.

All actors are constructed automation, not personal testing, qualifying reviews, genuine
independent use, authenticated importers or accessibility conformance. Source remains unreleased
0.2.5; publicv0.2.4 unchanged. Stage1 closed at zero, Stage2 owner-led, Stage3 dormant. No release,
deployment, participant contact or outreach is authorized or performed by this slice.
