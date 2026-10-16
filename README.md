# CarScraper

A .NET 10 Blazor Server app for comparing AutoTrader UK listings. Python and Selenium collect the listings.
Both applications use `Database/cars.sqlite3`.

## Setup

Install the .NET 10 SDK, Python 3.10 or later, and Google Chrome.
Run these commands from this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
dotnet restore CarScraper.slnx
dotnet run --project frontend/CarScraper.Web
```

Open the local URL printed by .NET. The default development profile uses `http://localhost:5236`.
You can also open `CarScraper.slnx` in Visual Studio and start `CarScraper.Web`.

The Python interpreter defaults to `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` elsewhere.
Selenium obtains a compatible Chrome driver on its first run, which requires internet access.
The Blazor server and Python worker run on the same computer. Run one app instance per database.

## Create and run a search

1. Enter a postcode, filters, and one or more make/model pairs.
   Select **Any age** to ignore both year limits. Uncheck it to restore the previous year range.
2. Select **Save search**. Blazor writes a draft to SQLite and selects it in the history.
3. Select **Search**. The saved search enters the queue.
4. Watch the status and results. Blazor reads SQLite every two seconds.

The server runs one Python search at a time. You can save other searches while it runs.
Leave background Chrome unchecked to handle cookie consent in the Chrome window.
Closing the browser tab does not stop a search. The Blazor server must remain running.
The UI has no Excel download and does not create spreadsheets.

Filter collected results by name/location, fuel, or transmission. Sort by distance, price, year, or mileage.
Advert links open in a separate tab. Unknown listing fields remain blank.

**Search again** reuses the saved criteria and primary key. The worker clears that search's previous results when it starts.
Create a new search when you want to preserve an earlier snapshot.
If a search fails, its collected results remain visible as partial results. Select **Search again** to retry.

## Database contract

There are two tables:

| Table | Purpose |
| --- | --- |
| `searches` | Criteria, make/model JSON, options, timestamps, progress, errors, and run status. Primary key: `id`. |
| `search_results` | Collected listing fields. `search_id` references `searches.id`. Advert links are unique within a search. |

The lifecycle is `draft → queued → running → completed` or `failed`.
Blazor saves and queues the search. Python claims a queued search before opening Chrome.
A second worker cannot claim the same queued record. Duplicate button clicks cannot queue an active search again.

Blazor passes only the search ID and database path to Python:

```powershell
.\.venv\Scripts\python.exe -m carscraper.jobs.worker --search-id 1 --database Database/cars.sqlite3
```

This command requires an existing **queued** search. Python reads all search parameters from SQLite.
It commits each collected page and updates the existing search status. It never creates a second search record.

Both runtimes use the same schema and additive migration files in `carscraper/storage/`.
Existing searches retain their IDs and results. The migration marks earlier searches as completed.
SQLite uses write-ahead logging and a 30-second lock timeout to support polling during writes.

Queued searches survive an app restart. The app marks interrupted running searches as failed so they can be retried.
On normal shutdown, the app stops its Python process and Chrome process tree.

## Configuration

Use the `Scraper` section in `frontend/CarScraper.Web/appsettings.json`:

```json
{
  "Scraper": {
    "RepositoryRoot": "../..",
    "DatabasePath": "Database/cars.sqlite3",
    "PythonExecutable": ".venv/Scripts/python.exe"
  }
}
```

`RepositoryRoot` is relative to the web project's content root. Database and interpreter paths are relative to the repository root.
You can use absolute paths or environment variables such as `Scraper__DatabasePath`.
For a published app, set `RepositoryRoot` to the checkout that contains the Python package and virtual environment.
The app binds to localhost for local personal use. It has no user authentication.

## Code structure

```text
CarScraper.slnx
frontend/
  CarScraper.Web/
    Components/Searches/       Search form, history, and result table
    Configuration/             Python and database paths
    Models/                    Search criteria, status records, and listings
    Data/                      SQLite schema setup and repository
    Services/                  Queue, hosted worker, and Python process runner
  CarScraper.Web.Tests/         .NET/Python integration tests
carscraper/
  config.py                    Python search validation
  paths.py                     Python application paths
  scraping/                    URL construction, parsing, and browser traversal
  storage/
    schema.sql                 Base table definitions
    search_lifecycle.sql       Shared additive lifecycle migration
    database.py                Connection and migration helpers
    repository.py              Existing command-line history persistence
    search_run.py              Claiming, incremental results, and completion
  jobs/worker.py               Run a saved search by ID
  exports/excel.py             Optional standalone CLI export
  cli.py                       Standalone CLI
tests/                         Python tests
Database/cars.sqlite3           Shared local database
```

The previous Streamlit UI has been removed. Blazor owns search creation and process scheduling.
Python owns browser automation, parsing, and incremental result persistence.

## Standalone CLI

The JSON-based CLI remains available independently of Blazor:

```powershell
Copy-Item search.example.json search.json
.\.venv\Scripts\python.exe autotrader_scraper.py --dry-run
.\.venv\Scripts\python.exe autotrader_scraper.py --database Database/cars.sqlite3 --max-pages 1
```

Edit `search.json` before running. This standalone command creates a completed search snapshot and an Excel workbook.
It does not use the Blazor queue. The example JSON does not control the Blazor form.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
dotnet test CarScraper.slnx
```

Tests cover migration, search claiming, duplicate starts, partial results, failures, and the .NET/Python database contract.
Integration tests use the repository's Python virtual environment and temporary databases.
They substitute browser scraping with synthetic listings. Live AutoTrader compatibility remains unverified.

After building the web app, an optional headless Chrome check tests saving and starting a search through the UI:

```powershell
.\.venv\Scripts\python.exe tests/blazor_ui_smoke.py
```

This check uses a temporary database and forces a validation failure before contacting AutoTrader.

The scraper stops on unrecognized result pages and saves diagnostic HTML under `debug/`.
Check the server log and the search error for consent screens, access challenges, or changed markup.
The scraper does not bypass access challenges. Update `carscraper/scraping/parsing.py` if the result markup changes.

Inspired by [Shedload of Code's tutorial](https://www.shedloadofcode.com/blog/how-to-scrape-autotrader-with-python-and-selenium-to-search-for-multiple-makes-and-models/).
