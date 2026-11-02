# ScopeProof market comparison and product direction

Researched: 2026-11-02. Official-source capability research, not customer validation.
Repository baseline: resulting main `5b9860bce7f4d9349692e02b9bb8e492cad2e135`
([PR #247](https://github.com/YuzeJ21/Scope-Proof/pull/247)). Source/package identity is
**0.2.5, unreleased**; the public evaluation download remains **v0.2.4**.
The [2026-07-26 comparison](market-comparison-2026-07-26.md) remains a historical snapshot.

## Supported product facts

ScopeProof is a reviewer-controlled acceptance-coverage assistant for public GitHub PRs:
confirmed criteria → exact-head candidate evidence → explicit gaps → reviewer decisions →
export → changed-head re-review. Implementation, candidate tests, supplied runtime evidence and
human acceptance remain separate. The deterministic core never executes target-repository code.

Current source supports saved comparisons, attributable static references, readable decision
history and continuation after confirmed criteria edits. References and imported JUnit context
do not upgrade automatic evidence or gates. Recorded identities are assertions, not authenticated
approvals. See the [README](../../README.md) and [Stage 2 roadmap](../../ROADMAP.md#stage-2--owner-led-productization).

Stage 2 is active owner-led productization. Stage 1 is closed as not pursued with all external
counts at zero. No independent repeat use, customers, revenue, validated buyer or price is
recorded. Stage 3 remains dormant and gated. Engineering progress does not change those facts.

## Current official-source comparison

These are documented vendor capabilities, not independently measured reliability, completeness
or adoption. The comparison establishes overlap, not superiority or competitor absence.

| Workflow | Documented capability | Implication and comparison limit |
| --- | --- | --- |
| [GitHub Copilot code review](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review) | Reviews PRs, suggests fixes, gathers repository context and can use MCP context and skills. New-push review is configurable. Optional approving reviews can satisfy required approvals; new commits dismiss them. | Native PR review and changed-head behavior already exist. GitHub instructs users to validate feedback and supplement it with human review. These capabilities do not establish criterion-level correctness. |
| [CodeRabbit issue trackers](https://docs.coderabbit.ai/connections/issue-trackers) | Fetches issue descriptions, acceptance criteria and discussions, assesses changes against linked acceptance criteria and flags gaps. Supports GitHub/GitLab Issues, Azure Boards, Jira and Linear. | Requirement validation is direct overlap, not a unique ScopeProof claim. Documentation alone does not establish efficacy or equivalence to ScopeProof's saved decision model. |
| [Qodo ticket integrations](https://docs.qodo.ai/integrations/ticketing-integrations) | Uses ticket intent to report missing/incomplete requirements and manual-validation needs as findings, rather than explicit compliance statuses. Optional unrelated-change detection is disabled by default. Dedicated acceptance-criteria fields are supported for Jira custom fields and Azure DevOps. | Intent alignment and scope feedback already occur inside review. Field support varies by provider; do not infer that a missing dedicated field means no requirement context is available. |
| [Tiden quality gates and traceability](https://docs.tiden.ai/docs/product/quality-gates) | Combines spec coverage, test results, risk, freshness and production issues. Distinguishes verified, missing/stale execution and absent tests. SHA-bound release captures use that commit's results and retain capture history. | Closest documented workflow overlap in this comparison: traceability, freshness, gate signals and risk acceptance. This is a research judgment, not a measured substitute ranking. |
| [GitHub Spec Kit evolving specs](https://github.github.com/spec-kit/guides/evolving-specs.html) | Converge assesses implementation against spec, plan and tasks under the constitution and may append remaining tasks. It does not rewrite intent to accept the code. | Intent-to-implementation reconciliation is an existing development workflow. Its documentation does not establish the same evidence or saved-review model. |

[Tiden branches](https://docs.tiden.ai/docs/product/branches) are product-model workspaces for
specs, tests and components, linked to source PRs. Its intent closing pass checks promises against
merged code. Automatic intent-branch merges do not wait for that branch's Quality Gate; this is
product-model merging, not bypassing source-PR protection. It supplies no basis to claim ScopeProof
is safer or that Tiden lacks gates.

## Advantages and constraints

**Implemented strengths:** deterministic, inspectable records; explicit missing evidence;
exact-head provenance; separate static/runtime/acceptance states; conservative stale-state handling;
and auditable handoff/re-review. No paid model dependency or target-code execution is needed.
These are engineering properties, not demonstrated adoption advantages.

**Material constraints:** public-only access excludes private commercial source; the
[evaluation-only policy](../../USE_POLICY.md) grants no open-source license. Local setup, manual
confirmation and conservative retrieval can add work. Identity is asserted, collaboration is
local, and operator/recipient fit is unvalidated. The frozen R-002 result found candidates for
5/20 research criteria; this is not a production accuracy estimate or permission to retune it.

Existing PR/ticket products already provide broad context and familiar entry points. A manual
checklist with immutable links, CI observations and reviewer notes is also a credible baseline
requiring no new paid AI service. ScopeProof must justify its extra coordination cost. This
research makes no current vendor price, free-tier or willingness-to-pay claim.

## Positioning hypothesis and practical direction

The strongest hypothesis is **explain and revisit an acceptance decision**: a technical reviewer
can show a PM or requirements owner which confirmed promises have current candidate evidence,
which remain unresolved, who recorded each decision and what needs another look after changes.
A QA or engineering leader might eventually own a budget, but buyer, authority, frequency and
commercial value remain unknown. Audit vocabulary does not establish regulated-industry fit.

1. **Now: finish one source-bound typed CLI criteria handoff.** Prepare an optional validated
   normalized-criteria draft from the requirements source, then require the existing explicit human
   confirmation before analysis. Preserve criterion IDs, order, text, priority, type, source
   metadata and required evidence levels, including E3/E4. The draft is neither confirmation nor
   approval and carries no runtime verification or acceptance. Keep plain-text intake available;
   do not change retrieval, automatic evidence, gates or prior decisions.
2. **Later: consider safe review transfer as a separately designed outcome.** Define how an
   imported record retains producer/source identity, historical decisions and stale-state limits
   before building portability. Do not infer authenticated collaboration or carry acceptance to a
   new head. Do not start a broad accounts, integrations or parity queue.
3. **Release only through separate authorization.** Finish the bounded slice and its required
   engineering checks first. Current source is not a public download, and the completed private
   v0.2.5 candidate remains bound to its original source and bytes.
4. **Keep the genuine-use gate unchanged.** Stage 3 needs a separate owner decision and genuine
   independent-use evidence. Automated journeys, reports, benchmarks and releases cannot supply
   that evidence. No personal testing, recruitment, outreach or qualifying-review request follows
   from this direction.

Narrow or reject the value hypothesis if existing habits suffice, useful gaps are rare, review
cost exceeds value or people confuse candidates with correctness. The [roadmap](../../ROADMAP.md)
governs stage and release decisions; this research authorizes no publication or external contact.
