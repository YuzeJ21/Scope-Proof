# Saved-review discovery implementation plan

1. Add failing storage tests for deterministic, bounded review-ID enumeration.
2. Add failing Streamlit tests for fresh-session discovery and selection-based reopening.
3. Implement `JsonReviewStore.list_review_ids()` without parsing records or following symlinks.
4. Update the existing reopen expander to use discovered IDs when available and retain the manual empty-state path.
5. Run focused storage and Streamlit regression tests, then the full verification suite.
6. Verify a fresh session against a real saved record in the in-app browser, including selection and reopening.
7. Publish through a protected pull request, confirm exact merge-SHA checks, synchronize `main`, and continue to the next verified gap.
