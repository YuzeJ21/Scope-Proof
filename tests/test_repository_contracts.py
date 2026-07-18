import tomllib
from html.parser import HTMLParser
from pathlib import Path
from struct import unpack
from urllib.parse import urlsplit

from PIL import Image


def _mp4_duration_seconds(path: Path) -> float:
    data = path.read_bytes()
    marker = data.find(b"mvhd")
    assert marker >= 0, "MP4 must contain an mvhd movie header"
    version = data[marker + 4]
    if version == 0:
        timescale = unpack(">I", data[marker + 16 : marker + 20])[0]
        duration = unpack(">I", data[marker + 20 : marker + 24])[0]
    elif version == 1:
        timescale = unpack(">I", data[marker + 24 : marker + 28])[0]
        duration = unpack(">Q", data[marker + 28 : marker + 36])[0]
    else:
        raise AssertionError(f"unsupported mvhd version: {version}")
    return duration / timescale


class _PublicSiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms = 0
        self.links: list[str] = []
        self.remote_scripts: list[str] = []
        self.video_tracks: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form":
            self.forms += 1
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "script" and str(values.get("src", "")).startswith(("http://", "https://")):
            self.remote_scripts.append(str(values["src"]))
        if tag == "track":
            self.video_tracks.append(values)


def test_readme_states_product_limits() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "does not replace QA" in readme
    assert "No paid LLM API" in readme
    assert "deliberately constructed demo" in readme
    assert "public repositories only" in readme


def test_core_never_imports_streamlit() -> None:
    imports = [
        path
        for path in Path("scopeproof_core").rglob("*.py")
        if "import streamlit" in path.read_text(encoding="utf-8")
    ]
    assert imports == []


def test_project_has_no_paid_llm_runtime_dependency() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    dependencies = " ".join(project["dependencies"]).lower()
    assert "openai" not in dependencies
    assert "anthropic" not in dependencies


