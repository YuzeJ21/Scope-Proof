# ScopeProof market comparison and product adjustment

Date: 2026-07-28
Status: current product and competitor-documentation audit
Boundary: competitor capabilities below are vendor-advertised unless explicitly
labelled as a ScopeProof implementation fact. This document is not customer or
market validation.

Version boundary: public install remains v0.2.3; current source is the unreleased `0.2.4.dev0`
development line. Post-release engineering changes do not constitute market validation.

## Product category

ScopeProof is not a general AI code reviewer, test-management system, or static
analysis quality gate. It is a reviewer-controlled acceptance-coverage
assistant for public GitHub pull requests:

1. load an immutable public PR snapshot;
2. normalize requirements into criteria;
3. require explicit human confirmation before analysis;
4. retrieve inspectable implementation and test candidates;
5. keep candidate evidence, observed CI, runtime verification, and human
   decisions separate;
6. fail closed when evidence or decisions are incomplete;
7. compare evidence across PR heads; and
8. export a reproducible review record.

The proposed wedge is the handoff gap between “the PR has been reviewed for
code quality” and “a PM, QA, or engineer can inspect how each agreed acceptance
criterion is supported at this exact head.”

## Current competitor map

| Category and products | Vendor-advertised job | Overlap with ScopeProof | ScopeProof distinction today |
| --- | --- | --- | --- |
| AI PR review — CodeRabbit, Qodo, GitHub Copilot code review | Find bugs or rule violations, summarize changes, suggest fixes, and automate or repeat reviews in the PR workflow. | PR context, changed-code inspection, review guidance, re-review. | ScopeProof does not generate general review comments or fixes. It starts from reviewer-confirmed criteria, exposes deterministic candidate lines, and leaves acceptance unresolved until a human decides. |
| Static analysis — SonarQube | Analyze issues introduced on new code and report a pass/fail quality gate to the repository platform. | Changed-code analysis, status/gate vocabulary, merge-time use. | ScopeProof does not scan for generic quality or security issues. Its gate is tied to criterion evidence, observed CI, runtime records, and current human decisions. |
| Test management and requirements traceability — Qase, TestRail | Link requirements to test cases and results; show covered/uncovered requirements and stale test results. | Requirement-to-test coverage, missing-coverage visibility, snapshots or reports. | ScopeProof works at a single public PR head, includes implementation candidates, and keeps linked/static candidates distinct from executed runtime verification. It is not a test repository or execution manager. |
| Work tracking — Azure Boards and GitHub controls | Link work items, PRs, commits, builds, reviews, and required status checks to provide traceability and merge controls. | Requirement/source linkage, PR identity, CI state, policy enforcement. | ScopeProof inspects criterion-level evidence inside the PR rather than treating an item link, template, approval, or passing check as proof that each criterion is covered. |

## Official evidence used

