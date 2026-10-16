# Code Structure Implementation Plan

> **For agentic workers:** Execute this refactor inline in the current session. The user authorized implementation and behavior preservation.

**Goal:** Separate responsibilities without changing search results, database schema, or launch commands.

**Architecture:** Put application code in `carscraper/`. Keep root scripts as entry points. Group browser operations, database operations, jobs, and UI views in separate packages.

**Tech Stack:** Python, Selenium, Beautiful Soup, SQLite, Streamlit, unittest.

## Global Constraints

- Preserve the existing SQLite database and schema.
- Preserve the local UI and command-line entry points.
- Do not add Excel output to the UI.
- Keep Python naming conventions. The installed coding-conventions skill targets .NET.

## Task 1: Separate backend responsibilities

Create `carscraper/config.py`, `paths.py`, and `listings.py` for configuration, application paths, and listing fields.
Create `scraping/urls.py`, `parsing.py`, and `browser.py` for URL creation, HTML extraction, and Selenium traversal.
Create `storage/schema.sql` and `repository.py` for schema initialization and database reads/writes.
Create `exports/excel.py` for the existing command-line workbook export.
Create `jobs/process.py` and `worker.py` for launching searches and processing a job.
Create `cli.py` for argument parsing. Keep `autotrader_scraper.py` as its entry point.

Interfaces retain `load_config(path)`, `search_url(car, criteria, page=1)`, `parse_listings(html, car)`,
`scrape(config, max_pages=10, delay=5, headless=False, debug_dir=...)`,
`save_search(config, rows, path, started_at, max_pages, delay)`,
`history(database=DATABASE)`, `results(search_id, database=DATABASE)`, and `export_excel(rows, path)`.

- [x] Extract existing functions without changing their behavior.
- [x] Move SQL schema into its own resource.
- [x] Update import paths and worker launch arguments.
- [x] Run parser, configuration, repository, CLI, and export tests.

## Task 2: Separate UI views

Create `ui/search_form.py`, `search_status.py`, `search_history.py`, `results.py`, and `dashboard.py`.
The dashboard calls `render_search_form()`, `render_search_status()`, and `render_search_history()`.
The history view calls `render_results(rows)`. Each view owns its Streamlit widgets.
Keep `app.py` as the Streamlit entry point. Keep `run_app.py` as the Windows launcher.

- [x] Extract each UI view into its own render function.
- [x] Keep form validation and result filters unchanged.
- [x] Update AppTest mocks to target the modules that own each dependency.
- [x] Run UI and worker integration tests.

## Task 3: Align tests and documentation

Split `tests/test_scraper.py` into configuration, parsing, repository, CLI, and export test modules.
Split worker integration checks from UI component checks.
Update `README.md` with the package layout and entry points.

- [x] Run `.\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v`.
- [x] Run the CLI dry-run and Python compilation checks.
- [x] Check local server startup and stop the verification server.
- [x] Run `git diff --check` and review the final file list.
