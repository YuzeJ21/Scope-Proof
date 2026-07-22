"""Local, outcome-blind source-contract tests for the R-002 benchmark."""

from __future__ import annotations

import ast
from collections import Counter
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from scopeproof_core.evals.r002_models import (
    R002_SCHEMA,
    R002CaseManifest,
    R002SourceError,
    R002SourceManifest,
    SWEbenchCriteriaSourceRow,
    SWEbenchSourcePin,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
)
from scopeproof_core.evals.r002_source import (
    R002_CRITERIA_SOURCE_COLUMNS,
    decode_criteria_source_rows,
    decode_verified_parquet,
    manifest_case_from_row,
    select_r002_criteria_source_rows,
    select_r002_rows,
    validate_manifest_criteria_sources,
    validate_manifest_rows,
)

SOURCE_SHA = "d" * 64
SOURCE_ERRORS = {
    "source_pin_mismatch",
    "approved_cohort_mismatch",
    "parquet_bytes_mismatch",
    "parquet_row_count_mismatch",
    "parquet_schema_mismatch",
    "parquet_field_type_mismatch",
    "parquet_uncompressed_limit",
    "row_count_mismatch",
    "unique_instance_count_mismatch",
    "repository_count_mismatch",
    "instance_pr_suffix_mismatch",
    "manifest_selection_mismatch",
    "manifest_row_mismatch",
}


def swebench_row(**overrides: str) -> dict[str, str]:
    row = {
        "repo": "scopeproof/fixture",
        "instance_id": "scopeproof__fixture-1",
        "base_commit": "a" * 40,
        "patch": "+ change",
        "test_patch": "+test",
        "problem_statement": "Fixture problem.",
        "hints_text": "",
        "created_at": "2024-01-01T00:00:00Z",
        "version": "1",
        "FAIL_TO_PASS": "[]",
        "PASS_TO_PASS": "[]",
        "environment_setup_commit": "b" * 40,
        "difficulty": "<15 min fix",
    }
    return {**row, **overrides}


def _pin(
    path: Path,
    rows: list[dict[str, object]],
    schema: tuple[str, ...] = R002_SCHEMA,
) -> SWEbenchSourcePin:
    source = path.read_bytes()
    return SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=len(source),
        sha256=sha256(source).hexdigest(),
        row_count=len(rows),
        repository_count=len({str(row["repo"]) for row in rows}),
        unique_instance_count=len({row["instance_id"] for row in rows}),
        schema=schema,
    )


def write_parquet_and_pin(
    tmp_path: Path,
    rows: list[dict[str, object]],
    *,
    fields: list[pa.Field] | None = None,
    row_group_size: int | None = None,
) -> tuple[Path, SWEbenchSourcePin]:
    path = tmp_path / "fixture.parquet"
    schema = pa.schema(fields or [pa.field(name, pa.string()) for name in R002_SCHEMA])
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(table, path, compression=None, row_group_size=row_group_size)
    return path, _pin(path, rows, tuple(schema.names))


def selection_rows() -> list[SWEbenchVerifiedRow]:
    repositories = [
        "alpha/one",
        "bravo/one",
        "charlie/one",
        "delta/one",
        "echo/one",
        "foxtrot/one",
        "golf/one",
        "hotel/one",
        "india/one",
        "juliet/one",
        "kilo/one",
        "lima/one",
    ]
    rows = []
    for number, repo in enumerate(repositories, start=1):
        count = 2 if number <= 8 else 1
        for duplicate in range(1, count + 1):
            rows.append(
                SWEbenchVerifiedRow.model_validate(
                    swebench_row(
                        repo=repo,
                        instance_id=repo.replace("/", "__") + f"-{number * 10 + duplicate}",
                    )
                )
            )
    return rows


def make_manifest(rows: list[SWEbenchVerifiedRow]) -> R002SourceManifest:
    selected = select_r002_rows(rows, SOURCE_SHA)
    cases = tuple(
        manifest_case_from_row(
            f"R002-{number:03d}",
            rows.index(row),
            row,
            "c" * 40,
        )
        for number, row in enumerate(selected, start=1)
    )
    return R002SourceManifest(
        source=SWEbenchSourcePin(
            dataset_id="fixture/dataset",
            config="fixture",
            split="test",
            revision="c" * 40,
            source_url="https://huggingface.co/fixture/data.parquet",
            parquet_path="data/test.parquet",
            byte_length=1,
            sha256=SOURCE_SHA,
            row_count=len(rows),
            repository_count=12,
            unique_instance_count=len(rows),
            schema=R002_SCHEMA,
        ),
        cases=cases,
    )


