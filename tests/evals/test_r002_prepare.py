"""Controlled-transport tests for bounded R-002 preparation."""

from __future__ import annotations

import json
import socket
from hashlib import sha256
from pathlib import Path

import httpx
import pytest

from scopeproof_core.evals import r002_prepare
from scopeproof_core.evals.r002_cache import R002Cache
from scopeproof_core.evals.r002_models import (
    R002CaseManifest,
    R002CriteriaSet,
    R002CriteriaSourceIndex,
    R002RequestKind,
    R002SourceManifest,
    SWEbenchCriteriaSourceRow,
    SWEbenchVerifiedRow,
    canonical_json_bytes,
    canonical_sha256,
)
from scopeproof_core.evals.r002_prepare import (
    R002NetworkPolicyError,
    R002ReadOnlyClient,
    _prepare_criteria_sources_from_manifest,
    _prepare_evidence_from_inputs,
    _write_all,
    validate_request_target,
)


@pytest.fixture
def manifest(r002_manifest_payload: dict[str, object]) -> R002SourceManifest:
    return R002SourceManifest.model_validate_json(json.dumps(r002_manifest_payload))


@pytest.fixture
def case(manifest: R002SourceManifest) -> R002CaseManifest:
    return manifest.cases[0]


def _response(
    status: int,
    *,
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> httpx.Response:
    return httpx.Response(
        status,
        headers=headers,
        stream=httpx.ByteStream(body),
    )


@pytest.fixture(autouse=True)
def _forbid_live_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_connect(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("R-002 preparation tests must use MockTransport")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    monkeypatch.setattr(socket, "getaddrinfo", fail_connect)


@pytest.mark.parametrize(
    "url",
    [
        "http://huggingface.co/source",
        "https://user:secret@huggingface.co/source",
        "https://127.0.0.1/source",
        "https://example.com/source",
        "https://huggingface.co:444/source",
        "https://huggingface.co/source#fragment",
    ],
)
def test_request_target_rejects_unsafe_common_urls(
    url: str, case: R002CaseManifest
) -> None:
    with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
        validate_request_target(
            url=url,
            request_kind=R002RequestKind.DATASET,
            case=case,
        )


def test_request_targets_are_exact_for_github_and_signed_hf(
    case: R002CaseManifest,
) -> None:
    validate_request_target(
        url=f"https://api.github.com/repos/{case.repository}/pulls/{case.pr_number}",
        request_kind=R002RequestKind.PR_METADATA,
        case=case,
    )
    validate_request_target(
        url=(
            f"https://raw.githubusercontent.com/{case.repository}/"
            f"{case.verified_pr_head_sha}/src/a.py"
        ),
        request_kind=R002RequestKind.HEAD_FILE,
        case=case,
    )
    validate_request_target(
        url="https://cdn-lfs.hf.co/object?signature=opaque",
        request_kind=R002RequestKind.DATASET,
        allow_signed_hf_query=True,
    )
    for url, kind in (
        (
            f"https://api.github.com/repos/{case.repository}/pulls/{case.pr_number}?x=1",
            R002RequestKind.PR_METADATA,
        ),
        (
            f"https://raw.githubusercontent.com/{case.repository}/"
            f"{case.verified_pr_head_sha}/../unsafe",
            R002RequestKind.HEAD_FILE,
        ),
        (
            "https://huggingface.co/object?signature=initial",
            R002RequestKind.DATASET,
        ),
    ):
        with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
            validate_request_target(url=url, request_kind=kind, case=case)


def test_dataset_download_streams_exact_bytes_into_unlinked_scratch(
    tmp_path: Path, manifest: R002SourceManifest
) -> None:
    payload = b"fixture parquet bytes"
    source = manifest.source.model_copy(
        update={
            "byte_length": len(payload),
            "sha256": sha256(payload).hexdigest(),
        }
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(
            200,
            headers={
                "Content-Length": str(len(payload)),
                "Content-Encoding": "identity",
            },
            body=payload,
        )

    client = R002ReadOnlyClient(httpx.MockTransport(handler))
    try:
        with client.download_dataset(source, R002Cache(tmp_path / "cache")) as handle:
            assert handle.read() == payload
            assert not any(
                item.name.startswith(".r002-scratch-")
                for item in (tmp_path / "cache").iterdir()
            )
    finally:
        client.close()
    assert [request.method for request in requests] == ["GET"]
    assert requests[0].headers["accept-encoding"] == "identity"


def test_dataset_redirects_are_bounded_and_queries_stay_on_allowed_hosts(
    tmp_path: Path, manifest: R002SourceManifest
) -> None:
    payload = b"x"
    source = manifest.source.model_copy(
        update={"byte_length": 1, "sha256": sha256(payload).hexdigest()}
    )
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if len(seen) <= 3:
            return _response(
                302,
                headers={"Location": f"https://cdn-lfs.hf.co/object-{len(seen)}?sig=secret"},
            )
        return _response(
            200, headers={"Content-Length": "1"}, body=payload
        )

    client = R002ReadOnlyClient(httpx.MockTransport(handler))
    try:
        with client.download_dataset(source, R002Cache(tmp_path / "cache")) as handle:
            assert handle.read() == payload
    finally:
        client.close()
    assert len(seen) == 4

    def endless(request: httpx.Request) -> httpx.Response:
        return _response(
            302, headers={"Location": "https://cdn-lfs.hf.co/next?sig=secret"}
        )

    client = R002ReadOnlyClient(httpx.MockTransport(endless))
    try:
        with (
            pytest.raises(R002NetworkPolicyError, match="redirect_limit"),
            client.download_dataset(source, R002Cache(tmp_path / "second-cache")),
        ):
            pass
    finally:
        client.close()


@pytest.mark.parametrize(
    ("headers", "body", "reason"),
    [
        ({}, b"x", "content_length_invalid"),
        ({"Content-Length": "2"}, b"x", "content_length_invalid"),
        (
            {"Content-Length": "1", "Content-Encoding": "gzip"},
            b"x",
            "content_encoding",
        ),
        ({"Content-Length": "1"}, b"y", "dataset_identity_mismatch"),
    ],
)
def test_dataset_identity_and_encoding_fail_closed(
    tmp_path: Path,
    manifest: R002SourceManifest,
    headers: dict[str, str],
    body: bytes,
    reason: str,
) -> None:
    source = manifest.source.model_copy(
        update={"byte_length": 1, "sha256": sha256(b"x").hexdigest()}
    )
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(200, headers=headers, body=body)
        )
    )
    try:
        with (
            pytest.raises(R002NetworkPolicyError, match=reason),
            client.download_dataset(source, R002Cache(tmp_path / "cache")),
        ):
            pass
    finally:
        client.close()


def _pr_payload(case: R002CaseManifest) -> dict[str, object]:
    return {
        "number": case.pr_number,
        "state": "closed",
        "merged": True,
        "base": {
            "sha": case.dataset_base_commit,
            "repo": {"full_name": case.repository},
        },
        "head": {"sha": case.verified_pr_head_sha},
    }


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        ({"state": "open"}, "pr_not_merged"),
        ({"merged": False}, "pr_not_merged"),
        ({"number": 999}, "pr_identity_mismatch"),
        ({"base": {"sha": "0" * 40, "repo": {"full_name": "alpha/one"}}}, "pr_base_sha_mismatch"),
        ({"head": {"sha": "0" * 40}}, "pr_head_sha_mismatch"),
    ],
)
def test_pr_metadata_is_bounded_and_cross_bound(
    case: R002CaseManifest, mutation: dict[str, object], reason: str
) -> None:
    payload = {**_pr_payload(case), **mutation}
    body = json.dumps(payload).encode()
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(
                200, headers={"Content-Length": str(len(body))}, body=body
            )
        )
    )
    try:
        with pytest.raises(R002NetworkPolicyError, match=reason):
            client.validate_pr(case)
    finally:
        client.close()


