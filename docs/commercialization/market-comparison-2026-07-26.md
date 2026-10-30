# ScopeProof market comparison and product adjustment

Date: 2026-07-26 (original research)
Last refreshed: 2026-10-27
Status: official-source capability research and bounded roadmap decision

Operating-decision update, 2026-10-30: the [current roadmap](../../ROADMAP.md) supersedes the
maintenance-only recommendation below with bounded Stage 2 reviewer-workflow development.
The vendor research and release references below remain the dated 2026-10-27 snapshot; they
have not been re-researched. This update supplies no genuine-use or competitive-value evidence.

Vendor documentation records advertised capabilities, not independently observed efficacy.
This document establishes no customer validation, competitive superiority, or novelty. Public
install remains v0.2.3; source is the unreleased `0.2.4.dev0` development line. Historical engineering
results and frozen R-002 research remain unchanged.

## Product category and value hypothesis

ScopeProof is a reviewer-controlled acceptance-coverage assistant for public GitHub pull requests.
Its implemented workflow is confirmed criteria → exact public PR head → inspectable implementation
and test candidates → explicit missing evidence → reviewer decisions → export and changed-head
re-review. Static candidates, observed CI, supplied runtime records, and human acceptance remain
separate. ScopeProof never executes target-repository code.

The strongest value hypothesis is that this combination makes a specific acceptance decision more
inspectable and keeps decisions current after a head change. Each component has substantial
market overlap. This is a positioning hypothesis, not customer or market validation.

The primary-operator hypothesis is an engineer or technical QA reviewer able to inspect candidate
code and evidence. A PM or requirements owner may confirm intent and receive the resulting report.
These role assignments, recurring need, and willingness to adopt remain unvalidated.

## Current competitor map