def test_source_error_allowlist_is_closed_and_exact():
    assert R002SourceError.allowed_reason_codes == SOURCE_ERRORS
    for reason in SOURCE_ERRORS:
        assert R002SourceError(reason).args == (reason,)
    with pytest.raises(RuntimeError):
        R002SourceError("unregistered")


def test_pyarrow_is_not_imported_at_module_load_time():
    source_path = Path(__file__).parents[2] / "scopeproof_core/evals/r002_source.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for statement in tree.body
        if isinstance(statement, (ast.Import, ast.ImportFrom))
        for alias in statement.names
    }
    assert not any(name == "pyarrow" or name.startswith("pyarrow.") for name in imported)


def test_canonical_row_hash_preserves_unicode_and_field_order(tmp_path):
    row = swebench_row(problem_statement="café", patch="+  value\t", test_patch="+test")
    path, pin = write_parquet_and_pin(tmp_path, [row])
    with path.open("rb") as source:
        decoded = decode_verified_parquet(source, pin)
    assert canonical_json_bytes(decoded[0]).decode("utf-8") == (
        '{"FAIL_TO_PASS":"[]","PASS_TO_PASS":"[]","base_commit":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        '"created_at":"2024-01-01T00:00:00Z","difficulty":"<15 min fix",'
        '"environment_setup_commit":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",'
        '"hints_text":"","instance_id":"scopeproof__fixture-1","patch":"+  value\\t",'
        '"problem_statement":"café","repo":"scopeproof/fixture","test_patch":"+test","version":"1"}'
    )


def test_criteria_decode_reads_only_outcome_blind_projection(tmp_path, monkeypatch):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    real_parquet_file = pq.ParquetFile
    calls: list[list[str] | None] = []

    class RecordingParquetFile:
        def __init__(self, source):
            self._inner = real_parquet_file(source)
            self.metadata = self._inner.metadata
            self.schema_arrow = self._inner.schema_arrow

        def read(self, columns=None):
            calls.append(columns)
            forbidden = {"patch", "test_patch", "hints_text", "FAIL_TO_PASS", "PASS_TO_PASS"}
            assert not forbidden.intersection(columns or [])
            return self._inner.read(columns=columns)

    monkeypatch.setattr(pq, "ParquetFile", RecordingParquetFile)
    with path.open("rb") as source:
        rows = decode_criteria_source_rows(source, pin)
    assert [row.model_dump() for row in rows] == [
        {
            "repo": "scopeproof/fixture",
            "instance_id": "scopeproof__fixture-1",
            "base_commit": "a" * 40,
            "problem_statement": "Fixture problem.",
            "difficulty": "<15 min fix",
        }
    ]
    assert calls == [R002_CRITERIA_SOURCE_COLUMNS]


def test_decode_hashes_and_rewinds_before_constructing_parquet(tmp_path, monkeypatch):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    source = BytesIO(path.read_bytes())
    real_parquet_file = pq.ParquetFile

    def checked_parquet_file(handle):
        assert handle.tell() == 0
        return real_parquet_file(handle)

    monkeypatch.setattr(pq, "ParquetFile", checked_parquet_file)
    assert len(decode_verified_parquet(source, pin)) == 1


def test_decode_maps_hash_matching_invalid_parquet_to_a_closed_source_error():
    payload = b"this hash-matching payload is not a parquet file"
    pin = SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=len(payload),
        sha256=sha256(payload).hexdigest(),
        row_count=1,
        repository_count=1,
        unique_instance_count=1,
        schema=R002_SCHEMA,
    )
    with pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(BytesIO(payload), pin)
    assert raised.value.args == ("parquet_schema_mismatch",)


def test_decode_maps_bad_seekable_handle_before_parquet_construction(monkeypatch):
    class BadSource:
        def seek(self, offset):
            raise TypeError("not a binary source")

    monkeypatch.setattr(pq, "ParquetFile", lambda _source: pytest.fail("unexpected parquet"))
    pin = SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=1,
        sha256="0" * 64,
        row_count=1,
        repository_count=1,
        unique_instance_count=1,
        schema=R002_SCHEMA,
    )
    with pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(BadSource(), pin)
    assert raised.value.args == ("parquet_bytes_mismatch",)