def test_pr_and_head_success_use_only_exact_get_targets(
    case: R002CaseManifest,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "api.github.com":
            body = json.dumps(_pr_payload(case)).encode()
        else:
            body = b"head\n"
        return _response(
            200, headers={"Content-Length": str(len(body))}, body=body
        )

    client = R002ReadOnlyClient(httpx.MockTransport(handler))
    try:
        client.validate_pr(case)
        assert client.fetch_head_file(case, "src/a.py") == b"head\n"
    finally:
        client.close()
    assert [request.method for request in seen] == ["GET", "GET"]
    assert str(seen[0].url).endswith(
        f"/repos/{case.repository}/pulls/{case.pr_number}"
    )
    assert str(seen[1].url).endswith(
        f"/{case.repository}/{case.verified_pr_head_sha}/src/a.py"
    )


def test_request_count_and_declared_head_limit_fail_before_body_read(
    case: R002CaseManifest,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = json.dumps(_pr_payload(case)).encode()
        return _response(
            200, headers={"Content-Length": str(len(body))}, body=body
        )

    client = R002ReadOnlyClient(httpx.MockTransport(handler))
    try:
        for _ in range(20):
            client.validate_pr(case)
        with pytest.raises(R002NetworkPolicyError, match="request_limit"):
            client.validate_pr(case)
    finally:
        client.close()
    assert calls == 20

    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(
                200, headers={"Content-Length": str(4 * 1024 * 1024 + 1)}
            )
        )
    )
    try:
        with pytest.raises(R002NetworkPolicyError, match="head_file_limit"):
            client.fetch_head_file(case, "src/a.py")
    finally:
        client.close()


