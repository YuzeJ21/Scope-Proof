# R-003 static retrieval holdout design

Status: design complete; cohort generation and labels require a separate bounded owner approval.
No R-003 case has been selected, labelled, scored, or described as validation.

## Decision

R-003 will be a 20-case, public, deterministic, static holdout drawn from the same immutable
SWE-bench Verified source pin as R-002. It will evaluate only narrow retrieval changes justified
by constructed regression fixtures. It will not execute target-repository code, change gates, or
advance Stage 1.

R-002 is a seen diagnostic cohort and must never be used as the holdout. Its inputs, labels,
result, and score remain frozen.

## Outcome-blind cohort selection

Before reading ScopeProof output, criteria, patches, test names, or relevance labels:

1. Validate the exact R-002 source revision, Parquet byte length, SHA-256, schema, 500 rows,
   12 repositories, and 500 unique instance IDs.
2. Exclude all 20 R-002 instance IDs.
3. Give every repository one R-003 case.
4. Give eight additional slots to repositories ordered by remaining case count descending and
   repository name ascending.
5. Within each repository, order eligible rows by
   `SHA256("ScopeProof:R-003:<pinned-file-sha256>:<instance_id>")`.
6. Take the repository quota, order the 20 selected rows by repository and instance ID, and assign
   `R003-001` through `R003-020`.
7. Freeze a redacted source manifest containing only validated public identities, SHAs, bounded
   factual metadata, and content hashes. Raw source bodies remain ignored locally.

The domain-separated selector prevents accidental reuse of the R-002 ordering and is fixed before
any product result is available.

## Independent criteria and labels

R-003 preserves the R-002 two-pass authority boundary:

1. Read only each pinned problem statement and draft atomic benchmark-owner criteria.
2. Freeze source spans, criterion text, priority, type, and required evidence level.
3. Obtain explicit batch owner confirmation before opening patches or generating ScopeProof
   output.
4. Only then create the complete candidate-line universe from validated implementation and test
   diffs.
5. Label every criterion-line pair without inspecting ScopeProof retrieval.
6. Obtain a second explicit batch owner confirmation for the complete label set.
7. Only after both confirmations, run the current baseline and any proposed narrow variant.

Benchmark-owner confirmation is not source-owner confirmation. All records remain
`public_engineering_research`, execute no target code, and contribute zero Stage 1 credit.

## Evaluation contract

A proposed retrieval change is eligible for R-003 only when a constructed fixture first
demonstrates the defect and the change is limited to exact identifiers, bounded paths, file roles,
evidence types, or local context. The comparison must report:

- criterion candidate coverage and labelled-candidate precision with numerators and denominators;
- zero must-have False Ready outcomes;
- zero immutable-reference errors;
- zero implementation/test separation errors;
- deterministic byte-equivalent reruns;
- complete missing-evidence explanations;
- unchanged gate precedence and evidence levels.

No threshold is selected from R-002 or R-003 results. A failed or neutral holdout remains an
engineering result, not a reason to weaken the gate.

## Unsupported approaches

R-003 will not add embeddings, LLM verdicts, semantic claims, generic code review, security
scanning, automatic fixes, repository cloning, patch application, Docker, target dependency
installation, or target test execution.

## Approval packet

The next bounded owner decision is:

> Approve outcome-blind generation of the 20-case R-003 source manifest and a problem-statement-
> only criterion proposal under this design. This does not approve criteria, labels, scoring,
> publication, or any retrieval change.

If approved, criterion confirmation and label confirmation remain two later explicit gates. Until
then, R-003 status is `awaiting_owner_approval_before_cohort_generation`.

## Self-review

- Selection is specified before output and excludes the entire seen R-002 cohort.
- Criteria and labels are frozen before scoring.
- Source-owner and benchmark-owner authority are not conflated.
- The design cannot generate customer, runtime, acceptance, or Stage 1 evidence.
- No paid service or target-code execution is introduced.
- The only open decision is explicit and bounded; no scoring can occur accidentally.