def test_decode_stops_reading_an_oversized_stream_after_one_extra_chunk():
    class OversizedRecordingSource:
        def __init__(self):
            self.bytes_returned = 0
            self.read_calls = 0

        def seek(self, offset):
            assert offset == 0

        def read(self, size):
            self.read_calls += 1
            if self.read_calls > 1:
                pytest.fail("source was read past the bounded mismatch check")
            chunk = b"x" * size
            self.bytes_returned += len(chunk)
            return chunk

    source = OversizedRecordingSource()
    pin = SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=1,
        sha256="0" * 64,
        row_count=1,
        repository_count=1,
        unique_instance_count=1,
        schema=R002_SCHEMA,
    )
    with pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(source, pin)
    assert raised.value.args == ("parquet_bytes_mismatch",)
    assert source.bytes_returned <= pin.byte_length + 64 * 1024


def test_decode_requests_only_one_excess_byte_from_a_size_respecting_stream():
    class RecordingSource:
        def __init__(self, payload):
            self.payload = payload
            self.offset = 0
            self.request_sizes = []
            self.bytes_returned = 0

        def seek(self, offset):
            self.offset = offset

        def read(self, size):
            self.request_sizes.append(size)
            chunk = self.payload[self.offset : self.offset + size]
            self.offset += len(chunk)
            self.bytes_returned += len(chunk)
            return chunk

    source = RecordingSource(b"0123456789x")
    pin = SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=10,
        sha256="0" * 64,
        row_count=1,
        repository_count=1,
        unique_instance_count=1,
        schema=R002_SCHEMA,
    )
    with pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(source, pin)
    assert raised.value.args == ("parquet_bytes_mismatch",)
    assert source.request_sizes == [pin.byte_length + 1]
    assert source.bytes_returned <= pin.byte_length + 1


@pytest.mark.parametrize("error_type", [EOFError, RuntimeError])
@pytest.mark.parametrize("method", ["seek", "read"])
def test_decode_hides_ordinary_handle_prose_with_a_stable_error_code(method, error_type):
    class RuntimeSource:
        def seek(self, offset):
            if method == "seek":
                raise error_type("secret seek prose")

        def read(self, size):
            if method == "read":
                raise error_type("secret read prose")
            return b""

    pin = SWEbenchSourcePin(
        dataset_id="fixture/dataset",
        config="fixture",
        split="test",
        revision="c" * 40,
        source_url="https://huggingface.co/fixture/data.parquet",
        parquet_path="data/test.parquet",
        byte_length=1,
        sha256="0" * 64,
        row_count=1,
        repository_count=1,
        unique_instance_count=1,
        schema=R002_SCHEMA,
    )
    with pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(RuntimeSource(), pin)
    assert raised.value.args == ("parquet_bytes_mismatch",)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True
    assert "secret" not in str(raised.value)


@pytest.mark.parametrize("decoder", [decode_criteria_source_rows, decode_verified_parquet])
def test_decode_maps_parquet_read_failures_without_wrapping_model_validation(
    tmp_path, monkeypatch, decoder
):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    real_parquet_file = pq.ParquetFile

    class FailingReadParquetFile:
        def __init__(self, source):
            self._inner = real_parquet_file(source)
            self.metadata = self._inner.metadata
            self.schema_arrow = self._inner.schema_arrow

        def read(self, columns=None):
            raise pa.ArrowInvalid("fixture read failure")

    monkeypatch.setattr(pq, "ParquetFile", FailingReadParquetFile)
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decoder(source, pin)
    assert raised.value.args == ("parquet_schema_mismatch",)


def test_decode_maps_runtime_parquet_read_failures_without_leaking_prose(tmp_path, monkeypatch):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    real_parquet_file = pq.ParquetFile

    class FailingReadParquetFile:
        def __init__(self, source):
            self._inner = real_parquet_file(source)
            self.metadata = self._inner.metadata
            self.schema_arrow = self._inner.schema_arrow

        def read(self, columns=None):
            raise RuntimeError("secret parquet prose")

    monkeypatch.setattr(pq, "ParquetFile", FailingReadParquetFile)
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, pin)
    assert raised.value.args == ("parquet_schema_mismatch",)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


