# Participant Evidence Unblocker Design

## Problem

ScopeProof's local engineering, public-alpha kit, release, and GitHub health checks are already
passing, but repeated overnight goals keep cycling on the same external gate: no genuine public PR
participant has supplied the four required inputs for a confirmed alpha case. Continuing to rerun
maintenance checks after the repo is clean creates noise without moving the product toward real
validation.

## Goal

Add an owner-facing unblocker that redirects future Codex work away from endless monitoring and
toward the only honest next step: manually obtaining one qualified participant case, then resuming
Codex with the required public inputs.

## Scope

- Create `docs/alpha/participant-evidence-unblocker.md`.
- Link it from `docs/alpha/concierge-host-checklist.md`.
- Add a repository contract that requires the unblocker to preserve ScopeProof's no-billing,
  no-automation, no-invented-evidence, and no-noisy-GitHub boundaries.

## Non-goals

- No automated outreach, scraping, email, recurring monitor, or GitHub issue comment.
- No paid OpenAI/LLM API, billing, organization, private repository, or fork testing.
- No synthetic participant, invented PR, invented requirement, or validation claim.
- No app, CLI, schema, release, workflow, or GitHub Action behavior change.

## Design

The unblocker is a short operational document. It states why the previous overnight goal blocked,
lists the exact owner action, includes the four qualifying inputs, and provides a copy-paste Codex
resume prompt that only starts a first-alpha-case run after those inputs exist.

Future maintenance runs should use this document as the stop condition: after one clean audit with
no alerts, no open PRs, no docs drift, and no participant inputs, Codex should report
`waiting_for_external_participant_evidence` and hand back the owner action instead of creating more
monitoring churn.

## Verification

- Repository contract verifies the unblocker exists and contains the required boundaries, input
  checklist, stop condition, and resume prompt.
- Focused verification runs repository contracts after the change.