def test_problem_only_phase_publishes_only_selected_problem_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
) -> None:
    dataset = b"x"
    rows = tuple(
        SWEbenchCriteriaSourceRow(
            repo=case.repository,
            instance_id=case.instance_id,
            base_commit=case.dataset_base_commit,
            problem_statement=f"Problem statement {number}.",
            difficulty=case.difficulty,
        )
        for number, case in enumerate(manifest.cases, start=1)
    )
    cases = tuple(
        case.model_copy(
            update={
                "problem_statement_sha256": sha256(
                    row.problem_statement.encode()
                ).hexdigest()
            }
        )
        for case, row in zip(manifest.cases, rows, strict=True)
    )
    prepared_manifest = manifest.model_copy(
        update={
            "source": manifest.source.model_copy(
                update={
                    "byte_length": len(dataset),
                    "sha256": sha256(dataset).hexdigest(),
                }
            ),
            "cases": cases,
        }
    )
    monkeypatch.setattr(
        r002_prepare,
        "decode_criteria_source_rows",
        lambda source, pin: list(rows),
    )
    monkeypatch.setattr(
        r002_prepare,
        "validate_manifest_criteria_sources",
        lambda supplied_manifest, supplied_rows: list(supplied_rows),
    )
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(
            200,
            headers={"Content-Length": str(len(dataset))},
            body=dataset,
        )

    cache_root = tmp_path / "cache"
    result = _prepare_criteria_sources_from_manifest(
        manifest=prepared_manifest,
        cache_root=cache_root,
        transport=httpx.MockTransport(handler),
    )

    assert result.executed_case_count == 20
    assert len(R002Cache(cache_root).load_criteria_source_index().cases) == 20
    assert not (cache_root / "cache-index.json").exists()
    assert {request.url.host for request in requests} == {"huggingface.co"}
    assert not any("github" in str(request.url) for request in requests)

    marker_path = cache_root / "criteria-source-index.json"
    before = marker_path.read_bytes()
    real_write = R002Cache.write_bytes
    writes = 0

    def fail_last_problem(self, relative_name: str, data: bytes):
        nonlocal writes
        writes += 1
        if writes == 20:
            raise RuntimeError("controlled final problem failure")
        return real_write(self, relative_name, data)

    with monkeypatch.context() as scoped:
        scoped.setattr(R002Cache, "write_bytes", fail_last_problem)
        with pytest.raises(RuntimeError, match="controlled final problem failure"):
            _prepare_criteria_sources_from_manifest(
                manifest=prepared_manifest,
                cache_root=cache_root,
                transport=httpx.MockTransport(handler),
            )
    assert marker_path.read_bytes() == before

    with monkeypatch.context() as scoped:
        scoped.setattr(
            R002ReadOnlyClient,
            "close",
            lambda self: (_ for _ in ()).throw(RuntimeError("secret cleanup detail")),
        )
        with pytest.raises(R002NetworkPolicyError, match="network_failure"):
            _prepare_criteria_sources_from_manifest(
                manifest=prepared_manifest,
                cache_root=cache_root,
                transport=httpx.MockTransport(handler),
            )
    assert marker_path.read_bytes() == before