def test_decode_maps_eoferror_from_parquet_construction_without_leaking_prose(
    tmp_path, monkeypatch
):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])

    def failed_parquet_construction(source):
        raise EOFError("secret parquet constructor prose")

    monkeypatch.setattr(pq, "ParquetFile", failed_parquet_construction)
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, pin)
    assert raised.value.args == ("parquet_schema_mismatch",)
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


@pytest.mark.parametrize(
    ("pin_change", "error"),
    [
        ("byte_length", "parquet_bytes_mismatch"),
        ("row_count", "parquet_row_count_mismatch"),
        ("repository_count", "repository_count_mismatch"),
        ("unique_instance_count", "unique_instance_count_mismatch"),
    ],
)
def test_decode_rejects_pin_and_collection_count_mismatches(tmp_path, pin_change, error):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    value = getattr(pin, pin_change)
    pin = pin.model_copy(update={pin_change: value + 1})
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(source, pin)
    assert raised.value.args == (error,)


def test_decode_rejects_schema_order_non_string_and_nested_types(tmp_path):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row()])
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(
            source, pin.model_copy(update={"schema": tuple(reversed(R002_SCHEMA))})
        )
    assert raised.value.args == ("parquet_schema_mismatch",)

    fields = [pa.field(name, pa.string()) for name in R002_SCHEMA]
    fields[0] = pa.field("repo", pa.list_(pa.string()))
    nested_path, nested_pin = write_parquet_and_pin(
        tmp_path, [swebench_row(repo=["scopeproof/fixture"])], fields=fields
    )
    with nested_path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_verified_parquet(source, nested_pin)
    assert raised.value.args == ("parquet_field_type_mismatch",)


def test_decode_rejects_nulls_and_model_content_bounds(tmp_path):
    null_path, null_pin = write_parquet_and_pin(tmp_path, [{**swebench_row(), "patch": None}])
    with null_path.open("rb") as source, pytest.raises(ValidationError):
        decode_verified_parquet(source, null_pin)

    for field, value in (
        ("problem_statement", "x" * (128 * 1024 + 1)),
        ("patch", "x" * (512 * 1024 + 1)),
        ("test_patch", "x" * (512 * 1024 + 1)),
        ("hints_text", "x" * (1024 * 1024)),
    ):
        path, pin = write_parquet_and_pin(tmp_path, [swebench_row(**{field: value})])
        with path.open("rb") as source, pytest.raises(ValidationError):
            decode_verified_parquet(source, pin)

    criteria_path, criteria_pin = write_parquet_and_pin(
        tmp_path, [swebench_row(problem_statement="x" * (128 * 1024 + 1))]
    )
    with criteria_path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, criteria_pin)
    assert raised.value.args == ("manifest_row_mismatch",)


def test_decode_rejects_parquet_uncompressed_metadata_over_sixteen_mebibytes(tmp_path):
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row(hints_text="x" * (16 * 1024 * 1024))])
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, pin)
    assert raised.value.args == ("parquet_uncompressed_limit",)


def test_decode_sums_all_row_group_uncompressed_sizes(tmp_path):
    rows = [
        swebench_row(instance_id="scopeproof__fixture-1", hints_text="x" * (8 * 1024 * 1024)),
        swebench_row(instance_id="scopeproof__fixture-2", hints_text="y" * (8 * 1024 * 1024)),
    ]
    path, pin = write_parquet_and_pin(tmp_path, rows, row_group_size=1)
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, pin)
    assert raised.value.args == ("parquet_uncompressed_limit",)


def test_multibyte_utf8_problem_and_canonical_bounds_are_byte_based(tmp_path):
    accepted_problem = "é" * (64 * 1024)
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row(problem_statement=accepted_problem)])
    with path.open("rb") as source:
        assert decode_criteria_source_rows(source, pin)[0].problem_statement == accepted_problem

    rejected_problem = "é" * (64 * 1024 + 1)
    path, pin = write_parquet_and_pin(tmp_path, [swebench_row(problem_statement=rejected_problem)])
    with path.open("rb") as source, pytest.raises(R002SourceError) as raised:
        decode_criteria_source_rows(source, pin)
    assert raised.value.args == ("manifest_row_mismatch",)

    accepted = SWEbenchVerifiedRow.model_validate(swebench_row(hints_text="é" * 524_000))
    assert len(canonical_json_bytes(accepted)) <= 1024 * 1024
    with pytest.raises(ValidationError):
        SWEbenchVerifiedRow.model_validate(swebench_row(hints_text="é" * 524_288))


