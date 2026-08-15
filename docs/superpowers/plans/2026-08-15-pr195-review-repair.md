# PR #195 Timing and Cohort Integrity Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove contradictory timing evidence from the voluntary feedback form and make optional-discovery cohort allocation deterministic before PR #195 merges.

**Architecture:** Keep this a static strategy-and-contract repair. Repository contracts define the fail-closed timing schema and immutable cohort allocation rule; the GitHub issue form and Stage 2 packet are the only authoritative surfaces changed to satisfy those contracts.

**Tech Stack:** GitHub Issue Forms YAML, Markdown, Python 3.11+ repository contracts, pytest, Ruff.

## Global Constraints

- Stage 1 remains `closed_not_pursued_by_owner` with all five external-evidence measurements at zero.
- Stage 2 remains `owner_led_productization_active` without customer-validation claims.
- External discovery remains optional, inactive by default, and separately owner-authorized.
- Authorization alone cannot activate optional-discovery persistence or calculation. First
  implement a Pydantic-validated qualification-record model and an atomic validated storage
  boundary with regression coverage.
- Missing, ambiguous, private, malformed, or self-reported timing fails closed to `not observed`.
- ScopeProof remains an evidence assistant and never executes target-repository code.
- Preserve the unrelated untracked `.coverage 2` byte-for-byte and never stage it.

---

### Task 1: Make timing evidence internally consistent

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`

**Interfaces:**
- Consumes: the public feedback Issue Form as plain YAML text.
- Produces: one authoritative `timing_evidence` dropdown and one required
  `timing_evidence_support` field.

- [ ] **Step 1: Write the failing timing contract**

Add a focused contract next to `test_optional_external_feedback_collects_bounded_signals_without_price_research`:

```python
def test_optional_external_feedback_timing_is_single_source_and_fail_closed() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(
        encoding="utf-8"
    )
    assert "id: timing_evidence" in template
    assert "id: timing_evidence_support" in template
    for removed_id in (
        "completion_time",
        "timing_observation_status",
        "timing_observer_category",
        "timing_public_evidence_reference",
    ):
        assert f"id: {removed_id}" not in template
    for option in (
        "Not independently observed",
        '"Independently observed: under 5 minutes"',
        '"Independently observed: 5 to 10 minutes"',
        '"Independently observed: more than 10 minutes"',
    ):
        assert f"- {option}" in template
    assert "both an observer category and a specific public evidence reference" in template
    assert "fails closed to not observed" in template
    assert "cannot upgrade a Not independently observed selection" in template
```

Update the existing bounded-signals contract to require the two new IDs and reject the four old IDs.

- [ ] **Step 2: Run the timing contract and verify RED**

Run:

```bash
uv run python -m pytest tests/test_repository_contracts.py::test_optional_external_feedback_timing_is_single_source_and_fail_closed -q
```

Expected: FAIL because `timing_evidence` is absent and the four contradictory fields remain.

- [ ] **Step 3: Implement the minimal Issue Form repair**

In `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`, replace the four old timing fields with:

```yaml
  - type: dropdown
    id: timing_evidence
    attributes:
      label: Independently observed timing evidence
      description: Select one authoritative status and time band. Self-reported timing is not independently observed.
      options:
        - Not independently observed
        - "Independently observed: under 5 minutes"
        - "Independently observed: 5 to 10 minutes"
        - "Independently observed: more than 10 minutes"
    validations:
      required: true
  - type: textarea
    id: timing_evidence_support
    attributes:
      label: Independent timing support
      description: For an observed selection, include both an observer category and a specific public evidence reference. For Not independently observed, enter Not observed. Missing, ambiguous, private, or malformed support fails closed to not observed. Supporting text cannot upgrade a Not independently observed selection.
    validations:
      required: true
