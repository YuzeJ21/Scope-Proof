"""Bounded, GET-only preparation for the R-002 engineering benchmark."""

from __future__ import annotations

import ipaddress
import json
from collections import Counter, defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from urllib.parse import SplitResult, quote, unquote, urljoin, urlsplit

import httpx

from scopeproof_core.evals.r002_cache import R002Cache
from scopeproof_core.evals.r002_diff import parse_case_diffs
from scopeproof_core.evals.r002_models import (
    R002_REQUEST_LIMITS,
    R002CachedCase,
    R002CachedHeadFile,
    R002CacheIndex,
    R002CaseManifest,
    R002CriteriaSet,
    R002CriteriaSourceCase,
    R002CriteriaSourceIndex,
    R002CriteriaSourcePreparationResult,
    R002Error,
    R002PreparationCaseResult,
    R002PreparationResult,
    R002RequestKind,
    R002SourceManifest,
    SWEbenchSourcePin,
    SWEbenchVerifiedRow,
    canonical_sha256,
    load_confirmed_criteria,
    load_source_manifest,
    validate_r002_logical_path,
)
from scopeproof_core.evals.r002_source import (
    decode_criteria_source_rows,
    decode_verified_parquet,
    validate_manifest_criteria_sources,
    validate_manifest_rows,
)
from scopeproof_core.evals.r002_verify import verify_case_head_files

_ONE_MIB = 1024 * 1024
_FOUR_MIB = 4 * _ONE_MIB
_SIXTEEN_MIB = 16 * _ONE_MIB
_PACK_LIMIT = 128 * _ONE_MIB
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


class R002NetworkPolicyError(R002Error):
    allowed_reason_codes = frozenset(
        {
            "content_encoding",
            "content_length_invalid",
            "dataset_identity_mismatch",
            "head_case_limit",
            "head_file_limit",
            "head_pack_limit",
            "http_status",
            "network_failure",
            "pr_base_sha_mismatch",
            "pr_head_sha_mismatch",
            "pr_identity_mismatch",
            "pr_not_merged",
            "redirect_limit",
            "redirect_location_invalid",
            "request_limit",
            "response_invalid",
            "unsafe_request_target",
        }
    )


class R002PreparationError(R002Error):
    allowed_reason_codes = frozenset(
        {
            "criteria_manifest_drift",
            "criteria_not_confirmed",
            "criteria_source_index_mismatch",
            "preparation_integrity_failed",
        }
    )


def _validated_url(url: str) -> SplitResult:
    if type(url) is not str:
        raise R002NetworkPolicyError("unsafe_request_target")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except Exception:
        raise R002NetworkPolicyError("unsafe_request_target") from None
    try:
        ipaddress.ip_address(hostname or "")
    except ValueError:
        pass
    else:
        raise R002NetworkPolicyError("unsafe_request_target")
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.fragment
    ):
        raise R002NetworkPolicyError("unsafe_request_target")
    return parsed


def validate_request_target(
    *,
    url: str,
    request_kind: R002RequestKind,
    case: R002CaseManifest | None = None,
    allow_signed_hf_query: bool = False,
) -> SplitResult:
    """Validate the complete target before any GET is constructed."""
    parsed = _validated_url(url)
    host = parsed.hostname or ""
    if request_kind is R002RequestKind.DATASET:
        if host != "huggingface.co" and not host.endswith(".hf.co"):
            raise R002NetworkPolicyError("unsafe_request_target")
        if parsed.query and not (
            allow_signed_hf_query and (host == "huggingface.co" or host.endswith(".hf.co"))
        ):
            raise R002NetworkPolicyError("unsafe_request_target")
    else:
        if parsed.query or case is None:
            raise R002NetworkPolicyError("unsafe_request_target")
        if request_kind is R002RequestKind.PR_METADATA:
            expected = f"/repos/{case.repository}/pulls/{case.pr_number}"
            if host != "api.github.com" or parsed.path != expected:
                raise R002NetworkPolicyError("unsafe_request_target")
        elif request_kind is R002RequestKind.HEAD_FILE:
            prefix = f"/{case.repository}/{case.verified_pr_head_sha}/"
            if host != "raw.githubusercontent.com" or not parsed.path.startswith(prefix):
                raise R002NetworkPolicyError("unsafe_request_target")
            logical_path = unquote(parsed.path.removeprefix(prefix))
            try:
                valid_path = validate_r002_logical_path(logical_path)
            except ValueError:
                raise R002NetworkPolicyError("unsafe_request_target") from None
            encoded_path = parsed.path.removeprefix(prefix)
            if valid_path != logical_path or quote(logical_path, safe="/") != encoded_path:
                raise R002NetworkPolicyError("unsafe_request_target")
        else:
            raise R002NetworkPolicyError("unsafe_request_target")
    return parsed