def test_selection_is_repository_balanced_and_hash_ranked():
    rows = selection_rows()
    selected = select_r002_rows(rows, SOURCE_SHA)
    assert len(selected) == 20
    assert len({row.repo for row in selected}) == 12
    assert max(Counter(row.repo for row in selected).values()) == 2
    assert [row.instance_id for row in selected] == sorted(row.instance_id for row in rows)
    assert [row.instance_id for row in select_r002_criteria_source_rows(rows, SOURCE_SHA)] == [
        row.instance_id for row in selected
    ]

    extra = SWEbenchVerifiedRow.model_validate(
        swebench_row(repo="alpha/one", instance_id="alpha__one-99")
    )
    expected = min(
        [row for row in rows if row.repo == "alpha/one"] + [extra],
        key=lambda row: sha256(f"{SOURCE_SHA}:{row.instance_id}".encode()).hexdigest(),
    )
    full_rows = [*rows, extra]
    assert expected in select_r002_rows(full_rows, SOURCE_SHA)
    assert len(select_r002_rows(full_rows, SOURCE_SHA)) == 20


def test_selection_is_permutation_stable_and_outcome_blind():
    rows = selection_rows()
    baseline = [row.instance_id for row in select_r002_rows(rows, SOURCE_SHA)]
    reordered = list(reversed(rows))
    assert [row.instance_id for row in select_r002_rows(reordered, SOURCE_SHA)] == baseline
    outcome_mutated = [
        row.model_copy(update={"patch": "different patch", "test_patch": "different tests"})
        for row in rows
    ]
    assert [row.instance_id for row in select_r002_rows(outcome_mutated, SOURCE_SHA)] == baseline


def _underrepresented_repositories() -> list[SWEbenchVerifiedRow]:
    return selection_rows()[:-1]


def _overrepresented_repositories() -> list[SWEbenchVerifiedRow]:
    extra = SWEbenchVerifiedRow.model_validate(
        swebench_row(repo="mike/one", instance_id="mike__one-1")
    )
    return [*selection_rows(), extra]


@pytest.mark.parametrize(
    "rows_factory", [_underrepresented_repositories, _overrepresented_repositories]
)
def test_selection_requires_exactly_twelve_repositories(rows_factory):
    with pytest.raises(R002SourceError) as raised:
        select_r002_rows(rows_factory(), SOURCE_SHA)
    assert raised.value.args == ("repository_count_mismatch",)


def test_selection_rejects_duplicate_identities_and_unsatisfied_quotas():
    rows = selection_rows()
    duplicate = rows.copy()
    duplicate[-1] = duplicate[-1].model_copy(update={"instance_id": duplicate[0].instance_id})
    with pytest.raises(R002SourceError) as raised:
        select_r002_rows(duplicate, SOURCE_SHA)
    assert raised.value.args == ("unique_instance_count_mismatch",)

    one_per_repository = list({row.repo: row for row in rows}.values())
    assert len(one_per_repository) == 12
    with pytest.raises(R002SourceError) as raised:
        select_r002_rows(one_per_repository, SOURCE_SHA)
    assert raised.value.args == ("manifest_selection_mismatch",)


