# Inbound Alpha Intake Design

## Problem

The previous participant-evidence unblocker still asks the owner to manually contact people. The
owner does not want to manually change anything or manually perform outreach. ScopeProof needs a
public, inbound-only path where qualified participants can submit a candidate public PR themselves.

## Goal

Replace the manual-outreach default with a self-serve public intake path that collects only public,
source-owner-confirmed alpha-case candidates through GitHub Issues.

## Scope

- Add a new GitHub issue template for public-alpha case submissions before review.
- Update the public site CTA to send candidates to that issue template.
- Update the participant-evidence unblocker and concierge checklist so they prefer inbound-only
  intake and do not tell the owner to DM people manually.
- Add repository contracts that require the inbound issue template, public CTA, and no-private-data
  boundaries.

## Non-goals

- No automated outreach, scraping, email, contact harvesting, or paid acquisition.
- No paid OpenAI/LLM API, billing, organization, second account, private repository, or fork
  testing.
- No claim that an inbound submission is validation before the documented review and outcome
  workflow completes.
- No app, CLI, schema, workflow, release, or GitHub Action behavior change.

## Design

The new issue template is named `public-alpha-case.yml`. It asks for the public PR URL, public
requirements URL, authority statement, confidentiality confirmation, participant role, and expected
review question. It includes safety checkboxes that prohibit private code, credentials, customer
data, confidential requirements, synthetic validation, and constructed demo claims.

The site alpha section changes from a LinkedIn-DM instruction to an inbound issue-submission CTA.
The quickstart and qualification checklist remain linked as supporting materials.

The unblocker becomes owner-passive: after a clean audit, Codex should point to the inbound issue
template and wait for a real public submission. If a qualifying issue appears, Codex can resume the
first-alpha-case workflow using the submitted public inputs.

## Verification

- Repository contracts verify the issue template exists, is linked from the site, preserves the four
  required inputs, and prohibits private or invented evidence.
- Existing public-site contracts verify the site remains self-contained, no forms/analytics/remote
  scripts are added, and no LinkedIn link is introduced.
