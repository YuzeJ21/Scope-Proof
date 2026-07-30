"""ScopeProof-authored R-002 contract fixtures; no benchmark source bodies."""

from __future__ import annotations

from copy import deepcopy

import pytest


def _sha(number: int) -> str:
    return f"{number:064x}"


def _git_sha(number: int) -> str:
    return f"{number:040x}"


@pytest.fixture
def r002_manifest_payload() -> dict[str, object]:
    repositories = [
        "alpha/one",
        "alpha/two",
        "bravo/one",
        "bravo/two",
        "charlie/one",
        "charlie/two",
        "delta/one",
        "delta/two",
        "echo/one",
        "foxtrot/one",
        "golf/one",
        "hotel/one",
    ]
    cases: list[dict[str, object]] = []
    for number in range(1, 21):
        repository = repositories[(number - 1) // 2] if number <= 16 else repositories[number - 9]
        pr_number = {9: 2, 10: 20}.get(number, number)
        cases.append(
            {
                "case_id": f"R002-{number:03d}",
                "instance_id": repository.replace("/", "__") + f"-{pr_number}",
                "repository": repository,
                "pr_number": pr_number,
                "pr_url": f"https://github.com/{repository}/pull/{pr_number}",
                "dataset_base_commit": _git_sha(number),
                "verified_pr_head_sha": _git_sha(number + 100),
                "row_index": number,
                "difficulty": "fixture difficulty",
                "row_sha256": _sha(number),
                "problem_statement_sha256": _sha(number + 100),
                "patch_sha256": _sha(number + 200),
                "test_patch_sha256": _sha(number + 300),
            }
        )
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source": {
            "dataset_id": "fixture/dataset",
            "config": "fixture",
            "split": "test",
            "revision": _git_sha(900),
            "source_url": "https://huggingface.co/fixture/data.parquet",
            "parquet_path": "data/test.parquet",
            "byte_length": 1,
            "sha256": _sha(900),
            "row_count": 20,
            "repository_count": 12,
            "unique_instance_count": 20,
            "schema": ["repo"],
        },
        "cases": cases,
    }


@pytest.fixture
def r002_criteria_payload(r002_manifest_payload: dict[str, object]) -> dict[str, object]:
    cases = []
    for case in r002_manifest_payload["cases"]:  # type: ignore[index]
        case = dict(case)
        cases.append(
            {
                "case_id": case["case_id"],
                "problem_statement_sha256": case["problem_statement_sha256"],
                "criteria": [
                    {
                        "criterion_id": "AC-01",
                        "text": "Fixture criterion.",
                        "priority": "must_have",
                        "criterion_type": "behavior",
                        "criterion_source": "user_confirmed",
                        "source_span": "problem_statement:L1-L1",
                        "required_evidence_level": "E1",
                    }
                ],
            }
        )
    return {
        "pack_id": "R-002",
        "classification": "public_engineering_research",
        "eligible_for_stage_1": False,
        "does_not_advance_stage_1": True,
        "target_repository_code_executed": False,
        "source_manifest_sha256": _sha(999),
        "source_owner_confirmed": False,
        "benchmark_owner_confirmed": True,
        "cases": cases,
    }


@pytest.fixture
def copied_manifest(r002_manifest_payload: dict[str, object]) -> dict[str, object]:
    return deepcopy(r002_manifest_payload)
