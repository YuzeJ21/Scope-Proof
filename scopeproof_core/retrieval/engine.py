"""Conservative line-level matching that never claims semantic proof."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from urllib.parse import quote

from scopeproof_core.schemas.models import (
    ChangedFile,
    ChangedLine,
    Criterion,
    CriterionRetrievalDiagnostic,
    EvidenceItem,
    EvidenceLevel,
    EvidenceRetrievalResult,
    EvidenceSourceScope,
    EvidenceType,
    LineChangeType,
    PullRequestSnapshot,
    RetrievalOutcome,
    RetrievedFile,
)

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_STOP_WORDS = {
    "a",
    "all",
    "an",
    "and",
    "as",
    "be",
    "can",
    "current",
    "if",
    "is",
    "of",
    "on",
    "should",
    "shows",
    "the",
    "to",
    "user",
    "users",
    "with",
}


def _stem(word: str) -> str:
    value = word.casefold()
    if len(value) > 5 and value.endswith("ing"):
        return value[:-3]
    if len(value) > 4 and value.endswith("ed"):
        return value[:-2]
    if len(value) > 4 and value.endswith("s"):
        return value[:-1]
    return value


def _criterion_terms(text: str) -> tuple[set[str], set[str]]:
    raw = [match.group(0).casefold() for match in _WORD.finditer(text)]
    identifiers = {token for token in raw if "_" in token}
    expanded: set[str] = set()
    for token in raw:
        for part in token.split("_"):
            normalized = _stem(part)
            if normalized not in _STOP_WORDS and len(normalized) > 1:
                expanded.add(normalized)
        if token in identifiers:
            expanded.add(token)
    return expanded, identifiers


def _line_terms(content: str) -> set[str]:
    terms: set[str] = set()
    for match in _WORD.finditer(content):
        token = match.group(0).casefold()
        terms.add(token)
        terms.update(_stem(part) for part in token.split("_"))
    return terms


def classify_changed_path_evidence_type(path_value: str) -> EvidenceType:
    """Classify a changed path using the established retrieval rules."""
    path = PurePosixPath(path_value)
    normalized_parts = tuple(part.casefold() for part in path.parts)
    lower_path = path_value.casefold()
    name = path.name.casefold()
    if (
        any(part in {"test", "tests"} for part in normalized_parts)
        or any(part in {"eval", "evals"} for part in normalized_parts)
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    ):
        return EvidenceType.TEST
    if path.suffix.casefold() in {".md", ".rst"} or "docs" in normalized_parts:
        return EvidenceType.DOCUMENTATION
    if "migration" in lower_path or "alembic" in lower_path:
        return EvidenceType.CONTRACT
    if any(marker in lower_path for marker in ("openapi", "schema", "contract")):
        return EvidenceType.CONTRACT
    return EvidenceType.IMPLEMENTATION


def _evidence_type(file: ChangedFile) -> EvidenceType:
    return classify_changed_path_evidence_type(file.path)


def _permalink(
    snapshot: PullRequestSnapshot, file_path: str, line_number: int, commit_sha: str
) -> str:
    repository = quote(snapshot.repository, safe="/")
    commit = quote(commit_sha, safe="")
    path = quote(file_path, safe="/")
    return f"https://github.com/{repository}/blob/{commit}/{path}#L{line_number}-L{line_number}"


def _candidate_file(retrieved: RetrievedFile) -> ChangedFile:
    return ChangedFile(
        path=retrieved.path,
        status="unchanged_candidate",
        lines=[
            ChangedLine(change_type=LineChangeType.CONTEXT, line_number=index, content=content)
            for index, content in enumerate(retrieved.content.splitlines(), start=1)
        ],
    )


def _context_excerpt(changed_file: ChangedFile, line_number: int) -> str:
    """Return the matched line with at most one inspectable neighbor on each side."""

    inspectable = [
        line
        for line in changed_file.lines
        if line.change_type is not LineChangeType.REMOVED and line.line_number is not None
    ]
    match_index = next(
        index
        for index, line in enumerate(inspectable)
        if line.line_number == line_number
    )
    start = max(0, match_index - 1)
    end = min(len(inspectable), match_index + 2)
    return "\n".join(line.content for line in inspectable[start:end])


def retrieve_evidence_with_diagnostics(
    snapshot: PullRequestSnapshot,
    criteria: list[Criterion],
    unchanged_files: list[RetrievedFile] | None = None,
) -> EvidenceRetrievalResult:
    """Return unchanged evidence candidates plus separate deterministic search metadata."""
    evidence: list[EvidenceItem] = []
    diagnostics: list[CriterionRetrievalDiagnostic] = []
    unchanged_candidates = unchanged_files or []
    inputs = [
        (file, EvidenceSourceScope.CHANGED_FILE, snapshot.head_sha)
        for file in snapshot.files
    ]
    inputs.extend(
        (_candidate_file(file), EvidenceSourceScope.UNCHANGED_CANDIDATE, file.commit_sha)
        for file in unchanged_candidates
    )
    searched_paths = sorted({changed_file.path for changed_file, _, _ in inputs})
    searched_evidence_types = sorted(
        {_evidence_type(changed_file) for changed_file, _, _ in inputs},
        key=lambda item: item.value,
    )

    for criterion in criteria:
        criterion_terms, identifiers = _criterion_terms(criterion.text)
        inspectable_line_count = 0
        exact_identifier_match_line_count = 0
        term_overlap_line_count = 0
        below_threshold_line_count = 0
        matches: list[
            tuple[float, ChangedFile, int, str, set[str], bool, EvidenceSourceScope, str]
        ] = []
        for changed_file, source_scope, commit_sha in inputs:
            kind = _evidence_type(changed_file)
            for line in changed_file.lines:
                if line.change_type is LineChangeType.REMOVED or line.line_number is None:
                    continue
                inspectable_line_count += 1
                line_terms = _line_terms(line.content)
                matched = criterion_terms & line_terms
                exact_identifier = bool(identifiers & line_terms)
                if exact_identifier:
                    exact_identifier_match_line_count += 1
                if matched:
                    term_overlap_line_count += 1
                if identifiers and not exact_identifier:
                    continue
                if not matched:
                    continue
                score = len(matched) / len(criterion_terms)
                if exact_identifier:
                    score = max(score, 0.9)
                if kind is EvidenceType.TEST and score < 0.4 and not exact_identifier:
                    below_threshold_line_count += 1
                    continue
                if score < 0.25:
                    below_threshold_line_count += 1
                    continue
                matches.append(
                    (
                        min(score, 1.0),
                        changed_file,
                        line.line_number,
                        line.content,
                        matched,
                        exact_identifier,
                        source_scope,
                        commit_sha,
                    )
                )
        matches.sort(key=lambda item: (-item[0], item[1].path, item[2]))
        selected_matches = []
        selected_types: set[EvidenceType] = set()
        for match in matches:
            kind = _evidence_type(match[1])
            if kind not in selected_types:
                selected_matches.append(match)
                selected_types.add(kind)
        for match in matches:
            if match not in selected_matches:
                selected_matches.append(match)
            if len(selected_matches) == 8:
                break

        for index, (
            score,
            changed_file,
            line_number,
            content,
            matched,
            exact,
            source_scope,
            commit_sha,
        ) in enumerate(
            selected_matches[:8], start=1
        ):
            kind = _evidence_type(changed_file)
            level = EvidenceLevel.E2 if kind is EvidenceType.TEST else EvidenceLevel.E1
            limitations = ["Candidate evidence does not prove the criterion is satisfied"]
            if source_scope is EvidenceSourceScope.UNCHANGED_CANDIDATE:
                limitations.insert(0, "Evidence comes from a bounded unchanged candidate file")
            if kind is EvidenceType.TEST:
                limitations.append("Candidate test evidence requires reviewer confirmation")
                limitations.append(
                    "Candidate test/eval definition shows test intent, not execution"
                )
            evidence.append(
                EvidenceItem(
                    evidence_id=f"EV-{criterion.criterion_id}-{index:02d}",
                    criterion_id=criterion.criterion_id,
                    evidence_type=kind,
                    evidence_level=level,
                    source_scope=source_scope,
                    file_path=changed_file.path,
                    line_start=line_number,
                    line_end=line_number,
                    commit_sha=commit_sha,
                    permalink=_permalink(snapshot, changed_file.path, line_number, commit_sha),
                    excerpt=content.strip(),
                    context_excerpt=_context_excerpt(changed_file, line_number),
                    matching_rule="exact_identifier" if exact else "keyword_overlap",
                    relevance_reason=f"Matched terms: {', '.join(sorted(matched))}",
                    relevance_score=round(score, 3),
                    limitations=limitations,
                )
            )

        accepted_candidate_count = len(selected_matches[:8])
        if accepted_candidate_count:
            outcome = RetrievalOutcome.CANDIDATES_FOUND
        elif not criterion_terms:
            outcome = RetrievalOutcome.NO_SEARCHABLE_TERMS
        elif inspectable_line_count == 0:
            outcome = RetrievalOutcome.NO_INSPECTABLE_LINES
        elif identifiers and exact_identifier_match_line_count == 0:
            outcome = RetrievalOutcome.EXACT_IDENTIFIER_NOT_FOUND
        elif term_overlap_line_count == 0:
            outcome = RetrievalOutcome.NO_TERM_OVERLAP
        else:
            outcome = RetrievalOutcome.BELOW_RELEVANCE_THRESHOLD

        diagnostics.append(
            CriterionRetrievalDiagnostic(
                criterion_id=criterion.criterion_id,
                outcome=outcome,
                searched_terms=sorted(criterion_terms),
                exact_identifiers=sorted(identifiers),
                searched_paths=searched_paths,
                searched_evidence_types=searched_evidence_types,
                changed_file_count=len(snapshot.files),
                unchanged_candidate_file_count=len(unchanged_candidates),
                inspectable_line_count=inspectable_line_count,
                exact_identifier_match_line_count=exact_identifier_match_line_count,
                term_overlap_line_count=term_overlap_line_count,
                below_threshold_line_count=below_threshold_line_count,
                accepted_candidate_count=accepted_candidate_count,
            )
        )

    return EvidenceRetrievalResult(evidence=evidence, diagnostics=diagnostics)


def retrieve_evidence(
    snapshot: PullRequestSnapshot,
    criteria: list[Criterion],
    unchanged_files: list[RetrievedFile] | None = None,
) -> list[EvidenceItem]:
    """Compatibility wrapper returning the established ordered evidence candidates."""
    return retrieve_evidence_with_diagnostics(
        snapshot,
        criteria,
        unchanged_files=unchanged_files,
    ).evidence
