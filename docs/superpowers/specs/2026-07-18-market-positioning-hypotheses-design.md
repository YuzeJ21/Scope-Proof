# ScopeProof Market Positioning Hypotheses Design

## Status and evidence boundary

This is a research design for a documentation-only commercialization-readiness slice. It does not
establish a market category, customer demand, willingness to pay, competitive superiority, or
Stage 1 advancement. ScopeProof remains at
`waiting_for_inbound_public_alpha_submission`.

## Problem

ScopeProof's current documentation explains the product and its evidence boundaries, but it does
not give a source-backed account of the adjacent tools a practitioner may already use. Without
that account, “acceptance coverage” can be mistaken for broad requirements traceability, test
management, or generic AI code review. That ambiguity makes the commercialization hypothesis
harder to test and creates an overclaim risk.

## Considered approaches

### 1. Broad competitor feature scorecard

Compare many vendors across a large feature grid. This looks comprehensive but would become stale
quickly, invites unsupported equivalence, and overweights features ScopeProof is not trying to
build.

### 2. Adjacent-alternatives map — selected

Use current official documentation to describe a few adjacent workflows, then state the narrower
ScopeProof job as a falsifiable hypothesis. This provides enough market context without declaring
the products direct substitutes or claiming superiority.

### 3. Persona-specific campaign positioning

Write separate messages for product managers, QA practitioners, and engineers. This is premature
before genuine alpha evidence shows who feels the problem, uses the output, and influences a
purchase decision.

## Selected design

Create `docs/commercialization/market-positioning-hypotheses.md` with five explicit layers:

1. current product and validation state;
2. verified facts from official Qase, Microsoft, TestRail, and GitHub documentation;
3. ScopeProof's implemented workflow, supported by repository documentation and tests;
4. ICP, job-to-be-done, differentiated-value, likely-user, and likely-buyer hypotheses;
5. adoption risks, trust requirements, falsification questions, and evidence gates.

Link the document from `README.md` and the Stage 2 roadmap section. The links make the research
discoverable; they do not convert hypotheses into product or market claims.

## Positioning hypothesis

For product, QA, and engineering practitioners who must inspect whether a public pull request has
candidate evidence for explicitly confirmed acceptance criteria, ScopeProof provides a local,
deterministic, reviewer-controlled requirement-to-evidence review at an immutable commit. It keeps
missing, partial, ambiguous, and stale evidence visible and separates candidate evidence from
runtime verification and human acceptance.

This is narrower than lifecycle traceability, test management, or generic code review. The
hypothesis is useful only if genuine practitioners can understand the boundary, reach an
inspectable report quickly, find a decision-relevant gap, and choose to use it again.

## Non-goals

- Do not rank competitors or claim feature superiority.
- Do not quote or infer vendor pricing.
- Do not add billing, paid APIs, accounts, private-repository support, or integrations.
- Do not change product code, evidence rules, gates, schemas, persistence, or exports.
- Do not claim a validated ICP, buyer, demand signal, or willingness to pay.

## Acceptance criteria

- Every external capability statement links to an official vendor source.
- Verified facts and ScopeProof hypotheses are visibly separated.
- The document names current alternatives, adoption friction, trust requirements, users, and a
  likely-buyer hypothesis.
- The document states what ScopeProof does not do.
- The next evidence needed is a genuine completed public-alpha review, not more internal activity.
- README and roadmap links describe the document as research, not validation.
- Repository contracts, link checks, lint, and diff hygiene pass.
