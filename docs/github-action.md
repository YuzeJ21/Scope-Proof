# GitHub Actions starter (safe preview)

ScopeProof includes a repository-local workflow starter at
`.github/workflows/scopeproof.yml` and a copyable example at
`examples/github-actions/scopeproof.yml`.

It is deliberately a **safe preview**, not an enforcement integration:

- It runs only on `pull_request`; it never uses `pull_request_target`.
- It needs a checked-in `.scopeproof/requirements.txt`, one confirmed criterion
  per line. If it is missing, the step summary says **Needs Review** and cannot
  say Ready.
- It uses the event's head-repository fork flag to create a non-mutating plan.
  Fork PRs receive no write plan.
- For a non-fork PR with checked-in confirmed requirements, it may create or
  update one informational comment using GitHub's short-lived `github.token`.
  The pure planner supplies create/update/skip decisions and a head-SHA marker;
  fork, missing-requirements, and missing-token paths make no write request.
- `SCOPEPROOF_REQUIRED_CHECK=false` is a documented non-blocking default. Do
  not make it a required check until confirmed dogfood reviews show that the
  requirements source and evidence rules fit the repository.

The workflow's public-PR evidence command is informational and
`continue-on-error`; GitHub API limits, temporary network failures, or an
incomplete diff must remain visible for human review, not become a false pass.

## Local fixture check

The event runner does not call GitHub. To inspect its output with a saved event
payload, run:

```bash
python -m scopeproof_core.github_action_runner \
  --event-path path/to/pull_request_event.json \
  --requirements-confirmed
```

The JSON output includes the trusted event context, human-readable summary, and
the proposed comment action. It contains no token and does not mutate GitHub.
