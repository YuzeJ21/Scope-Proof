# Evidence-Level Guidance Design

## Context

A clean-installed v0.1.15 browser audit reproduced a first-use comprehension gap. During criteria
confirmation, each criterion exposes `Required evidence` values E1, E2, and E3 without defining
them. The evidence matrix later displays and filters E0 through E4 without a legend. The README
defines the levels, but a reviewer should not have to leave the active workflow to understand a
setting that affects evidence sufficiency.

The audit evidence is saved under
`/Users/yjian070/.codex/visualizations/2026/07/13/scopeproof-v0.1.15-first-use-audit`.
The same audit confirmed that the workflow status, confirmation gate, provisional wording,
criterion detail, and recovery guidance are healthy.

## Decision

Add two concise captions using the existing Streamlit typography and spacing:

1. Under `2 · Confirm Criteria`, when criteria exist:

   > Evidence levels set the minimum proof needed for each criterion: E1 = implementation or
   > contract candidate; E2 = test candidate; E3 = manually recorded runtime verification. Static
   > PR analysis can produce only E1 or E2.

2. Under `3 · Evidence Matrix`, when analysis exists:

   > Evidence levels: E0 = no candidate found; E1 = implementation or contract candidate; E2 = test
   > candidate; E3 = manually recorded runtime verification; E4 = explicit human acceptance.
   > Levels describe evidence type, not correctness.

The captions define the existing schema contract without adding a new component, tooltip pattern,
or navigation path. The criteria caption appears only when a criterion set is available; the matrix
caption appears only with analyzed findings.

Because v0.1.15 has now been published, the same branch changes the single source version to
`0.1.16.dev0`. README continues to install the verified v0.1.15 wheel. This prevents subsequent
source builds and new local reviews from impersonating the public release.

## Alternatives Considered

### 1. Recommended: concise captions at both decision surfaces

The definitions are visible at the point of use, keyboard-neutral, and consistent with existing
caption guidance around runtime evidence and final acceptance.

### 2. Repeat a help tooltip on every evidence dropdown

Rejected because it duplicates the same copy for every criterion and hides essential semantics
behind pointer or focus interaction.

### 3. Add an expandable evidence-level reference panel

Rejected because the content is short and foundational. Collapsing it would preserve the current
discoverability problem and add unnecessary interaction.

## Behavior and Boundaries

- EvidenceLevel values, ranks, and allowed choices remain unchanged.
- Static retrieval still produces only E1 implementation/contract candidates and E2 test
  candidates.
- E3 and E4 remain human-supplied evidence levels under the existing runtime/resolution contracts.
- The captions do not claim that a level proves correctness, test execution, runtime behavior, or
  final acceptance.
- No persisted or exported object changes, so no schema migration is needed.
- No gate, scoring, retrieval, confirmation, final-acceptance, or workflow-state behavior changes.
- No paid API, billing, private repository, fork test, external service, or untrusted-code execution.

## Verification

- AppTest first fails because the captions are absent from criteria and analyzed matrix states.
- Focused AppTest then proves both exact captions appear at the intended states.
- Existing criteria, matrix-filter, runtime-evidence, resolution, and summary tests remain green.
- Ruff, the complete offline suite, deterministic benchmark, diff check, clean-wheel identity,
  installed benchmark, and packaged health smoke pass.
- A live browser reruns the demo flow and captures the criteria and matrix states. Before and after
  screenshots are inspected together to verify hierarchy, wrapping, and unchanged controls.

The browser demo and AppTest remain controlled product evidence, not external PR validation or
runtime evidence for a reviewed pull request.
