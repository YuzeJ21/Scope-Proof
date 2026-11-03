# Product review: consolidate the evaluation path

Reviewed 2026-11-02 (America/Toronto), against PR #250 main
`6a74fe9888d54f5edcd3033457c0d9234056024f`. Live post-merge CI passed. The earlier
[market comparison](market-comparison-2026-11-02.md) preserves its PR #247 snapshot;
its typed-criteria and transfer recommendations are now implemented, not remaining work.

## Product assessment

The implemented workflow is substantial: confirmed intent, exact-head evidence and missing
evidence, explicit decisions, retained history, changed-head comparisons, audited corrections,
and safe record handoff. The last three PRs closed typed intent preservation and CLI/workbench
transfer. They did not add human-use evidence or update the public v0.2.4 package.

The concrete gap found in this audit is evaluation coherence. README exceeds 1,100 lines;
the documentation map still routes its current-market link to an older comparison; the current
priority table leaves completed handoff selected; the private candidate guide describes record
v5 while current source writes v9; and README's current browser count is stale. These are
inspectable communication defects, not measured user-abandonment causes. Adding another adapter
does not address them. The [evaluation guide](../evaluation-guide.md) is the selected correction.

## Market structure and tradeoffs

Official pages were revisited for this decision. These are vendor-documented capabilities,
not hands-on comparisons, independently measured quality or proof of market demand.

| Alternative | Documented overlap | Implication for ScopeProof |
| --- | --- | --- |
| [GitHub Copilot code review](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review) | Native PR review, repository context and suggested fixes. | Competes at the review entry point. ScopeProof should not become another general reviewer or imply that deterministic evidence is universally better. |
| [CodeRabbit issue trackers](https://docs.coderabbit.ai/connections/issue-trackers) | Uses acceptance criteria and flags requirement gaps. | Requirement checking is not a unique claim. ScopeProof must justify the work of explicit confirmation and recording decisions. |
| [Qodo ticket context](https://docs.qodo.ai/integrations/ticketing-integrations) | Reports missing/incomplete intent and manual-validation needs; optional unrelated-change detection. | Ticket alignment and scope feedback already exist. Dedicated acceptance-criteria fields vary by provider; missing fields do not mean absent intent context. |
| [Tiden quality gates](https://docs.tiden.ai/docs/product/quality-gates) | Spec/test traceability, freshness, risk acceptance and build-SHA release captures. | Durable traceability and freshness are also competitive territory. ScopeProof's local record model is a candidate distinction, not a defensible moat established by this research. |
| Existing checklist + immutable links + CI + reviewer notes | A practical workflow substitute; no measured efficacy asserted here. | The relevant comparison is total effort to explain a decision and revisit it after changes, not feature count. |

**Strengths already implemented:** local operation, deterministic and inspectable decisions,
explicit unknowns, head-bound references, conservative stale-state treatment, original history
preservation and no paid model dependency. These are engineering properties; whether they reduce
effort or earn trust is unknown.

**Disadvantages and risks:** public-only access excludes private source; evaluation-only terms
are not an open-source license or general commercial-use grant; local setup and manual decisions
cost effort; identity is asserted; collaboration has no authenticated shared workspace. Conservative
candidate retrieval misses evidence (frozen R-002: 5/20 criteria with candidates). The public
package lags the source workflow. Buyer, repeat use, willingness to pay and usefulness are unknown.

## Adjustments and next stages

1. **Execute now — one coherent evaluation entry.** Explain the job as "explain and revisit an
   acceptance decision"; route readers to the version map and short constructed workflow.
   Mark the old candidate historical and the completed transfer outcome complete. Correct
   current evidence counts without rewriting historical observations. Finish with existing
   documentation contracts, link/source checks, independent automated review and protected CI.
2. **Next bounded option — current distribution readiness.** If selected, freeze a current
   source commit and prepare a separately named packet for that revision: wheel/source parity,
   installed workflow, v5-to-v9 upgrades on copies, exact hashes and unresolved limitations.
   Preserve PR #221's original packet. Do not silently replace its same-version bytes. Candidate
   preparation and public publication are separate decisions; this audit does neither. The
   reason for this option is the concrete public/source capability gap, not another green CI run.
3. **Later — usefulness decision.** Keep Stage 3 dormant until genuine independent use and
   separate authorization exist. The relevant evidence is whether another reviewer can explain
   a changed acceptance decision with less rework than their existing habit and chooses to reuse
   the workflow. These are research questions, not achieved results or a new recruitment task.
4. **Expand only for a named constraint.** A source-format gap, repeat setup failure or repeated
   handoff problem could justify a bounded change. Private repositories, licensing, authenticated
   collaboration and hosting need separate product decisions and appropriate evidence. No accounts,
   billing, generic review, security scanning, automatic fixes or speculative adapter queue.

Under the owner's current preference, neither personal testing nor qualifying reviews are tasks.
If independent use remains absent, finish the selected engineering outcome and remain honest
about that limit. Do not relabel automation as customer evidence or endlessly add parity features.