| Workflow | Documented capability and overlap | Limit on the comparison |
| --- | --- | --- |
| Tiden — closest documented overlap | Intent verification, spec/test traceability, freshness-aware quality gates, and risk acceptance overlap strongly with acceptance-evidence review. [Product](https://tiden.ai) and [quality gates](https://docs.tiden.ai/docs/product/quality-gates) | Closest is a research judgment about workflow overlap, not a measured substitute or efficacy ranking. |
| CodeRabbit — issue-aware PR review | Fetches acceptance criteria and assesses linked requirements against changes, flagging gaps. [Issue trackers](https://docs.coderabbit.ai/connections/issue-trackers) | Requirement checking is already a direct documented capability; it is not a unique ScopeProof claim. |
| Qodo — ticket-aware review | Uses ticket intent for requirement-alignment findings and can flag unrelated changes. Acceptance-criteria fields vary by provider. [Ticket integrations](https://docs.qodo.ai/integrations/ticketing-integrations) | Its current docs describe findings rather than explicit compliance statuses. This is not evidence that either approach is more reliable. |
| Qase — requirements traceability | Connects external requirements to test cases and latest results, with linked/unlinked views, stale-case flags, versioned snapshots, and exports. [Traceability matrix](https://docs.qase.io/en/articles/9123660-requirements-traceability-matrix) | Traceability, missing coverage, and staleness are established adjacent jobs; a matrix alone does not distinguish ScopeProof. |
| GitHub Spec Kit — specification and convergence | `converge` assesses implementation against the spec, plan, tasks, and constitution; remaining work can be appended to tasks. [Evolving specs](https://github.github.com/spec-kit/guides/evolving-specs.html) | Intent-to-implementation reconciliation is already part of a development workflow, beyond conventional code review. |
| Kiro — spec-driven development | Specs contain requirements/acceptance criteria, design, and executable task tracking. [Specs](https://kiro.dev/docs/specs/) | Explicit criteria and tracked implementation are not novel. This comparison does not establish a matching saved-review or evidence model. |
| GitHub Copilot and Graphite — PR review | Provide AI review feedback and suggested changes. [Copilot review](https://docs.github.com/en/copilot/concepts/agent-capabilities/agent-powered-workflows-and-operations/code-review), [Graphite AI reviews](https://graphite.com/docs/ai-reviews) | ScopeProof is not a general code reviewer; these can still be alternatives to an additional review step. |

### Tiden branch and gate distinction

Tiden branches are product-model workspaces for specs, tests, and components, linked to source
PRs; they are not source-code PR branches. Its documentation says automatic intent-branch merges
occur after linked PRs merge and do not wait for the branch Quality Gate, including when blocked
or unavailable. That describes product-model merging, not bypassing source-PR branch protection.
Do not generalize it into a claim that Tiden has no gates or that ScopeProof is safer.
[Branches](https://docs.tiden.ai/docs/product/branches)

### Additional primary documentation

[CodeRabbit PR review](https://docs.coderabbit.ai/overview/pull-request-review) and
[Qodo code review](https://docs.qodo.ai/code-review) describe broader review surfaces. The refreshed
issue/ticket pages above are the basis for the direct acceptance-criteria overlap. Older feature,
rate-limit, preview, or pricing descriptions are not carried forward as current facts.

## ScopeProof implementation and adoption limits

CLI lifecycle parity is implemented. Bounded keyboard-only and visible-focus engineering evidence
is implemented for the installed Chromium path. Current packaged-browser coverage comprises eleven
checks: one full installed-wheel Chromium journey, four constructed Streamlit selection checks,
and six helper/capture checks. This total is not
a count of full end-to-end journeys.
These are engineering results, not accessibility conformance or independent use. Real screen-reader
operation, Windows desktop, Linux desktop, non-Chromium behavior, and WCAG conformance remain
unsupported by the available evidence.

Independent qualifying reviews and repeat-use evidence remain zero. Conservative R-002 retrieval
found candidates for 5 of 20 research criteria; that frozen result is not a production accuracy
estimate or a reason to retune the benchmark. Reviewer identity remains asserted rather than
authenticated. The local setup and manual criteria confirmation have unmeasured coordination cost.

Public-repository-only scope excludes many private commercial workflows. The
[evaluation-only use policy](../../USE_POLICY.md) grants no open-source license; public visibility
and no paid LLM API dependency do not grant broader use rights. Licensing is an adoption constraint,
not a pricing or demand finding, and no licensing change is proposed.

## Existing alternatives and the decision threshold

A manual acceptance checklist with immutable diff links, CI results, reviewer notes, and a later
head comparison is a practical baseline requiring no new paid AI service. Existing issue templates,
spreadsheets, and team review habits may be sufficient. Spec Kit also supplies a repository-based
intent/convergence workflow. This research makes no current vendor pricing or free-tier claim.

The unvalidated question is whether ScopeProof's combined confirmed-criteria, exact-head candidate,
missing-evidence, reviewer-decision, and re-review record is worth its setup and review cost against
those alternatives. A feature table cannot answer it. Neither automated research nor another
release can create independent-use evidence.

## Roadmap adjustment

Maintain a bounded engineering reference product. Start a slice only for a demonstrated defect,
required upkeep, or a named bounded research question; define its outcome and completion evidence
before implementation. Finish the relevant regression and repository checks, align documentation,
then stop. If no concrete need remains, stay in maintenance.

Additional adapters, authenticated identity, tracker intake, and collaboration are evidence-gated
options, not pilot-critical prerequisites or a standing feature backlog. Do not copy competitors'
breadth, broaden into generic review/security/auto-fix, or add accounts, private repositories,
hosted processing, billing, or paid APIs to create activity. Unsupported platform checks may stay
unsupported. No personal testing or qualifying-review request is required by this direction.

## Stage implications

- Stage 1 is `closed_not_pursued_by_owner` with all external-evidence counts at zero; it did not pass.
- Stage 2 is `owner_led_productization_active` in bounded maintenance/reference-product mode.
- Stage 3 is dormant and gated. No beta, release, deployment, outreach, or participant program is
  authorized by this research or by completed engineering checks.
- Stage 4 expansion requires a named constraint, appropriate evidence, and a separate owner decision.
- R-003 generation and label confirmation remain separate owner gates; R-002 stays frozen.

The [roadmap](../../ROADMAP.md) governs current scope. External commercial discovery remains
optional and separate; it requires authorization before contact and creates no adoption or
willingness-to-pay claim in advance.
