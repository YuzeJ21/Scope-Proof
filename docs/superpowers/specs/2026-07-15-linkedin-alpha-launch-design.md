# ScopeProof LinkedIn Alpha Recruitment Launch Design

## Context

ScopeProof v0.1.22 is published from protected `main`, its wheel and checksum are independently
verified, and the repository is an engineering-complete public alpha. The remaining beta-entry
gap is genuine use on a public pull request with source-owner-confirmed acceptance criteria and a
recorded human outcome.

The repository already contains a truthful LinkedIn draft, a 60-second constructed-demo script,
an evidence matrix, and a 1280x720 demo screenshot. The draft does not identify v0.1.22, provide a
direct repository or release path, define one low-friction call to action, or give the owner a
repeatable process for screening and responding to volunteers.

## Audience and objective

The primary audience is product managers, QA practitioners, and engineers who own or can confirm
acceptance criteria for a genuine public GitHub pull request. The objective is to recruit a small
number of honest public-alpha participants, not to maximize impressions or imply adoption.

The primary call to action is a LinkedIn direct message. A volunteer is asked to provide only a
public PR URL, their relationship to the requirements, a public requirements source or confirmed
criteria, and confirmation that no confidential information is involved. ScopeProof must not run
the case as confirmed dogfood until the source-owner confirmation is explicit.

## Selected launch approach

Publish a problem-first image post. The post opens with the gap between green CI and product
intent, explains ScopeProof in plain language, discloses that the shown case is deliberately
constructed, links to the public repository and v0.1.22 release, and asks qualified volunteers to
send a LinkedIn DM.

A 60-second captioned demo is prepared as a follow-up path, not required for the first post. A
link-preview-only post is not selected because it demonstrates less of the workflow and provides a
weaker first-read explanation.

## Deliverables

### Final LinkedIn post

`docs/launch/linkedin-draft.md` becomes a copy-ready alpha recruitment post. It must include:

- the narrow product question;
- local-first and no-paid-LLM positioning;
- explicit reviewer confirmation of criteria;
- static evidence versus runtime-verification boundary;
- deliberately constructed demo disclosure verbatim;
- ScopeProof v0.1.22 repository and release links;
- one DM-first call to action for genuine public PRs;
- no customer, adoption, production-accuracy, runtime-correctness, or market-validation claim.

### Alpha recruitment playbook

`docs/launch/linkedin-alpha-playbook.md` contains:

- exact posting steps for an image-led post;
- copy-ready image alt text;
- a short first-response DM;
- a qualification DM covering public PR, source-owner confirmation, public criteria, and privacy;
- accepted, technical-smoke-only, and declined routing;
- a follow-up demo-post checklist;
- a pre-publication evidence and privacy checklist;
- a results log boundary that forbids invented or unattributed outcomes.

### LinkedIn visual

`docs/assets/scopeproof-linkedin-alpha.png` is a 1200x1200 PNG designed for a LinkedIn image post.
It contains a short problem hook, ScopeProof identity, public-alpha label, and a visibly disclosed
constructed-demo boundary. It must not contain invented testimonials, customer logos, usage
metrics, accuracy percentages, or claims that a PR is correct.

The graphic may use the existing evidence-matrix visual as a reference, but detailed UI text must
not be presented as an exact product screenshot unless it remains legible and faithful. The
repository's original screenshot remains the authoritative UI image.

## GitHub integration

The launch package is integrated through one protected pull request. Repository metadata is
already suitable: the repository is public, has a descriptive summary and relevant topics, and
v0.1.22 is the latest release. No issue comment, participant record, GitHub Discussion, recurring
monitor, LinkedIn post, or direct message is created by the repository change.

## Verification

Repository contracts require the current release links, exact constructed-demo disclosure,
DM-first CTA, public-PR qualification fields, prohibited-claim language, alt text, and the visual
asset's PNG signature and 1200x1200 dimensions. Full pytest, Ruff, benchmark, dependency, diff,
protected CI, and CodeQL gates remain required.

## Boundaries

No paid or LLM API, billing, organization, private repository, fork test, synthetic user,
synthetic validation, invented evidence, generic review, security-scanning product feature,
automatic fix, or open-source license is introduced. The materials do not constitute legal advice
and do not change the evaluation-only use policy.
