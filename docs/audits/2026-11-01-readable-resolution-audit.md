# Readable decision-audit handoff — 2026-11-01

Baseline main after PR #241: `69c8a1cc35991e20b7f5ca971a23cb10bb668c2c`. Live GitHub main
CI, CodeQL and base advance were green, with no open PR and clean local source. Independent
read-only gap assessments identified persisted JUnit withdrawal and incomplete readable audit
handoff. The selected bounded outcome serves a report recipient: determine applicable and earlier
decisions without opening the application or interpreting JSON. JUnit withdrawal remains a separate
lifecycle/migration decision; generic mapping visibility was already implemented.

## Implemented contract

Existing Markdown and HTML reports now retain the complete recorded resolution events when
given a validated full saved state. A shared private field projection supplies event ID, status,
revision, target, recorded outcome, asserted reviewer, timestamp as recorded, note, evidence URL,
claimed level and runtime reference. Existing deterministic classification preserves append order
and distinguishes Current, Superseded and Prior revision; clocks do not establish authority.

Review-level flags render `final_acceptance=true/false`, without inferring revocation, prior
acceptance or a snapshot/event association. Runtime IDs and E3/E4 claims remain recorded context;
legacy unlinked claims retain the existing warning. Offset timestamps retain their offset, and
naive legacy times disclose that their timezone was not recorded. Absent and explicitly empty
optional values remain distinct.

Full state with no events has an explicit empty-history message. Analysis-only and retained-history
reports disclose unavailable complete history even if they retain latest resolution snapshots.
They do not borrow a parent record's events or attach current/historical heads, criterion text or
source provenance to old events by ID. Recorded actors are not authenticated identities.

Markdown uses the existing escaped-text policy for event values; HTML escapes every value into
inert text. The new history creates no link directives, artifact fetch or target-code execution.
Existing Pydantic and deterministic validation runs before rendering; forged state is rejected.
No public exporter signature, JSON/CSV contract, saved record v7, gate, decision, runtime evidence
or frozen research changes. The core remains independent of Streamlit and GitHub UI code.

## Automatic evidence and limits

Local baseline reporting:158 passed. Root missing-feature RED:10 failures plus one state-preservation
pass; independent safety RED:17 failures plus four validation-preservation passes. New report and
safety cases cover metadata, append-order authority, historical unavailability, empty optional
fields, hostile text/URLs, time uncertainty, legacy runtime links, forged-state rejection and
unchanged saved bytes/machine reports. Thirty-two new cases and adjacent reporting tests pass.
Initial presentation-decoder and legacy-fixture expectations were corrected without weakening
production validation or changing gate outcomes; initial failures remain in the evidence packet.

Independent whole-branch review at `7f3cfcee6a026edc728e0903a86770413892511a` found one supported
reporting defect: schema-valid mixed legacy events could display an extra decision instead of
their applicable review-level false flag. Extra manual fields could also trigger a criterion-only
warning on that review-level target. Ten failing public-export regressions cover both mixed
directions and manual-ID variants. The fix selects semantics by target, retains extra recorded
fields as explicitly unapplied context, and limits the legacy manual warning to criterion targets.
The ten cases pass without changing schema acceptance, stored data, machine reports or gates.
The installed CLI handoff also checks a saved mixed legacy record. Initial 32-case evidence and
review head remain distinct from this fix pass; full checks are rerun on the final source.

One additional installed CLI case copies only the constructed product-import fixture to a
temporary directory, uses the installed interpreter outside the checkout with explicit storage,
exports both readable formats, checks recorded distinctions and verifies unchanged bytes.
Historical CLI output explicitly reports unavailable history. Its missing-feature regression was
reproduced against the previous version-bound wheel, without altering that wheel or its prior
results. The existing saved-comparison browser journey downloads enriched Markdown and checks
recorded Current/Prior revision metadata against validated downloaded JSON, preserving its
no-record-writes contract. Superseded events are covered by report regressions. Browser collection
remains seventeen checks, including three installed journeys; no server generation is added.

Windows adds the bounded report regressions. Full-suite 95% unrounded coverage, lint/lock,
deterministic benchmarks, fresh package/CLI/browser, independent review and exact-head/resulting-main
results are recorded in the external version-bound packet:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-01-readable-resolution-audit`.
This source document is not a moving main ledger. All seven frozen R-002 hashes remain bound to
the baseline; no historical expectation or score is rewritten.

The initial Windows installed audit test exposed a transport mismatch: the isolated child used
the platform's default piped output encoding while the test decoded UTF-8. The test now explicitly
requests Python UTF-8 mode and verifies a constructed Unicode actor without replacing or ignoring
undecodable data. This scopes installed compatibility to the explicit test environment; it does
not assert a new encoding policy for every Windows shell or redirection. Product code is unchanged
by this test-harness repair; native Windows CI is required again on its final commit.

All actors are constructed automation, not personal testing, qualifying reviews, customer
validation, genuine independent use or accessibility conformance. Source remains unreleased
0.2.5; public v0.2.4 and historical candidate archives are unchanged. Stage 1 remains closed at
zero, Stage 2 owner-led, Stage 3 dormant. No release, deployment, participant contact or public
post is authorized or performed by this slice.
