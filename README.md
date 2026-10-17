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

1. Choose **New search** from the sidebar or landing page. The form starts blank.
2. Enter a postcode, filters, one or more make/model pairs, a page count, and a delay.
   Type in the make field to narrow the alphabetical brand list, then click a brand or use the arrow keys and Enter.
   Select **Any age** to ignore both year limits. Uncheck it to restore the previous year range.
3. Select **Start search**. Blazor saves and queues the search, then opens its loading screen.
4. Watch its progress and collected listing count. The screen switches to results automatically when the search finishes.

Choose **Previous searches** for an open list of saved searches with their essential criteria, status, and result count.
Selecting an entry opens the same results page used by the new-search workflow. Active searches show their loading screen.
You can refresh or return to a search by URL without starting another run. Status updates every two seconds.
Use **Delete search** in the history list or results page to remove a search and its saved listings after confirmation.
Queued and running searches must finish before they can be deleted.

The server runs one Python search at a time. You can save other searches while it runs.
For each make/model, the scraper navigates to page 1, parses and saves its results,
then navigates to page 2 and continues through the requested page count. Each page
loads separately in the same Chrome session, with the configured delay between navigations.
Missing Next links, repeated adverts, and empty result pages do not shorten the requested run.
Leave background Chrome unchecked to handle cookie consent in the Chrome window.
Closing the browser tab does not stop a search. The Blazor server must remain running.

Filter collected results by name/location, fuel, or transmission. Sort by distance, price, year, or mileage.
Advert links open in a separate tab. Unknown listing fields remain blank.

**Search again** reuses the saved criteria and primary key. The worker clears that search's previous results when it starts.
Create a new search when you want to preserve an earlier snapshot.
If a search fails, its collected results remain visible as partial results. Select **Retry search** to try again.

## Database contract

There are three tables:

| Table | Purpose |
| --- | --- |
| `searches` | Criteria, make/model JSON, options, timestamps, progress, errors, and run status. Primary key: `id`. |
| `search_results` | Collected listing fields. `search_id` references `searches.id`. Advert links are unique within a search. |
| `car_brands` | Brand names for the searchable make field, returned in alphabetical order. |

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
They also seed the 151-brand catalog from `car_brands.sql` without duplicating existing names.
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

Edit `search.json` before running. This standalone command saves a completed search snapshot to SQLite.
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

This check uses a temporary database and synthetic listings to verify the full workflow and a validation failure without contacting AutoTrader.

The scraper stops on unrecognized result pages and saves diagnostic HTML under `debug/`.
Check the server log and the search error for consent screens, access challenges, or changed markup.
The scraper does not bypass access challenges. Update `carscraper/scraping/parsing.py` if the result markup changes.

Inspired by [Shedload of Code's tutorial](https://www.shedloadofcode.com/blog/how-to-scrape-autotrader-with-python-and-selenium-to-search-for-multiple-makes-and-models/).
