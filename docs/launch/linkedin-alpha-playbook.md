# ScopeProof LinkedIn Public-Alpha Playbook

This playbook turns the copy-ready post into a truthful, privacy-safe recruitment path. The owner
publishes the post and sends every LinkedIn message manually. Do not automate outreach, scrape
profiles, create synthetic participants, or report an outcome that a real participant did not
provide.

## Publish the image-led post

1. Open a new LinkedIn post and choose visibility **Anyone**.
2. Upload `docs/assets/scopeproof-linkedin-alpha.png` as the post image.
3. Add the alt text below to the image.
4. Paste only the body under `Copy-ready post` from `linkedin-draft.md`.
5. Confirm that the repository URL, `v0.1.22` release URL, DM call to action, and required demo
   disclosure are present. Because the image is the post media, keep the two URLs in the text and
   do not rely on a link-preview card.
6. Complete the pre-publication checklist below, then publish manually.
7. If the post is visible publicly, add it to the LinkedIn profile's Featured section when that
   feature is available on the owner's profile.

LinkedIn's current image-post guidance supports alt text and recommends a 1080-pixel image width;
the prepared square image is 1200x1200. LinkedIn currently limits ordinary post text to 3,000
characters. Recheck LinkedIn's current help pages before publishing if the platform changes:

- https://www.linkedin.com/help/linkedin/answer/a527229
- https://www.linkedin.com/help/linkedin/answer/a525301
- https://www.linkedin.com/help/linkedin/answer/a548496

## Image alt text

> ScopeProof public-alpha card. A requirement-to-evidence matrix shows evidence found, partial
> evidence, and missing evidence. The headline says that green CI is not the same as complete
> product intent. The image is labeled as a deliberately constructed demo.

## Asset provenance

| Final asset | Export | Provenance |
| --- | --- | --- |
| `docs/assets/scopeproof-linkedin-alpha.png` | PNG, 1200x1200 | An abstract, text-free matrix background was created with built-in ImageGen. All visible copy, status labels, disclosure text, dimensions, and layout were applied deterministically and then inspected at original resolution. |

The matrix is an abstract visual motif, not a captured participant case or an exact application
screenshot. The asset contains no customer data, testimonial, product metric, or validation result.

## First-response DM

Send this only after a person contacts the owner:

> Thanks for offering to try ScopeProof. Before we continue, please share only public information:
> the public PR URL, how you are connected to its requirements, and where the acceptance criteria
> are publicly documented. Please do not send private code, credentials, customer information, or
> confidential requirements. I will confirm the case is in scope before asking you to do anything
> else.

## Qualification record

Record only the minimum public information needed to route the request. Do not copy unrelated
profile data into the repository.

- **Public PR URL:** A reachable GitHub pull request in a public repository.
- **Source-owner confirmation:** The participant owns the requirements or is explicitly able to
  confirm the acceptance criteria used for the review.
- **Public criteria:** A public requirements source exists, or the source owner can confirm the
  normalized atomic criteria before analysis.
- **No confidential information:** The participant confirms that the PR, requirements, and
  evidence being discussed are public and contain no secrets or confidential material.

All four conditions must be explicit before a case can count as confirmed public-alpha dogfood.
If any answer is unclear, ask one narrow follow-up question; do not infer consent or authority.

## Routing

### Accept for supervised public-alpha review

Use this route only when every qualification field is satisfied:

> This case is in scope for a supervised ScopeProof public-alpha review. I will normalize the
> public acceptance criteria first and send them back for your confirmation before analysis. The
> review maps static implementation and test evidence; it does not execute the PR, prove runtime
> behavior, guarantee correctness, or replace QA. No paid LLM API is involved.

Follow the confirmed-dogfood protocol in `docs/dogfood/public-pr-protocol.md`. Record the
participant's own outcome without improving, generalizing, or inventing it.

### Technical smoke only

Use this route when the PR is public but Source-owner confirmation or Public criteria is missing:

> The public PR can be considered for a technical workflow smoke check, but it cannot count as
> confirmed product validation without a source owner who can confirm the acceptance criteria.
> Any smoke result would show only that the workflow ran; it would not establish usefulness,
> correctness, runtime verification, or external validation.

### Decline

Decline when the repository or requirements are private, confidential information may be present,
the sender cannot authorize the criteria, or the requested work falls outside ScopeProof's narrow
requirement-to-evidence workflow:

> Thank you for offering. I cannot use this case because ScopeProof's public alpha accepts only
> public pull requests with source-owner-confirmed acceptance criteria and no confidential
> information. Please do not send private source or credentials. I will not retain the case as
> validation evidence.

## Optional 60-second follow-up video

Use `demo-script.md` only after the image post is live and the owner wants a follow-up demonstration.

1. Record only the bundled deliberately constructed CSV-export demo.
2. Keep the full capture between 45 and 60 seconds; show the requirement, confirmed criteria,
   evidence matrix, a Missing detail, and the Blocked verdict.
3. Display the required disclosure on screen and repeat it in the post text.
4. Add accurate captions and review them manually before publishing.
5. Do not show browser tabs, notifications, tokens, private repositories, participant data, or
   local filesystem paths.
6. Do not describe the demo as a customer case, external validation, runtime proof, or an actual
   production incident.
7. Recheck LinkedIn's current video specifications before upload:
   https://www.linkedin.com/help/linkedin/answer/a7174587

## Pre-publication checklist

- [ ] The image is `scopeproof-linkedin-alpha.png`, is legible, and includes the constructed-demo
      boundary.
- [ ] The post body is no more than 3,000 characters.
- [ ] The repository and `v0.1.22` release links resolve publicly.
- [ ] The exact required demo disclosure is present.
- [ ] The CTA says `DM me`; no automated outreach or email is enabled.
- [ ] No customer name, private source, secret, usage metric, testimonial, or unconfirmed result is
      present.
- [ ] No adoption, production accuracy, runtime correctness, or market-validation claim is made.
- [ ] The image alt text is added.
- [ ] A human reviews the final LinkedIn preview before selecting Post.

## Results-log boundary

The public post itself is not validation. A like, impression, profile view, repository star, or
unqualified DM is not product evidence. Record a result only after a real participant completes
the documented protocol, and distinguish these outcomes:

- qualified interest;
- criteria confirmed;
- analysis completed;
- participant outcome received;
- declined or withdrawn.

Attribute every recorded statement to its actual public source or participant record. Preserve
negative and incomplete outcomes. Never convert Technical smoke only into product validation, and
never invent a quote, metric, participant, acceptance criterion, or result.
