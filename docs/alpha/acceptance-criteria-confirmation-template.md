# Acceptance-criteria confirmation template

Create a plain-text `requirements.txt` file with one criterion per line. Each line should state one observable, source-owner-confirmed requirement.

```text
The export includes a CSV file.
An empty result shows a clear next action.
The error state preserves the user's entered criteria.
```

Before analysis, confirm:

- Every line comes from the linked public requirement source.
- You have not inferred new requirements from the implementation.
- Each criterion is atomic enough to receive its own evidence verdict.
- The file contains no confidential or private material.

Do not ask ScopeProof to invent, broaden, or silently normalize product intent. The participant must confirm the normalized criteria first.