```

- [ ] **Step 4: Run the timing contracts and verify GREEN**

Run:

```bash
uv run python -m pytest tests/test_repository_contracts.py::test_optional_external_feedback_timing_is_single_source_and_fail_closed tests/test_repository_contracts.py::test_optional_external_feedback_collects_bounded_signals_without_price_research -q
```

Expected: 2 passed.

- [ ] **Step 5: Commit the timing repair**

```bash
git add tests/test_repository_contracts.py .github/ISSUE_TEMPLATE/public-alpha-feedback.yml
git commit -m "docs: make optional timing evidence fail closed"
```

### Task 2: Make discovery cohorts reproducible

**Files:**
- Modify: `tests/test_repository_contracts.py`
- Modify: `docs/commercialization/stage2-readiness-packet.md`

**Interfaces:**
- Consumes: the authoritative Stage 2 packet as plain text; no qualification records.
- Produces: a static contract for the canonical qualification tuple
  (`alpha_case_id`, `review_id`, `qualified_at_utc`, `feedback_issue_number`),
  `evidence_snapshot_sha256`, duplicate-session rejection, consecutive five-record cohorts,
  immutable freeze, confirmed-False-Ready invalidation exception, friction-outcome consistency,
  correction handling, and incomplete-cohort hold.

- [ ] **Step 1: Write the failing cohort contract**

Add a focused contract:

```python
def test_optional_discovery_cohorts_are_ordered_once_and_frozen() -> None:
    packet = Path("docs/commercialization/stage2-readiness-packet.md").read_text(
        encoding="utf-8"
    )
    rules = packet.split("## Optional-discovery decision rules", maxsplit=1)[1].split(
        "## Boundaries", maxsplit=1
    )[0]
    normalized = " ".join(rules.split())
    for required in (
        "alpha_case_id",
        "review_id",
        "qualified_at_utc",
        "feedback_issue_number",
        "evidence_snapshot_sha256",
        "(qualified_at_utc, feedback_issue_number) ascending",
        "positions 1–5, 6–10",
        "Freeze a cohort when its fifth member is assigned",
        "cannot reorder, replace, or repartition a frozen cohort",
        "Corrections annotate the original qualification record",
        "do not create a new cohort member",
        "Reject a new qualification record before ordering",
        "same completed session can appear in at most one cohort",
        "revalidated participant_false_ready becomes confirmed",
        "Created material product friction requires one Narrow-positive friction_category",
        "fewer than five unassigned qualifying records",
        "no optional-discovery decision is calculated",
    ):
        assert required in normalized
```

- [ ] **Step 2: Run the cohort contract and verify RED**

Run:

```bash
uv run python -m pytest tests/test_repository_contracts.py::test_optional_discovery_cohorts_are_ordered_once_and_frozen -q
```

Expected: FAIL because the packet says only “non-overlapping sets of five.”

- [ ] **Step 3: Implement the minimal packet repair**

Replace the ambiguous batching sentence with the canonical qualification record, ascending tuple,
duplicate-session rejection, consecutive positions, fifth-member freeze, non-repartition rule,
original-record correction rule, confirmed-False-Ready invalidation exception, friction-outcome
consistency, and incomplete-cohort hold from the confirmed design. Keep the existing
Stop/Pivot/Narrow/Continue precedence and the statement that discovery rules do not control
owner-led productization.

- [ ] **Step 4: Run the focused cohort and Stage 2 contracts**

Run:

```bash
uv run python -m pytest tests/test_repository_contracts.py::test_optional_discovery_cohorts_are_ordered_once_and_frozen tests/test_repository_contracts.py::test_owner_led_stage_two_strategy_preserves_zero_external_evidence -q
```

Expected: 2 passed.

- [ ] **Step 5: Commit the cohort repair**

```bash
git add tests/test_repository_contracts.py docs/commercialization/stage2-readiness-packet.md
git commit -m "docs: freeze optional discovery cohorts"
```

### Task 3: Verify, publish, review, and stop at owner handoff

**Files:**
- Verify: `.github/ISSUE_TEMPLATE/public-alpha-feedback.yml`
- Verify: `docs/commercialization/stage2-readiness-packet.md`
- Verify: `tests/test_repository_contracts.py`
- Preserve: `.coverage 2`

**Interfaces:**
- Consumes: the two green repair commits and exact PR #195 GitHub state.
- Produces: a reviewed, green owner handoff.

- [ ] **Step 1: Run exact-head local verification**

Run Ruff, all repository contracts, the complete suite with coverage, both deterministic benchmarks,
Issue Form YAML parsing, and `git diff --check`. Require 95 percent or higher combined coverage,
zero benchmark mismatches, and zero must-have False Ready outcomes.

- [ ] **Step 2: Audit and push named commits**

Verify the branch diff, commit list, remote divergence, and preserved `.coverage 2` hash. Push
`codex/stage2-readiness-packet` without force.

- [ ] **Step 3: Resolve repaired threads and monitor the exact head**

Resolve only the two review threads whose findings are satisfied. Wait for every available exact-
head check and review to become terminal. Repair any newly confirmed in-scope Critical or Important
finding test-first and repeat verification.

- [ ] **Step 4: Stop at the separate owner merge decision**

When the PR is open, current, clean, mergeable, reviewed, and green, hand it back to the owner for a
separate merge decision. Do not merge from this reusable plan. A later explicit owner authorization
may direct a separate execution to merge and verify resulting `main`.

- [ ] **Step 5: Report the handoff**

Report the PR URL, exact head/base, check conclusions, local verification, preserved `.coverage 2`
proof, the owner merge decision required, and remaining separately owner-gated actions.
