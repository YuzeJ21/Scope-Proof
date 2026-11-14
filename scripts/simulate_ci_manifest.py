"""Run the constructed CSV export CI workflow and publish its manifest artifacts."""

from __future__ import annotations

import argparse
import csv
import io
import os
import runpy
import sqlite3
import subprocess
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scopeproof_core.criteria.confirmation import (
    build_criteria_source_provenance,
    validate_criteria_source_confirmation,
)
from scopeproof_core.criteria.document import NormalizedCriteriaDocument
from scopeproof_core.reviews.ci_status import (
    EXACT_HEAD_PATTERN,
    CIStatusManifest,
    CIStatusRun,
    load_ci_status_manifest,
)
from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    CheckState,
    CIObservation,
    CriteriaSourceProvenance,
    Criterion,
    EvidenceLevel,
    PullRequestSnapshot,
    source_text_sha256,
)

_ACTOR = "CONSTRUCTED scripted actor"
_TIMESTAMP = datetime(2026, 11, 1, tzinfo=UTC)
_REPOSITORY = "constructed/export"
_PR_NUMBER = 1
_REQUIREMENTS = (
    ("AC-01", "Export only records matching the selected category filter.", "category_filter"),
    (
        "AC-02",
        "Export only records the current analyst is authorized to access.",
        "row_entitlement",
    ),
    ("AC-03", "Use the CSV header id,category,amount in that order.", "csv_header"),
)
_EXPECTED = {criterion: test for criterion, _, test in _REQUIREMENTS}
_FORMAT = """import csv
import io

def write_csv(rows):
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\\n")
    writer.writerow(("id", "category", "amount"))
    writer.writerows(rows)
    return output.getvalue()
"""
_QUERY_A = """def select_export_rows(db, analyst, category):
    # Apply category filter and analyst authorization to each export row.
    return db.execute(
        "SELECT id, category, amount FROM records WHERE analyst = ? AND category = ? ORDER BY id",
        (analyst, category),
    ).fetchall()
"""
_QUERY_B = """def select_export_rows(db, analyst, category):
    # CONSTRUCTED regression in the CSV export filter and analyst authorization.
    return db.execute("SELECT id, category, amount FROM records ORDER BY id").fetchall()
"""
_HEAD_LABELS = ("A", "B")
_RUN_PLAN = (
    ("A", "A", ("category_filter", "row_entitlement", "csv_header")),
    ("B", "B", ("category_filter", "csv_header")),
    ("B-targeted", "B", ("row_entitlement",)),
)


class SimulatedCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    criterion: str
    test: str
    outcome: Literal["passed", "failed", "not_run"]
    observed: str