def test_manifest_validation_checks_selection_fixed_row_identity_and_projection():
    rows = selection_rows()
    manifest = make_manifest(rows)
    selected = validate_manifest_rows(manifest, rows)
    criteria_rows = [
        SWEbenchCriteriaSourceRow.model_validate(
            {
                "repo": row.repo,
                "instance_id": row.instance_id,
                "base_commit": row.base_commit,
                "problem_statement": row.problem_statement,
                "difficulty": row.difficulty,
            }
        )
        for row in rows
    ]
    criteria_selected = validate_manifest_criteria_sources(manifest, criteria_rows)
    case_ids = [case.instance_id for case in manifest.cases]
    assert [row.instance_id for row in selected] == case_ids
    assert [row.instance_id for row in criteria_selected] == case_ids
    assert all(not hasattr(row, "patch") for row in criteria_selected)

    wrong_selection = manifest.model_copy(update={"cases": tuple(reversed(manifest.cases))})
    with pytest.raises(R002SourceError) as raised:
        validate_manifest_rows(wrong_selection, rows)
    assert raised.value.args == ("manifest_selection_mismatch",)

    wrong_case = manifest.cases[0].model_copy(update={"row_sha256": "0" * 64})
    wrong_row = manifest.model_copy(update={"cases": (wrong_case, *manifest.cases[1:])})
    with pytest.raises(R002SourceError) as raised:
        validate_manifest_rows(wrong_row, rows)
    assert raised.value.args == ("manifest_row_mismatch",)

    changed_problem = criteria_rows.copy()
    changed_problem[0] = changed_problem[0].model_copy(update={"problem_statement": "changed"})
    with pytest.raises(R002SourceError) as raised:
        validate_manifest_criteria_sources(manifest, changed_problem)
    assert raised.value.args == ("manifest_row_mismatch",)


def test_manifest_case_binds_instance_pr_suffix_and_hashes():
    row = SWEbenchVerifiedRow.model_validate(swebench_row())
    case = manifest_case_from_row("R002-001", 3, row, "c" * 40)
    assert case == R002CaseManifest(
        case_id="R002-001",
        instance_id="scopeproof__fixture-1",
        repository="scopeproof/fixture",
        pr_number=1,
        pr_url="https://github.com/scopeproof/fixture/pull/1",
        dataset_base_commit="a" * 40,
        verified_pr_head_sha="c" * 40,
        row_index=3,
        difficulty="<15 min fix",
        row_sha256=sha256(canonical_json_bytes(row)).hexdigest(),
        problem_statement_sha256=sha256(row.problem_statement.encode()).hexdigest(),
        patch_sha256=sha256(row.patch.encode()).hexdigest(),
        test_patch_sha256=sha256(row.test_patch.encode()).hexdigest(),
    )
    bad = row.model_copy(update={"instance_id": "not-a-pr-suffix"})
    with pytest.raises(R002SourceError) as raised:
        manifest_case_from_row("R002-001", 3, bad, "c" * 40)
    assert raised.value.args == ("instance_pr_suffix_mismatch",)


def _changed_case_value(field: str):
    if field == "row_index":
        return 99
    if field == "dataset_base_commit":
        return "0" * 40
    if field == "difficulty":
        return "changed"
    return "0" * 64


@pytest.mark.parametrize(
    "field",
    [
        "row_index",
        "dataset_base_commit",
        "difficulty",
        "row_sha256",
        "problem_statement_sha256",
        "patch_sha256",
        "test_patch_sha256",
    ],
)
def test_full_manifest_validator_checks_each_source_bound_field(field):
    rows = selection_rows()
    manifest = make_manifest(rows)
    case = manifest.cases[0]
    replacement = _changed_case_value(field)
    changed_case = case.model_copy(update={field: replacement})
    changed_manifest = manifest.model_copy(update={"cases": (changed_case, *manifest.cases[1:])})
    with pytest.raises(R002SourceError) as raised:
        validate_manifest_rows(changed_manifest, rows)
    assert raised.value.args == ("manifest_row_mismatch",)


@pytest.mark.parametrize(
    "field",
    ["row_index", "dataset_base_commit", "difficulty", "problem_statement_sha256"],
)
def test_criteria_manifest_validator_checks_each_projected_field(field):
    rows = selection_rows()
    manifest = make_manifest(rows)
    criteria_rows = [
        SWEbenchCriteriaSourceRow.model_validate(
            {
                "repo": row.repo,
                "instance_id": row.instance_id,
                "base_commit": row.base_commit,
                "problem_statement": row.problem_statement,
                "difficulty": row.difficulty,
            }
        )
        for row in rows
    ]
    case = manifest.cases[0]
    replacement = _changed_case_value(field)
    changed_case = case.model_copy(update={field: replacement})
    changed_manifest = manifest.model_copy(update={"cases": (changed_case, *manifest.cases[1:])})
    with pytest.raises(R002SourceError) as raised:
        validate_manifest_criteria_sources(changed_manifest, criteria_rows)
    assert raised.value.args == ("manifest_row_mismatch",)
