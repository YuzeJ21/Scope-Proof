# LinkedIn Post — ScopeProof Public Alpha

## Copy-ready post

Green CI is useful. It is not the same as complete product intent.

I built ScopeProof to answer one narrow pre-merge question:

**Does this PR have auditable implementation and test evidence for the acceptance criteria a reviewer confirmed?**

ScopeProof is a local-first, deterministic evidence assistant. It does not use a paid LLM API. A reviewer first confirms normalized, atomic acceptance criteria. ScopeProof then maps candidate implementation and test evidence to each criterion, links findings to an immutable GitHub commit, and keeps partial or missing evidence visible.

Static implementation evidence is not runtime verification. Reviewers record runtime observations, decisions, and exceptions separately. ScopeProof does not execute untrusted repository code and does not replace QA or engineering review.

I am looking for product managers, QA practitioners, and engineers who own or can confirm the requirements for a genuine public pull request. If you are willing to try one supervised public-alpha review, DM me with the public PR URL and your relationship to its acceptance criteria. Please do not send private source, credentials, customer information, or confidential requirements.

Repository: https://github.com/YuzeJ21/Scope-Proof

Current release: https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.1.22

This is a deliberately constructed demo case. ScopeProof uses deterministic evidence rules and human review; it does not guarantee correctness or replace QA.

#ProductManagement #QualityAssurance #SoftwareEngineering #DeveloperTools

## Publication boundary

Post only after completing `linkedin-alpha-playbook.md`. Public repository visibility does not
grant an open-source license; ScopeProof remains available for evaluation and review under its
[use policy](../../USE_POLICY.md).
