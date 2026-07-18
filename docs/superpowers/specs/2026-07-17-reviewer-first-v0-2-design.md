# ScopeProof Reviewer-First v0.2 Design

## Decision

ScopeProof v0.2 is a reviewer-controlled acceptance-coverage assistant for public GitHub pull
requests. Its primary user is a pull-request reviewer or technical lead. QA and product
practitioners are secondary users. The primary success moment is reaching an inspectable
acceptance-coverage report in under five minutes.

The product will say what evidence it found, what it did not inspect, and what still requires a
human decision. It will not claim to prove product intent, runtime behavior, correctness, or market
validation.

## Product Boundary

The default workbench is a product workflow:

`Public PR -> Confirm criteria -> Review coverage -> Record decisions -> Export`

Alpha research is an optional feedback mode layered on that workflow. Qualification, participant
role, consent, friction, and outcome collection are not default product steps. A constructed demo
remains available and remains explicitly labelled as constructed evidence rather than participant
validation.

The following remain excluded: paid model APIs, private repositories, billing, accounts,
organizations, fork testing, untrusted-code execution, generic code review, security scanning,
automatic fixes, automated outreach, and notification-producing publication.

## Terminology

The internal persisted enums remain readable for backward compatibility, but the primary UI and
human-readable reports use presentation terms that do not imply correctness.

### Evidence type

- Implementation
- Test
- Runtime
- Documentation or contract when relevant

### Evidence status

- Strong candidate: a high deterministic lexical match at the requested static evidence type.
- Weak candidate: a lower match or a candidate below the requested evidence type.
- No candidate: complete ingestion found no candidate.
- Analysis incomplete: ingestion limitations prevent a reliable no-candidate statement.
- Reviewer verified: a human recorded an external verification with an attributable note.
- Rejected: a reviewer explicitly rejected the candidate finding.

### Review status

- Action required
- Review incomplete
- Accepted with exceptions
- Review complete

The legacy `FindingStatus`, `EvidenceLevel`, and `GateVerdict` values remain in JSON records. A
small UI-independent presentation module maps validated core values to the new labels. This avoids
silently reinterpreting existing records and keeps machine-readable compatibility explicit.

## Core Components

### Presentation service

Create a UI-independent presentation module that returns Pydantic-validated criterion coverage
rows. Each row separates criterion text, evidence types, candidate status, reviewer decision,
candidate count, and concern. The Streamlit matrix and Markdown/CSV/HTML reports consume the same
mapping so terminology cannot drift by surface.

### Evidence context

`EvidenceItem` gains an optional validated `context_excerpt`. Retrieval constructs it
deterministically from at most one inspectable neighboring line before and after the matched line.
The immutable permalink and exact matched line range stay unchanged. Context is display help, not
additional proof. Older records without context remain valid.

### Observed CI state

The public GitHub adapter continues to aggregate visible check runs because anonymous public API
access cannot reliably establish every repository's protected required-check policy. The product
therefore calls this value `Observed CI state`. Only explicit success conclusions count as passing;
`neutral` and `skipped` do not prove a successful check. Any failure or pending run keeps the
existing fail-closed precedence.

### Review comparison

The existing comparison service remains the source of deterministic before/after facts. When a
saved review is reopened and the same public PR is fetched at a new head SHA, the previous validated
bundle is preserved in session. After the new analysis, the workbench shows added and removed
evidence IDs, changed criterion findings, changed decisions, gate transition, and ruleset change.
Neither review is mutated.

### Human verification

Add an atomic lifecycle operation that accepts a `RuntimeEvidence` and a matching
`MANUALLY_VERIFIED` resolution event. It validates both against the active criterion and appends
both, then recalculates the gate once. The UI collects the external observation and decision in one
form while the stored evidence and human decision remain separate records.

### Final acceptance

A final-acceptance event is eligible only when every active criterion has a current, accepted
resolution: accepted, accepted exception, manually verified, or not in scope. Change required,
rejected finding, missing decisions, stale prior-revision events, failing observed CI, or incomplete
ingestion cannot enable final acceptance. The gate remains deterministic and is not overridden by
the button.

### Alpha feedback session

The default workbench has an optional `Alpha feedback session` toggle. When enabled, it requests the
existing public qualification fields. After criteria confirmation, it creates one local
Pydantic-validated `AlphaCaseRecord`, stores its case ID in session, and displays it. After analysis
and review, the participant can record exactly one validated outcome in the workbench. Consent
remains separate and off by default. Standard reviews never create alpha records.

## Workbench Flow

1. Start review: enter a public PR. Advanced options contain the session-only GitHub token and an
   explicit list of bounded unchanged repository paths. Alpha feedback fields appear only when the
   optional mode is enabled.
2. Confirm criteria: normalize, edit, assign priority and requested evidence type, then explicitly
   confirm. Alpha mode creates the local case at this boundary.
3. Review coverage: run deterministic retrieval and inspect the presentation matrix. Each candidate
   shows type, source scope, matched line, context, rationale, and limitations.
4. Record decisions: accept, request change, accept an exception, reject a finding, mark out of
   scope, or record external verification. Final acceptance is disabled until prerequisites pass.
5. Export: save locally, compare a re-review when applicable, download validated reports, and—only
   in alpha feedback mode—record the voluntary outcome and consent.

The workbench will move secondary history, research, and advanced controls into collapsed sections.
The GitHub Action remains available as an advanced, non-default preview, but the default workflow
will no longer advertise PR comments or automated publication.

## Error Handling and Trust

- Invalid public URLs, unsafe paths, failed GitHub requests, invalid alpha inputs, and invalid
  evidence records leave the active review unchanged.
- Partial or failed ingestion never becomes review complete.
- Missing required checks are not invented; observed CI limitations are explicit.
- Candidate context is escaped in every human-readable export.
- Optional tokens never enter persisted state or exports.
- No application path checks out or executes pull-request code.

## Responsive Design

The static landing page and workbench must remain usable at 390 CSS pixels. Hero text uses bounded
font sizing and overflow wrapping. Buttons stack when required, wide evidence tables remain within
scrollable containers, and no page-level horizontal overflow is permitted.

## Roadmap and Validation

The engineering reset does not unlock beta. Genuine public alpha requires five completed reviews,
at least three independent practitioners, at least three public repositories, three journeys
completed within ten minutes, recorded misleading candidates, zero confirmed False Ready outcomes,
and at least two independent statements of intent to reuse. If these do not exist, the truthful
state remains `waiting_for_external_participant_evidence` without polling or fabricated evidence.

## Verification

Every behavior change follows a red-green-refactor cycle. Final verification includes Ruff, the
complete pytest suite with coverage at or above 95 percent, the deterministic benchmark with zero
must-have False Ready mismatches, package build and isolated installation, CLI and workbench health
smokes, all supported export formats, repository contract checks, and inspected desktop and 390px
browser captures.

## Release and Publication

All work is delivered on one `codex/scopeproof-v0-2-product-reset` branch and one pull request.
Unrelated local files are not staged. The pull request is merged only after protected checks pass.
Version `v0.2.0` is published only after the merged source, wheel, documentation, public site, and
installation smoke are verified. GitHub issue and pull-request comments are not used for progress
updates.
