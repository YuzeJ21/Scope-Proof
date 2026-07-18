# Participant evidence unblocker

Use this when a ScopeProof maintenance goal keeps ending at
`waiting_for_inbound_public_alpha_submission`.

## Why the monitor stopped

ScopeProof can verify repository health, release state, public docs, workflow pins, and local
contracts. It cannot create the external evidence required for a confirmed public-alpha case. A
clean maintenance audit with no participant input is useful once; repeating it overnight does not
move the product closer to validation.

Do not start another overnight monitor for this gate after one clean audit. Start the first genuine
alpha case only after a candidate submits the required public inputs through the inbound-only public
alpha issue form:

https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml

## Owner action

Do not manually contact participants. Do not send DMs, scrape profiles, send email, create a contact
list in the repository, or follow up. Keep the owner path passive: publish or share the public site
if desired, then wait for inbound public issue submissions.

The next Codex run needs all four inputs:

- public PR URL
- public HTTPS requirements source
- explicit authority to confirm criteria
- explicit confirmation that no private or confidential information is included

If any input is missing, do not run ScopeProof as a confirmed alpha case. Route the lead as a
technical smoke, decline it, or wait for the missing public confirmation.

## Hard boundaries

- No paid OpenAI/LLM API.
- No billing, organization, second account, private repository, or fork testing.
- No automated outreach, scraping, mass messaging, or email.
- No synthetic validation, invented evidence, invented participant, invented requirement, or
  invented outcome.
- No GitHub issue comment, PR comment, release note, or notification-only update just to say the
  project is still waiting.
- No private source, tokens, credentials, customer data, private links, or confidential
  requirements.

## Resume prompt

Use this only after one real candidate supplies all four required public inputs.

```text
/goal Run ScopeProof's first genuine public-alpha case in `/Users/yjian070/Documents/New project 2`.

Inputs supplied by the owner:
- Public PR URL: <paste public GitHub PR URL>
- Public HTTPS requirements source: <paste public requirements URL>
- Criteria authority: <paste the participant's explicit authority statement>
- Confidentiality confirmation: <paste the participant's explicit confirmation that no private or confidential information is included>

Use the documented public-alpha workflow. Confirm the normalized acceptance criteria before analysis. Do not execute untrusted repository code. Do not use paid OpenAI/LLM APIs, billing, organizations, private repos, fork testing, automated outreach, scraping, synthetic validation, invented evidence, or GitHub issue/PR comments that create notification noise.

Create or update only the validated local alpha-case record allowed by the existing `scopeproof alpha` commands. Run the review against the supplied public PR and requirements only after criteria confirmation. Preserve the exact reviewed head SHA, cited evidence or missing evidence per criterion, and exactly one participant outcome: `found_useful_gap`, `showed_only_known_information`, or `created_friction`.

If any supplied input is not public, not explicit, or not enough to prove source-owner-confirmed criteria authority, stop the alpha-case run and route it as technical smoke or declined. Do not claim external validation without a completed participant outcome.
```

## What Codex should do if restarted too early

Run one clean health audit if needed, report the exact missing input, and hand back this document.
Do not create another long-running monitor when the only missing item is a real participant. Point
to the inbound-only public alpha issue form instead:

https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml
