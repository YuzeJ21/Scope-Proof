"""Strict, deterministic persisted contracts for the R-002 research benchmark."""

from __future__ import annotations

import json
import re
import warnings
from collections import Counter
from collections.abc import Sequence
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Annotated, ClassVar, Literal, NamedTuple, Self
from urllib.parse import quote, unquote

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    model_validator,
)

from scopeproof_core.retrieval.engine import _evidence_type
from scopeproof_core.schemas.models import (
    GITHUB_REPOSITORY_PATTERN,
    ChangedFile,
    CheckState,
    CIReasonCode,
    Criterion,
    CriterionSource,
    EvidenceLevel,
    EvidenceType,
    FindingStatus,
    GateVerdict,
    LineChangeType,
    Priority,
)


def validate_r002_logical_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        value.startswith("/")
        or "\\" in value
        or "\x00" in value
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ValueError("invalid R-002 logical path")
    return value


def validate_r002_source_span(value: str) -> str:
    match = re.fullmatch(r"problem_statement:L([1-9]\d*)-L([1-9]\d*)", value)
    if match is None or int(match.group(1)) > int(match.group(2)) or len(value) > 64:
        raise ValueError("invalid R-002 source span")
    return value


R002CaseId = Annotated[str, Field(pattern=r"^R002-\d{3}$")]
GitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
R002LogicalPath = Annotated[
    str, Field(min_length=1, max_length=512), AfterValidator(validate_r002_logical_path)
]
R002SourceSpan = Annotated[str, AfterValidator(validate_r002_source_span)]


class R002DiffStream(StrEnum):
    PATCH = "patch"
    TEST_PATCH = "test_patch"


def validate_r002_hunk_id(value: str) -> str:
    match = re.fullmatch(r"(patch|test_patch):(.+):H([1-9]\d*)", value)
    if match is None:
        raise ValueError("invalid R-002 hunk ID")
    validate_r002_logical_path(match.group(2))
    return value


def r002_hunk_index(value: str) -> int:
    """Return the validated natural one-based index from an R-002 hunk ID."""

    validate_r002_hunk_id(value)
    return int(value.rsplit(":H", maxsplit=1)[1])


R002HunkId = Annotated[
    str,
    Field(min_length=10, max_length=1024),
    AfterValidator(validate_r002_hunk_id),
]


def _permalink_repository(permalink: str, *, path: str, head_sha: str, line: int) -> str:
    match = re.fullmatch(
        r"https://github\.com/(?P<repository>[^/]+/[^/]+)/blob/"
        r"(?P<head>[0-9a-f]{40})/(?P<path>.+)#L(?P<start>[1-9]\d*)-L(?P<end>[1-9]\d*)",
        permalink,
    )
    if match is None:
        raise ValueError("permalink must be canonical")
    repository = unquote(match.group("repository"))
    permalink_path = unquote(match.group("path"))
    if (
        not re.fullmatch(GITHUB_REPOSITORY_PATTERN, repository)
        or validate_r002_logical_path(permalink_path) != path
        or match.group("head") != head_sha
        or int(match.group("start")) != line
        or int(match.group("end")) != line
        or permalink
        != f"https://github.com/{quote(repository, safe='/')}/blob/{head_sha}/"
        f"{quote(path, safe='/')}#L{line}-L{line}"
    ):
        raise ValueError("permalink must bind canonical repository, head, path, and line")
    return repository


class R002MetricState(StrEnum):
    VALUE = "value"
    NOT_APPLICABLE = "not_applicable"


class R002RequestKind(StrEnum):
    DATASET = "dataset"
    PR_METADATA = "pr_metadata"
    HEAD_FILE = "head_file"


R002_REQUEST_LIMITS = {
    R002RequestKind.DATASET: 4,
    R002RequestKind.PR_METADATA: 20,
    R002RequestKind.HEAD_FILE: 128,
}
R002_COMMAND_FAILURE_CODES = (
    "source_manifest_missing",
    "criteria_missing",
    "labels_missing",
    "prepared_cache_missing",
    "criteria_not_confirmed",
    "labels_not_confirmed",
    "input_validation_failed",
    "network_policy_failed",
    "network_unavailable",
    "source_integrity_failed",
    "preparation_integrity_failed",
    "annotation_required",
    "reannotation_required",
    "benchmark_gate_failed",
    "filesystem_failed",
    "internal_error",
)
R002_RESULT_LIMITATIONS = (
    "Criteria and relevance labels are benchmark-owner research judgements, "
    "not source-owner confirmation.",
    "Only static historical diff and immutable PR-head evidence was evaluated.",
    "No target code or tests were executed and current CI was not observed.",
    "Candidate evidence does not prove correctness or criterion satisfaction.",
    "R-002 is engineering evidence only and contributes zero Stage 1 validation credit.",
)
R002_ANNOTATION_UNIVERSE_MAX_BYTES = 256 * 1024 * 1024
R002_ANNOTATION_REVIEW_MAX_BYTES = 512 * 1024 * 1024
R002_REDACTION_RAW_VALUE_MAX_BYTES = 1024 * 1024 * 1024
R002_REDACTION_TRACKED_FILE_MAX_BYTES = 512 * 1024 * 1024
R002_STATIC_EVIDENCE_TYPES = (
    EvidenceType.IMPLEMENTATION,
    EvidenceType.TEST,
    EvidenceType.DOCUMENTATION,
    EvidenceType.CONTRACT,
)
R002_STATIC_EVIDENCE_TYPE_RANK = {
    evidence_type: rank for rank, evidence_type in enumerate(R002_STATIC_EVIDENCE_TYPES)
}
R002_CRITERION_ID_PATTERN = r"^AC-(0[1-9]|1[0-6])$"
R002_SCHEMA = (
    "repo",
    "instance_id",
    "base_commit",
    "patch",
    "test_patch",
    "problem_statement",
    "hints_text",
    "created_at",
    "version",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "environment_setup_commit",
    "difficulty",
)
R002_SOURCE: dict[str, object] = {
    "dataset_id": "SWE-bench/SWE-bench_Verified",
    "config": "default",
    "split": "test",
    "revision": "91aa3ed51b709be6457e12d00300a6a596d4c6a3",
    "source_url": "https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/91aa3ed51b709be6457e12d00300a6a596d4c6a3/data/test-00000-of-00001.parquet",
    "parquet_path": "data/test-00000-of-00001.parquet",
    "byte_length": 2_090_470,
    "sha256": "43ed5a3d1d98da36472c1ade65ddd2085d7b4ff694fcaf6a023a07c5c1f32f21",
    "row_count": 500,
    "repository_count": 12,
    "unique_instance_count": 500,
    "schema": list(R002_SCHEMA),
}
R002_APPROVED_CASES_SHA256 = "ef091bb60e78abf9311112ff434f9e80613438915db198662aecd5f469cee336"


class R002ApprovedCase(NamedTuple):
    """The immutable, redacted production identity for one approved R-002 case."""

    case_id: str
    repository: str
    pr_number: int
    dataset_base_commit: str
    head_sha: str
    row_index: int
    row_sha256: str
    problem_statement_sha256: str
    patch_sha256: str
    test_patch_sha256: str


# This production-only projection is deliberately separate from R002SourceManifest:
# structural fixtures may model a synthetic cohort, but persisted cache/index/result
# artifacts must remain tied to the approved, outcome-blind cohort.
R002_APPROVED_CASES: tuple[R002ApprovedCase, ...] = (
    R002ApprovedCase(
        "R002-001",
        "astropy/astropy",
        14096,
        "1a4462d72eb03f30dc83a879b1dd57aac8b2c18b",
        "271b2875d9aae0a5875acba0b1b27dc4885fd6e5",
        7,
        "2ab9bc4442553756efedd9737e68d2c11a68954da353a12acb903c86ba414ec0",
        "938971021e89cd882f6ea33d61202fe7aa0091d7be4748b100ddc7e164db90cd",
        "57a810467af331eba7c3238bbcd78268a47e96ad75eed3e2aa8b908da99104bc",
        "3a6a8ffc9c81264bccb9990b926bc6b1c2253a9aa7ce47810b5d28ad95c2596c",
    ),
    R002ApprovedCase(
        "R002-002",
        "astropy/astropy",
        7166,
        "26d147868f8a891a6009a25cd6a8576d2e1bd747",
        "3306a25dee0dc9c7583f9ede5155ad9a416279d8",
        16,
        "ba1ba98c4ec623be61f8f5efbe700a6afac5390a057f6d6a6fdc4ef254433eb8",
        "70c79d6da0284ce81f9e951dbab5c77d94bf8a27cd156f54169b424d75d11e43",
        "b720439fe90e5673cf5d75523a36c25927c9f78f785f280508433447293be578",
        "b86ae285f129f2941e27ff5f3229511c58199ae4a9e93b2d32e05dd4c2766dd7",
    ),
    R002ApprovedCase(
        "R002-003",
        "django/django",
        11087,
        "8180ffba21bf10f4be905cb0d4890dc2bcff2788",
        "f110de5c04818b8f915dcf65da37a50c1424c6e6",
        29,
        "0469361e971f290aeafbd49942b2e8305400f8c337fe4f0c177ddc19a85204d8",
        "9bd93972a91db1ad0e44e65720dd0f36f000de6264e770ffdaaeb06996a338f3",
        "38dfd449272afdf7269e56d798668fd4167db5c34c775614ca0b2fb47eb25789",
        "00c3a6c821fbf38e48279ab12d29b9f3edffe76295d1ca2a39bb500863a39a86",
    ),
    R002ApprovedCase(
        "R002-004",
        "django/django",
        12262,
        "69331bb851c34f05bc77e9fc24020fe6908b9cd5",
        "e3d546a1d986f83d8698c32e13afd048b65d06eb",
        76,
        "144160660b3e379ed645123e7ae4fff017e8cc3afee680eef9d58868b73c8fe5",
        "eb0c9b99667bc7666a6ff518747eaa71c6d392f727583d3f90cabe5cf4afe994",
        "9ec3e3ad1dd4c1993e6c0fb4698939f8f7eb192128fe0d696add4abb969e7037",
        "769a15faf523189f8c37917ff3c002c381f0e5a517c481020ea71abe5ee58cf9",
    ),
    R002ApprovedCase(
        "R002-005",
        "matplotlib/matplotlib",
        20676,
        "6786f437df54ca7780a047203cbcfaa1db8dc542",
        "5c08ff65b884bd03d80eba0a6de01a9d24599299",
        256,
        "5cd6ca2a9b3f4cd1056da08095356d10d5073a93f26317615efd66d223b2aac7",
        "c201ac5236b0a5eb57faa1768a12c67f0132074a5538d82feb717a62af9ad01d",
        "2943065dce13dc7e0f4f5bacc13353a4fe4e3fc3398086c9421b1b4cf4012383",
        "d39f439303c71d295be1d94a6f1d0501b7ffe7030bce1c6f5fc6845c990ce3eb",
    ),
    R002ApprovedCase(
        "R002-006",
        "matplotlib/matplotlib",
        25287,
        "f8ffce6d44127d4ea7d6491262ab30046b03294b",
        "264e7d37d2ee89c6019af4e5743653f4748448e1",
        276,
        "b12837067251cb70ae564442328e30d10aa23ebf5d0ba30eaefae1b290106da9",
        "f9bbb7794506f072129a5e7941e265280853fd873550828d7a66e91baa611c7e",
        "762993a12dfbd18ea1cd9b78c54a5d3262a2e011aa5c79bca562751ff2aba82a",
        "86204b551acc12241d3bbb5618a57f44e8341deeb867a860d7cd45c9a3b59163",
    ),
    R002ApprovedCase(
        "R002-007",
        "mwaskom/seaborn",
        3187,
        "22cdfb0c93f8ec78492d87edb810f10cb7f57a31",
        "9372112ea432a8b3d5bd9e11051a999b63905e86",
        288,
        "80aa45876204fa0a13ba2c7916e5723b61713622784ca260ebd40f7786abd9d0",
        "72157e71b5c0ed5d58d66a7eeb30ed7b2fb237374183b9ebee200f5d58abd77b",
        "578f98370810261561a8936dd7202e8c6644ef8d9ae52a54578a680f3cb4fc1f",
        "580a0ee004bb0143ba24afcaf0e45ec309635fa4610049ed91a8a15f7e9e1fc8",
    ),
    R002ApprovedCase(
        "R002-008",
        "pallets/flask",
        5014,
        "7ee9ceb71e868944a46e1ff00b506772a53a4f1d",
        "b8b410014d85f9861acc87c5f21c9a55a42d09c9",
        289,
        "5cc7ccbd782cf546cdded80c0811a572ba428ecace70022e5982477ad6a47489",
        "f77d8eab7dd608172aa78b3b50dfa7e0e9b3a6a1c52d14a1cb02417eb5a0ab00",
        "087d51d66413bfa35111ac0eca31f1db1636572702cfd967c428049b453f451d",
        "e16f06b260b5169a49397e9d571b5af70317cd23792e1437232fabf718fe8871",
    ),
    R002ApprovedCase(
        "R002-009",
        "psf/requests",
        1766,
        "847735553aeda6e6633f2b32e14ba14ba86887a4",
        "92d3616b02fc0ce5b1a89d884a4b1c7d602cb364",
        292,
        "35c5b9191de9f49b68c229d1af037792a54c1cdd418b7003bfc5527541c6eec6",
        "90d541e87a05a5135b7ee242c82702e5cad1e2cae9e5571fcbc032d7d6d80682",
        "fdf4dc67f564bc801f1fe74b1e6000a3186f19acec083f7585caef1b58671b12",
        "8104cc2c46abb076affea41d2f19d40a908fbc696aee3115dfffc5b0354662b4",
    ),
    R002ApprovedCase(
        "R002-010",
        "pydata/xarray",
        4075,
        "19b088636eb7d3f65ab7a1046ac672e0689371d8",
        "5650db2b9076787d848fa180e4b752aa578629c4",
        304,
        "8b74893d1cc8df31c7ec8c4bcaf6b05f7dff93c23800f8e497266bb536576e92",
        "d1cc08eec285573fc56f2a58a623e0b7adf33e6f75fd16b4214dd1db4b3e46a6",
        "643f8e9f14148cb48741a09de7c02ec50175a2a63d8bef84821ad6ab12c4b141",
        "ac49c8fe1085bfb95c0d5df8e513f7a0fa9299c9f18ce878be2362e08797517b",
    ),
    R002ApprovedCase(
        "R002-011",
        "pydata/xarray",
        6992,
        "45c0a114e2b7b27b83c9618bc05b36afac82183c",
        "ca01949cb889ee38aae33560b02de1f7625fd921",
        316,
        "b2929496bc01afda4604941fb957f49b6cf64e0a8184e78c2b1bf993f3a8a6ac",
        "2fd625e5f58b6b7b7c292b9ba90307e8583cad9d4ddb395fe9805bb06c74208b",
        "2c9df82ff3c01c158b6cf1155a89b46da0d60f6705cd29ededd6bce02e9847e8",
        "41f0aead689f02738cecae41605836cb9e6aceb17e1e6c0e4b7ffa57191763a8",
    ),
    R002ApprovedCase(
        "R002-012",
        "pylint-dev/pylint",
        7080,
        "3c5eca2ded3dd2b59ebaf23eb289453b5d2930f0",
        "c744a5357abfd30b84de9d171c901de4d555669b",
        327,
        "25624f1c827f50c9cf055262a27ebb1a485ed0bd0305469a849d549d0926c26e",
        "82319497af035b3cdcd4ee71b5fccd578074989dfa157dc54ecc5bf8ea76ceab",
        "f908ad1f6d4b8df3755a634c6741abf8ae613bc59278a54c16560c16d255580f",
        "7d42b9582d23667623d84307132d46e63588cbcfe63c35bccb7a52940bf5ca08",
    ),
    R002ApprovedCase(
        "R002-013",
        "pytest-dev/pytest",
        7490,
        "7f7a36478abe7dd1fa993b115d22606aa0e35e88",
        "ccad10a82908d7a12cd6024e00be11af413edf1c",
        344,
        "0cda868e19eb39388dde21e14ca951ef9d0deea5a32a8cbeab9149945e4e2408",
        "9a5e8c33368dc3bbe9c5f03d3136a574cebede61fea6c575d39ddf108b92d947",
        "88a7af7e123619306d887c6a9bd1f905acc4872b454df914094c038b71356e30",
        "fe5323cfe9d6be9648be22ffb13a95079c6e17c13f09987f4c1b8589d27c690c",
    ),
    R002ApprovedCase(
        "R002-014",
        "pytest-dev/pytest",
        7521,
        "41d211c24a6781843b174379d6d6538f5c17adb9",
        "8616a5f1d989eec5e2c5f2129040149fe4cf4347",
        345,
        "3fc86672e886cb8326e6729b9438d775a377d75f2e41d481e7d1934fb19f0a44",
        "39f1953e5d5a7481355aa6109b16ecaebbb037957e473cc71e9ab1402d3aa9b9",
        "e1f62165b6ecc14c60b08bb71a59b927adba0c3b9a8393394481cc6a4f0f8f0e",
        "5d7b9e51ea700508725976f0643bd1c601afcb5373481118f8741e4660d64e59",
    ),
    R002ApprovedCase(
        "R002-015",
        "scikit-learn/scikit-learn",
        13779,
        "b34751b7ed02b2cfcc36037fb729d4360480a299",
        "2ca0e6c7958a8c217a4788cad08768249d6a0522",
        363,
        "b75c49d788db78afa25500c392c597a2107aed49c439549972836873e6a8ceee",
        "d32c6ecdfaf0eeb42a35e7cb05bd03fc034571aaef7c7743a452422c2bcdc6bc",
        "6faf85c3ffaaebff5458d13c730b28c4d6acfded07cc733b80278df6d2166cb4",
        "fb96b7aa463a986df0b395398d07262b26ee71f60e84696d6e60932db59c7fc1",
    ),
    R002ApprovedCase(
        "R002-016",
        "scikit-learn/scikit-learn",
        14496,
        "d49a6f13af2f22228d430ac64ac2b518937800d0",
        "8e8a34535f8f8743aedf88553d62e66423118423",
        367,
        "8f4615aae668d879679359f06220df42cd8d198653cfed4241724326075ac77b",
        "7860d59abe6e6a85ed92cbc43c7b632982164bc89105df4df399793154bb15df",
        "5f9a4088607136868645a435d919f0d07737643a2ab25ab11672234c01ca1853",
        "ea556bb6d85c2d707dc36a6df92174f9b514c53a04e61c7f492a7dddf5086d9c",
    ),
    R002ApprovedCase(
        "R002-017",
        "sphinx-doc/sphinx",
        8459,
        "68aa4fb29e7dfe521749e1e14f750d7afabb3481",
        "333e7a447edfcb3092032ac801116e1eec193e44",
        403,
        "076da25d826502bcd19d69bcd9eb3a109f8b3e2dd4224482541f36dfc5ad64cc",
        "5a7af99001528e86ff4d88a9bf03e4b87b08c1c4907ef4230d6dfa05a3375018",
        "8bf406df3ba81a273c45b95b9c14c70ba7e4ae7c0a5e387c5544d0d608d4900d",
        "7a3d56dc1bc60a57becc535d9032530e8703309049f50ff28a2ddb196171ea1f",
    ),
    R002ApprovedCase(
        "R002-018",
        "sphinx-doc/sphinx",
        9230,
        "567ff22716ac258b9edd2c1711d766b440ac0b11",
        "9a132b4f8114f1652a9bc494b740b6632c3545a9",
        413,
        "3b12d82c5290396b3a7972957b15d302baf7686662eb0bf65b46c79a4e5c64d6",
        "e814405fe0885a2284bec4dfdf1efa5bd0386117d02410e9ad0ec98c0e1712ab",
        "e6cc08c8b1858c3d41964c220e396638c15e601f88fa9cb6493938e5fdd814c6",
        "0971215a38b16f54484b9a2f11da137413f131dfc453fd9a08de1978d31360b0",
    ),
    R002ApprovedCase(
        "R002-019",
        "sympy/sympy",
        20801,
        "e11d3fed782146eebbffdc9ced0364b223b84b6c",
        "b5424dd3d0484087ae9d175c014e9a803e91a875",
        478,
        "754b459bdbb9a9f094572df632e40c980c09f7e08a25c8957d9f876f5c9f1db0",
        "d97c4296d41c2a7cdf87b6e2de16dd10a5755318d9bde720c8677b8787c20ec3",
        "dbec818a9a22bcfeaeeb2f292cf7bba7048f84bca05aa04f38870e483ec803d5",
        "f84920fc71c885455f40e439ea052707b7936b1367ba6af67a2a7b9c3f626f9c",
    ),
    R002ApprovedCase(
        "R002-020",
        "sympy/sympy",
        21612,
        "b4777fdcef467b7132c055f8ac2c9a5059e6a145",
        "305d1300055245c26c0261ffaf77575fb2e9f9d9",
        482,
        "8a45d630025652ef97b71f933739e60ea6b5ee7768804f9062e20856f4cbb967",
        "657b0dc782c25c6b54593dac7ccb7c4aaa95bd6da6e1a87b2e4b778f86d29b99",
        "72e403affa86c748aad0332d53ef48a2bff26cad6ee96d5588c28c1b30982c3e",
        "d199d4ee685de99f64461d66f3b8424c6544dd38c665812a6ff0d6f3ccfd6f6b",
    ),
)
R002_APPROVED_CASE_BY_ID = {case.case_id: case for case in R002_APPROVED_CASES}


