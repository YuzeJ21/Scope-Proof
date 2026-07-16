# Public-alpha participant quickstart

This ten-minute path is for a product manager, QA practitioner, or engineer who owns the requirements for a genuine public GitHub pull request. ScopeProof is an evidence assistant, not a correctness oracle. It does not replace QA, run repository code, or prove that a change is correct.

Use public sources only. Do not paste tokens, private repository content, customer data, secrets, or confidential material.

## Ten-minute path

1. **Minute 1 — qualify the case.** Confirm the pull request is public, you are the source owner for its requirements, and the case contains no confidential material. Use the [qualification checklist](public-pr-qualification-checklist.md).
2. **Minute 2 — open the requirement source.** Keep the public HTTPS ticket, issue, PRD, or acceptance-criteria URL beside the pull request.
3. **Minute 3 — normalize the criteria.** Copy only the requirements you confirm into `requirements.txt`, one criterion per line, using the [confirmation template](acceptance-criteria-confirmation-template.md).
4. **Minute 4 — initialize local evidence.** Run:

   ```bash
   scopeproof alpha init --pr PR_URL --requirements-source REQUIREMENTS_URL --participant-role qa --requirements requirements.txt --source-owner-confirmed --confirmed-no-confidential-information
   ```

5. **Minute 5 — run the review.** Run `scopeproof review --pr PR_URL --requirements requirements.txt --report scopeproof-review.md` and retain its printed review ID and reviewed head SHA.
6. **Minute 6 — inspect evidence.** Check every criterion verdict and its cited file or explicit missing-evidence statement. Implementation evidence is not test or runtime verification.
7. **Minute 7 — make decisions.** Accept, reject, or mark findings ambiguous. ScopeProof supports the decision; you own it.
8. **Minute 8 — record the outcome.** Select exactly one value in the [outcome form](outcome-form.md), then run:

   ```bash
   scopeproof alpha outcome CASE_ID --review-id REVIEW_ID --head-sha HEAD_SHA --result found_useful_gap
   ```

9. **Minute 9 — choose publication permissions.** Report and quotation permissions are separate and off by default. Add `--report-consent` or `--quote-consent` only when you explicitly agree.
10. **Minute 10 — verify the record.** Run `scopeproof alpha show CASE_ID`. Use `--public-summary` only after report consent. Keep the full local record private.

If the PR, criteria, or ownership cannot be confirmed, stop the alpha case. You may still run a clearly labeled technical smoke, but it is not user validation.
