# Public-alpha participant quickstart

This optional ten-minute path is for a product manager, QA practitioner, or engineer who owns or
is directly authorized to confirm requirements for a genuine public GitHub pull request.
ScopeProof is an evidence assistant, not a correctness oracle. Use public sources only; never enter
tokens, private code, customer data, secrets, or confidential material.

Submit the inbound public-alpha case form before starting locally:

https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml

The form is the only public-alpha intake. If it is not appropriate to submit a genuine public case,
use Standard review instead; do not treat a technical smoke or constructed example as alpha use.

## Install once

The commands below are the v0.2.3 post-publication install path. First check the
GitHub Releases page: https://github.com/YuzeJ21/Scope-Proof/releases.

Use the v0.2.3 asset URLs only when the GitHub Releases page shows v0.2.3 with `scopeproof-0.2.3-py3-none-any.whl` and `SHA256SUMS.txt`; otherwise, do not use an unpublished branch or candidate.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install \
  https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.2.3/scopeproof-0.2.3-py3-none-any.whl
scopeproof benchmark
scopeproof-web --host 127.0.0.1 --port 8501
```

Installation and benchmark success are setup evidence only. Stage 1 is closed as not pursued, and
this setup creates no external-evidence credit. It does not establish correctness, customer
validation, or target-repository runtime verification.

## Ten-minute path

1. **Minute 1 — qualify the case.** Confirm the PR and requirements source are public, you have
   authority to confirm the criteria, and no confidential information is involved.
2. **Minute 2 — start locally.** Run `scopeproof-web --host 127.0.0.1 --port 8501`, then enable
   **Alpha feedback session**. Standard review mode creates no participant record.
3. **Minute 3 — enter public sources.** Paste the canonical public PR URL and public HTTPS
   requirements source. Select only your role; ScopeProof does not collect names or contact data.
4. **Minute 4 — load the PR.** Confirm source authority and no confidential information, then fetch
   the PR. ScopeProof confirms public visibility from GitHub metadata; a session-only token is
   optional under Advanced source options but cannot make a private repository eligible.
5. **Minute 5 — confirm criteria.** Prepare one independently judgeable behavior per line, review
   the normalized set, and explicitly confirm it. This creates one validated local alpha case.
6. **Minute 6 — review coverage.** Run analysis and inspect every Strong candidate, Weak candidate,
   No candidate, or Analysis incomplete result and its immutable source line.
7. **Minute 7 — record decisions.** Accept, request change, reject a finding, accept an exception,
   mark out of scope, or record external verification. ScopeProof never executes PR code.
8. **Minute 8 — save the review.** Save the validated review locally so the outcome is bound to its
   exact review ID and head SHA.
9. **Minute 9 — record one outcome.** Choose found useful gap, showed only known information, or
   created friction. Add optional notes and a friction stage when relevant.
10. **Minute 10 — choose consent.** Aggregate-report and direct-quotation consent are separate and
    off by default. Submit once; keep the full local record private.

If the PR, criteria authority, public source, or confidentiality boundary cannot be confirmed, stop
the alpha session. A constructed demo or technical smoke is not participant validation.

## Optional post-review external feedback

After saving the review and recording the participant-selected outcome, read the
[30-day Design Partner Sprint](../commercialization/design-partner-sprint.md). A completed
participant may voluntarily submit the bounded
[public feedback form](https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-feedback.yml).

The feedback form records one completed-review outcome: a useful previously unknown gap,
already-known information, or material product friction, plus timing, decision impact, and reuse
intent. If the review is incomplete, do not use the completed-feedback form; stop or continue the
local Standard review without claiming an alpha outcome. The form contains no pricing question.
External commercial discovery is optional and separate from owner-led Stage 2 productization and
requires its own owner authorization. No paid product or billing is active. A form submission does
not reopen Stage 1 and does not count as customer, product, or commercial validation.