def _evidence_inputs(
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> tuple[
    R002SourceManifest,
    tuple[SWEbenchCriteriaSourceRow, ...],
    tuple[SWEbenchVerifiedRow, ...],
    R002CriteriaSet,
]:
    source_rows: list[SWEbenchCriteriaSourceRow] = []
    verified_rows: list[SWEbenchVerifiedRow] = []
    cases: list[R002CaseManifest] = []
    for number, case in enumerate(manifest.cases, start=1):
        problem = f"Problem statement {number}."
        path = f"src/file_{number}.py"
        patch = (
            f"diff --git a/{path} b/{path}\n"
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        )
        row = SWEbenchVerifiedRow(
            repo=case.repository,
            instance_id=case.instance_id,
            base_commit=case.dataset_base_commit,
            patch=patch,
            test_patch="",
            problem_statement=problem,
            hints_text="",
            created_at="2026-01-01",
            version="1",
            FAIL_TO_PASS="[]",
            PASS_TO_PASS="[]",
            environment_setup_commit="",
            difficulty=case.difficulty,
        )
        verified_rows.append(row)
        source_rows.append(
            SWEbenchCriteriaSourceRow(
                repo=row.repo,
                instance_id=row.instance_id,
                base_commit=row.base_commit,
                problem_statement=problem,
                difficulty=row.difficulty,
            )
        )
        cases.append(
            case.model_copy(
                update={
                    "row_sha256": sha256(canonical_json_bytes(row)).hexdigest(),
                    "problem_statement_sha256": sha256(problem.encode()).hexdigest(),
                    "patch_sha256": sha256(patch.encode()).hexdigest(),
                    "test_patch_sha256": sha256(b"").hexdigest(),
                }
            )
        )
    prepared_manifest = manifest.model_copy(
        update={"cases": tuple(cases)}
    )
    criteria_payload = json.loads(json.dumps(r002_criteria_payload))
    criteria_payload["source_manifest_sha256"] = canonical_sha256(prepared_manifest)
    for payload_case, manifest_case in zip(
        criteria_payload["cases"], prepared_manifest.cases, strict=True
    ):
        payload_case["problem_statement_sha256"] = manifest_case.problem_statement_sha256
    criteria = R002CriteriaSet.model_validate_json(json.dumps(criteria_payload))
    return (
        prepared_manifest,
        tuple(source_rows),
        tuple(verified_rows),
        criteria,
    )


def test_evidence_phase_prepares_all_cases_and_publishes_index_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> None:
    prepared_manifest, source_rows, verified_rows, criteria = _evidence_inputs(
        manifest, r002_criteria_payload
    )
    dataset = b"x"
    prepared_manifest = prepared_manifest.model_copy(
        update={
            "source": prepared_manifest.source.model_copy(
                update={
                    "byte_length": 1,
                    "sha256": sha256(dataset).hexdigest(),
                }
            )
        }
    )
    criteria = criteria.model_copy(
        update={"source_manifest_sha256": canonical_sha256(prepared_manifest)}
    )
    monkeypatch.setattr(
        r002_prepare,
        "decode_criteria_source_rows",
        lambda source, pin: list(source_rows),
    )
    monkeypatch.setattr(
        r002_prepare,
        "validate_manifest_criteria_sources",
        lambda supplied_manifest, rows: list(rows),
    )
    monkeypatch.setattr(
        r002_prepare,
        "decode_verified_parquet",
        lambda source, pin: list(verified_rows),
    )
    monkeypatch.setattr(
        r002_prepare,
        "validate_manifest_rows",
        lambda supplied_manifest, rows: list(rows),
    )
    by_pr = {
        (case.repository, case.pr_number): case for case in prepared_manifest.cases
    }
    fail_last = False

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "huggingface.co":
            return _response(200, headers={"Content-Length": "1"}, body=dataset)
        if request.url.host == "api.github.com":
            parts = request.url.path.split("/")
            case = by_pr[(f"{parts[2]}/{parts[3]}", int(parts[-1]))]
            if fail_last and case.case_id == "R002-020":
                return _response(503)
            body = json.dumps(_pr_payload(case)).encode()
            return _response(
                200, headers={"Content-Length": str(len(body))}, body=body
            )
        assert request.url.host == "raw.githubusercontent.com"
        return _response(200, headers={"Content-Length": "4"}, body=b"new\n")

    cache_root = tmp_path / "cache"
    transport = httpx.MockTransport(handler)
    criteria_result = _prepare_criteria_sources_from_manifest(
        manifest=prepared_manifest,
        cache_root=cache_root,
        transport=transport,
    )
    assert criteria_result.executed_case_count == 20

    result = _prepare_evidence_from_inputs(
        manifest=prepared_manifest,
        criteria=criteria,
        cache_root=cache_root,
        transport=transport,
    )
    index = R002Cache(cache_root).load_index()
    assert result.executed_case_count == 20
    assert result.failed_case_count == 0
    assert result.head_file_count == 20
    assert result.candidate_line_count == 20
    assert len(index.cases) == 20
    assert all(case.head_files for case in index.cases)

    marker_path = cache_root / "cache-index.json"
    before = marker_path.read_bytes()
    fail_last = True
    with pytest.raises(R002NetworkPolicyError, match="http_status"):
        _prepare_evidence_from_inputs(
            manifest=prepared_manifest,
            criteria=criteria,
            cache_root=cache_root,
            transport=httpx.MockTransport(handler),
        )
    assert marker_path.read_bytes() == before

    fail_last = False
    with monkeypatch.context() as scoped:
        scoped.setattr(
            R002ReadOnlyClient,
            "close",
            lambda self: (_ for _ in ()).throw(RuntimeError("secret cleanup detail")),
        )
        with pytest.raises(R002NetworkPolicyError, match="network_failure"):
            _prepare_evidence_from_inputs(
                manifest=prepared_manifest,
                criteria=criteria,
                cache_root=cache_root,
                transport=httpx.MockTransport(handler),
            )
    assert marker_path.read_bytes() == before


def test_evidence_phase_rejects_criteria_drift_before_constructing_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> None:
    _, _, _, criteria = _evidence_inputs(manifest, r002_criteria_payload)
    constructed = False

    class ClientProbe:
        def __init__(self, *args, **kwargs) -> None:
            nonlocal constructed
            constructed = True

    monkeypatch.setattr(r002_prepare, "R002ReadOnlyClient", ClientProbe)
    with pytest.raises(r002_prepare.R002PreparationError, match="criteria_manifest_drift"):
        _prepare_evidence_from_inputs(
            manifest=manifest,
            criteria=criteria.model_copy(
                update={"source_manifest_sha256": "f" * 64}
            ),
            cache_root=tmp_path / "cache",
            transport=httpx.MockTransport(lambda request: pytest.fail("network")),
        )
    assert constructed is False


def test_network_and_response_failures_use_stable_closed_reasons(
    tmp_path: Path,
    manifest: R002SourceManifest,
    case: R002CaseManifest,
) -> None:
    with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
        validate_request_target(
            url=123,  # type: ignore[arg-type]
            request_kind=R002RequestKind.DATASET,
        )
    with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
        validate_request_target(
            url="https://huggingface.co:invalid/source",
            request_kind=R002RequestKind.DATASET,
        )
    with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
        validate_request_target(
            url="https://[invalid/source",
            request_kind=R002RequestKind.DATASET,
        )
    with pytest.raises(R002NetworkPolicyError, match="unsafe_request_target"):
        validate_request_target(
            url="https://api.github.com/repos/alpha/one/pulls/1",
            request_kind=R002RequestKind.PR_METADATA,
            case=None,
        )

    source = manifest.source.model_copy(
        update={"byte_length": 1, "sha256": sha256(b"x").hexdigest()}
    )
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("offline"))
        )
    )
    try:
        with (
            pytest.raises(R002NetworkPolicyError, match="network_failure"),
            client.download_dataset(source, R002Cache(tmp_path / "network-cache")),
        ):
            pass
    finally:
        client.close()

    client = R002ReadOnlyClient(
        httpx.MockTransport(lambda request: pytest.fail("send must not run"))
    )
    client._client.build_request = lambda *args, **kwargs: (  # type: ignore[method-assign]
        (_ for _ in ()).throw(ValueError("signed query detail"))
    )
    try:
        with (
            pytest.raises(R002NetworkPolicyError, match="network_failure"),
            client.download_dataset(source, R002Cache(tmp_path / "build-cache")),
        ):
            pass
    finally:
        client.close()

    malformed_redirect = _response(
        302, headers={"Location": "https://[invalid/signed?secret=value"}
    )
    client = R002ReadOnlyClient(
        httpx.MockTransport(lambda request: malformed_redirect)
    )
    try:
        with (
            pytest.raises(
                R002NetworkPolicyError, match="redirect_location_invalid"
            ),
            client.download_dataset(
                source, R002Cache(tmp_path / "redirect-parse-cache")
            ),
        ):
            pass
    finally:
        client.close()

    for response, reason in (
        (_response(302), "redirect_location_invalid"),
        (_response(503), "http_status"),
        (
            _response(200, headers={"Content-Length": "1"}, body=b"xx"),
            "dataset_identity_mismatch",
        ),
    ):
        client = R002ReadOnlyClient(
            httpx.MockTransport(lambda request, value=response: value)
        )
        try:
            with (
                pytest.raises(R002NetworkPolicyError, match=reason),
                client.download_dataset(
                    source, R002Cache(tmp_path / f"cache-{reason}")
                ),
            ):
                pass
        finally:
            client.close()

    for operation in (
        lambda client: client.validate_pr(case),
        lambda client: client.fetch_head_file(case, "src/a.py"),
    ):
        client = R002ReadOnlyClient(
            httpx.MockTransport(lambda request: _response(404))
        )
        try:
            with pytest.raises(R002NetworkPolicyError, match="http_status"):
                operation(client)
        finally:
            client.close()