def _require_approved_case_ids(items: Sequence[object]) -> None:
    if tuple(item.case_id for item in items) != tuple(  # type: ignore[attr-defined]
        item.case_id for item in R002_APPROVED_CASES
    ):
        raise ValueError("R-002 records must use the ordered approved case IDs")


def _approved_case(case_id: str) -> R002ApprovedCase:
    try:
        return R002_APPROVED_CASE_BY_ID[case_id]
    except KeyError as error:
        raise ValueError("R-002 record has an unapproved case ID") from error


class R002StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class R002Error(Exception):
    allowed_reason_codes: ClassVar[frozenset[str]]

    def __init__(self, reason_code: str) -> None:
        if reason_code not in self.allowed_reason_codes:
            raise RuntimeError("unregistered R-002 reason code")
        self.reason_code = reason_code
        super().__init__(reason_code)


class R002SourceError(R002Error):
    allowed_reason_codes = frozenset({"source_pin_mismatch", "approved_cohort_mismatch"})


class R002AnnotationError(R002Error):
    allowed_reason_codes = frozenset(
        {
            "criteria_manifest_drift",
            "criteria_manifest_context_invalid",
            "criteria_manifest_projection_drift",
            "candidate_label_upstream_drift",
            "annotation_universe_drift",
        }
    )


class R002Manifest(R002StrictModel):
    pack_id: Literal["R-002"] = "R-002"
    classification: Literal["public_engineering_research"] = "public_engineering_research"
    eligible_for_stage_1: Literal[False] = False
    does_not_advance_stage_1: Literal[True] = True
    target_repository_code_executed: Literal[False] = False


with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message='Field name "schema".*', category=UserWarning)

    class SWEbenchSourcePin(R002StrictModel):
        dataset_id: str = Field(min_length=1)
        config: str = Field(min_length=1)
        split: str = Field(min_length=1)
        revision: GitSha
        source_url: str = Field(pattern=r"^https://huggingface\.co/.+\.parquet$")
        parquet_path: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.parquet$")
        byte_length: StrictInt = Field(gt=0)
        sha256: Sha256
        row_count: StrictInt = Field(gt=0)
        repository_count: StrictInt = Field(gt=0)
        unique_instance_count: StrictInt = Field(gt=0)
        schema: tuple[str, ...] = Field(min_length=1, max_length=len(R002_SCHEMA))


class R002CaseManifest(R002StrictModel):
    case_id: R002CaseId
    instance_id: str = Field(pattern=r"^[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-\d+$")
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    pr_url: str = Field(pattern=r"^https://github\.com/.+/.+/pull/\d+$")
    dataset_base_commit: GitSha
    verified_pr_head_sha: GitSha
    row_index: StrictInt = Field(ge=0, lt=500)
    difficulty: str = Field(min_length=1, max_length=64)
    row_sha256: Sha256
    problem_statement_sha256: Sha256
    patch_sha256: Sha256
    test_patch_sha256: Sha256

    @model_validator(mode="after")
    def bind_identity(self) -> Self:
        expected_instance = self.repository.replace("/", "__") + f"-{self.pr_number}"
        expected_url = f"https://github.com/{self.repository}/pull/{self.pr_number}"
        if self.instance_id != expected_instance or self.pr_url != expected_url:
            raise ValueError("case identity fields disagree")
        return self