def _declared_length(response: httpx.Response, *, limit: int, required: bool) -> int | None:
    if response.headers.get("content-encoding", "").strip().lower() not in {"", "identity"}:
        raise R002NetworkPolicyError("content_encoding")
    raw = response.headers.get("content-length")
    if raw is None:
        if required:
            raise R002NetworkPolicyError("content_length_invalid")
        return None
    if not raw.isdecimal() or len(raw) > 20:
        raise R002NetworkPolicyError("content_length_invalid")
    try:
        value = int(raw)
    except ValueError:
        raise R002NetworkPolicyError("content_length_invalid") from None
    if value > limit:
        raise R002NetworkPolicyError("content_length_invalid")
    return value


def _bounded_body(response: httpx.Response, *, limit: int) -> bytes:
    declared = _declared_length(response, limit=limit, required=False)
    body = bytearray()
    try:
        for chunk in response.iter_raw():
            if len(chunk) > limit - len(body):
                raise R002NetworkPolicyError("response_invalid")
            body.extend(chunk)
    except R002NetworkPolicyError:
        raise
    except Exception:
        raise R002NetworkPolicyError("network_failure") from None
    if declared is not None and len(body) != declared:
        raise R002NetworkPolicyError("response_invalid")
    return bytes(body)


def _write_all(handle: object, chunk: bytes) -> None:
    view = memoryview(chunk)
    offset = 0
    try:
        while offset < len(view):
            written = handle.write(view[offset:])  # type: ignore[attr-defined]
            if type(written) is not int or written <= 0 or written > len(view) - offset:
                raise R002NetworkPolicyError("network_failure")
            offset += written
    except R002NetworkPolicyError:
        raise
    except Exception:
        raise R002NetworkPolicyError("network_failure") from None


