# ScopeProof Engineering Rules

ScopeProof is an evidence assistant, not a correctness oracle.

1. Every criterion verdict must cite explicit evidence or state what evidence is missing.
2. Implementation evidence must never be presented as test or runtime verification.
3. Users must confirm normalized acceptance criteria before analysis.
4. Never execute untrusted repository code in the application server.
5. Validate every persisted or exported object with Pydantic schemas.
6. Keep gate decisions deterministic and reproducible.
7. Treat False Ready as more harmful than False Blocked.
8. Add regression coverage for every evidence rule and gate change.
9. Do not add generic code review, security scanning, or auto-fix features.
10. Keep the core engine independent from Streamlit and GitHub UI layers.
