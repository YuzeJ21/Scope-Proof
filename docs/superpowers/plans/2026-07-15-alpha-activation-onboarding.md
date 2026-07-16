# ScopeProof Alpha Activation and Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a privacy-safe participant kit, Pydantic-validated local alpha-case workflow, and a
guided real-public-PR path in the local workbench.

**Architecture:** Keep alpha evidence contracts and storage in a new `scopeproof_core.alpha`
package. Expose them through nested CLI commands, while Streamlit provides only qualification and
navigation guidance and continues to use the existing review engine and persistence.

**Tech Stack:** Python 3.11+, Pydantic v2, argparse, Streamlit, pytest, Streamlit AppTest.

## Global Constraints

- Public GitHub pull requests only.
- No paid or LLM API, billing, private repository, automated outreach, email, GitHub comments,
  synthetic participants, or invented evidence.
- Every persisted alpha object is Pydantic validated with `extra="forbid"`.
- No participant name, email, profile, or DM content field.
- Criteria remain user-confirmed before analysis.
- Static candidates never become runtime verification.
- Report and quote consent are separate and false by default.

---

### Task 1: Define alpha-case contracts

**Files:**
- Create: `scopeproof_core/alpha/__init__.py`
- Create: `scopeproof_core/alpha/models.py`
- Create: `tests/alpha/test_models.py`

**Interfaces:**
- Produces: `ParticipantRole`, `AlphaOutcome`, `AlphaFrictionStage`,
  `AlphaPublicationConsent`, `AlphaQualification`, `AlphaCaseRecord`, and
  `AlphaCasePublicSummary`.

- [ ] **Step 1: Write failing model tests**

Add tests that construct a valid record and reject extra fields, non-GitHub PR URLs, HTTP
requirements sources, false confidentiality confirmation, blank/duplicate criteria, outcome
without review linkage, friction without a stage, non-friction with a stage, and completion fields
without an outcome. Require consent defaults to false and require the model schema to contain no
`name`, `email`, `profile`, or `dm` field.

```python
def test_alpha_record_requires_explicit_public_safe_qualification() -> None:
    with pytest.raises(ValidationError):
        AlphaCaseRecord(
            public_pr_url="https://github.com/acme/repo/pull/7",
            requirements_source_url="http://example.test/ticket/7",
            participant_role=ParticipantRole.QA,
            source_owner_confirmed=True,
            no_confidential_information=True,
            confirmed_criteria=["Export CSV"],
        )
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest -q tests/alpha/test_models.py`

Expected: import failure because `scopeproof_core.alpha.models` does not exist.

- [ ] **Step 3: Implement the Pydantic contracts**

Use string enums, strict booleans via `Literal[True]`, bounded text fields, HTTPS validation, and
one model-level transition validator. Generate case IDs as `alpha-` plus a UUID hex value.

```python
class AlphaOutcome(StringEnum):
    FOUND_USEFUL_GAP = "found_useful_gap"
    SHOWED_ONLY_KNOWN_INFORMATION = "showed_only_known_information"
    CREATED_FRICTION = "created_friction"


class AlphaPublicationConsent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report: bool = False
    quote: bool = False
```

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest -q tests/alpha/test_models.py`

Expected: all model tests pass.

- [ ] **Step 5: Commit**

Commit as `feat: define validated alpha case records`.

### Task 2: Add safe local alpha-case storage and transitions

**Files:**
- Create: `scopeproof_core/alpha/service.py`
- Create: `scopeproof_core/alpha/storage.py`
- Create: `tests/alpha/test_service.py`
- Create: `tests/alpha/test_storage.py`

**Interfaces:**
- Consumes: Task 1 models.
- Produces: `initialize_alpha_case`, `record_alpha_outcome`, `public_alpha_summary`,
  `JsonAlphaCaseStore`, and `default_alpha_case_directory`.

- [ ] **Step 1: Write failing service tests**

Require initialization to preserve public qualification, outcome recording to return a new model
with review ID/head SHA/outcome/completed time, and public-summary export to fail without report
consent and omit local notes even with consent.

```python
def test_public_summary_requires_report_consent(valid_completed_case) -> None:
    with pytest.raises(ValueError, match="report publication consent"):
        public_alpha_summary(valid_completed_case)