def test_response_cleanup_is_sanitized_and_preserves_primary_policy_error(
    tmp_path: Path,
    manifest: R002SourceManifest,
) -> None:
    source = manifest.source.model_copy(
        update={"byte_length": 1, "sha256": sha256(b"x").hexdigest()}
    )
    for status, expected in ((200, "network_failure"), (503, "http_status")):
        response = _response(
            status,
            headers={"Content-Length": "1"} if status == 200 else None,
            body=b"x" if status == 200 else b"",
        )
        cleanup_error: BaseException = (
            RuntimeError("secret cleanup detail")
            if status == 200
            else KeyboardInterrupt("secret cleanup interrupt")
        )
        response.close = lambda value=cleanup_error: (  # type: ignore[method-assign]
            (_ for _ in ()).throw(value)
        )
        client = R002ReadOnlyClient(
            httpx.MockTransport(lambda request, value=response: value)
        )
        try:
            with (
                pytest.raises(R002NetworkPolicyError, match=expected),
                client.download_dataset(
                    source, R002Cache(tmp_path / f"response-close-{status}")
                ),
            ):
                pass
        finally:
            client.close()


def test_declared_length_and_scratch_short_writes_fail_closed(
    tmp_path: Path,
    manifest: R002SourceManifest,
) -> None:
    source = manifest.source.model_copy(
        update={"byte_length": 1, "sha256": sha256(b"x").hexdigest()}
    )
    response = _response(
        200,
        headers={"Content-Length": "9" * 5000},
        body=b"x",
    )
    client = R002ReadOnlyClient(
        httpx.MockTransport(lambda request: response)
    )
    try:
        with (
            pytest.raises(R002NetworkPolicyError, match="content_length_invalid"),
            client.download_dataset(
                source, R002Cache(tmp_path / "oversized-length-cache")
            ),
        ):
            pass
    finally:
        client.close()

    class ShortWriter:
        def __init__(self, *, progress: int) -> None:
            self.progress = progress
            self.body = bytearray()

        def write(self, value: memoryview) -> int:
            written = min(self.progress, len(value))
            self.body.extend(value[:written])
            return written

    writer = ShortWriter(progress=1)
    _write_all(writer, b"complete")
    assert bytes(writer.body) == b"complete"

    with pytest.raises(R002NetworkPolicyError, match="network_failure"):
        _write_all(ShortWriter(progress=0), b"blocked")