- [CodeRabbit documentation](https://docs.coderabbit.ai/) advertises
  context-aware PR reviews, bug detection, standards enforcement, suggested
  fixes, and IDE/CLI/PR surfaces.
- [CodeRabbit linked-issue validation](https://docs.coderabbit.ai/issues/pr-validation)
  compares issue requirements with PR changes and reports Addressed, Not
  addressed, or Unclear. Requirement checking alone is therefore not a
  ScopeProof distinction.
- [CodeRabbit rate-limit documentation](https://docs.coderabbit.ai/management/plans)
  states that a rate-limited push receives a passing check even though no new
  review ran and a prior approval remains. This supports ScopeProof's proposed
  fail-closed wedge: no valid current-head evidence means no valid current-head
  decision.
- [Qodo code review documentation](https://docs.qodo.ai/code-review) advertises
  multi-agent PR findings, rule enforcement, repository context, and
  requirement-gap detection.
- [Qodo requirement-gap documentation](https://docs.qodo.ai/code-review/view-requirement-gaps-in-findings)
  labels its specification comparison as a Research Preview and advises users
  to validate outputs before relying on them.
- [GitHub Copilot code review documentation](https://docs.github.com/en/copilot/concepts/agents/code-review)
  describes AI-generated PR feedback and suggested fixes; it also states the
  feature is available on paid Copilot plans and consumes AI credits.
- [GitHub status-check documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)
  describes pending, passing, and failing checks attached to commits.
- [SonarQube pull-request analysis documentation](https://docs.sonarsource.com/sonarqube-server/2026.1/analyzing-source-code/pull-request-analysis/introduction)
  describes new-code issue analysis and PR quality-gate reporting.
- [Qase traceability-matrix documentation](https://docs.qase.io/en/articles/9123660-requirements-traceability-matrix)
  describes requirement-to-test coverage, execution status, versioned
  snapshots, and stale-case detection.
- [TestRail Jira Coverage Check documentation](https://support.testrail.com/hc/en-us/articles/47341662234772-Jira-Coverage-Check)
  describes covered and uncovered Jira entities based on linked test cases or
  results.
- [Azure Boards linking documentation](https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/add-link?view=azure-devops)
  describes traceability links among work items, GitHub PRs, commits, builds,
  and test objects.
- [GitHub pull-request standardization documentation](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests)
  describes templates, linked issues, required checks, signed commits, and
  approving reviews.

## Competitive assessment

### Where ScopeProof is credible

- Deterministic, local-first inspection with no paid LLM API.
- Explicit source-owner criteria confirmation before analysis.
- Strong separation among implementation candidates, test candidates, observed
  CI, manually recorded runtime verification, and acceptance.
- Immutable evidence references and changed-head comparison.
- Conservative False Ready posture and inspectable missing-evidence
  explanations.
- Portable exports and versioned local records.
- CLI lifecycle parity is implemented for core-backed resolution, external runtime verification,
  final acceptance, and changed-head comparison.
- Bounded keyboard-only and visible-focus engineering evidence is implemented for the installed
  Chromium path; it is not accessibility conformance.

### Where ScopeProof is immature

- Genuine independent use remains zero; the current wedge is a hypothesis.
- The public-PR-only, local-first workflow creates setup and collaboration
  friction compared with installed PR applications.
- Criteria must be supplied and confirmed manually; there is no validated
  integration with an issue or test-management source.
- Retrieval coverage is intentionally conservative and the completed R-002
  baseline found candidates for only 5 of 20 research criteria.
- Real screen-reader operation, Windows desktop, Linux desktop, non-Chromium browser behavior, and
  WCAG conformance remain unsupported. The bounded keyboard/focus and native-zoom checks do not
  establish those broader claims.
- There is no evidence yet that users will repeat the workflow or pay for a team
  product.

## Roadmap adjustment

### Build now — evidence trust and first-use quality

1. Keep v0.2.3 dependency health, exact-head verification, packaging, and
   release-status evidence aligned after the source merge and before any
   owner-controlled tag or GitHub Release decision.
2. Preserve retrieval diagnostics as explanations, never verdict evidence.
3. Improve conservative retrieval only through new constructed regressions and
   a prospectively frozen holdout; do not retune on R-002.
4. Attempt real assistive-technology and available desktop-platform checks only in genuine,
   observable environments; keep unavailable rows unsupported.
5. Keep export, changed-head re-review, and missing-evidence explanations clear.

### Design now, implement only after genuine use evidence

1. A source-adapter contract for importing owner-confirmed criteria from issue
   trackers without treating the link itself as evidence.
2. A portable handoff bundle for another reviewer to inspect and decide without
   an account system.
3. A repository policy file for team-owned criterion vocabulary and evidence
   expectations.
4. A lightweight history view for review deltas and unresolved handoffs.

### Do not build yet

- Generic AI code review, security scanning, style comments, or automatic fixes.
- Hosted accounts, private-repository access, billing, or paid APIs.
- Broad project-management or test-execution management.
- Team dashboards, enterprise controls, or integrations justified only by
  competitor feature parity.
- Any feature described as validated without genuine participant evidence.

## Stage implications

- Stage 0 engineering maturity can continue internally.
- Stage 1 remains at zero until a qualifying non-owner public-alpha review
  occurs.
- Stage 2 commercial discovery cannot claim willingness to pay before Stage 1
  evidence exists.
- Stage 3 controlled beta requires independent repeat use, including real
  changed-head re-review.
- Stage 4 expansion is evidence-gated; competitor breadth is not a reason to
  copy features.

The best near-term positioning is therefore: **“Inspect acceptance coverage at
an exact public PR head without confusing candidate code, CI, runtime proof, or
human acceptance.”** It should remain a positioning hypothesis until genuine
users demonstrate that this job is important and repeated.