```

- [ ] **Step 2: Write failing storage tests**

Require save/load validation, no silent overwrite, explicit same-case update, sorted case IDs,
rejection of unsafe IDs, rejection of symlink roots, and failure on malformed JSON.

- [ ] **Step 3: Verify RED**

Run: `python3 -m pytest -q tests/alpha/test_service.py tests/alpha/test_storage.py`

Expected: import failures for service and storage.

- [ ] **Step 4: Implement transitions and store**

`record_alpha_outcome` must use `model_copy(update=...)` followed by
`AlphaCaseRecord.model_validate(...)`. `JsonAlphaCaseStore.update` must require the stored and
incoming `case_id` to match and must write a fully validated JSON document.

- [ ] **Step 5: Verify GREEN and regression**

Run: `python3 -m pytest -q tests/alpha tests/storage`

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

Commit as `feat: store local alpha case evidence`.

### Task 3: Add nested alpha CLI workflow

**Files:**
- Modify: `scopeproof_core/cli.py`
- Modify: `tests/cli/test_cli.py`

**Interfaces:**
- Consumes: Task 2 services and store.
- Produces: `scopeproof alpha init`, `scopeproof alpha outcome`, and `scopeproof alpha show`.

- [ ] **Step 1: Write failing CLI tests**

Use temporary requirements/notes files. Assert init creates one validated record, outcome updates
that record with the reviewed SHA, normal output includes local notes, public summary refuses
without report consent, and public summary omits notes after consent. Assert parser errors for a
missing confidentiality flag and friction without a stage.

```python
assert main([
    "alpha", "init", "--pr", "https://github.com/acme/repo/pull/7",
    "--requirements-source", "https://github.com/acme/repo/issues/6",
    "--participant-role", "qa", "--requirements", str(requirements),
    "--confirmed-no-confidential-information", "--storage-dir", str(store),
]) == 0
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest -q tests/cli/test_cli.py -k alpha`

Expected: argparse rejects the missing `alpha` command.

- [ ] **Step 3: Implement command handlers and parser**

Add `_alpha_init`, `_alpha_outcome`, and `_alpha_show`. Read criteria and notes from UTF-8 files,
never command-line free text. Print sorted JSON and route expected OSError/ValueError/Pydantic
errors through the existing parser error boundary.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest -q tests/cli/test_cli.py`

Expected: all CLI tests pass.

- [ ] **Step 5: Commit**

Commit as `feat: add alpha evidence CLI workflow`.

### Task 4: Publish the participant kit

**Files:**
- Create: `docs/alpha/participant-quickstart.md`
- Create: `docs/alpha/public-pr-qualification-checklist.md`
- Create: `docs/alpha/acceptance-criteria-confirmation-template.md`
- Create: `docs/alpha/outcome-form.md`
- Modify: `docs/dogfood/public-pr-protocol.md`
- Modify: `README.md`
- Modify: `tests/test_repository_contracts.py`

**Interfaces:**
- Consumes: Task 3 CLI commands.
- Produces: a ten-minute participant path and exact copy-ready templates.

- [ ] **Step 1: Add failing repository contracts**

Require all four files, the four qualification fields, exact three outcome values, separate report
and quote consent, no-private-data wording, all three CLI command examples, and links from README
and the dogfood protocol.

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest -q tests/test_repository_contracts.py -k alpha_participant`

Expected: missing-file failure.

- [ ] **Step 3: Write the participant documents**

Keep the quickstart to ten numbered minutes. Include one criterion per line, the exact source-owner
confirmation, commands with placeholder public URLs, the outcome form, and explicit refusal to
collect names, emails, private source, tokens, customer data, or confidential requirements.

- [ ] **Step 4: Verify GREEN and wording**

Run: `python3 -m pytest -q tests/test_repository_contracts.py`

Then search the new docs for private-repository, correctness, customer, adoption, and validated
claims; every occurrence must be a limitation or prohibition.

- [ ] **Step 5: Commit**

Commit as `docs: add alpha participant kit`.

### Task 5: Guide the real-public-PR path in Streamlit

**Files:**
- Modify: `apps/web/app.py`
- Modify: `tests/apps/test_streamlit_app.py`

**Interfaces:**
- Consumes: Task 1 qualification model and Task 4 quickstart path.
- Produces: preflight-gated confirmed-alpha fetch, technical-smoke alternative, five-stage cue,
  source-owner confirmation cue, copyable next actions, and Outcome guidance.

- [ ] **Step 1: Write failing AppTest contracts**

Assert the five-stage string is visible on first load; confirmed-alpha fetch is disabled until
four preflight inputs are satisfied; technical smoke is labeled not product validation; criteria
confirmation states source-owner responsibility; analyzed demo renders recommended action in a
code block; Summary exposes exactly the three alpha outcomes and links the quickstart.

- [ ] **Step 2: Verify RED**

Run the new AppTest names individually and require assertion failures for missing widgets/copy.

- [ ] **Step 3: Implement minimal UI guidance**

Add a `Review path` radio, a real-alpha preflight expander, session-only inputs, and an
`AlphaQualification` validation attempt. Keep demo loading independent. For technical smoke,
allow public PR fetch only after public/no-confidential confirmation and show the limitation.

Render the stable five-stage cue near the top. Add explicit source-owner copy beside the existing
Confirm criteria button. Keep the existing `st.info(recommended_action)` and add a code block with
the same deterministic text. Add an Outcome section after Summary with the three values and CLI
recording pattern; do not write alpha records from Streamlit.

- [ ] **Step 4: Verify GREEN and full AppTest**

Run: `python3 -m pytest -q tests/apps/test_streamlit_app.py`

Expected: all AppTests pass without widget-state warnings.

- [ ] **Step 5: Commit**

Commit as `feat: guide confirmed public alpha reviews`.

### Task 6: Verify the complete activation slice

**Files:**
- Verify only.

- [ ] Run Ruff on all Python files.
- [ ] Run full pytest with the repository's 95 percent coverage gate.
- [ ] Run the deterministic benchmark and require 12 cases, 13 criteria, zero mismatches, zero
      false blockers, and zero must-have False Ready.
- [ ] Run `pip check`, build/install the wheel, exercise all new alpha CLI commands from the
      installed wheel, and verify the installed workbench health endpoint.
- [ ] Run `git diff --check` and review the slice for Critical or Important findings.