def test_phase_cleanup_preserves_primary_asynchronous_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
) -> None:
    dataset = b"x"
    prepared_manifest = manifest.model_copy(
        update={
            "source": manifest.source.model_copy(
                update={
                    "byte_length": 1,
                    "sha256": sha256(dataset).hexdigest(),
                }
            )
        }
    )
    closed = False
    real_close = R002ReadOnlyClient.close

    def tracked_close(self: R002ReadOnlyClient) -> None:
        nonlocal closed
        closed = True
        real_close(self)
        raise KeyboardInterrupt("cleanup interrupt")

    monkeypatch.setattr(R002ReadOnlyClient, "close", tracked_close)
    monkeypatch.setattr(
        r002_prepare,
        "decode_criteria_source_rows",
        lambda source, pin: (_ for _ in ()).throw(SystemExit("primary interrupt")),
    )
    with pytest.raises(SystemExit, match="primary interrupt"):
        _prepare_criteria_sources_from_manifest(
            manifest=prepared_manifest,
            cache_root=tmp_path / "interrupt-cache",
            transport=httpx.MockTransport(
                lambda request: _response(
                    200, headers={"Content-Length": "1"}, body=dataset
                )
            ),
        )
    assert closed is True


def test_invalid_json_and_head_aggregate_limits_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    case: R002CaseManifest,
) -> None:
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(
                200, headers={"Content-Length": "1"}, body=b"{"
            )
        )
    )
    try:
        with pytest.raises(R002NetworkPolicyError, match="response_invalid"):
            client.validate_pr(case)
    finally:
        client.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(r002_prepare, "_SIXTEEN_MIB", 1)
        client = R002ReadOnlyClient(
            httpx.MockTransport(
                lambda request: _response(
                    200, headers={"Content-Length": "2"}, body=b"xx"
                )
            )
        )
        try:
            with pytest.raises(R002NetworkPolicyError, match="head_case_limit"):
                client.fetch_head_file(case, "src/a.py")
        finally:
            client.close()

    with monkeypatch.context() as scoped:
        scoped.setattr(r002_prepare, "_PACK_LIMIT", 1)
        client = R002ReadOnlyClient(
            httpx.MockTransport(
                lambda request: _response(
                    200, headers={"Content-Length": "2"}, body=b"xx"
                )
            )
        )
        try:
            with pytest.raises(R002NetworkPolicyError, match="head_pack_limit"):
                client.fetch_head_file(case, "src/a.py")
        finally:
            client.close()