class R002ReadOnlyClient:
    """A phase-local client with no generic public request method."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            follow_redirects=False,
            timeout=15.0,
            transport=transport,
            headers={
                "User-Agent": "ScopeProof-R002/1",
                "Accept": "application/json, application/octet-stream;q=0.9",
                "Accept-Encoding": "identity",
            },
        )
        self.request_count_by_kind: Counter[R002RequestKind] = Counter()
        self._case_head_bytes: defaultdict[str, int] = defaultdict(int)
        self._pack_head_bytes = 0

    def close(self) -> None:
        self._client.close()

    @contextmanager
    def _stream_once(
        self,
        url: str,
        request_kind: R002RequestKind,
        *,
        case: R002CaseManifest | None = None,
        allow_signed_hf_query: bool = False,
    ) -> Iterator[httpx.Response]:
        validate_request_target(
            url=url,
            request_kind=request_kind,
            case=case,
            allow_signed_hf_query=allow_signed_hf_query,
        )
        self.request_count_by_kind[request_kind] += 1
        if self.request_count_by_kind[request_kind] > R002_REQUEST_LIMITS[request_kind]:
            raise R002NetworkPolicyError("request_limit")
        try:
            request = self._client.build_request("GET", url)
            response = self._client.send(request, stream=True)
        except Exception:
            raise R002NetworkPolicyError("network_failure") from None
        primary: BaseException | None = None
        try:
            yield response
        except BaseException as error:
            primary = error
        finally:
            try:
                response.close()
            except BaseException as cleanup_error:
                if primary is None:
                    if isinstance(cleanup_error, Exception):
                        raise R002NetworkPolicyError("network_failure") from None
                    raise
        if primary is not None:
            raise primary.with_traceback(primary.__traceback__)

    @contextmanager
    def download_dataset(
        self, source: SWEbenchSourcePin, cache: R002Cache
    ) -> Iterator[object]:
        initial = validate_request_target(
            url=source.source_url, request_kind=R002RequestKind.DATASET
        )
        if initial.query:
            raise R002NetworkPolicyError("unsafe_request_target")
        url = source.source_url
        redirects = 0
        while True:
            with self._stream_once(
                url,
                R002RequestKind.DATASET,
                allow_signed_hf_query=redirects > 0,
            ) as response:
                if response.status_code in _REDIRECT_CODES:
                    if redirects >= 3:
                        raise R002NetworkPolicyError("redirect_limit")
                    location = response.headers.get("location")
                    if not location or len(location) > 8192:
                        raise R002NetworkPolicyError("redirect_location_invalid")
                    try:
                        next_url = urljoin(url, location)
                        validate_request_target(
                            url=next_url,
                            request_kind=R002RequestKind.DATASET,
                            allow_signed_hf_query=True,
                        )
                    except R002NetworkPolicyError:
                        raise
                    except Exception:
                        raise R002NetworkPolicyError(
                            "redirect_location_invalid"
                        ) from None
                    url = next_url
                    redirects += 1
                    continue
                if response.status_code != 200:
                    raise R002NetworkPolicyError("http_status")
                declared = _declared_length(
                    response, limit=source.byte_length, required=True
                )
                if declared != source.byte_length:
                    raise R002NetworkPolicyError("content_length_invalid")
                with cache.open_unlinked_scratch() as scratch:
                    digest = sha256()
                    length = 0
                    try:
                        for chunk in response.iter_raw():
                            if len(chunk) > source.byte_length - length:
                                raise R002NetworkPolicyError(
                                    "dataset_identity_mismatch"
                                )
                            _write_all(scratch, chunk)
                            digest.update(chunk)
                            length += len(chunk)
                    except R002NetworkPolicyError:
                        raise
                    except Exception:
                        raise R002NetworkPolicyError("network_failure") from None
                    if (
                        length != source.byte_length
                        or digest.hexdigest() != source.sha256
                    ):
                        raise R002NetworkPolicyError("dataset_identity_mismatch")
                    scratch.flush()
                    scratch.seek(0)
                    yield scratch
                return

    def validate_pr(self, case: R002CaseManifest) -> None:
        url = f"https://api.github.com/repos/{case.repository}/pulls/{case.pr_number}"
        with self._stream_once(
            url, R002RequestKind.PR_METADATA, case=case
        ) as response:
            if response.status_code != 200:
                raise R002NetworkPolicyError("http_status")
            body = _bounded_body(response, limit=_ONE_MIB)
        try:
            payload = json.loads(body)
            repository = payload["base"]["repo"]["full_name"]
            number = payload["number"]
            base_sha = payload["base"]["sha"]
            head_sha = payload["head"]["sha"]
            merged = payload["merged"]
            state = payload["state"]
        except Exception:
            raise R002NetworkPolicyError("response_invalid") from None
        if (
            type(repository) is not str
            or type(number) is not int
            or type(base_sha) is not str
            or type(head_sha) is not str
            or type(merged) is not bool
            or type(state) is not str
        ):
            raise R002NetworkPolicyError("response_invalid")
        if repository != case.repository or number != case.pr_number:
            raise R002NetworkPolicyError("pr_identity_mismatch")
        if state != "closed" or merged is not True:
            raise R002NetworkPolicyError("pr_not_merged")
        if base_sha != case.dataset_base_commit:
            raise R002NetworkPolicyError("pr_base_sha_mismatch")
        if head_sha != case.verified_pr_head_sha:
            raise R002NetworkPolicyError("pr_head_sha_mismatch")

    def fetch_head_file(self, case: R002CaseManifest, logical_path: str) -> bytes:
        url = (
            f"https://raw.githubusercontent.com/{case.repository}/"
            f"{case.verified_pr_head_sha}/{quote(logical_path, safe='/')}"
        )
        with self._stream_once(
            url, R002RequestKind.HEAD_FILE, case=case
        ) as response:
            if response.status_code != 200:
                raise R002NetworkPolicyError("http_status")
            case_remaining = _SIXTEEN_MIB - self._case_head_bytes[case.case_id]
            pack_remaining = _PACK_LIMIT - self._pack_head_bytes
            limit = min(_FOUR_MIB, case_remaining, pack_remaining)
            if limit <= 0:
                reason = (
                    "head_case_limit"
                    if case_remaining <= pack_remaining
                    else "head_pack_limit"
                )
                raise R002NetworkPolicyError(reason)
            declared = response.headers.get("content-length")
            if declared is not None and declared.isdecimal():
                if len(declared) > 20:
                    raise R002NetworkPolicyError("content_length_invalid")
                try:
                    declared_value = int(declared)
                except ValueError:
                    raise R002NetworkPolicyError("content_length_invalid") from None
                if declared_value > _FOUR_MIB:
                    raise R002NetworkPolicyError("head_file_limit")
                if declared_value > case_remaining:
                    raise R002NetworkPolicyError("head_case_limit")
                if declared_value > pack_remaining:
                    raise R002NetworkPolicyError("head_pack_limit")
            try:
                body = _bounded_body(response, limit=limit)
            except R002NetworkPolicyError as error:
                if error.reason_code != "response_invalid":
                    raise
                if limit == _FOUR_MIB:
                    raise R002NetworkPolicyError("head_file_limit") from None
                if limit == case_remaining:
                    raise R002NetworkPolicyError("head_case_limit") from None
                raise R002NetworkPolicyError("head_pack_limit") from None
        case_total = self._case_head_bytes[case.case_id] + len(body)
        pack_total = self._pack_head_bytes + len(body)
        self._case_head_bytes[case.case_id] = case_total
        self._pack_head_bytes = pack_total
        return body


def _prepare_criteria_sources_from_manifest(
    *,
    manifest: R002SourceManifest,
    cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002CriteriaSourcePreparationResult:
    cache = R002Cache(cache_root)
    client = R002ReadOnlyClient(transport)
    try:
        with client.download_dataset(manifest.source, cache) as source:
            rows = decode_criteria_source_rows(source, manifest.source)  # type: ignore[arg-type]
        selected = validate_manifest_criteria_sources(manifest, rows)
        cases: list[R002CriteriaSourceCase] = []
        for case, row in zip(manifest.cases, selected, strict=True):
            body = row.problem_statement.encode("utf-8")
            cache.write_bytes(f"criteria-sources/{case.problem_statement_sha256}", body)
            cases.append(
                R002CriteriaSourceCase(
                    case_id=case.case_id,
                    problem_statement_sha256=case.problem_statement_sha256,
                    byte_length=len(body),
                )
            )
        index = R002CriteriaSourceIndex(
            source_sha256=manifest.source.sha256,
            manifest_sha256=canonical_sha256(manifest),
            complete=True,
            cases=tuple(cases),
        )
        result = R002CriteriaSourcePreparationResult(
            phase="criteria_sources",
            complete=True,
            executed_case_count=20,
            failed_case_count=0,
            skipped_case_count=0,
            case_ids=tuple(case.case_id for case in cases),
            errors=(),
            hard_gate_errors=(),
        )
    except BaseException as error:
        primary = error
    else:
        primary = None
    finally:
        try:
            client.close()
        except BaseException as cleanup_error:
            if primary is None:
                if isinstance(cleanup_error, Exception):
                    raise R002NetworkPolicyError("network_failure") from None
                raise
    if primary is not None:
        raise primary.with_traceback(primary.__traceback__)
    cache.publish_criteria_source_index(index)
    return result


def prepare_criteria_sources(
    *,
    manifest_path: Path,
    cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002CriteriaSourcePreparationResult:
    return _prepare_criteria_sources_from_manifest(
        manifest=load_source_manifest(manifest_path),
        cache_root=cache_root,
        transport=transport,
    )


def _prepare_evidence_from_inputs(
    *,
    manifest: R002SourceManifest,
    criteria: R002CriteriaSet,
    cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002PreparationResult:
    manifest_hash = canonical_sha256(manifest)
    if not criteria.benchmark_owner_confirmed:
        raise R002PreparationError("criteria_not_confirmed")
    if criteria.source_manifest_sha256 != manifest_hash:
        raise R002PreparationError("criteria_manifest_drift")
    cache = R002Cache(cache_root)
    criteria_index = cache.load_criteria_source_index()
    if (
        criteria_index.source_sha256 != manifest.source.sha256
        or criteria_index.manifest_sha256 != manifest_hash
        or tuple((item.case_id, item.problem_statement_sha256) for item in criteria_index.cases)
        != tuple((item.case_id, item.problem_statement_sha256) for item in manifest.cases)
    ):
        raise R002PreparationError("criteria_source_index_mismatch")
    client = R002ReadOnlyClient(transport)
    cached_cases: list[R002CachedCase] = []
    results: list[R002PreparationCaseResult] = []
    try:
        with client.download_dataset(manifest.source, cache) as source:
            rows = decode_verified_parquet(source, manifest.source)  # type: ignore[arg-type]
        selected = validate_manifest_rows(manifest, rows)
        for case, row in zip(manifest.cases, selected, strict=True):
            client.validate_pr(case)
            parsed = parse_case_diffs(
                case_id=case.case_id, patch=row.patch, test_patch=row.test_patch
            )
            paths = sorted({item.path for item in parsed.files})
            head_files = {
                path: client.fetch_head_file(case, path) for path in paths
            }
            verified = verify_case_head_files(
                case=case, parsed=parsed, head_file_bytes=head_files
            )
            cache.write_content_addressed_model(
                f"rows/{case.row_sha256}", row, SWEbenchVerifiedRow
            )
            cached_heads: list[R002CachedHeadFile] = []
            for path, content in sorted(head_files.items()):
                digest = sha256(content).hexdigest()
                cache.write_bytes(f"head-files/{digest}", content)
                cached_heads.append(
                    R002CachedHeadFile(
                        logical_path=path,
                        head_sha=case.verified_pr_head_sha,
                        byte_length=len(content),
                        content_sha256=digest,
                    )
                )
            cached_cases.append(
                R002CachedCase(
                    case_id=case.case_id,
                    row_sha256=case.row_sha256,
                    problem_statement_sha256=case.problem_statement_sha256,
                    patch_sha256=case.patch_sha256,
                    test_patch_sha256=case.test_patch_sha256,
                    parsed_case_sha256=canonical_sha256(parsed),
                    verified_lines=verified.lines,
                    head_files=tuple(cached_heads),
                )
            )
            results.append(
                R002PreparationCaseResult(
                    case_id=case.case_id,
                    status="prepared",
                    head_file_count=len(cached_heads),
                    candidate_line_count=len(verified.lines),
                )
            )
        criteria_hash = canonical_sha256(criteria)
        index = R002CacheIndex(
            source_sha256=manifest.source.sha256,
            manifest_sha256=manifest_hash,
            criteria_set_sha256=criteria_hash,
            complete=True,
            cases=tuple(cached_cases),
        )
        result = R002PreparationResult(
            phase="evidence",
            complete=True,
            criteria_set_sha256=criteria_hash,
            executed_case_count=20,
            failed_case_count=0,
            skipped_case_count=0,
            head_file_count=sum(item.head_file_count for item in results),
            candidate_line_count=sum(item.candidate_line_count for item in results),
            cases=tuple(results),
            errors=(),
            hard_gate_errors=(),
        )
    except BaseException as error:
        primary = error
    else:
        primary = None
    finally:
        try:
            client.close()
        except BaseException as cleanup_error:
            if primary is None:
                if isinstance(cleanup_error, Exception):
                    raise R002NetworkPolicyError("network_failure") from None
                raise
    if primary is not None:
        raise primary.with_traceback(primary.__traceback__)
    cache.publish_index(index)
    return result


def prepare_r002(
    *,
    manifest_path: Path,
    criteria_path: Path,
    cache_root: Path,
    transport: httpx.BaseTransport | None = None,
) -> R002PreparationResult:
    manifest = load_source_manifest(manifest_path)
    criteria = load_confirmed_criteria(criteria_path, canonical_sha256(manifest))
    return _prepare_evidence_from_inputs(
        manifest=manifest,
        criteria=criteria,
        cache_root=cache_root,
        transport=transport,
    )
