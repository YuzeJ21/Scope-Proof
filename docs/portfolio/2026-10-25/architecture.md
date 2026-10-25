# ScopeProof evidence path — `0.2.4.dev0` integrity draft

Demonstrated core revision: `47ebc4f275b9f307c9305af3890782fa7578dff4`.
The published v0.2.3 wheel does not include these draft changes.

```mermaid
flowchart LR
    A[Public PR URL] --> B[GitHub metadata and verified public origin]
    B --> C[Mutable file and commit pages]
    B --> D[Exact base and head SHA]
    C --> E[SHA-addressed compare cross-check]
    D --> E
    E -->|Mismatch or unavailable: stop| X[No analysis or Ready conclusion]
    E -->|Consistent snapshot| F[Deterministic candidate retrieval]
    R[Requirements source] --> N[Normalize atomic criteria]
    N --> H{Reviewer confirms exact criteria}
    H -->|No| X
    H -->|Yes| F
    F --> P[Pydantic ReviewBundle: candidate and finding relationships]
    P --> G[Deterministic gate]
    O[Observed CI at exact head] --> G
    V[Separately supplied runtime record] --> P
    U[Human decisions and final acceptance] --> G
    G --> S[Validated local save and JSON / Markdown / CSV / HTML exports]
    G --> Q[Changed-head re-review comparison]
```

Candidate implementation and contract lines are E1; test candidates are E2. Neither is an
observed run. E3 is a separately recorded external runtime observation, and E4 is explicit human
acceptance. The app does not execute the target repository. GitHub pages and candidate references
must stay tied to one public PR base/head pair. Partial or inconsistent ingestion cannot yield
Ready. The core engine owns parsing, validation, retrieval, comparison, and gate logic; Streamlit
and GitHub presentation remain edge layers.

The compare API's unpaginated response has a 250-commit ceiling. This draft rejects larger
comparisons rather than producing a potentially mixed snapshot. That is an availability limit,
not successful verification.