class SimulatedRun(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    label: Literal["A", "B", "B-targeted"]
    head: str = Field(pattern=EXACT_HEAD_PATTERN)
    environment: Literal["synthetic SQLite and Python"] = "synthetic SQLite and Python"
    checks: list[SimulatedCheck]


def build_manifest(runs: Sequence[SimulatedRun], confirmation: CriteriaSourceProvenance) -> bytes:
    """Use only reported check rows and the predeclared ticket mapping."""
    manifest_runs = []
    for run in runs:
        outcomes = {}
        for check in run.checks:
            if _EXPECTED.get(check.criterion) != check.test or check.test in outcomes:
                raise ValueError("duplicate or mismapped simulated check")
            outcomes[check.test] = "skipped" if check.outcome == "not_run" else check.outcome
        manifest_runs.append(CIStatusRun(
            run_id=run.label,
            head_sha=run.head,
            source_url=f"https://ci.example.invalid/builds/{run.label}",
            outcomes=outcomes,
        ))
    manifest = CIStatusManifest(
        schema_version="criterion-ci-status-v1",
        repository=_REPOSITORY,
        pr_number=_PR_NUMBER,
        criteria_sha256=confirmation.normalized_criteria_sha256,
        expected_tests={criterion: [test] for criterion, test in _EXPECTED.items()},
        runs=manifest_runs,
    )
    payload = _model_bytes(manifest)
    load_ci_status_manifest(payload)
    return payload


def _model_bytes(model: BaseModel) -> bytes:
    return (model.model_dump_json(indent=2) + "\n").encode("utf-8")


def _git(repository: Path, *arguments: str) -> str:
    timestamp = _TIMESTAMP.isoformat()
    env = {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME=_ACTOR, GIT_AUTHOR_EMAIL="fixture@example.invalid",
        GIT_COMMITTER_NAME=_ACTOR, GIT_COMMITTER_EMAIL="fixture@example.invalid",
        GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp,
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
    )
    return subprocess.run(
        ("git", "-c", "core.autocrlf=false", *arguments),
        cwd=repository, env=env, check=True, stdout=subprocess.PIPE,
    ).stdout.decode("utf-8")


def _fixture_builds(scratch: Path) -> tuple[str, dict[str, str], str]:
    repository = scratch / "fixture-git"
    repository.mkdir()
    _git(repository, "init", "-q", "--template=", "--object-format=sha1", "--initial-branch=main")
    _git(repository, "commit", "-qm", "Constructed base", "--allow-empty")
    base = _git(repository, "rev-parse", "HEAD").strip()
    (repository / "export_format.py").write_bytes(_FORMAT.encode("utf-8"))
    heads = {}
    for label, query in zip(_HEAD_LABELS, (_QUERY_A, _QUERY_B), strict=True):
        (repository / "export_query.py").write_bytes(query.encode("utf-8"))
        _git(repository, "add", "export_format.py", "export_query.py")
        _git(repository, "commit", "-qm", f"Constructed build {label}")
        heads[label] = head = _git(repository, "rev-parse", "HEAD").strip()
        snapshot = scratch / label
        snapshot.mkdir()
        for name in ("export_format.py", "export_query.py"):
            content = _git(repository, "show", f"{head}:{name}")
            (snapshot / name).write_bytes(content.encode("utf-8"))
    diff = _git(repository, "diff", "--abbrev=7", heads["A"], heads["B"])
    return base, heads, diff


def _run_checks(
    label: Literal["A", "B", "B-targeted"],
    head: str,
    snapshot: Path,
    planned: Sequence[str],
) -> SimulatedRun:
    # Execute only the two constructed modules written in this run's private scratch directory.
    select = runpy.run_path(str(snapshot / "export_query.py"))["select_export_rows"]
    write_csv = runpy.run_path(str(snapshot / "export_format.py"))["write_csv"]
    results = []
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE records(id INTEGER, category TEXT, amount INTEGER, analyst TEXT)")
        db.executemany("INSERT INTO records VALUES (?, ?, ?, ?)", [
            (1, "A", 12, "alice"), (2, "B", 34, "alice"), (3, "A", 56, "bob"),
        ])
        for criterion, test in _EXPECTED.items():
            if test not in planned:
                outcome, observed = "not_run", "Expected check absent from this run."
            else:
                if test == "csv_header":
                    actual = next(csv.reader(io.StringIO(write_csv([]))))
                    expected = ["id", "category", "amount"]
                else:
                    rows = list(csv.DictReader(io.StringIO(write_csv(select(db, "alice", "A")))))
                    if test == "category_filter":
                        actual = sorted({row["category"] for row in rows})
                        expected = ["A"]
                    else:
                        actual = sorted({int(row["id"]) for row in rows} - {1, 2})
                        expected = []
                outcome = "passed" if actual == expected else "failed"
                observed = f"Expected {expected!r}; observed {actual!r}."
            results.append(SimulatedCheck(
                criterion=criterion, test=test, outcome=outcome, observed=observed,
            ))
    return SimulatedRun(label=label, head=head, checks=results)


def _write_confirmation(output: Path) -> CriteriaSourceProvenance:
    source = "".join(f"{text}\n" for _, text, _ in _REQUIREMENTS)
    (output / "ticket-requirements.txt").write_bytes(source.encode("utf-8"))
    document = NormalizedCriteriaDocument(
        schema_version=1,
        source_text_sha256=source_text_sha256(source),
        criteria=[
            Criterion(criterion_id=criterion, text=text, required_evidence_level=EvidenceLevel.E3)
            for criterion, text, _ in _REQUIREMENTS
        ],
    )
    (output / "criteria.json").write_bytes(_model_bytes(document))
    criteria = document.criteria_for_source(source)
    confirmation = build_criteria_source_provenance(
        source_uri="https://ticket.example.invalid/EXP-17",
        source_revision="ticket-revision-1",
        source_text=source,
        criteria=criteria,
        confirmed_by=_ACTOR,
        confirmed_at=_TIMESTAMP,
    )
    path = output / "confirmation.json"
    path.write_bytes(_model_bytes(confirmation))
    return validate_criteria_source_confirmation(path, source_text=source, criteria=criteria)


def _review_fixture(snapshot: Path, base: str, run: SimulatedRun) -> PullRequestSnapshot:
    failed = any(check.outcome == "failed" for check in run.checks)
    status = CheckState.FAILING if failed else CheckState.PASSING
    return PullRequestSnapshot(
        repository=_REPOSITORY,
        pr_number=_PR_NUMBER,
        title="CONSTRUCTED CSV export acceptance",
        html_url=f"https://github.com/{_REPOSITORY}/pull/{_PR_NUMBER}",
        base_sha=base,
        head_sha=run.head,
        fetched_at=_TIMESTAMP,
        check_state=status,
        ci_observation=CIObservation(
            state=status,
            reason="Simulated CI job outcome from executed fixture checks.",
            total_check_runs=1,
            successful_check_runs=int(not failed),
            failing_check_runs=int(failed),
        ),
        files=[
            ChangedFile(
                path=name,
                status="added",
                lines=[
                    ChangedLine(change_type="added", line_number=number, content=line)
                    for number, line in enumerate(
                        (snapshot / name).read_text(encoding="utf-8").splitlines(), 1,
                    )
                ],
            )
            for name in ("export_format.py", "export_query.py")
        ],
    )


def simulate(output: Path) -> None:
    """Publish CI records and rolling ScopeProof manifests in a new directory."""
    output.mkdir()
    confirmation = _write_confirmation(output)
    runs = []
    with TemporaryDirectory(prefix="scopeproof-constructed-ci-") as directory:
        scratch = Path(directory)
        base, heads, diff = _fixture_builds(scratch)
        (output / "build-A-to-B.diff").write_bytes(diff.encode("utf-8"))
        for label, build, planned in _RUN_PLAN:
            run = _run_checks(label, heads[build], scratch / build, planned)
            runs.append(run)
            manifest = build_manifest(runs, confirmation)
            (output / f"{label}-ci.json").write_bytes(_model_bytes(run))
            (output / f"{label}-scopeproof-manifest.json").write_bytes(manifest)
            if label == build:
                fixture = _review_fixture(scratch / build, base, run)
                (output / f"{build}-fixture.json").write_bytes(_model_bytes(fixture))
    ticket = [
        "# EXP-17 · Constructed internal ticket",
        "",
        "The ticket and ScopeProof share the same fixed requirements and run artifacts.",
        "",
        "| Criterion | Confirmed wording | Expected test |",
        "| --- | --- | --- |",
        *[f"| {criterion} | {text} | {test} |" for criterion, text, test in _REQUIREMENTS],
        "",
        *[f"- [{run.label} CI run]({run.label}-ci.json) at `{run.head}`" for run in runs],
        "- [A-to-B source diff](build-A-to-B.diff)",
        "",
    ]
    (output / "ticket.md").write_bytes("\n".join(ticket).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for constructed CI artifacts")
    output = parser.parse_args().output
    simulate(output)
    print(f"Constructed pipeline artifacts written to {output}")


if __name__ == "__main__":
    main()
