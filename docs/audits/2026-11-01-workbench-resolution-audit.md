# Workbench decision-audit consistency — 2026-11-01

Baseline main: `cdd243815e1cfaac0f2ec720dbbc64b0f82a9f8d` (PR #242). GitHub main CI,
CodeQL and base advance were green, no open PRs existed, and both local checkouts were clean.
The owner explicitly selected the known workbench discrepancy, delegating implementation,
automated testing, independent agent review and merge without personal testing/qualifying reviews.

## Reproduced gap and bounded change

The previous workbench chose an event's extra `decision` before inspecting its target. A supported
loaded review-level `final_acceptance=false` event with an accepted/manual extra could therefore
display that extra as its outcome. Review-level manual extras could also show a criterion-only
legacy re-record warning. The workbench additionally labelled offset/naive timestamps as UTC and
omitted audit IDs, URLs and explicit empty/missing metadata already present in readable reports.

The existing report projection is now a plain core-reviews function shared by both readable
exporters and the workbench. Its target-first outcome, additional-field labels, metadata and
missing/empty strings are unchanged. The workbench retains its combined status/revision display,
shows IDs/targets/runtime references as wrapped inert code and other values as plain text, and
retains the applicable criterion-only legacy warning. Review-level manual extras have no warning
requiring a new criterion observation. Nothing invents authenticated actors, execution, historical
heads, criteria-source provenance or a flag-to-snapshot association.

The shared projection preserves offsets using ISO formatting and explicitly identifies a legacy
timestamp whose timezone was not recorded. Current/Superseded/Prior revision classification still
comes from the existing lifecycle, in append order. No schema, storage version, migration, gate,
acceptance, runtime evidence, dependency or public exporter signature changes. The core imports
neither Streamlit nor the GitHub/UI layers. Frozen R-002 inputs and results remain untouched.

## Automatic verification and limits

Thirteen focused baseline cases passed. Five mixed-shape AppTest regressions reproduced the old
display before source edits, including review-level accepted/manual extras and criterion true/false
extras. One initial fixture incorrectly attempted a new final-acceptance transition; it was
corrected to model the supported loaded legacy shape, without weakening validation. Twelve new
AppTest cases cover those outcomes, missing/empty values, hostile metadata, offset/naive times,
empty histories and append-order status, while preserving state and machine exports.

Two fixed constructed saved states retain byte-identical Markdown, HTML, JSON and CSV across the
projection extraction. The initial text-mode CSV comparison normalized CRLF; the final comparison
checks exact encoded bytes. A new order-test selector initially also matched the criterion-detail
caption; it now selects only event-status values. Initial failures and an interrupted covered run
remain separate in the external packet rather than being counted as passing evidence.

The installed-wheel journey reopens one constructed mixed legacy review, pairs fields within each
event, downloads real Markdown/JSON, verifies inert hostile fields and no external requests, checks
desktop/390px/CSS 200% layouts, then restarts and confirms unchanged record bytes. These captures
are automated constructed engineering evidence, not accessibility conformance or genuine use.
Current browser collection is eighteen checks: four installed Chromium journeys, eight constructed
selection checks and six helper/capture checks. Windows adds the bounded twelve new AppTest cases;
existing report regressions continue to exercise the shared projection on that platform.

Full-suite coverage at the existing unrounded 95% threshold, lint/lock, deterministic benchmarks,
clean-installed CLI/browser checks, independent review and exact-head/resulting-main identities
are recorded separately in the version-bound packet:
`/Users/yjian070/Documents/ScopeProof-product-audits/2026-11-01-workbench-resolution-audit`.
This document describes the bounded contract and is not a moving-head CI ledger.

Source remains unreleased 0.2.5; public v0.2.4 and historical candidate archives are unchanged.
Stage 1 is closed at zero external evidence, Stage 2 remains owner-led and Stage 3 dormant/gated.
No personal testing, qualifying reviews, customer validation, completed beta, release, deployment,
participant contact or public marketing post is supplied or implied.
