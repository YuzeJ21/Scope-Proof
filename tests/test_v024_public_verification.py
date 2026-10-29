"""Strict contract for the dated public-release evidence, not current-source validation."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RELEASE_SHA = "11bcdc66f7d8f5a29055688208de1ed337eed07f"
DOWNLOAD_ROOT = "https://github.com/YuzeJ21/Scope-Proof/releases/download/v0.2.4"
ARTIFACTS = {
    "scopeproof-0.2.4-py3-none-any.whl": (
        320694,
        "350ec7375ddab278f4dfef9737c341b5f26fe6e23dff7d0568df363cd4f3a287",
    ),
    "scopeproof-0.2.4.tar.gz": (
        7227148,
        "773c922b6abd7da0191b676c77fc2787d44abc022d3656e0921260dd1180daa8",
    ),
    "SHA256SUMS.txt": (
        190,
        "ab2de99af4bfbbd595794f7cb7d11254f2acdd27c3ca258bf1a6e0a0cc53d7c7",
    ),
}


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PublishedAsset(StrictRecord):
    name: str
    bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    url: str


class PublicChecks(StrictRecord):
    actor: Literal["automated_checks"]
    http_authentication: Literal["none; curl configuration disabled"]
    successful_http_requests: Literal[5]
    verified_assets: Literal[3]
    fresh_install_formats: tuple[Literal["wheel"], Literal["source"]]
    python_version: Literal["3.12.0"]
    package_core_review_cli_web_version: Literal["0.2.4"]
    dependency_checks: Literal["passed for both installations"]
    acceptance_cases_per_install: Literal[12]
    comparison_cases_per_install: Literal[2]
    benchmark_mismatches: Literal[0]
    must_have_false_ready: Literal[0]
    uncited_file_false_ready: Literal[0]
    workbench_health: Literal["ok"]
    workbench_process_stopped: Literal[True]


class CandidateCompatibility(StrictRecord):
    actor: Literal["automated_checks"]
    evidence: Literal["same final wheel bytes before publication"]
    platform: Literal["macOS"]
    python_versions: tuple[Literal["3.11.15"], Literal["3.13.14"]]
    checks: Literal["fresh installs, identity, dependencies and both constructed benchmarks passed"]


class SourceCI(StrictRecord):
    source_sha: Literal["11bcdc66f7d8f5a29055688208de1ed337eed07f"]
    ci_run_id: Literal[40907232114]
    codeql_run_id: Literal[40907230758]
    base_advance_run_id: Literal[40907231657]
    conclusion: Literal["success"]
    tests_passed: Literal[2700]
    tests_skipped: Literal[8]
    unrounded_coverage_percent: Literal[95.0834]
    packaged_browser_checks: Literal[11]
    full_browser_journeys: Literal[1]
    constructed_selection_checks: Literal[4]
    helper_capture_checks: Literal[6]


class EvidenceBoundary(StrictRecord):
    evidence: Literal["engineering only"]
    source_review_actor: Literal["independent automated agent"]
    target_repository_code_executed: Literal[False]
    genuine_independent_use_credit: Literal[0]
    qualifying_review_credit: Literal[0]
    stage_1: Literal["closed_not_pursued_by_owner"]
    stage_3: Literal["dormant"]


class ReleaseVerificationRecord(StrictRecord):
    record_version: Literal[1]
    version: Literal["0.2.4"]
    tag: Literal["v0.2.4"]
    release_id: Literal[428120360]
    release_url: Literal["https://github.com/YuzeJ21/Scope-Proof/releases/tag/v0.2.4"]
    source_sha: Literal["11bcdc66f7d8f5a29055688208de1ed337eed07f"]
    source_tree: Literal["9b5bd8f6c468299f2d39c677a7b61c3cccb86a29"]
    annotated_tag_object: Literal["8d99d3d6b337e5a670c0947b707083e2ac822751"]
    published_at: datetime
    verified_at: datetime
    assets: list[PublishedAsset] = Field(min_length=3, max_length=3)
    public_checks: PublicChecks
    prior_candidate_compatibility: CandidateCompatibility
    release_source_ci: SourceCI
    boundaries: EvidenceBoundary
    operational_note: str


def test_v024_public_evidence_is_strict_sanitized_and_bound_to_released_bytes() -> None:
    path = Path("docs/releases/v0.2.4-public-verification.json")
    raw = path.read_text(encoding="utf-8")
    record = ReleaseVerificationRecord.model_validate_json(raw)
    assert record.published_at.tzinfo is not None
    assert record.verified_at.tzinfo is not None
    assert record.published_at <= record.verified_at
    assert {asset.name for asset in record.assets} == set(ARTIFACTS)
    for asset in record.assets:
        assert (asset.bytes, asset.sha256) == ARTIFACTS[asset.name]
        assert asset.url == f"{DOWNLOAD_ROOT}/{asset.name}"

    summary = path.with_suffix(".md").read_text(encoding="utf-8")
    assert RELEASE_SHA in summary
    assert record.release_url in summary
    assert all(asset.sha256 in summary for asset in record.assets)
    assert "HTTP 404" in record.operational_note
    assert "public verification passed" in record.operational_note
    assert all(marker not in raw + summary for marker in ("/Users/", "/private/tmp/", "file://"))
