# ScopeProof Market Positioning Hypotheses

Last researched: 2026-07-18

This document is market research, not customer or market validation. It separates current public
facts from hypotheses that still require genuine use. ScopeProof has no qualifying completed
participant case, repeat-use evidence, customer, revenue, validated buyer, or validated price. The
current external state is `waiting_for_inbound_public_alpha_submission`.

## Implemented ScopeProof workflow

ScopeProof's implemented public-alpha workflow is:

`public PR → user-confirmed criteria → deterministic candidate evidence → criterion findings →`
`reviewer decisions → export → immutable-head comparison`

The workbench and CLI keep implementation, test, runtime, and human-decision evidence distinct.
They preserve missing and partial evidence, bind a review to an exact commit SHA, and do not execute
pull-request code. These are implemented capabilities with engineering verification; they do not
prove accuracy in production, customer value, or demand.

## Verified adjacent-workflow facts

These products overlap with parts of the problem but are not assumed to be direct substitutes.
The facts below come from current official documentation.

| Adjacent workflow | Verified capability | What the source does not establish about ScopeProof |
| --- | --- | --- |
| Qase requirements and traceability | Qase links requirements to test cases. Its traceability matrix can pull external requirements from tools including GitHub, show linked and unlinked test cases, show latest execution status, flag potentially stale cases, version snapshots, and export CSV or PDF. [Qase requirements](https://docs.qase.io/en/articles/5563700-requirements) and [traceability matrix](https://docs.qase.io/en/articles/9123660-requirements-traceability-matrix) | It does not prove that ScopeProof's criterion-to-PR-candidate review is novel, better, or wanted. |
| Azure DevOps lifecycle traceability | Azure DevOps links work items with branches, commits, pull requests, builds, releases, tests, and deployments, and supports requirements-traceability reporting. [Microsoft end-to-end traceability](https://learn.microsoft.com/en-us/azure/devops/cross-service/end-to-end-traceability?view=azure-devops) | It does not validate a separate lightweight product for teams outside an integrated lifecycle suite. |
| TestRail specification-first testing | TestRail supports defining test cases before automation, mapping cases to automated scripts, uploading test results, and preserving requirement, manual-test, and automation traceability. [TestRail specification-first workflow](https://support.testrail.com/hc/en-us/articles/12609869124116-Specification-first-workflow) | It does not establish that reviewers need deterministic candidate-evidence review before formal test management. |
| GitHub Copilot code review | Copilot code review provides code feedback and suggested changes on pull requests. Its review is a comment rather than an approval or merge-blocking decision, and re-review can be requested after new pushes. [GitHub Copilot code review](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review) | It does not establish ScopeProof as a general code reviewer, and ScopeProof should not position itself as one. |

These documented capabilities support a research hypothesis that “requirements traceability”
alone may be too broad to distinguish ScopeProof. Genuine participant research must test that
positioning.

## Narrow positioning hypothesis

For a practitioner who must decide whether a public pull request has inspectable candidate evidence
for explicitly confirmed acceptance criteria, ScopeProof provides a local, deterministic,
reviewer-controlled coverage review at an immutable commit. It explains why each candidate matched,
keeps missing or ambiguous evidence visible, separates static evidence from runtime verification,
and requires the human reviewer to make the acceptance decision.

The proposed category is **pre-merge acceptance-evidence review**, not generic requirements
management, test management, lifecycle traceability, AI code review, or proof of correctness. This
category and wording are hypotheses until genuine participants recognize the job in their own work.

## ICP, user, and buyer hypotheses

### Initial ideal-customer-profile hypothesis

A small or medium product-engineering team that:

- reviews public GitHub pull requests against explicit acceptance criteria;
- has product, QA, and engineering participants crossing the intent-to-implementation boundary;
- lacks a trusted, inspectable criterion-level handoff before merge; and
- can evaluate a local public-repository workflow without private data or procurement work.

Team size, company size, regulated-industry fit, and private-repository demand are unvalidated.

### User hypothesis

The direct user may be a product manager, QA practitioner, or engineer who can confirm the criteria
and inspect the evidence matrix. Genuine sessions must determine which role experiences the
strongest recurring pain; the repository currently provides no basis for choosing one primary
persona.

### Likely-buyer hypothesis

If a team product is eventually justified, the likely buyer may be the QA or engineering leader
accountable for release confidence and review consistency. A product-operations or product leader
could instead own the problem when acceptance intent is the main failure point. No buyer has been
validated, and no procurement or budget claim is made.

## Job-to-be-done hypothesis

> Before approving a pull request—or after its head changes—help me see which confirmed acceptance
> criteria have current candidate evidence, why it matched, what evidence is missing or stale, and
> which human decisions must be revisited, without treating static code as proof that the behavior
> works.

## Differentiated-value hypotheses

The potentially differentiated combination is:

- criteria are normalized and explicitly confirmed before analysis;
- every finding cites an immutable SHA, path, line range, excerpt, and provenance or names the
  missing evidence;
- ambiguous candidates and incomplete ingestion fail closed;
- candidate strength, runtime observations, and human decisions remain separate;
- re-review compares evidence and decisions across immutable revisions; and
- the default workflow is local, deterministic, public-repository-only, and requires no paid LLM
  API.

Each item is an implemented or policy-backed property. Their value, uniqueness, and importance to
a buyer remain hypotheses.

## Current alternatives a participant may choose

A practitioner may reasonably continue with:

- a pull-request checklist or description template;
- manual comparison between acceptance criteria, the diff, and CI results;
- linked work items and tests in an integrated lifecycle suite;
- a test-management traceability matrix;
- human or AI-assisted code review; or
- a spreadsheet or release checklist maintained by the team.

ScopeProof must outperform the coordination cost of these existing habits for the narrow job. A
feature comparison cannot prove that advantage; only observed genuine use can.

## Adoption friction hypotheses

- Criteria must already be public, explicit, and confirmable by an authorized person.
- Public-repository-only scope excludes many commercial teams from the current alpha.
- Users may resist normalizing criteria before seeing a result.
- Deterministic matching may surface more unresolved work than familiar checklist workflows.
- The candidate-versus-proof boundary may feel slower than a simple “pass” signal.
- Local setup, GitHub access, and evidence review may exceed the value of one-off pull requests.
- Evaluation-only licensing may block broader adoption even if the workflow is useful.

These are risks to observe, not findings from participants.

## Trust requirements

A credible product must continue to:

- explain every verdict and every missing-evidence state;
- bind citations and review state to immutable revisions;
- never execute untrusted pull-request code in the application server;
- keep implementation, test, runtime, and human-decision evidence distinct;
- make ambiguity, truncation, retrieval failure, and stale decisions visible;
- validate saved and exported objects and preserve deterministic output;
- keep False Ready at zero in confirmed participant outcomes; and
- avoid collecting private code, credentials, confidential requirements, or customer data in the
  public alpha.

## What ScopeProof does not do

ScopeProof does not invent product requirements, prove correctness, replace QA, run pull-request
code, perform generic code review, scan for security issues, auto-fix code, manage test cases,
orchestrate releases, or provide full lifecycle traceability. The current product has no private
repository support, hosted source processing, accounts, teams, enterprise controls, billing, or
paid API dependency.

## Evidence needed to validate or reject the hypotheses

The next evidence is not another release, benchmark case, star, download, or owner rehearsal. It is
a genuine completed public-alpha review with source-owner-confirmed criteria, an exact reviewed
head SHA, a saved review, and a participant-selected outcome.

Across five completed reviews, record:

- who performed criteria confirmation, evidence review, and the final decision by role;
- the alternative workflow they would otherwise have used;
- whether the report exposed a useful, attributable gap;
- whether the result affected a review or release decision;
- time to an inspectable report and the largest friction point;
- whether the candidate-versus-proof distinction was understood; and
- whether the participant independently intends to use ScopeProof on another pull request.

Disconfirm or narrow the positioning if participants do not recognize the job, existing tools are
good enough, useful gaps are rare, the workflow costs more than manual review, or reviewers mistake
candidate evidence for correctness. Do not solve a failed hypothesis by broadening into generic
code review, security scanning, billing, or paid AI features.

## Commercial boundary

The existing USD 99 per team per month and USD 999 per team per year figures remain research-only
price anchors in the design-partner sprint. They are not active prices, an offer for sale, or
evidence of willingness to pay. Commercial discovery remains gated on genuine Stage 1 evidence and
a separate owner decision.
