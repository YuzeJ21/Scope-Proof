# Evaluation setup and historical public-alpha participant path

The source/package candidate is **v0.2.4**. Public install remains **v0.2.3** until a matching
[GitHub Release](https://github.com/YuzeJ21/Scope-Proof/releases) contains the v0.2.4 wheel, source
archive, and `SHA256SUMS.txt`. Use the [current evaluation quickstart](../../README.md#quickstart)
for conditional v0.2.4 installation, checksum verification, supported environments, and saved-record
v5 upgrade guidance. Before publication, use the published v0.2.3 release or explicitly choose the
[current source setup](../development-environment.md); candidate CLI commands are not v0.2.3
wheel instructions.

No personal testing, public case, qualifying review, or participant feedback is required to
download and evaluate ScopeProof. Start a local Standard review or the deliberately constructed
demo. Installation, benchmarks, and demo results are engineering evidence only; ScopeProof is an
evidence assistant, not a correctness oracle. Confirm normalized criteria before analysis; target
repository code is never executed. Use public sources only and never enter private code, customer
data, secrets, or confidential material. An optional session-only GitHub token belongs only in the
local token control and must never appear in a report.

For an ordinary problem, use the [sanitized defect form](https://github.com/YuzeJ21/Scope-Proof/issues/new?template=defect.yml)
with the version or commit, minimal safe steps, expected behavior, and actual behavior. Report
security concerns through [private vulnerability reporting](https://github.com/YuzeJ21/Scope-Proof/security/advisories/new)
and follow the [security policy](../../SECURITY.md).

Stage 1 is closed as not pursued with every external count at zero. Stage 3 is dormant and gated.
The participant path below is an archive of the published v0.2.3 workflow, not a current invitation
or an evaluation-download requirement. Optional external discovery requires separate owner
authorization under the [design-partner protocol](../commercialization/design-partner-sprint.md).

## Archived v0.2.3 public-alpha participant quickstart

This archived ten-minute path describes the published v0.2.3 participant workflow. Stage 1 is
closed as not pursued; it is not a current invitation to participate. It was written for a product
manager, QA practitioner, or engineer authorized to confirm requirements for a genuine public PR.
ScopeProof is an evidence assistant, not a correctness oracle. Use public sources only; never enter
tokens, private code, customer data, secrets, or confidential material.

The historical inbound public-alpha case form was:

https://github.com/YuzeJ21/Scope-Proof/issues/new?template=public-alpha-case.yml

The form is the only public-alpha intake. If it is not appropriate to submit a genuine public case,
use Standard review instead; do not treat a technical smoke or constructed example as alpha use.

### Install once

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

### Ten-minute path

1. **Minute 1 — qualify the case.** Confirm the PR and requirements source are public, you have
   authority to confirm the criteria, and no confidential information is involved.
2. **Minute 2 — start locally.** Run `scopeproof-web --host 127.0.0.1 --port 8501`, then enable
   **Alpha feedback session**. Standard review mode creates no participant record.
3. **Minute 3 — enter public sources.** Paste the canonical public PR URL and public HTTPS
   requirements source. Select only your role; ScopeProof does not collect names or contact data.
4. **Minute 4 — load the PR.** Confirm source authority, public visibility, and no confidential
   information, then fetch the PR. The v0.2.3 wheel did not enforce the later verified-public
   GitHub metadata rule; that safeguard is present only in the unreleased `0.2.4.dev0` source.
   A session-only token is optional under Advanced source options.
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

### Optional post-review external feedback

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
