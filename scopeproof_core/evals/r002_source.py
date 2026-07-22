"""Offline validation and outcome-blind selection for pinned R-002 source rows."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from hashlib import sha256
from typing import BinaryIO, TypeVar

from scopeproof_core.evals.r002_models import (
    GitSha,
    R002CaseId,
    R002CaseManifest,
    R002SourceError,
    R002SourceManifest,
    SWEbenchCriteriaSourceRow,
    SWEbenchSourcePin,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
)

R002_CRITERIA_SOURCE_COLUMNS = (
    "repo",
    "instance_id",
    "base_commit",
    "problem_statement",
    "difficulty",
)
_R = TypeVar("_R", SWEbenchCriteriaSourceRow, SWEbenchVerifiedRow)


def _validate_parquet_container(source: BinaryIO, pin: SWEbenchSourcePin, *, pa, pq):
    try:
        source.seek(0)
        digest = sha256()
        length = 0
        while chunk := source.read(min(64 * 1024, pin.byte_length - length + 1)):
            if not isinstance(chunk, bytes):
                raise TypeError("source must return bytes")
            length += len(chunk)
            if length > pin.byte_length:
                raise R002SourceError("parquet_bytes_mismatch")
            digest.update(chunk)
    except R002SourceError:
        raise
    except Exception:
        raise R002SourceError("parquet_bytes_mismatch") from None
    if length != pin.byte_length or digest.hexdigest() != pin.sha256:
        raise R002SourceError("parquet_bytes_mismatch")
    try:
        source.seek(0)
    except R002SourceError:
        raise
    except Exception:
        raise R002SourceError("parquet_bytes_mismatch") from None
    try:
        parquet = pq.ParquetFile(source)
        metadata = parquet.metadata
        if metadata.num_rows != pin.row_count:
            raise R002SourceError("parquet_row_count_mismatch")
        if tuple(parquet.schema_arrow.names) != pin.schema:
            raise R002SourceError("parquet_schema_mismatch")
        if any(not pa.types.is_string(field.type) for field in parquet.schema_arrow):
            raise R002SourceError("parquet_field_type_mismatch")
        uncompressed = sum(
            metadata.row_group(group).column(column).total_uncompressed_size
            for group in range(metadata.num_row_groups)
            for column in range(metadata.num_columns)
        )
        if uncompressed > 16 * 1024 * 1024:
            raise R002SourceError("parquet_uncompressed_limit")
    except R002SourceError:
        raise
    except Exception:
        raise R002SourceError("parquet_schema_mismatch") from None
    return parquet


def decode_verified_parquet(
    source: BinaryIO, pin: SWEbenchSourcePin
) -> list[SWEbenchVerifiedRow]:
    """Decode the complete pinned source only after the criteria path is confirmed."""

    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet = _validate_parquet_container(source, pin, pa=pa, pq=pq)
    try:
        decoded = parquet.read().to_pylist()
    except R002SourceError:
        raise
    except Exception:
        raise R002SourceError("parquet_schema_mismatch") from None
    rows = [SWEbenchVerifiedRow.model_validate(item) for item in decoded]
    validate_row_collection(rows, pin)
    return rows


def decode_criteria_source_rows(
    source: BinaryIO, pin: SWEbenchSourcePin
) -> list[SWEbenchCriteriaSourceRow]:
    """Decode only criteria-safe columns and never materialize patches or test names."""

    import pyarrow as pa
    import pyarrow.parquet as pq

    parquet = _validate_parquet_container(source, pin, pa=pa, pq=pq)
    try:
        projected = parquet.read(columns=R002_CRITERIA_SOURCE_COLUMNS).to_pylist()
    except R002SourceError:
        raise
    except Exception:
        raise R002SourceError("parquet_schema_mismatch") from None
    rows = [SWEbenchCriteriaSourceRow.model_validate(item) for item in projected]
    if any(len(row.problem_statement.encode("utf-8")) > 128 * 1024 for row in rows):
        raise R002SourceError("manifest_row_mismatch")
    validate_criteria_source_collection(rows, pin)
    return rows


def validate_row_collection(
    rows: Sequence[SWEbenchVerifiedRow], pin: SWEbenchSourcePin
) -> None:
    _validate_collection(rows, pin)


def validate_criteria_source_collection(
    rows: Sequence[SWEbenchCriteriaSourceRow], pin: SWEbenchSourcePin
) -> None:
    _validate_collection(rows, pin)


def _validate_collection(rows: Sequence[_R], pin: SWEbenchSourcePin) -> None:
    if len(rows) != pin.row_count:
        raise R002SourceError("row_count_mismatch")
    instance_ids = [row.instance_id for row in rows]
    if len(set(instance_ids)) != pin.unique_instance_count:
        raise R002SourceError("unique_instance_count_mismatch")
    if len({row.repo for row in rows}) != pin.repository_count:
        raise R002SourceError("repository_count_mismatch")


def _select_r002_rows(rows: Sequence[_R], parquet_sha256: str) -> list[_R]:
    grouped: dict[str, list[_R]] = defaultdict(list)
    for row in rows:
        grouped[row.repo].append(row)
    if len(grouped) != 12:
        raise R002SourceError("repository_count_mismatch")
    instance_ids = [row.instance_id for row in rows]
    if len(instance_ids) != len(set(instance_ids)):
        raise R002SourceError("unique_instance_count_mismatch")
    repository_order = sorted(grouped, key=lambda repo: (-len(grouped[repo]), repo))
    quotas = {repo: 1 for repo in grouped}
    for repo in repository_order[:8]:
        quotas[repo] += 1
    chosen: list[_R] = []
    for repo, candidates in grouped.items():
        if len(candidates) < quotas[repo]:
            raise R002SourceError("manifest_selection_mismatch")
        ranked = sorted(
            candidates,
            key=lambda row: (
                sha256(f"{parquet_sha256}:{row.instance_id}".encode()).hexdigest(),
                row.instance_id,
            ),
        )
        chosen.extend(ranked[: quotas[repo]])
    if len(chosen) != 20:
        raise R002SourceError("manifest_selection_mismatch")
    return sorted(chosen, key=lambda row: (row.repo, row.instance_id))


def select_r002_rows(
    rows: Sequence[SWEbenchVerifiedRow], parquet_sha256: str
) -> list[SWEbenchVerifiedRow]:
    return _select_r002_rows(rows, parquet_sha256)


def select_r002_criteria_source_rows(
    rows: Sequence[SWEbenchCriteriaSourceRow], parquet_sha256: str
) -> list[SWEbenchCriteriaSourceRow]:
    return _select_r002_rows(rows, parquet_sha256)


def manifest_case_from_row(
    case_id: R002CaseId,
    row_index: int,
    row: SWEbenchVerifiedRow,
    verified_pr_head_sha: GitSha,
) -> R002CaseManifest:
    match = re.fullmatch(
        re.escape(row.repo.replace("/", "__")) + r"-(\d+)", row.instance_id
    )
    if match is None:
        raise R002SourceError("instance_pr_suffix_mismatch")
    pr_number = int(match.group(1))
    row_bytes = canonical_json_bytes(row)
    return R002CaseManifest(
        case_id=case_id,
        instance_id=row.instance_id,
        repository=row.repo,
        pr_number=pr_number,
        pr_url=f"https://github.com/{row.repo}/pull/{pr_number}",
        dataset_base_commit=row.base_commit,
        verified_pr_head_sha=verified_pr_head_sha,
        row_index=row_index,
        difficulty=row.difficulty,
        row_sha256=sha256(row_bytes).hexdigest(),
        problem_statement_sha256=sha256(row.problem_statement.encode("utf-8")).hexdigest(),
        patch_sha256=sha256(row.patch.encode("utf-8")).hexdigest(),
        test_patch_sha256=sha256(row.test_patch.encode("utf-8")).hexdigest(),
    )


def validate_manifest_criteria_sources(
    manifest: R002SourceManifest,
    rows: Sequence[SWEbenchCriteriaSourceRow],
) -> list[SWEbenchCriteriaSourceRow]:
    validate_criteria_source_collection(rows, manifest.source)
    selected = select_r002_criteria_source_rows(rows, manifest.source.sha256)
    if [row.instance_id for row in selected] != [case.instance_id for case in manifest.cases]:
        raise R002SourceError("manifest_selection_mismatch")
    row_indexes = {row.instance_id: index for index, row in enumerate(rows)}
    for case, row in zip(manifest.cases, selected, strict=True):
        if (
            row_indexes[row.instance_id] != case.row_index
            or row.base_commit != case.dataset_base_commit
            or row.difficulty != case.difficulty
            or sha256(row.problem_statement.encode("utf-8")).hexdigest()
            != case.problem_statement_sha256
        ):
            raise R002SourceError("manifest_row_mismatch")
    return selected


def validate_manifest_rows(
    manifest: R002SourceManifest,
    rows: Sequence[SWEbenchVerifiedRow],
) -> list[SWEbenchVerifiedRow]:
    validate_row_collection(rows, manifest.source)
    selected = select_r002_rows(rows, manifest.source.sha256)
    if [row.instance_id for row in selected] != [case.instance_id for case in manifest.cases]:
        raise R002SourceError("manifest_selection_mismatch")
    row_indexes = {row.instance_id: index for index, row in enumerate(rows)}
    for case, row in zip(manifest.cases, selected, strict=True):
        observed = manifest_case_from_row(
            case.case_id,
            row_indexes[row.instance_id],
            row,
            case.verified_pr_head_sha,
        )
        if observed != case:
            raise R002SourceError("manifest_row_mismatch")
    return selected
