# Review-store root type guard implementation plan

1. Add failing core tests for list, load, and save when the store root is a regular file.
2. Add a failing Streamlit test for the recoverable non-directory-store state.
3. Extend the core root assertion with the minimal existing-non-directory check.
4. Run focused tests, then full Ruff, pytest, and benchmark verification.
5. Build and probe a clean archived wheel.
6. Publish through a protected PR, merge only after checks pass, synchronize `main`, and continue.