class R002SourceManifest(R002Manifest):
    source: SWEbenchSourcePin
    cases: tuple[R002CaseManifest, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def validate_cohort(self) -> Self:
        expected_ids = [f"R002-{number:03d}" for number in range(1, 21)]
        if [case.case_id for case in self.cases] != expected_ids:
            raise ValueError("case IDs must be consecutive R002-001 through R002-020")
        if list(self.cases) != sorted(
            self.cases, key=lambda case: (case.repository, case.instance_id)
        ):
            raise ValueError("cases must be ordered by repository and instance ID")
        for values, label in (
            ([case.instance_id for case in self.cases], "instance IDs"),
            ([case.pr_url for case in self.cases], "PR URLs"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        counts = Counter(case.repository for case in self.cases)
        if len(counts) != 12 or max(counts.values()) > 2:
            raise ValueError("cohort must cover 12 repositories with at most two cases each")
        return self


class SWEbenchVerifiedRow(R002StrictModel):
    repo: str
    instance_id: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    version: str
    FAIL_TO_PASS: str
    PASS_TO_PASS: str
    environment_setup_commit: str
    difficulty: str

    @model_validator(mode="after")
    def validate_bounded_content(self) -> Self:
        if len(canonical_json_bytes(self)) > 1024 * 1024:
            raise ValueError("verified row exceeds one MiB")
        if len(self.problem_statement.encode()) > 128 * 1024 or any(
            len(value.encode()) > 512 * 1024 for value in (self.patch, self.test_patch)
        ):
            raise ValueError("verified row content exceeds R-002 bounds")
        return self


class SWEbenchCriteriaSourceRow(R002StrictModel):
    repo: str
    instance_id: str
    base_commit: str
    problem_statement: str
    difficulty: str


class R002DiffLimits(R002StrictModel):
    files: Literal[32] = 32
    hunks: Literal[256] = 256
    diff_lines: Literal[50000] = 50000
    path_characters: Literal[512] = 512
    line_bytes: Literal[65536] = 65536


class R002HeadFileLimits(R002StrictModel):
    bytes_per_file: Literal[4194304] = 4194304
    bytes_per_case: Literal[16777216] = 16777216
    bytes_per_pack: Literal[134217728] = 134217728
    request_count: Literal[128] = 128


R002_HEAD_FILE_LIMITS = R002HeadFileLimits()


class R002ParsedLine(R002StrictModel):
    change_type: LineChangeType
    old_line_number: StrictInt | None = Field(default=None, ge=1)
    new_line_number: StrictInt | None = Field(default=None, ge=1)
    content: str
    normalized_line_sha256: Sha256

    @model_validator(mode="after")
    def validate_marker_numbers(self) -> Self:
        expected = {
            LineChangeType.ADDED: (False, True),
            LineChangeType.REMOVED: (True, False),
            LineChangeType.CONTEXT: (True, True),
        }[self.change_type]
        actual = (self.old_line_number is not None, self.new_line_number is not None)
        if actual != expected:
            raise ValueError("parsed line numbers must match its change marker")
        encoded = self.content.encode("utf-8")
        if len(encoded) > 65536:
            raise ValueError("parsed line content must not exceed 65,536 UTF-8 bytes")
        if "\r" in self.content or "\n" in self.content:
            raise ValueError("parsed line content must not contain embedded newlines")
        if sha256(encoded).hexdigest() != self.normalized_line_sha256:
            raise ValueError("parsed line normalized hash must match UTF-8 content")
        return self


class R002ParsedHunk(R002StrictModel):
    hunk_id: R002HunkId
    old_start: StrictInt = Field(ge=1)
    old_count: StrictInt = Field(ge=0, le=50000)
    new_start: StrictInt = Field(ge=1)
    new_count: StrictInt = Field(ge=0, le=50000)
    lines: tuple[R002ParsedLine, ...] = Field(max_length=50000)

    @model_validator(mode="after")
    def reconstruct_counts_and_line_numbers(self) -> Self:
        old_number = self.old_start
        new_number = self.new_start
        for line in self.lines:
            if line.old_line_number is not None:
                if line.old_line_number != old_number:
                    raise ValueError("parsed hunk old line numbers must be consecutive")
                old_number += 1
            if line.new_line_number is not None:
                if line.new_line_number != new_number:
                    raise ValueError("parsed hunk new line numbers must be consecutive")
                new_number += 1
        if (
            self.old_count != old_number - self.old_start
            or self.new_count != new_number - self.new_start
        ):
            raise ValueError("parsed hunk counts must match its lines")
        return self


class R002ParsedFile(R002StrictModel):
    stream: R002DiffStream
    path: R002LogicalPath
    hunks: tuple[R002ParsedHunk, ...] = Field(min_length=1, max_length=256)
    additions: StrictInt = Field(ge=0, le=50000)
    deletions: StrictInt = Field(ge=0, le=50000)

    @model_validator(mode="after")
    def reconstruct_counts_and_order(self) -> Self:
        if any(
            hunk.hunk_id != f"{self.stream}:{self.path}:H{number}"
            for number, hunk in enumerate(self.hunks, start=1)
        ):
            raise ValueError("parsed file hunk IDs must be ordered and consecutive")
        starts = [(hunk.old_start, hunk.new_start) for hunk in self.hunks]
        if starts != sorted(starts):
            raise ValueError("parsed file hunks must be stably ordered")
        additions = sum(
            line.change_type is LineChangeType.ADDED for hunk in self.hunks for line in hunk.lines
        )
        deletions = sum(
            line.change_type is LineChangeType.REMOVED for hunk in self.hunks for line in hunk.lines
        )
        if self.additions != additions or self.deletions != deletions:
            raise ValueError("parsed file counts must match its hunks")
        return self


class R002ParsedDiff(R002StrictModel):
    stream: R002DiffStream
    files: tuple[R002ParsedFile, ...] = Field(max_length=32)
    file_count: StrictInt = Field(ge=0, le=32)
    hunk_count: StrictInt = Field(ge=0, le=256)
    diff_line_count: StrictInt = Field(ge=0, le=50000)

    @model_validator(mode="after")
    def reconstruct_counts_and_order(self) -> Self:
        paths = [item.path for item in self.files]
        if any(item.stream is not self.stream for item in self.files):
            raise ValueError("parsed diff files must match the diff stream")
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise ValueError("parsed diff paths must be sorted and unique")
        expected = (
            len(self.files),
            sum(len(item.hunks) for item in self.files),
            sum(len(hunk.lines) for item in self.files for hunk in item.hunks),
        )
        if (self.file_count, self.hunk_count, self.diff_line_count) != expected:
            raise ValueError("parsed diff counts must match its files")
        return self


class R002ParsedCase(R002StrictModel):
    case_id: R002CaseId
    files: tuple[R002ParsedFile, ...] = Field(max_length=32)
    file_count: StrictInt = Field(ge=0, le=32)
    hunk_count: StrictInt = Field(ge=0, le=256)
    diff_line_count: StrictInt = Field(ge=0, le=50000)

    @model_validator(mode="after")
    def reconstruct_counts_and_stream_separation(self) -> Self:
        keys = [(item.stream.value, item.path) for item in self.files]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("parsed case files must be sorted and unique")
        patch_paths = {item.path for item in self.files if item.stream is R002DiffStream.PATCH}
        test_paths = {item.path for item in self.files if item.stream is R002DiffStream.TEST_PATCH}
        if patch_paths & test_paths:
            raise ValueError("patch and test_patch paths must remain distinguishable")
        expected = (
            len(self.files),
            sum(len(item.hunks) for item in self.files),
            sum(len(hunk.lines) for item in self.files for hunk in item.hunks),
        )
        if (self.file_count, self.hunk_count, self.diff_line_count) != expected:
            raise ValueError("parsed case counts must match its files")
        return self


class R002VerifiedLine(R002StrictModel):
    stream: R002DiffStream
    path: R002LogicalPath
    hunk_id: R002HunkId
    new_line_number: StrictInt = Field(ge=1)
    normalized_line_sha256: Sha256
    head_file_sha256: Sha256
    head_sha: GitSha
    permalink: str

    @model_validator(mode="after")
    def bind_hunk_and_permalink_fields(self) -> Self:
        if not self.hunk_id.startswith(f"{self.stream}:{self.path}:H"):
            raise ValueError("verified line hunk ID must bind stream and path")
        _permalink_repository(
            self.permalink,
            path=self.path,
            head_sha=self.head_sha,
            line=self.new_line_number,
        )
        return self


def _verified_line_order(line: R002VerifiedLine) -> tuple[str, str, int, int]:
    return (line.stream.value, line.path, line.new_line_number, r002_hunk_index(line.hunk_id))


def _verified_line_identity(line: R002VerifiedLine) -> tuple[str, int]:
    return (line.path, line.new_line_number)


class R002VerifiedCaseLines(R002StrictModel):
    case_id: R002CaseId
    head_sha: GitSha
    lines: tuple[R002VerifiedLine, ...] = Field(max_length=50000)

    @model_validator(mode="after")
    def bind_immutable_head_lines(self) -> Self:
        approved = _approved_case(self.case_id)
        if self.head_sha != approved.head_sha:
            raise ValueError("verified lines must use the approved head SHA")
        order_keys = [_verified_line_order(line) for line in self.lines]
        identity_keys = [_verified_line_identity(line) for line in self.lines]
        if order_keys != sorted(order_keys) or len(identity_keys) != len(set(identity_keys)):
            raise ValueError("verified lines must be sorted and unique")
        for line in self.lines:
            if (
                line.head_sha != self.head_sha
                or _permalink_repository(
                    line.permalink,
                    path=line.path,
                    head_sha=self.head_sha,
                    line=line.new_line_number,
                )
                != approved.repository
            ):
                raise ValueError("verified line must bind its approved immutable head")
        return self

    def by_path_and_line(self, path: str, number: int) -> R002VerifiedLine:
        matches = [
            line for line in self.lines if line.path == path and line.new_line_number == number
        ]
        if len(matches) != 1:
            raise ValueError("verified line must match exactly once")
        return matches[0]


class R002CachedHeadFile(R002StrictModel):
    logical_path: R002LogicalPath
    head_sha: GitSha
    byte_length: StrictInt = Field(ge=0, le=R002_HEAD_FILE_LIMITS.bytes_per_file)
    content_sha256: Sha256


class R002CachedCase(R002StrictModel):
    case_id: R002CaseId
    row_sha256: Sha256
    problem_statement_sha256: Sha256
    patch_sha256: Sha256
    test_patch_sha256: Sha256
    parsed_case_sha256: Sha256
    verified_lines: tuple[R002VerifiedLine, ...] = Field(max_length=50000)
    head_files: tuple[R002CachedHeadFile, ...] = Field(max_length=32)

    @model_validator(mode="after")
    def bind_approved_cache_case(self) -> Self:
        approved = _approved_case(self.case_id)
        if (
            self.row_sha256,
            self.problem_statement_sha256,
            self.patch_sha256,
            self.test_patch_sha256,
        ) != (
            approved.row_sha256,
            approved.problem_statement_sha256,
            approved.patch_sha256,
            approved.test_patch_sha256,
        ):
            raise ValueError("cached case hashes must bind the approved projection")
        if any(line.head_sha != approved.head_sha for line in self.verified_lines):
            raise ValueError("cached verified lines must use the approved head SHA")
        line_order_keys = [_verified_line_order(line) for line in self.verified_lines]
        line_identity_keys = [_verified_line_identity(line) for line in self.verified_lines]
        if (
            line_order_keys != sorted(line_order_keys)
            or len(line_identity_keys) != len(set(line_identity_keys))
            or any(
                _permalink_repository(
                    line.permalink,
                    path=line.path,
                    head_sha=approved.head_sha,
                    line=line.new_line_number,
                )
                != approved.repository
                for line in self.verified_lines
            )
        ):
            raise ValueError("cached verified lines must be sorted unique immutable references")
        paths = [item.logical_path for item in self.head_files]
        if (
            paths != sorted(paths)
            or len(paths) != len(set(paths))
            or any(item.head_sha != approved.head_sha for item in self.head_files)
        ):
            raise ValueError("cached head files must be sorted unique approved-head files")
        head_files_by_path = {item.logical_path: item for item in self.head_files}
        if any(
            (head_file := head_files_by_path.get(line.path)) is None
            or head_file.head_sha != line.head_sha
            or head_file.content_sha256 != line.head_file_sha256
            for line in self.verified_lines
        ):
            raise ValueError("cached verified lines must join exactly one matching head file")
        if sum(item.byte_length for item in self.head_files) > R002_HEAD_FILE_LIMITS.bytes_per_case:
            raise ValueError("cached case exceeds the head-file byte limit")
        return self


class R002CriteriaSourceCase(R002StrictModel):
    case_id: R002CaseId
    problem_statement_sha256: Sha256
    byte_length: StrictInt = Field(ge=1)


class R002CriteriaSourceIndex(R002Manifest):
    source_sha256: Sha256
    manifest_sha256: Sha256
    complete: Literal[True] = True
    cases: tuple[R002CriteriaSourceCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_criteria_sources(self) -> Self:
        _require_approved_case_ids(self.cases)
        if any(
            item.problem_statement_sha256 != _approved_case(item.case_id).problem_statement_sha256
            for item in self.cases
        ):
            raise ValueError("criteria sources must bind approved problem hashes")
        return self


class R002CacheIndex(R002Manifest):
    source_sha256: Sha256
    manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    complete: Literal[True] = True
    cases: tuple[R002CachedCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_complete_cache(self) -> Self:
        _require_approved_case_ids(self.cases)
        if sum(len(case.head_files) for case in self.cases) > R002_HEAD_FILE_LIMITS.request_count:
            raise ValueError("cache index exceeds the head-file request limit")
        if (
            sum(item.byte_length for case in self.cases for item in case.head_files)
            > R002_HEAD_FILE_LIMITS.bytes_per_pack
        ):
            raise ValueError("cache index exceeds the head-file byte limit")
        return self


class R002CriteriaSourcePreparationResult(R002Manifest):
    phase: Literal["criteria_sources"]
    complete: Literal[True]
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    case_ids: tuple[R002CaseId, ...] = Field(min_length=20, max_length=20)
    errors: tuple[str, ...] = Field(max_length=0)
    hard_gate_errors: tuple[str, ...] = Field(max_length=0)

    @model_validator(mode="after")
    def require_complete_criteria_source_preparation(self) -> Self:
        if (
            self.executed_case_count,
            self.failed_case_count,
            self.skipped_case_count,
            self.case_ids,
            self.errors,
            self.hard_gate_errors,
        ) != (20, 0, 0, tuple(case.case_id for case in R002_APPROVED_CASES), (), ()):
            raise ValueError("criteria-source preparation must be complete 20/0/0")
        return self


class R002PreparationCaseResult(R002StrictModel):
    case_id: R002CaseId
    status: Literal["prepared"]
    head_file_count: StrictInt = Field(ge=0, le=32)
    candidate_line_count: StrictInt = Field(ge=0)


class R002PreparationResult(R002Manifest):
    phase: Literal["evidence"]
    complete: Literal[True]
    criteria_set_sha256: Sha256
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    head_file_count: StrictInt = Field(ge=0, le=R002_HEAD_FILE_LIMITS.request_count)
    candidate_line_count: StrictInt = Field(ge=0)
    cases: tuple[R002PreparationCaseResult, ...] = Field(min_length=20, max_length=20)
    errors: tuple[str, ...] = Field(max_length=0)
    hard_gate_errors: tuple[str, ...] = Field(max_length=0)

    @model_validator(mode="after")
    def require_complete_evidence_preparation(self) -> Self:
        _require_approved_case_ids(self.cases)
        if (
            self.executed_case_count,
            self.failed_case_count,
            self.skipped_case_count,
            self.errors,
            self.hard_gate_errors,
        ) != (20, 0, 0, (), ()):
            raise ValueError("evidence preparation must be complete 20/0/0")
        if (
            self.head_file_count,
            self.candidate_line_count,
        ) != (
            sum(case.head_file_count for case in self.cases),
            sum(case.candidate_line_count for case in self.cases),
        ):
            raise ValueError("preparation totals must reconstruct from ordered cases")
        return self


class R002CommandFailure(R002Manifest):
    ok: Literal[False] = False
    operation_failed: Literal[True] = True
    command: Literal["prepare", "annotate", "run"]
    reason_code: Literal[
        "source_manifest_missing",
        "criteria_missing",
        "labels_missing",
        "prepared_cache_missing",
        "criteria_not_confirmed",
        "labels_not_confirmed",
        "input_validation_failed",
        "network_policy_failed",
        "network_unavailable",
        "source_integrity_failed",
        "preparation_integrity_failed",
        "annotation_required",
        "reannotation_required",
        "benchmark_gate_failed",
        "filesystem_failed",
        "internal_error",
    ]
    errors: tuple[str, ...] = Field(min_length=1, max_length=1)

    @model_validator(mode="after")
    def bind_error_code(self) -> Self:
        if self.errors != (self.reason_code,):
            raise ValueError("command failure errors must contain only the stable reason code")
        return self


class R002RedactionAudit(R002Manifest):
    passed: Literal[True] = True
    tracked_file_count: StrictInt = Field(ge=0)
    raw_value_count: StrictInt = Field(ge=0)
    checked_value_sha256: tuple[Sha256, ...] = Field(max_length=R002_REDACTION_RAW_VALUE_MAX_BYTES)

    @model_validator(mode="after")
    def require_complete_redaction_audit(self) -> Self:
        if (
            self.tracked_file_count < 1
            or self.raw_value_count != len(self.checked_value_sha256)
            or self.checked_value_sha256 != tuple(sorted(set(self.checked_value_sha256)))
        ):
            raise ValueError("redaction audit must report sorted unique checked values")
        return self


class R002Criterion(Criterion):
    """Frozen R-002 copy of the core criterion contract for confirmed persistence."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class R002CriterionCase(R002StrictModel):
    case_id: R002CaseId
    problem_statement_sha256: Sha256
    criteria: tuple[R002Criterion, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="before")
    @classmethod
    def require_complete_serialized_criteria(cls, value: object) -> object:
        if not isinstance(value, dict) or not isinstance(value.get("criteria"), (list, tuple)):
            return value
        required_fields = {
            "criterion_id",
            "text",
            "priority",
            "criterion_type",
            "criterion_source",
            "source_span",
            "required_evidence_level",
        }
        for criterion in value["criteria"]:
            fields = (
                set(type(criterion).model_fields)
                if isinstance(criterion, Criterion)
                else set(criterion)
                if isinstance(criterion, dict)
                else set()
            )
            if fields != required_fields:
                raise ValueError("R-002 criteria require complete serialized fields")
        # JSON arrays are canonical persisted tuples. Core Criterion values are
        # copied into the frozen R-002 subtype rather than retained by reference.
        criteria = tuple(
            criterion.model_dump() if isinstance(criterion, Criterion) else criterion
            for criterion in value["criteria"]
        )
        return {**value, "criteria": criteria}

    @model_validator(mode="after")
    def validate_criteria(self) -> Self:
        ids = [item.criterion_id for item in self.criteria]
        if ids != [f"AC-{number:02d}" for number in range(1, len(ids) + 1)]:
            raise ValueError("criterion IDs must be ordered and consecutive")
        if not any(item.priority is Priority.MUST_HAVE for item in self.criteria):
            raise ValueError("every case requires at least one MUST_HAVE criterion")
        if any(
            item.criterion_source is not CriterionSource.USER_CONFIRMED for item in self.criteria
        ):
            raise ValueError("R-002 criteria must use the operator-confirmed source value")
        if any(
            item.source_span is None
            or validate_r002_source_span(item.source_span) != item.source_span
            for item in self.criteria
        ):
            raise ValueError("every R-002 criterion requires a bounded problem-statement span")
        if any(
            len(item.text) > 512 or "\n" in item.text or "\r" in item.text for item in self.criteria
        ):
            raise ValueError("R-002 criteria must be bounded single-line paraphrases")
        return self


class R002CriterionReviewCase(R002CriterionCase):
    problem_statement: str = Field(min_length=1, max_length=131072)


def _validate_criteria_cases(cases: Sequence[R002CriterionCase]) -> None:
    ids = [case.case_id for case in cases]
    hashes = [case.problem_statement_sha256 for case in cases]
    if ids != [f"R002-{number:03d}" for number in range(1, 21)]:
        raise ValueError("criteria cases must be ordered and complete")
    if len(hashes) != len(set(hashes)):
        raise ValueError("criteria cases require complete unique problem hashes")


class _CriteriaCollection(R002Manifest):
    source_manifest_sha256: Sha256
    cases: tuple[R002CriterionCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_cases(self) -> Self:
        _validate_criteria_cases(self.cases)
        return self


class R002CriteriaProposal(R002Manifest):
    source_manifest_sha256: Sha256
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[False] = False
    cases: tuple[R002CriterionReviewCase, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def bind_cases(self) -> Self:
        _validate_criteria_cases(self.cases)
        return self


class R002CriteriaSet(_CriteriaCollection):
    source_owner_confirmed: Literal[False] = False
    benchmark_owner_confirmed: Literal[True]


class R002CandidateLineKey(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=R002_CRITERION_ID_PATTERN)
    stream: R002DiffStream
    path: R002LogicalPath
    new_line_number: StrictInt = Field(ge=1)
    normalized_line_sha256: Sha256


def r002_annotation_key_order(
    key: R002CandidateLineKey,
) -> tuple[str, str, str, str, int, str]:
    return (
        key.case_id,
        key.criterion_id,
        key.stream.value,
        key.path,
        key.new_line_number,
        key.normalized_line_sha256,
    )


class R002CandidateLabel(R002StrictModel):
    key: R002CandidateLineKey
    relevant: bool
    reason_code: Literal[
        "direct_static_candidate",
        "supporting_static_candidate",
        "test_intent_candidate",
        "unrelated_candidate",
        "insufficient_context",
    ]

    @model_validator(mode="after")
    def bind_reason_to_relevance(self) -> Self:
        true_codes = {
            "direct_static_candidate",
            "supporting_static_candidate",
            "test_intent_candidate",
        }
        if self.relevant != (self.reason_code in true_codes):
            raise ValueError("candidate reason code must agree with relevance")
        if (
            self.reason_code == "test_intent_candidate"
            and self.key.stream is not R002DiffStream.TEST_PATCH
        ):
            raise ValueError("test intent candidates require test_patch stream")
        return self


class R002ExpectedMissing(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=R002_CRITERION_ID_PATTERN)
    evidence_type: Literal[
        EvidenceType.IMPLEMENTATION,
        EvidenceType.TEST,
        EvidenceType.DOCUMENTATION,
        EvidenceType.CONTRACT,
    ]
    reason_code: Literal["no_owner_labelled_relevant_candidate"]


def _expected_missing_order(item: R002ExpectedMissing) -> tuple[str, str, int]:
    return (
        item.case_id,
        item.criterion_id,
        R002_STATIC_EVIDENCE_TYPE_RANK[item.evidence_type],
    )


class R002AnnotationUniverse(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_count: StrictInt = Field(ge=1, le=250000)
    candidate_keys: tuple[R002CandidateLineKey, ...] = Field(min_length=1, max_length=250000)

    @model_validator(mode="after")
    def bind_keys(self) -> Self:
        keys = [r002_annotation_key_order(key) for key in self.candidate_keys]
        if self.candidate_count != len(keys) or len(keys) != len(set(keys)) or keys != sorted(keys):
            raise ValueError("annotation keys must be sorted, unique, and complete")
        return self


class R002AnnotationReviewItem(R002StrictModel):
    key: R002CandidateLineKey
    line_content: str
    previous_line: str | None = None
    next_line: str | None = None
    relevant: bool | None = None
    reason_code: str | None = None

    @model_validator(mode="after")
    def validate_line_bounds(self) -> Self:
        if any(
            value is not None and len(value.encode()) > 65536
            for value in (self.line_content, self.previous_line, self.next_line)
        ):
            raise ValueError("annotation review lines must not exceed 64 KiB")
        return self


class R002AnnotationReview(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    items: tuple[R002AnnotationReviewItem, ...] = Field(min_length=1, max_length=250000)

    @model_validator(mode="after")
    def bind_ordered_unique_items(self) -> Self:
        keys = [r002_annotation_key_order(item.key) for item in self.items]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("annotation review items must be sorted and unique")
        # The cache writer additionally compares this collection against the
        # persisted annotation-universe count and hash when both are available.
        return self


class _LabelCollection(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    annotation_universe_sha256: Sha256
    annotation_count: StrictInt = Field(ge=1, le=250000)
    labels: tuple[R002CandidateLabel, ...] = Field(min_length=1, max_length=250000)
    expected_missing: tuple[R002ExpectedMissing, ...] = Field(max_length=20 * 16 * 4)

    @model_validator(mode="after")
    def bind_labels(self) -> Self:
        keys = [r002_annotation_key_order(label.key) for label in self.labels]
        if (
            self.annotation_count != len(keys)
            or len(keys) != len(set(keys))
            or keys != sorted(keys)
        ):
            raise ValueError("labels must be sorted, unique, and complete")
        actual_records = tuple(_expected_missing_order(item) for item in self.expected_missing)
        if actual_records != tuple(sorted(actual_records)) or len(actual_records) != len(
            set(actual_records)
        ):
            raise ValueError("expected missing records must be sorted and unique")
        return self


class R002CandidateLabelProposal(_LabelCollection):
    benchmark_owner_confirmed: Literal[False] = False


class R002CandidateLabelSet(_LabelCollection):
    benchmark_owner_confirmed: Literal[True]


class R002Metric(R002StrictModel):
    state: R002MetricState
    numerator: StrictInt = Field(ge=0)
    denominator: StrictInt = Field(ge=0)
    value: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_ratio(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("metric numerator cannot exceed denominator")
        if self.denominator == 0:
            if self.state is not R002MetricState.NOT_APPLICABLE or self.value is not None:
                raise ValueError("zero denominator must be not_applicable")
        elif (
            self.state is not R002MetricState.VALUE
            or self.value != self.numerator / self.denominator
        ):
            raise ValueError("nonzero denominator must report the exact ratio")
        return self


class R002RetrievedCandidate(R002StrictModel):
    key: R002CandidateLineKey
    evidence_type: EvidenceType
    evidence_level: EvidenceLevel
    hunk_id: R002HunkId
    head_file_sha256: Sha256
    matching_rule: Literal["exact_identifier", "keyword_overlap"]
    relevance_score: float = Field(ge=0, le=1)
    owner_label_relevant: bool

    @model_validator(mode="after")
    def bind_hunk_to_candidate_key(self) -> Self:
        if self.hunk_id.startswith(f"{self.key.stream}:{self.key.path}:H"):
            return self
        raise ValueError("retrieved candidate hunk ID must bind stream and path")


class R002MissingExplanation(R002StrictModel):
    case_id: R002CaseId
    criterion_id: str = Field(pattern=R002_CRITERION_ID_PATTERN)
    evidence_type: EvidenceType
    source: Literal["scopeproof_finding", "r002_retrieval_comparison"]
    finding_status: FindingStatus
    reason_code: str = Field(min_length=1)

    @model_validator(mode="after")
    def bind_reason_to_its_evidence_source(self) -> Self:
        if self.source == "scopeproof_finding":
            if self.reason_code != "scopeproof_finding_explicit_gap" or self.finding_status not in {
                FindingStatus.PARTIAL,
                FindingStatus.MISSING,
                FindingStatus.NEEDS_REVIEW,
            }:
                raise ValueError("finding missing explanations require their fixed gap reason")
        elif (
            self.reason_code
            not in {
                "no_candidate_retrieved_for_type",
                "retrieved_only_owner_labelled_irrelevant",
            }
            or self.finding_status is not FindingStatus.EVIDENCE_FOUND
        ):
            raise ValueError("retrieval missing explanations require an evidence-found finding")
        return self


class R002CaseResult(R002StrictModel):
    case_id: R002CaseId
    repository: str = Field(pattern=GITHUB_REPOSITORY_PATTERN)
    pr_number: StrictInt = Field(gt=0)
    head_sha: GitSha
    criterion_count: StrictInt = Field(ge=1, le=16)
    annotation_candidate_count: StrictInt = Field(ge=0, le=250000)
    retrieved_candidates: tuple[R002RetrievedCandidate, ...] = Field(max_length=250000)
    missing_explanations: tuple[R002MissingExplanation, ...] = Field(max_length=64)
    gate_verdict: GateVerdict
    gate_reason_codes: tuple[str, ...] = Field(max_length=3)
    blocking_criteria: tuple[str, ...] = Field(max_length=16)
    conditional_criteria: tuple[str, ...] = Field(max_length=16)
    unresolved_criteria: tuple[str, ...] = Field(max_length=16)
    check_state: CheckState
    ci_reason_code: CIReasonCode
    runtime_evidence_count: StrictInt = Field(ge=0)
    resolution_count: StrictInt = Field(ge=0)
    final_acceptance: bool
    separation_errors: StrictInt = Field(ge=0)
    reference_errors: StrictInt = Field(ge=0)
    limitations: tuple[str, ...] = Field(
        min_length=len(R002_RESULT_LIMITATIONS), max_length=len(R002_RESULT_LIMITATIONS)
    )

    @model_validator(mode="after")
    def reject_non_static_success_signals(self) -> Self:
        approved = _approved_case(self.case_id)
        if (self.repository, self.pr_number, self.head_sha) != (
            approved.repository,
            approved.pr_number,
            approved.head_sha,
        ):
            raise ValueError("case result must bind the approved immutable identity")
        criterion_groups = (
            self.blocking_criteria,
            self.conditional_criteria,
            self.unresolved_criteria,
        )
        if self.gate_verdict not in {GateVerdict.BLOCKED, GateVerdict.NEEDS_REVIEW}:
            raise ValueError("R-002 case results must be blocked or needs_review")
        if any(tuple(sorted(set(group))) != group for group in criterion_groups):
            raise ValueError("criterion groups must be sorted unique criterion IDs")
        criterion_universe = {f"AC-{number:02d}" for number in range(1, self.criterion_count + 1)}
        if any(item not in criterion_universe for group in criterion_groups for item in group):
            raise ValueError("criterion groups must remain within the case criteria")
        if any(
            set(left) & set(right)
            for left, right in (
                (self.blocking_criteria, self.conditional_criteria),
                (self.blocking_criteria, self.unresolved_criteria),
                (self.conditional_criteria, self.unresolved_criteria),
            )
        ):
            raise ValueError("criterion groups must be pairwise disjoint")
        expected_reasons: tuple[str, ...]
        if self.gate_verdict is GateVerdict.BLOCKED:
            if not self.blocking_criteria:
                raise ValueError("blocked R-002 cases require blocking criteria")
            expected_reasons = tuple(
                sorted(
                    code
                    for code, criteria in (
                        ("blocking_criteria", self.blocking_criteria),
                        ("conditional_criteria", self.conditional_criteria),
                        ("unresolved_criteria", self.unresolved_criteria),
                    )
                    if criteria
                )
            )
        else:
            if self.blocking_criteria or not self.unresolved_criteria:
                raise ValueError("needs_review R-002 cases require unresolved criteria only")
            expected_reasons = tuple(
                sorted(
                    code
                    for code, criteria in (
                        ("conditional_criteria", self.conditional_criteria),
                        ("unresolved_criteria", self.unresolved_criteria),
                        ("checks_not_passing", ("ci",)),
                    )
                    if criteria
                )
            )
        if self.gate_reason_codes != expected_reasons:
            raise ValueError("R-002 gate reason codes must match the gate shape")
        if (
            self.check_state is not CheckState.UNAVAILABLE
            or self.ci_reason_code is not CIReasonCode.NO_OBSERVATIONS
        ):
            raise ValueError("R-002 case results require unavailable unobserved CI")
        if (
            self.runtime_evidence_count != 0
            or self.resolution_count != 0
            or self.final_acceptance
            or self.separation_errors != 0
            or self.reference_errors != 0
        ):
            raise ValueError("R-002 case results cannot contain success or integrity signals")
        if self.limitations != R002_RESULT_LIMITATIONS:
            raise ValueError("R-002 case results require the fixed limitations")
        for candidate in self.retrieved_candidates:
            planned_type = _evidence_type(ChangedFile(path=candidate.key.path, status="modified"))
            if candidate.evidence_type is not planned_type:
                raise ValueError("R-002 candidate type must match its changed path")
            if candidate.key.stream is R002DiffStream.TEST_PATCH and (
                candidate.evidence_type is not EvidenceType.TEST
                or candidate.evidence_level is not EvidenceLevel.E2
            ):
                raise ValueError("test_patch candidates must be TEST E2 evidence")
            if candidate.key.stream is R002DiffStream.PATCH and candidate.evidence_level is not (
                EvidenceLevel.E2 if planned_type is EvidenceType.TEST else EvidenceLevel.E1
            ):
                raise ValueError("patch candidates must match planned evidence level")
        if any(
            item.evidence_type not in R002_STATIC_EVIDENCE_TYPES
            for item in self.missing_explanations
        ):
            raise ValueError("R-002 missing explanations must be static evidence types")
        candidate_keys = [r002_annotation_key_order(item.key) for item in self.retrieved_candidates]
        if candidate_keys != sorted(candidate_keys) or len(candidate_keys) != len(
            set(candidate_keys)
        ):
            raise ValueError("retrieved candidates must be sorted unique references")
        if self.annotation_candidate_count < len(candidate_keys):
            raise ValueError("annotation candidate count must cover unique retrieved candidates")
        explanation_keys = [
            (item.case_id, item.criterion_id, item.evidence_type.value)
            for item in self.missing_explanations
        ]
        if explanation_keys != sorted(explanation_keys) or len(explanation_keys) != len(
            set(explanation_keys)
        ):
            raise ValueError("missing explanations must be sorted unique references")
        for case_id, criterion_id, *_ in candidate_keys + explanation_keys:
            if case_id != self.case_id or not re.fullmatch(r"AC-(0[1-9]|1[0-6])", criterion_id):
                raise ValueError("result references must remain within the case criteria")
            if int(criterion_id.removeprefix("AC-")) > self.criterion_count:
                raise ValueError("result references cannot exceed the case criterion count")
        return self


class R002Metrics(R002StrictModel):
    owner_confirmed_label_candidate_precision: R002Metric
    criterion_candidate_coverage: R002Metric
    candidate_to_gold_file_coverage: R002Metric
    candidate_to_gold_hunk_coverage: R002Metric
    missing_evidence_explanation_completeness: R002Metric
    implementation_test_separation_errors: StrictInt = Field(ge=0)
    immutable_reference_integrity_errors: StrictInt = Field(ge=0)
    parse_errors: StrictInt = Field(ge=0)
    schema_errors: StrictInt = Field(ge=0)
    source_hash_errors: StrictInt = Field(ge=0)
    source_sha_errors: StrictInt = Field(ge=0)
    unexpected_ready_count: StrictInt = Field(ge=0)
    normalized_rerun_mismatches: StrictInt = Field(ge=0)

    @model_validator(mode="after")
    def require_zero_integrity_errors(self) -> Self:
        error_counts = (
            self.implementation_test_separation_errors,
            self.immutable_reference_integrity_errors,
            self.parse_errors,
            self.schema_errors,
            self.source_hash_errors,
            self.source_sha_errors,
            self.unexpected_ready_count,
            self.normalized_rerun_mismatches,
        )
        if any(error_counts):
            raise ValueError("successful R-002 metrics require zero integrity errors")
        return self


class R002DeterminismProjection(R002Manifest):
    source_manifest_sha256: Sha256
    criteria_set_sha256: Sha256
    candidate_label_set_sha256: Sha256
    scopeproof_commit: GitSha
    case_results: tuple[R002CaseResult, ...] = Field(min_length=20, max_length=20)
    metrics: R002Metrics
    limitations: tuple[str, ...] = Field(
        min_length=len(R002_RESULT_LIMITATIONS), max_length=len(R002_RESULT_LIMITATIONS)
    )

    @model_validator(mode="after")
    def bind_safe_case_results(self) -> Self:
        _require_approved_case_ids(self.case_results)
        if self.limitations != R002_RESULT_LIMITATIONS:
            raise ValueError("R-002 projections require the fixed limitations")
        if any(
            (result.repository, result.pr_number, result.head_sha)
            != (approved.repository, approved.pr_number, approved.head_sha)
            for result, approved in zip(self.case_results, R002_APPROVED_CASES, strict=True)
        ):
            raise ValueError("R-002 projections require the approved cohort identities")
        unique_candidates = {
            r002_annotation_key_order(candidate.key): candidate
            for result in self.case_results
            for candidate in result.retrieved_candidates
        }
        denominator = len(unique_candidates)
        numerator = sum(candidate.owner_label_relevant for candidate in unique_candidates.values())
        expected_precision = R002Metric(
            state=(R002MetricState.VALUE if denominator else R002MetricState.NOT_APPLICABLE),
            numerator=numerator,
            denominator=denominator,
            value=(numerator / denominator if denominator else None),
        )
        if self.metrics.owner_confirmed_label_candidate_precision != expected_precision:
            raise ValueError(
                "owner-confirmed candidate precision must reconstruct from case results"
            )
        if (
            self.metrics.implementation_test_separation_errors
            != sum(result.separation_errors for result in self.case_results)
            or self.metrics.immutable_reference_integrity_errors
            != sum(result.reference_errors for result in self.case_results)
            or self.metrics.unexpected_ready_count
            != sum(result.gate_verdict is GateVerdict.READY for result in self.case_results)
        ):
            raise ValueError("R-002 derivable metric counters must reconstruct from case results")
        # The remaining coverage/error denominators depend on confirmed labels,
        # parsed inputs, and two-pass comparison; Task 8 cross-binds them there.
        return self


class R002BenchmarkResult(R002DeterminismProjection):
    executed_case_count: StrictInt = Field(ge=0)
    failed_case_count: StrictInt = Field(ge=0)
    skipped_case_count: StrictInt = Field(ge=0)
    confirmed_criterion_count: StrictInt = Field(ge=0)
    annotation_candidate_count: StrictInt = Field(ge=0, le=250000)
    unexpected_ready_count: StrictInt = Field(ge=0)
    normalized_rerun_mismatches: StrictInt = Field(ge=0)
    hard_gate_errors: tuple[str, ...] = Field(max_length=0)

    @model_validator(mode="after")
    def require_successful_run_boundary(self) -> Self:
        if (
            self.executed_case_count != 20
            or self.failed_case_count != 0
            or self.skipped_case_count != 0
            or self.confirmed_criterion_count < 20
            or self.annotation_candidate_count < 1
            or self.confirmed_criterion_count
            != sum(item.criterion_count for item in self.case_results)
            or self.annotation_candidate_count
            != sum(item.annotation_candidate_count for item in self.case_results)
            or self.unexpected_ready_count != self.metrics.unexpected_ready_count
            or self.normalized_rerun_mismatches != self.metrics.normalized_rerun_mismatches
            or self.hard_gate_errors
        ):
            raise ValueError("R-002 benchmark result violates the successful-run boundary")
        return self


def canonical_json_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_sha256(value: BaseModel | dict[str, object]) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def case_projection_sha256(cases: Sequence[R002CaseManifest]) -> str:
    payload = [case.model_dump(mode="json") for case in cases]
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def load_source_manifest(path: Path) -> R002SourceManifest:
    value = R002SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source.model_dump(mode="json") != R002_SOURCE:
        raise R002SourceError("source_pin_mismatch")
    if case_projection_sha256(value.cases) != R002_APPROVED_CASES_SHA256:
        raise R002SourceError("approved_cohort_mismatch")
    return value


def load_confirmed_criteria(path: Path, manifest_sha256: str) -> R002CriteriaSet:
    value = R002CriteriaSet.model_validate_json(path.read_text(encoding="utf-8"))
    if value.source_manifest_sha256 != manifest_sha256:
        raise R002AnnotationError("criteria_manifest_drift")
    try:
        manifest = load_source_manifest(path.with_name("source_manifest.json"))
    except (OSError, ValidationError, R002SourceError) as error:
        raise R002AnnotationError("criteria_manifest_context_invalid") from error
    if canonical_sha256(manifest) != manifest_sha256:
        raise R002AnnotationError("criteria_manifest_drift")
    criteria_projection = tuple(
        (case.case_id, case.problem_statement_sha256) for case in value.cases
    )
    manifest_projection = tuple(
        (case.case_id, case.problem_statement_sha256) for case in manifest.cases
    )
    if criteria_projection != manifest_projection:
        raise R002AnnotationError("criteria_manifest_projection_drift")
    return value


def load_confirmed_labels(
    path: Path, manifest_sha256: str, criteria_sha256: str
) -> R002CandidateLabelSet:
    value = R002CandidateLabelSet.model_validate_json(path.read_text(encoding="utf-8"))
    if (
        value.source_manifest_sha256 != manifest_sha256
        or value.criteria_set_sha256 != criteria_sha256
    ):
        raise R002AnnotationError("candidate_label_upstream_drift")
    try:
        criteria = load_confirmed_criteria(path.with_name("criteria.json"), manifest_sha256)
    except (OSError, ValidationError, R002AnnotationError) as error:
        raise R002AnnotationError("candidate_label_upstream_drift") from error
    if canonical_sha256(criteria) != criteria_sha256:
        raise R002AnnotationError("candidate_label_upstream_drift")
    criterion_pairs = tuple(
        (case.case_id, criterion.criterion_id)
        for case in criteria.cases
        for criterion in case.criteria
    )
    criterion_pair_set = set(criterion_pairs)
    if any(
        (label.key.case_id, label.key.criterion_id) not in criterion_pair_set
        for label in value.labels
    ):
        raise R002AnnotationError("candidate_label_upstream_drift")
    relevant_types = {
        (
            label.key.case_id,
            label.key.criterion_id,
            _evidence_type(ChangedFile(path=label.key.path, status="modified")),
        )
        for label in value.labels
        if label.relevant
    }
    expected_records = tuple(
        (case_id, criterion_id, evidence_type)
        for case_id, criterion_id in criterion_pairs
        for evidence_type in R002_STATIC_EVIDENCE_TYPES
        if (case_id, criterion_id, evidence_type) not in relevant_types
    )
    actual_records = tuple(
        (item.case_id, item.criterion_id, item.evidence_type) for item in value.expected_missing
    )
    if actual_records != expected_records:
        raise R002AnnotationError("candidate_label_upstream_drift")
    universe = R002AnnotationUniverse(
        source_manifest_sha256=value.source_manifest_sha256,
        criteria_set_sha256=value.criteria_set_sha256,
        candidate_count=value.annotation_count,
        candidate_keys=tuple(label.key for label in value.labels),
    )
    if canonical_sha256(universe) != value.annotation_universe_sha256:
        raise R002AnnotationError("annotation_universe_drift")
    # Task 7 additionally compares this reconstructed label universe with the
    # actual cache annotation universe during production run validation.
    return value
