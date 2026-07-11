# ScopeProof 60-Second Demo Script

## On-screen setup

Use the bundled deliberately constructed CSV export demo. Do not describe it as a real incident.

## Script

0–5 seconds: show the requirement source.

> The PR passed CI. Did it build every product behavior the requirement promised?

5–15 seconds: show the confirmed atomic criteria.

> ScopeProof keeps the requirements user-confirmed, then reviews one criterion at a time.

15–35 seconds: show the evidence matrix.

> The export implementation and a happy-path test are candidates. But the active-filter behavior is partial, and the error and analytics requirements have no candidate evidence.

35–50 seconds: expand a Missing detail.

> Each finding links to an immutable head SHA, explains why it matched, and says what evidence is still missing.

50–60 seconds: show the Blocked verdict and HTML report.

> ScopeProof does not replace QA or claim correctness. It makes the gap between product intent and implementation evidence auditable before merge.

## Required disclosure

Include this text in any public post or recording:

> This is a deliberately constructed demo case. ScopeProof uses deterministic evidence rules and human review; it does not guarantee correctness or replace QA.
