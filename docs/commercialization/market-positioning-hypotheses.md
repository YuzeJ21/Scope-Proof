# ScopeProof Market Positioning Hypotheses

Last researched: 2026-10-27
Product direction updated: 2026-10-30; competitor documentation was not refreshed by this change.

This is official-source market research, not customer or market validation. ScopeProof has zero
qualifying participant reviews, independent repeat-use evidence, customers, or revenue, and no
validated buyer or price. Stage 1 is `closed_not_pursued_by_owner`; Stage 2 engineering work does
not change these facts. The owner is not pursuing personal testing or qualifying reviews.

## Implemented workflow and strongest value hypothesis

`public PR → explicitly confirmed criteria → exact-head candidate evidence → missing evidence →`
`reviewer decisions → export → changed-head re-review`

The CLI and workbench keep implementation, test, supplied runtime, and human-decision evidence
separate, preserve incomplete ingestion and unresolved criteria, and never execute PR code.
Engineering verification supports these implementation statements; it does not establish usefulness
in independent work, accuracy in production, or demand.

The strongest value hypothesis is the combined record: **confirmed criteria, inspectable candidates
at an exact head, explicit missing evidence, attributable reviewer decisions, and re-review when
that head changes**. This may help a technical reviewer explain an acceptance decision to a PM or
requirements owner. No part of the combination is claimed novel, superior, or uniquely available.

## Documented overlap

The [current market comparison](market-comparison-2026-07-26.md) records the primary-source refresh
and its limits. These vendor-described capabilities are not independently verified efficacy:

| Workflow | Direct relevance |
| --- | --- |
| Tiden | Closest documented overlap: intent verification, spec/test traceability, gate signals, and risk acceptance. Its branches are product-model workspaces, distinct from source PRs; automatic intent-branch merges do not wait for that branch's gate. [Quality gates](https://docs.tiden.ai/docs/product/quality-gates), [branches](https://docs.tiden.ai/docs/product/branches) |
| CodeRabbit | Directly assesses linked issue acceptance criteria against PR changes. Requirement validation alone does not distinguish ScopeProof. [Issue trackers](https://docs.coderabbit.ai/connections/issue-trackers) |
| Qodo | Uses ticket requirements in review findings; may surface missing intent or unrelated changes. [Ticket integrations](https://docs.qodo.ai/integrations/ticketing-integrations) |
| Qase | Maps external requirements to tests and results with staleness indicators and versioned snapshots. [Traceability](https://docs.qase.io/en/articles/9123660-requirements-traceability-matrix) |
| GitHub Spec Kit | Convergence checks implementation against spec, plan, and tasks and appends remaining work. [Evolving specs](https://github.github.com/spec-kit/guides/evolving-specs.html) |
| Kiro | Specifications structure acceptance criteria, design, and tracked implementation tasks. [Specs](https://kiro.dev/docs/specs/) |

These sources weaken any broad claim that acceptance checking, traceability, or intent alignment
is a new category. They do not prove whether a narrow local review record is useful or redundant.

## Operator, recipient, and buyer hypotheses

The primary-operator hypothesis is an **engineer or technical QA reviewer** able to inspect source
candidates, evidence limits, and CI context. A **PM or requirements owner** may confirm intent and
receive the report or acceptance handoff. Actual roles, authority, and frequency of use remain
unvalidated; an exported report does not establish stakeholder participation.

A possible initial setting is a team reviewing public GitHub PRs against explicit criteria without
a satisfactory criterion-level handoff. Public-only access and local setup substantially narrow
that setting. Team size, regulated-industry fit, and private-repository demand are unknown.

If a team product were later justified, a QA or engineering leader might own the budget; a product
leader might own acceptance intent. There is no validated buyer, procurement path, or budget.

## Job-to-be-done hypothesis

> Before approving a PR, or after its head changes, show me which confirmed criteria have current
> candidate evidence, what remains missing or stale, and which human decisions need another look,
> so I can explain my acceptance decision without treating static code as runtime proof.

## Alternatives and adoption constraints

A manual checklist with immutable diff links, CI results, and reviewer notes may already solve the
job. Teams can use PR templates, spreadsheets, existing issue/test-management links, or spec-driven
workflows without adopting another evidence application. No paid AI service is necessary for the
manual baseline. This research makes no vendor pricing or free-tier claims.

ScopeProof would have to justify its setup and review cost against those habits. Current risks are
hypotheses: public criteria may be unavailable; normalization adds work; conservative candidates
may leave many unresolved rows; the candidate/proof distinction may be misunderstood; and local
records may complicate collaboration. No observed participant result establishes these costs.

The public-repository-only boundary excludes private commercial source. The
[evaluation-only use policy](../../USE_POLICY.md) grants no open-source license. Public visibility,
local operation, and no paid LLM dependency do not grant broader adoption rights. Licensing remains
an explicit constraint; no licensing change or commercial offer is proposed here.

## What remains fixed

Every verdict must cite evidence or identify its absence. Criteria require human confirmation
before analysis. Immutable provenance, typed persisted/exported records, deterministic fail-closed
gates, and separate candidate/runtime/acceptance states remain required. ScopeProof does not run PR
code, invent requirements, provide generic code review, scan for security issues, auto-fix code,
manage test execution, or replace QA and human acceptance.

## Evidence that could change the hypothesis

Only separately authorized genuine use could determine whether the workflow exposes an actionable
gap, affects a review decision, is understood, and is used again on a later PR without prompting.
Relevant observations would identify the operator and recipient, prior alternative, exact head,
confirmed criteria, missing evidence, actual human decision, friction, and independent repeat use.
These are possible future observations, not an active participant program or an assignment to the
owner. Stage 1 remains closed at zero and Stage 3 dormant and gated.

Narrow or reject the hypothesis if existing workflows suffice, useful gaps are rare, review cost
exceeds value, or people confuse candidates with correctness. Engineering checks, a new benchmark,
competitor claims, stars, downloads, or another release cannot supply that evidence.

## Current product decision

Develop the existing reviewer workflow through the
[ordered Stage 2 roadmap](../../ROADMAP.md#stage-2--owner-led-productization). Current source
capabilities include changed-file scope context and durable comparison of compatible
saved records or retained analyses after reopening, and separately attributable exact-head
static references selected from already-ingested source. Selected references are non-gating
context and do not improve an automatic retrieval score or establish execution. These choices follow inspectable
implementation gaps and an owner
decision to keep developing, not observed demand or a new competitive claim.

Each milestone has a reviewer outcome and automated finish line. Finish the selected slice before
starting another; do not generate an endless feature queue or repeat closed release preparation.
Additional adapters, authenticated identity, integrations and broader collaboration remain
separately scoped options. There is no active commercial-discovery program. No personal testing
or qualifying reviews are required for these engineering milestones; Stage 1 remains closed at
zero and Stage 3 dormant and gated.

External discovery is optional and separate and needs authorization before contact. Historical
price anchors are research context, not active prices, an offer, willingness-to-pay evidence, or
customer validation. The [roadmap](../../ROADMAP.md) governs stage and release decisions.