def test_public_preparation_wrappers_validate_before_delegation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> None:
    _, _, _, criteria = _evidence_inputs(manifest, r002_criteria_payload)
    criteria = criteria.model_copy(
        update={"source_manifest_sha256": canonical_sha256(manifest)}
    )
    marker = object()
    monkeypatch.setattr(r002_prepare, "load_source_manifest", lambda path: manifest)
    monkeypatch.setattr(
        r002_prepare,
        "_prepare_criteria_sources_from_manifest",
        lambda **kwargs: marker,
    )
    assert (
        r002_prepare.prepare_criteria_sources(
            manifest_path=tmp_path / "manifest.json",
            cache_root=tmp_path / "cache",
        )
        is marker
    )
    monkeypatch.setattr(
        r002_prepare,
        "load_confirmed_criteria",
        lambda path, manifest_hash: criteria,
    )
    monkeypatch.setattr(
        r002_prepare,
        "_prepare_evidence_from_inputs",
        lambda **kwargs: marker,
    )
    assert (
        r002_prepare.prepare_r002(
            manifest_path=tmp_path / "manifest.json",
            criteria_path=tmp_path / "criteria.json",
            cache_root=tmp_path / "cache",
        )
        is marker
    )


@pytest.mark.parametrize(
    ("headers", "body", "reason"),
    [
        ({"Content-Length": "invalid"}, b"{}", "content_length_invalid"),
        ({"Content-Length": "2"}, b"{", "response_invalid"),
        ({"Content-Length": "1"}, b"{}", "response_invalid"),
    ],
)
def test_bounded_json_body_rejects_length_disagreement(
    case: R002CaseManifest,
    headers: dict[str, str],
    body: bytes,
    reason: str,
) -> None:
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(200, headers=headers, body=body)
        )
    )
    try:
        with pytest.raises(R002NetworkPolicyError, match=reason):
            client.validate_pr(case)
    finally:
        client.close()