def test_public_docs_state_evaluation_only_use_policy() -> None:
    policy = Path("USE_POLICY.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "intentionally published without an open-source license" in policy
    assert "evaluation and review only" in policy
    assert "No additional permission is granted" in policy
    assert "GitHub Terms of Service" in policy
    assert "applicable law" in policy
    assert "warranty" in policy.lower()
    assert "correctness claim" in policy
    assert "service commitment" in policy
    assert "support obligation" in policy
    assert "repository owner" in policy
    assert "[evaluation-only use policy](USE_POLICY.md)" in readme
    assert "[evaluation-only use policy](USE_POLICY.md)" in contributing
    assert "- [x] **Software license decision:**" in roadmap
    assert not Path("LICENSE").exists()


def test_wheel_packages_use_policy_without_license_metadata() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert project["urls"]["Use Policy"] == (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md"
    )
    assert wheel["force-include"]["USE_POLICY.md"] == "scopeproof_core/USE_POLICY.md"
    assert "license" not in project
    assert "license-files" not in project
    assert not any(
        classifier.startswith("License ::") for classifier in project.get("classifiers", [])
    )


def test_python_312_ci_enforces_local_coverage_floor() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = config["project"]["optional-dependencies"]["dev"]
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    compatibility = workflow.split("  compatibility-python-311:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert "pytest-cov>=6,<7" in dev_dependencies
    assert "python -m pytest -q" in compatibility
    assert "--cov" not in compatibility
    assert "--cov=scopeproof_core" in verify
    assert "--cov=apps" in verify
    assert "--cov-report=term-missing:skip-covered" in verify
    assert "--cov-fail-under=95" in verify
    assert "codecov" not in workflow.lower()
    assert "coverage.xml" not in workflow
    assert ".coverage" in gitignore.splitlines()
    assert ".coverage.*" in gitignore.splitlines()


def test_internal_engineering_archive_has_provenance_index() -> None:
    archive = Path("docs/superpowers/README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "historical engineering records" in archive
    assert "not current product status" in archive
    assert "not runtime evidence" in archive
    assert "not adoption evidence" in archive
    assert "not a sequential user manual" in archive
    assert "[engineering archive index](docs/superpowers/README.md)" in contributing


def test_wheel_includes_bundled_benchmark_data() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]

    assert wheel["force-include"]["evals"] == "evals"
    assert list(Path("evals/fixtures").glob("*.json"))
    assert list(Path("evals/labels").glob("*.json"))


def test_ci_runs_lint_tests_and_benchmark() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m pip install --upgrade pip" in workflow
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "scopeproof_core.evals.runner" in workflow


def test_locked_development_environment_is_documented_and_verified() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    guide = Path("docs/development-environment.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    lock = Path("uv.lock").read_text(encoding="utf-8")

    assert Path(".python-version").read_text(encoding="utf-8").strip() == "3.12"
    assert 'name = "scopeproof"' in lock
    assert 'name = "streamlit"' in lock
    assert "uv sync --extra dev --locked" in guide
    assert "uv run pytest" in guide
    assert "uv run scopeproof benchmark" in guide
    assert "Streamlit 1.59.2" in guide
    assert "Streamlit 1.57.0" in guide
    assert "testing-interface regression" in guide
    assert "locked-environment:" in workflow
    assert "astral-sh/setup-uv@" not in workflow
    assert "python -m pip install uv==0.11.29" in workflow
    assert "python -m uv sync --extra dev --locked" in workflow
    assert (
        "python -m uv run python -m pytest -q tests/test_repository_contracts.py"
        in workflow
    )
    assert "python -m uv run scopeproof benchmark" in workflow
    assert "needs: [compatibility-python-311, locked-environment]" in workflow
    assert "[reproducible development environment](docs/development-environment.md)" in readme


def test_ci_avoids_duplicate_feature_branch_runs() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "on:\n  push:\n    branches: [main]\n  pull_request:\n" in workflow


def test_ci_builds_and_executes_installed_wheel() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Installed wheel smoke" in workflow
    assert "python -m pip wheel . --no-deps" in workflow
    assert "python -m pip install --force-reinstall --no-deps" in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow
    assert "from scopeproof_core import __version__" in workflow
    assert 'version("scopeproof") == __version__ == review.tool_version' in workflow
    assert "scopeproof --version" in workflow
    assert "scopeproof-web --version" in workflow
    assert "scopeproof benchmark" in workflow


def test_ci_starts_and_cleans_up_installed_web_workbench() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "setsid scopeproof-web" in workflow
    assert "STREAMLIT_SERVER_ADDRESS" not in workflow
    assert "STREAMLIT_SERVER_PORT" not in workflow
    assert "scopeproof-web --host 127.0.0.1 --port 8512" in workflow
    assert "http://127.0.0.1:8512/_stcore/health" in workflow
    assert "for attempt in $(seq 1 30)" in workflow
    assert '[ "$response" = "ok" ]' in workflow
    assert 'if ! kill -0 "$web_pid"' in workflow
    assert 'kill -- -"$web_pid"' in workflow
    assert 'wait "$web_pid"' in workflow
    assert "trap cleanup EXIT" in workflow
    assert 'cat "$web_log"' in workflow


def test_readme_documents_operating_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "streamlit run apps/web/app.py" in readme
    assert "RUN_LIVE_GITHUB_TESTS=1" in readme
    assert "scopeproof_core.evals.runner" in readme


def test_public_product_surfaces_use_reviewer_first_vocabulary() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    demo = Path("docs/launch/demo-script.md").read_text(encoding="utf-8")
    public_surfaces = "\n".join((readme, site, demo))

    assert "See which acceptance criteria have credible PR evidence" in readme
    assert "Prove the PR matches the product intent" not in public_surfaces
    assert "Alpha feedback session" in readme
    assert "GitHub Action advanced preview" in readme
    assert "Observed CI state" in readme


def test_readme_separates_release_install_from_contributor_setup() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert (
        "https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.2.0/"
        "scopeproof-0.2.0-py3-none-any.whl"
    ) in readme
    assert "scopeproof benchmark" in readme
    assert "scopeproof-web --host 127.0.0.1 --port 8501" in readme
    assert "## Contributor setup" in readme
    assert "python -m pip install -e '.[dev]'" in readme
    assert "streamlit run apps/web/app.py" in readme
    assert "scopeproof web" not in readme


def test_readme_documents_optional_release_checksum_verification() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    wheel_name = "scopeproof-0.2.0-py3-none-any.whl"

    assert f"releases/download/v0.2.0/{wheel_name}" in readme
    assert f"releases/download/v0.2.0/{wheel_name}.sha256" in readme
    assert f"shasum -a 256 -c {wheel_name}.sha256" in readme
    assert f"sha256sum -c {wheel_name}.sha256" in readme
    assert f"python -m pip install ./{wheel_name}" in readme
    assert "does not provide code-signing or product-correctness assurance" in readme


def test_project_exposes_web_launcher_without_coupling_core_to_ui() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["scripts"]["scopeproof-web"] == "apps.web.launcher:main"
    core_cli = Path("scopeproof_core/cli.py").read_text(encoding="utf-8")
    assert "streamlit" not in core_cli
    assert "apps.web" not in core_cli


def test_hatch_and_reviews_share_one_version_source() -> None:
    config = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version_source = Path("scopeproof_core/version.py").read_text(encoding="utf-8")

    assert config["project"]["dynamic"] == ["version"]
    assert "version" not in config["project"]
    assert config["tool"]["hatch"]["version"]["path"] == "scopeproof_core/version.py"
    assert '__version__ = "0.2.0"' in version_source


def test_readme_documents_confirmed_public_pr_cli_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof review --pr" in readme
    assert "--requirements requirements.txt" in readme
    assert "scopeproof export" in readme
    assert "reviewer-confirmed criteria" in readme
    assert "not required or persisted" in readme


def test_readme_documents_one_command_report_without_removing_repeat_export() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "--report scopeproof-review.md" in readme
    assert "refuses to overwrite" in readme
    assert "scopeproof export REVIEW_ID" in readme


def test_readme_documents_actual_stage_2a_durability_behavior() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "12 executable benchmark cases" in readme
    assert "criteria revisions" in readme
    assert "resolution history" in readme
    assert "Local review storage" in readme
    assert "unchanged candidate" in readme


def test_readme_documents_single_record_local_review_deletion() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof delete REVIEW_ID" in readme
    assert "Permanently delete the selected local review" in readme
    assert "Exported reports remain user-owned and are not removed" in readme
    assert "not secure erasure" in readme


def test_readme_documents_local_saved_review_discovery() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "scopeproof list" in readme
    assert "local review IDs" in readme
    assert "does not parse review contents" in readme


def test_security_policy_uses_github_private_vulnerability_reporting() -> None:
    policy = Path("SECURITY.md").read_text(encoding="utf-8")

    assert "private vulnerability report" in policy.lower()
    assert "Do not post security vulnerabilities in public issues" in policy


def test_contributing_guide_preserves_public_alpha_boundaries() -> None:
    guide = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "public repository" in guide.lower()
    assert "Do not include tokens" in guide
    assert "python -m pytest -q" in guide
    assert "private vulnerability report" in guide.lower()


def test_external_validation_runbook_permanently_excludes_fork_testing() -> None:
    runbook = Path("docs/github-action-external-validation.md").read_text(encoding="utf-8")

    assert "fork testing is permanently excluded" in runbook.lower()
    assert "optional test 3" not in runbook.lower()


def test_launch_matrix_keeps_action_as_an_advanced_preview() -> None:
    matrix = Path("docs/launch/evidence-matrix.md").read_text(encoding="utf-8")

    assert "GitHub Action advanced preview" in matrix
    assert "Trusted-base planning" in matrix
    assert "default first-use path" in matrix
    assert "successful hosted Action run" not in matrix


def test_public_docs_do_not_require_or_offer_external_fork_validation() -> None:
    public_docs = {
        "README.md": Path("README.md").read_text(encoding="utf-8"),
        "docs/privacy-readiness.md": Path("docs/privacy-readiness.md").read_text(
            encoding="utf-8"
        ),
    }
    combined = "\n".join(public_docs.values()).lower()

    assert "fork evidence required" not in combined
    assert "same-head rerun, and fork evidence" not in combined
    assert "external fork validation is optional" not in combined
    assert "fork testing is permanently excluded" in combined


def test_ci_validates_declared_minimum_python() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    compatibility = workflow.split("  compatibility-python-311:", maxsplit=1)[1].split(
        "\n  verify:", maxsplit=1
    )[0]
    verify = workflow.split("\n  verify:", maxsplit=1)[1]

    assert 'python-version: "3.11"' in compatibility
    assert "python -m pytest -q" in compatibility
    assert "python -m scopeproof_core.evals.runner" in compatibility
    assert "python -m pip wheel . --no-deps" in compatibility
    assert "scopeproof --version" in compatibility
    assert "scopeproof-web --version" in compatibility
    assert "needs: [compatibility-python-311, locked-environment]" in verify


def test_readme_documents_all_export_formats() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "`.md`, `.json`, `.csv`, or `.html`" in readme
    assert "`json`, `markdown`, `csv`, and `html`" in readme
    assert "Markdown / JSON / CSV / HTML" in readme
    assert "Markdown, JSON, CSV, and HTML exports" in readme


def test_roadmap_uses_evidence_gated_beta_stages() -> None:
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert "Five completed reviews" in roadmap
    assert "three independent practitioners" in roadmap
    assert "three public repositories" in roadmap
    assert "waiting_for_external_participant_evidence" in roadmap
    assert "source-owner-confirmed criteria" in roadmap
    assert "genuine public pull request" in roadmap
    assert "Software license decision" in roadmap
    assert "Do not create synthetic validation" in roadmap
    assert "No recurring monitor" in roadmap


def test_changelog_points_to_authoritative_release_history() -> None:
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "## Unreleased" in changelog
    assert "github.com/YuzeJ21/Scope-Proof/releases" in changelog
    assert "does not reconstruct" in changelog


def test_public_contribution_templates_preserve_evidence_boundaries() -> None:
    defect = Path(".github/ISSUE_TEMPLATE/defect.yml").read_text(encoding="utf-8")
    feedback = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(
        encoding="utf-8"
    )
    pull_request = Path(".github/pull_request_template.md").read_text(encoding="utf-8")

    assert "Do not include tokens" in defect
    assert "Reproduction" in defect
    assert "source-owner-confirmed" in feedback
    assert "constructed demo" in feedback
    assert "User-confirmed requirement" in pull_request
    assert "Static evidence is not runtime verification" in pull_request
    assert "Remaining limitations" in pull_request


def test_public_docs_link_governance_surfaces() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "[public roadmap](ROADMAP.md)" in readme
    assert "[changelog](CHANGELOG.md)" in readme
    assert "[public roadmap](ROADMAP.md)" in contributing
    assert "[changelog](CHANGELOG.md)" in contributing


def test_readme_shows_disclosed_constructed_demo_visual() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    image_path = Path("docs/assets/scopeproof-constructed-demo-evidence-matrix.jpg")

    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\xff\xd8\xff")
    assert image_path.stat().st_size > 50_000
    assert (
        "![ScopeProof deliberately constructed demo evidence matrix]"
        "(docs/assets/scopeproof-constructed-demo-evidence-matrix.jpg)"
    ) in readme
    assert "Controlled demo screenshot—not a customer case" in readme
    assert "not runtime verification or proof of correctness" in readme


def test_linkedin_alpha_launch_package_is_current_and_truthful() -> None:
    draft = Path("docs/launch/linkedin-draft.md").read_text(encoding="utf-8")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(
        encoding="utf-8"
    )
    disclosure = (
        "This is a deliberately constructed demo case. ScopeProof uses deterministic "
        "evidence rules and human review; it does not guarantee correctness or replace QA."
    )

    for required_text in (
        "https://github.com/YuzeJ21/Scope-Proof",
        "https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.0",
        disclosure,
        "DM me",
        "genuine public pull request",
        "product managers",
        "QA",
        "engineers",
    ):
        assert required_text in draft

    for required_field in (
        "Public PR URL",
        "Source-owner confirmation",
        "Public criteria",
        "No confidential information",
        "Technical smoke only",
        "Decline",
    ):
        assert required_field in playbook


def test_concierge_dm_first_outreach_is_manual_bounded_and_truthful() -> None:
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(
        encoding="utf-8"
    )

    for required_text in (
        "## DM-first outreach",
        "### Warm-contact message",
        "### Cold-contact message",
        "### One optional follow-up",
        "no sooner than seven days",
        "Do not send another message",
        "sent manually",
        "Do not automate",
        "Do not send private code",
        "genuine public PR",
        "own or are authorized to confirm",
        "No paid LLM API",
    ):
        assert required_text in playbook

    assert "I noticed your public work on [verified public project or PR]" in playbook
    assert "I know your team needs" not in playbook
    assert "ScopeProof customers" not in playbook
    assert "validated accuracy" not in playbook


def test_concierge_host_checklist_indexes_real_alpha_without_contact_data() -> None:
    checklist_path = Path("docs/alpha/concierge-host-checklist.md")
    playbook = Path("docs/launch/linkedin-alpha-playbook.md").read_text(
        encoding="utf-8"
    )
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert checklist_path.is_file()
    checklist = checklist_path.read_text(encoding="utf-8")
    for required_link in (
        "../../README.md#quickstart",
        "public-pr-qualification-checklist.md",
        "acceptance-criteria-confirmation-template.md",
        "participant-quickstart.md",
        "../dogfood/public-pr-protocol.md",
        "outcome-form.md",
    ):
        assert required_link in checklist

    for status in (
        "not_started",
        "qualified",
        "criteria_confirmed",
        "review_completed",
        "outcome_received",
        "declined",
        "withdrawn",
    ):
        assert f"`{status}`" in checklist

    prohibited_fields = (
        "participant name",
        "email address",
        "linkedin profile",
        "dm transcript",
        "contact list",
    )
    assert all(field not in checklist.lower() for field in prohibited_fields)
    assert "../alpha/concierge-host-checklist.md" in playbook
    assert (
        "[concierge host checklist](docs/alpha/concierge-host-checklist.md)"
        in roadmap
    )


def test_linkedin_alpha_visual_has_publishable_dimensions() -> None:
    image_path = Path("docs/assets/scopeproof-linkedin-alpha.png")

    assert image_path.is_file()
    assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert image_path.stat().st_size > 40_000
    with Image.open(image_path) as image:
        assert image.format == "PNG"
        assert image.size == (1200, 1200)


def test_public_alpha_participant_kit_is_safe_complete_and_actionable() -> None:
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(
        encoding="utf-8"
    )
    qualification = Path("docs/alpha/public-pr-qualification-checklist.md").read_text(
        encoding="utf-8"
    )
    criteria = Path(
        "docs/alpha/acceptance-criteria-confirmation-template.md"
    ).read_text(encoding="utf-8")
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    protocol = Path("docs/dogfood/public-pr-protocol.md").read_text(encoding="utf-8")

    assert all(f"Minute {minute}" in quickstart for minute in range(1, 11))
    assert "Alpha feedback session" in quickstart
    assert "Standard review mode creates no participant record" in quickstart
    assert "source owner" in qualification.lower()
    assert "No confidential information" in qualification
    assert "one criterion per line" in criteria.lower()
    assert "found_useful_gap" in outcome
    assert "showed_only_known_information" in outcome
    assert "created_friction" in outcome
    assert "report consent" in outcome.lower()
    assert "quotation consent" in outcome.lower()
    prohibited = ("participant name", "email address", "linkedin profile", "dm transcript")
    combined = "\n".join((quickstart, qualification, criteria, outcome)).lower()
    assert all(term not in combined for term in prohibited)
    assert (
        "[public-alpha participant quickstart](docs/alpha/participant-quickstart.md)"
        in readme
    )
    assert "docs/alpha/participant-quickstart.md" in protocol


def test_participant_evidence_unblocker_prevents_empty_monitoring_loops() -> None:
    unblocker = Path("docs/alpha/participant-evidence-unblocker.md").read_text(
        encoding="utf-8"
    )
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(
        encoding="utf-8"
    )

    assert "[participant evidence unblocker](participant-evidence-unblocker.md)" in checklist
    assert "waiting_for_external_participant_evidence" in unblocker
    assert "public PR URL" in unblocker
    assert "public HTTPS requirements source" in unblocker
    assert "explicit authority to confirm criteria" in unblocker
    assert (
        "explicit confirmation that no private or confidential information is included"
        in unblocker
    )
    assert "Do not start another overnight monitor" in unblocker
    assert "/goal Run ScopeProof's first genuine public-alpha case" in unblocker
    for forbidden in (
        "paid OpenAI/LLM API",
        "billing",
        "automated outreach",
        "scraping",
        "synthetic validation",
        "invented evidence",
        "fork testing",
        "GitHub issue comment",
    ):
        assert forbidden in unblocker


def test_inbound_alpha_case_submission_path_is_public_safe_and_owner_passive() -> None:
    template_path = Path(".github/ISSUE_TEMPLATE/public-alpha-case.yml")
    template = template_path.read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    unblocker = Path("docs/alpha/participant-evidence-unblocker.md").read_text(
        encoding="utf-8"
    )
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(
        encoding="utf-8"
    )

    issue_url = (
        "https://github.com/YuzeJ21/Scope-Proof/issues/new"
        "?template=public-alpha-case.yml"
    )
    assert "name: Public-alpha case submission" in template
    assert "title: \"[Alpha case]: \"" in template
    assert "public_pr_url" in template
    assert "public_requirements_url" in template
    assert "criteria_authority" in template
    assert "confidentiality_confirmation" in template
    assert "participant_role" in template
    assert "source-owner-confirmed acceptance criteria" in template
    assert "not a constructed demo, synthetic validation, or invented evidence" in template
    for forbidden in (
        "tokens",
        "credentials",
        "private code",
        "customer data",
        "confidential requirements",
    ):
        assert forbidden in template

    assert issue_url in site
    assert "Submit a public alpha case" in site
    assert "Use LinkedIn DM only" not in site
    assert "inbound-only" in unblocker
    assert issue_url in unblocker
    assert "Do not manually contact participants" in unblocker
    assert "Submit a public alpha case" in checklist
    assert issue_url in checklist


def test_public_pages_site_and_captioned_demo_are_truthful_and_self_contained() -> None:
    index_path = Path("site/index.html")
    styles_path = Path("site/styles.css")
    transcript_path = Path("site/demo-transcript.html")
    video_path = Path("site/assets/scopeproof-captioned-demo.mp4")
    captions_path = Path("site/assets/scopeproof-captioned-demo.vtt")
    poster_path = Path("site/assets/scopeproof-demo-poster.jpg")
    alpha_visual_path = Path("site/assets/scopeproof-linkedin-alpha.png")
    disclosure = (
        "This is a deliberately constructed demo case. ScopeProof uses deterministic "
        "evidence rules and human review; it does not guarantee correctness or replace QA."
    )

    html = index_path.read_text(encoding="utf-8")
    css = styles_path.read_text(encoding="utf-8")
    transcript = transcript_path.read_text(encoding="utf-8")
    captions = captions_path.read_text(encoding="utf-8")
    parser = _PublicSiteParser()
    parser.feed(html)

    assert html.count("<h1") == 1
    assert disclosure in html
    assert disclosure in transcript
    assert (
        "Public PR → Confirm criteria → Review coverage → Record decisions → Export"
        in html
    )
    assert "Likes, views, stars, impressions, and downloads are not product validation." in html
    assert "https://github.com/YuzeJ21/Scope-Proof" in html
    assert "https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.0" in html
    assert (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/docs/alpha/participant-quickstart.md"
        in html
    )
    qualification_url = (
        "https://github.com/YuzeJ21/Scope-Proof/blob/main/"
        "docs/alpha/public-pr-qualification-checklist.md"
    )
    assert qualification_url in parser.links
    assert "Check whether your PR qualifies" in html
    assert not any(
        urlsplit(link).hostname == "www.linkedin.com" for link in parser.links
    )
    assert "DM" in html
    assert "https://github.com/YuzeJ21/Scope-Proof/blob/main/USE_POLICY.md" in html
    assert parser.forms == 0
    assert parser.remote_scripts == []
    assert "analytics" not in html.lower()
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "clamp(2.35rem, 12vw, 3.5rem)" in css
    assert "overflow-wrap: anywhere" in css
    assert "max-width: 100%" in css
    assert ":focus-visible" in css
    assert parser.video_tracks == [
        {
            "kind": "captions",
            "src": "assets/scopeproof-captioned-demo.vtt",
            "srclang": "en",
            "label": "English",
            "default": None,
        }
    ]
    assert captions.startswith("WEBVTT\n")
    assert disclosure in captions
    assert video_path.read_bytes()[4:8] == b"ftyp"
    assert 59.9 <= _mp4_duration_seconds(video_path) <= 60.1
    assert video_path.stat().st_size > 100_000
    with Image.open(poster_path) as poster:
        assert poster.size == (1280, 720)
    with Image.open(alpha_visual_path) as alpha_visual:
        assert alpha_visual.size == (1200, 1200)


def test_commercial_validation_guide_and_roadmap_are_evidence_gated() -> None:
    guide_path = Path("docs/commercialization/design-partner-sprint.md")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")

    assert guide_path.is_file()
    guide = guide_path.read_text(encoding="utf-8")
    for required in (
        "30-day Design Partner Sprint",
        "free",
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "after a genuine participant completes a review",
        "waiting_for_external_participant_evidence",
        "Local Pro",
    ):
        assert required in guide
    for non_evidence in (
        "stars",
        "views",
        "downloads",
        "issue submissions",
        "constructed demos",
        "synthetic cases",
        "owner-authored examples",
    ):
        assert non_evidence in guide

    assert "## Stage 2 — Commercial discovery" in roadmap
    assert "two independent completed participants" in roadmap
    assert "voluntarily agree to discuss the team-price hypothesis" in roadmap
    assert "Local Pro remains deferred" in roadmap
    assert "not revenue, orders, customers, paid demand, or willingness to pay" in roadmap


def test_public_alpha_feedback_collects_bounded_commercial_signals() -> None:
    template = Path(".github/ISSUE_TEMPLATE/public-alpha-feedback.yml").read_text(
        encoding="utf-8"
    )
    for field_id in (
        "public_pr",
        "alpha_case_issue",
        "reviewed_head_sha",
        "public_requirements_url",
        "source_owner",
        "outcome",
        "completion_time",
        "useful_gap_category",
        "decision_impact",
        "reuse_intent",
        "design_partner_interest",
        "friction",
        "limitations",
        "safety",
    ):
        assert f"id: {field_id}" in template

    for required_text in (
        "USD 99 per team per month",
        "USD 999 per team per year",
        "research hypotheses only",
        "not a purchase agreement",
        "only after completing a genuine review",
        "Prefer not to answer",
        "submission alone is not validation",
    ):
        assert required_text in template

    forbidden_ids = (
        "name",
        "email",
        "linkedin_profile",
        "employer",
        "private_repository",
        "payment",
        "purchase_commitment",
        "sales_contact",
    )
    assert all(f"id: {field_id}" not in template for field_id in forbidden_ids)


def test_public_design_partner_positioning_is_free_inbound_and_noncommercial() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    site = Path("site/index.html").read_text(encoding="utf-8")
    quickstart = Path("docs/alpha/participant-quickstart.md").read_text(
        encoding="utf-8"
    )
    outcome = Path("docs/alpha/outcome-form.md").read_text(encoding="utf-8")
    checklist = Path("docs/alpha/concierge-host-checklist.md").read_text(
        encoding="utf-8"
    )
    public_surfaces = "\n".join((readme, site))

    guide = "docs/commercialization/design-partner-sprint.md"
    feedback_url = (
        "https://github.com/YuzeJ21/Scope-Proof/issues/new?"
        "template=public-alpha-feedback.yml"
    )
    assert guide in readme
    assert "../commercialization/design-partner-sprint.md" in quickstart
    assert guide in site
    assert feedback_url in site
    assert feedback_url in quickstart
    assert "../commercialization/design-partner-sprint.md" in outcome
    assert "../commercialization/design-partner-sprint.md" in checklist

    for required in (
        "free design-partner review",
        "No paid product or billing is active",
        "pricing question is optional research after product use",
        "public-repository-only",
        "acceptance-coverage assistant",
        "not an AI code reviewer",
    ):
        assert required in public_surfaces
    for unsupported_claim in (
        "ScopeProof customers",
        "validated pricing",
        "paid plan is available",
        "proven commercial demand",
    ):
        assert unsupported_claim not in public_surfaces

    assert "incomplete review" in site
    assert "participant-selected outcome" in quickstart
    assert "not commercial validation" in outcome


def test_pages_workflow_is_sha_pinned_minimal_and_deploys_only_static_site() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")

    assert "  push:\n    branches: [main]\n  workflow_dispatch:" in workflow
    assert "pull_request_target" not in workflow
    assert "schedule:" not in workflow
    assert "contents: read" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0" in workflow
    assert "actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6.0.0" in workflow
    assert (
        "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0"
        in workflow
    )
    assert "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128 # v5.0.0" in workflow
    assert "path: site" in workflow
    assert "github-pages" in workflow
    assert "cancel-in-progress: true" in workflow
    for line in workflow.splitlines():
        if "uses:" in line:
            reference = line.split("@", maxsplit=1)[1].split()[0]
            assert len(reference) == 40
            assert all(character in "0123456789abcdef" for character in reference)
