# LinkedIn Draft — Review Before Posting

## Draft

I built ScopeProof, a local-first tool for a narrow question before merge:

**Does this PR have auditable implementation and test evidence for the
user-confirmed acceptance criteria?**

It does not use a paid LLM API. A reviewer confirms atomic criteria, ScopeProof
maps deterministic candidate evidence to immutable GitHub commit links, and it
keeps missing or partial evidence visible instead of turning it into a confident
pass. Reviewers can record decisions, exceptions, and manually supplied runtime
observations separately from static code evidence.

The current demo is deliberately constructed. It shows a PR-shaped CSV-export
case where a happy path exists but other promised behavior is absent. That is a
workflow demonstration—not a customer case study, not a claim of runtime
correctness, and not a replacement for QA or engineering review.

I am looking for feedback from product, QA, and engineering teams on whether
the requirement-to-evidence workflow is useful before merge.

## Required disclosure

Add the [demo disclosure](demo-script.md#required-disclosure) verbatim to any
post containing the constructed demo. Do not publish until a reviewer checks
that no customer name, private source, usage metric, or unconfirmed finding was
added.
