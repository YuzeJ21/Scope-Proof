# ScopeProof product direction · 2026-11-23

ScopeProof helps a QA or release reviewer explain an acceptance decision for a public pull request and
revisit it after the build changes. The current product hypothesis is that a local, portable record
makes that handoff easier for teams already using a ticket tracker and CI. Buyer, demand, repeat use,
time savings, and willingness to pay remain unmeasured.

## What exists today

| Workflow | Shipped behavior and limits |
| --- | --- |
| Confirm intent and inspect a change | The CLI and workbench require confirmed criteria, cite exact-commit source candidates, and expose missing evidence and unresolved file scope. Static candidates cannot establish runtime behavior. |
| Record and revisit a decision | Local records preserve reviewer decisions, evidence corrections, criteria revisions, and history. Reviewers can compare eligible analyses, transfer the full record, or share an offline report. Recorded identities are assertions. |
| Bring CI context to a handoff | v0.2.8 displays externally supplied results for confirmed criteria and the reviewed commit. It distinguishes passing, failing, explicitly skipped, stale, and unknown outcomes. The workbench exports a separate offline HTML snapshot. ScopeProof leaves CI execution, manifest authentication, and acceptance decisions with their respective owners. |

The public [v0.2.8 evaluation release](https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.8)
was built from `7c5603fc59b1e33b199a4f9b3219f11b47eeec7d`. Public archive checks and fresh
installs are recorded there. PR #303 aligned the evaluation entry points and left development at
`0.2.9.dev0`. Its exact resulting main, `9c530daf6a5569e1a24998d60d45e3eb3f373bbb`, passed
5,064 tests with 40 skips, 95.6450% coverage, and 36 Chromium checks.
[Post-merge CI](https://github.com/YuzeJ21/Scope-Proof/actions/runs/44811537369)

The deployed product page serves the LinkedIn preview metadata and image. The card rendered by
LinkedIn Featured remains unverified.
[Pages deployment](https://github.com/YuzeJ21/Scope-Proof/actions/runs/44811573736)

## Market and product gaps

Vendor documentation establishes the capabilities below. Relative quality and workflow costs
require direct comparison on the same task.

| Alternative | Documented capability | Product implication |
| --- | --- | --- |
| GitHub native | Required checks and approvals protect merges. Signed artifact attestations can establish build provenance. [Branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) · [Artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) | Keep GitHub as the merge authority. Prove whether criterion-level context and a portable record add value over a checklist, links, and CI. |
| CodeRabbit | Evaluates linked issue objectives and flags changes outside the linked scope in the PR. [Linear integration](https://linear.app/integrations/coderabbit) · [Pre-merge checks](https://www.coderabbit.ai/blog/pre-merge-checks-built-in-and-custom-pr-enforced) | Ticket alignment alone is an established capability. ScopeProof can keep the confirmed criteria, evidence, and reviewer decisions inspectable across handoffs. |
| Qodo | Surfaces requirement gaps, unrelated changes, and manual-validation needs from supported ticket context. [Ticket integration overview](https://www.qodo.ai/academy/integrating-ai-code-review-tool-stack/) | Integrated ticket intake removes setup work. Keep the local confirmation path and test the benefit of reduced handoff effort before building a connector. |
| Tiden | Provides spec-to-test traceability, freshness-aware gates, risk acceptance, and release captures scoped to a supplied build SHA. [Quality gates](https://docs.tiden.ai/docs/product/quality-gates) | Exact build identity and traceability are established capabilities. Evaluate ScopeProof's smaller, local artifact workflow for teams without a managed spec/test platform. |
| Xray | Links Jira requirements, cases, runs, and defects, and imports automated results. [Test management](https://www.getxray.app/test-management/) | Teams with managed QA already have shared traceability. A PR-specific review handoff is a narrower use case. |

The largest adoption barriers are public-only source access, evaluation-only use rights, manual
setup, unauthenticated reviewer identities, and local retention. Full enterprise deployment would
need a concrete access and sharing model, approved use rights, and a plan for retention and audit
controls. The frozen R-002 result of 5/20 criteria with a retrieved candidate describes that
benchmark and leaves general retrieval performance open.
[Use policy](../../USE_POLICY.md) · [Privacy readiness](../privacy-readiness.md) ·
[Frozen R-002 results](../research/r002-swebench-verified/summary.md)

## Ordered development priorities

1. **Automate the CI snapshot handoff.** The development-source
   [CLI export](../evaluation-guide.md#export-a-ci-snapshot-from-the-cli) takes a saved review and
   matching local manifest. It reuses the workbench's validated renderer, rejects mismatches and
   pending states, and preserves the saved record and acceptance gate.
2. **Surface unresolved checks.** The development-source workbench and report use the same
   follow-up summary. In the constructed rehearsal, the second build initially shows a filter
   failure and a row-access skip. The targeted rerun changes the skip to failed without changing
   the reviewed commit or rewriting either review.
3. **Make the workflow inspectable before installation.** Prepare a candidate no-install two-build
   sample with labeled synthetic status changes and a clear explanation of the evidence boundary.
   Keep its producer and source identities explicit.
4. **Gate adoption and private architecture on independent use.** Stage 2 remains owner-led. Stage 1
   is closed with zero external evidence, and Stage 3 remains dormant. If separately authorized,
   look for one independent reviewer who can explain what changed, make a decision, and choose to
   return for another review. Use a demonstrated access or handoff need to scope any private design.
   The current engineering plan uses automation and independent engineering review.

See the [roadmap](../../ROADMAP.md#current-priorities--2026-11-07) for implementation status.
