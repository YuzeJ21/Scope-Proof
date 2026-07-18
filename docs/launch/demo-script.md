# ScopeProof 60-Second Demo Script

## On-screen setup

Use the bundled deliberately constructed CSV export demo. Do not describe it as a real incident.

## Script

0–5 seconds: show the requirement source.

> The PR passed CI. Did it build every product behavior the requirement promised?

5–15 seconds: show the confirmed atomic criteria.

> ScopeProof keeps the requirements user-confirmed, then reviews one criterion at a time.

15–35 seconds: show the acceptance-coverage matrix.

> The export implementation and a happy-path test are Strong candidates. The active-filter behavior is a Weak candidate, while the error and analytics requirements have No candidate.

35–50 seconds: expand a No candidate detail.

> Each finding links to an immutable head SHA, explains why it matched, and says what evidence is still missing.

50–60 seconds: show Action required and the HTML report.

> ScopeProof does not replace QA or claim correctness. It makes the gap between product intent and implementation evidence auditable before merge.

## Required disclosure

Include this text in any public post or recording:

> This is a deliberately constructed demo case. ScopeProof uses deterministic evidence rules and human review; it does not guarantee correctness or replace QA.