def test_unconfirmed_constructed_criteria_fails_before_cache_access(
    tmp_path: Path,
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> None:
    _, _, _, criteria = _evidence_inputs(manifest, r002_criteria_payload)
    unconfirmed = criteria.model_construct(
        **{
            **criteria.__dict__,
            "source_manifest_sha256": canonical_sha256(manifest),
            "benchmark_owner_confirmed": False,
        }
    )
    with pytest.raises(r002_prepare.R002PreparationError, match="criteria_not_confirmed"):
        _prepare_evidence_from_inputs(
            manifest=manifest,
            criteria=unconfirmed,
            cache_root=tmp_path / "missing-cache",
        )
    assert not (tmp_path / "missing-cache").exists()


def test_evidence_phase_rejects_mismatched_problem_cache_before_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    manifest: R002SourceManifest,
    r002_criteria_payload: dict[str, object],
) -> None:
    _, _, _, criteria = _evidence_inputs(manifest, r002_criteria_payload)
    criteria = criteria.model_copy(
        update={"source_manifest_sha256": canonical_sha256(manifest)}
    )
    mismatched = R002CriteriaSourceIndex.model_construct(
        source_sha256="0" * 64,
        manifest_sha256=canonical_sha256(manifest),
        complete=True,
        cases=(),
    )
    monkeypatch.setattr(
        R002Cache, "load_criteria_source_index", lambda self: mismatched
    )
    with pytest.raises(
        r002_prepare.R002PreparationError,
        match="criteria_source_index_mismatch",
    ):
        _prepare_evidence_from_inputs(
            manifest=manifest,
            criteria=criteria,
            cache_root=tmp_path / "cache",
        )


def test_head_stream_limits_apply_without_declared_length(
    monkeypatch: pytest.MonkeyPatch,
    case: R002CaseManifest,
) -> None:
    scenarios = (
        ("_FOUR_MIB", "head_file_limit"),
        ("_SIXTEEN_MIB", "head_case_limit"),
        ("_PACK_LIMIT", "head_pack_limit"),
    )
    for constant, reason in scenarios:
        with monkeypatch.context() as scoped:
            scoped.setattr(r002_prepare, constant, 1)
            client = R002ReadOnlyClient(
                httpx.MockTransport(
                    lambda request: _response(200, body=b"xx")
                )
            )
            try:
                with pytest.raises(R002NetworkPolicyError, match=reason):
                    client.fetch_head_file(case, "src/a.py")
            finally:
                client.close()


def test_exhausted_head_budgets_and_non_strict_pr_metadata_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    case: R002CaseManifest,
) -> None:
    for counter_name, counter_value, reason in (
        ("case", 16 * 1024 * 1024, "head_case_limit"),
        ("pack", 128 * 1024 * 1024, "head_pack_limit"),
    ):
        client = R002ReadOnlyClient(
            httpx.MockTransport(lambda request: _response(200))
        )
        if counter_name == "case":
            client._case_head_bytes[case.case_id] = counter_value
        else:
            client._pack_head_bytes = counter_value
        try:
            with pytest.raises(R002NetworkPolicyError, match=reason):
                client.fetch_head_file(case, "src/a.py")
        finally:
            client.close()

    payload = {**_pr_payload(case), "number": True}
    body = json.dumps(payload).encode()
    client = R002ReadOnlyClient(
        httpx.MockTransport(
            lambda request: _response(
                200, headers={"Content-Length": str(len(body))}, body=body
            )
        )
    )
    try:
        with pytest.raises(R002NetworkPolicyError, match="response_invalid"):
            client.validate_pr(case)
    finally:
        client.close()
