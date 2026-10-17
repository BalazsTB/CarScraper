# Blazor saved-search implementation

The Blazor app replaces Streamlit. The Python scraper remains a separate process.

## Responsibilities

- Blazor saves search criteria before starting a worker.
- The SQLite repository queues each saved primary key at most once while it is active.
- The hosted service runs one queued search at a time.
- The process runner uses an argument list to pass the search ID and database path to Python.
- Python claims the queued search, loads its criteria, and commits each result page.
- Blazor polls the database for status, errors, and results.

## Completion checks

- [x] Add a shared additive schema migration without changing existing IDs or results.
- [x] Load worker parameters from the saved search rather than JSON job files.
- [x] Add status, error, and incremental result persistence.
- [x] Add sidebar navigation and a landing page with New search and Previous searches.
- [x] Start from a blank form, then show progress and automatically transition to results.
- [x] Show saved searches as an open list linking to the shared results page.
- [x] Poll saved search results and display failures.
- [x] Remove Streamlit and its job-file implementation.
- [x] Test the .NET/Python database contract and duplicate-start protection.
- [x] Build the .NET solution and verify the UI in headless Chrome.

The standalone JSON-based CLI saves search snapshots to SQLite separately from this workflow.
