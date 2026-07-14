# Review-store root symlink guard implementation plan

1. Add failing core tests for list, load, and save through a symlinked store root.
2. Add a failing Streamlit test for the recoverable unsafe-store state.
3. Implement the explicit core guard and UI availability handling.
4. Run focused tests, then full Ruff, pytest, and benchmark verification.
5. Build and probe a clean archived wheel.
6. Publish through a protected PR, merge only after checks pass, synchronize `main`, and continue.
