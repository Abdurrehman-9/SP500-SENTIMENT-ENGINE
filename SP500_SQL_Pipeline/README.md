# S&P 500 Market Monitoring Engine — historical load and daily refresh

This package loads free source data into your **Microsoft SQL Server** database.
It does not calculate sentiment scores or train models yet. Your six-tab dashboard
and feature calculations come next.

## 1. Files and where the data goes

| File/location | Purpose |
|---|---|
| `01_create_database.sql` | Creates `SP500_Engine` and five tables. Run in SSMS. |
| `pipeline.py` | Both historical load (`backfill`) and daily refresh (`daily`). |
| `config.json` | Your SQL Server name and download settings. No password needed. |
| `02_verify_load.sql` | Queries to inspect the load in SSMS. |
| `test_pipeline.py` | Offline data-integrity checks. |
| `VALIDATION.md` | What was tested before delivery and what remains to test locally. |
| SQL Server `SP500_Engine` | The master structured data. SQL Server manages its physical MDF/LDF files. |
| `data/raw/<run-id>/` | Original downloaded responses and `report.json` for that run. |
| `logs/pipeline.log` | Running progress, warnings and errors. |

SQL tables: `PipelineRun` records job status; `FetchAudit` records each source result;
`ConstituentSnapshot` records observed membership; `SeriesObservation` stores index/VIX/P/E;
`DailyPrice` stores stock and ETF prices. No `.db` file or SQLite is used.
Keep raw files for tracing numbers back to source. These downloads can grow substantially
with daily runs. Back up SQL Server and the raw folder separately. `.gitignore` excludes
raw data and logs; Git is for code, not your master dataset.

## 2. Exact Windows setup commands

Download `SP500_SQL_Pipeline.zip` to your **Downloads** folder. Open **PowerShell**.
Run the following. Commands assume the download has exactly that filename.

```powershell
$Project = Join-Path $HOME 'SP500_Engine'
New-Item -ItemType Directory -Force -Path $Project | Out-Null
Expand-Archive -LiteralPath "$HOME\Downloads\SP500_SQL_Pipeline.zip" -DestinationPath $Project -Force
Set-Location $Project
py --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use **64-bit Python 3.11 or newer**. If `py` is not found, install Python from
https://www.python.org/downloads/windows/ with the Python launcher, reopen PowerShell,
then rerun the commands. Using the venv executable directly avoids activation-policy issues.

Install **Microsoft ODBC Driver 18 for SQL Server (x64)** if it is not already installed:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
Having SSMS installed does not necessarily mean this Python driver is installed.

Check the installed drivers:

```powershell
.\.venv\Scripts\python.exe -c "import pyodbc; print(pyodbc.drivers())"
```

The output should include `ODBC Driver 18 for SQL Server`.

## 3. Create the database and connect Python

1. Open SSMS and connect to your existing database engine using **Windows Authentication**.
2. Open `01_create_database.sql` from the project folder. Press **F5** to run the entire file.
3. Refresh **Databases**. You should see **SP500_Engine** and its five tables.

Then in PowerShell:

```powershell
notepad .\config.json
```

Change only `sql_server` to **exactly the Server name you use in SSMS**. Examples:

```json
"sql_server": "localhost"
```

or, for a named Express instance (JSON needs two backslashes):

```json
"sql_server": "YOUR-PC\\SQLEXPRESS"
```

Keep `sql_database` as `SP500_Engine`. Save and close Notepad. Run:

```powershell
.\.venv\Scripts\python.exe .\pipeline.py dbcheck
.\.venv\Scripts\python.exe -m unittest -v test_pipeline.py
```

Expected: `Connected successfully to SP500_Engine`, then passing tests.
Use the same Windows account as SSMS. No SQL password or API key is needed.
`trust_server_certificate: true` accommodates a local development SQL Server certificate;
use a trusted certificate and set it to `false` for a remote production server.

## 4. Load historical data — Step 2

```powershell
.\.venv\Scripts\python.exe .\pipeline.py backfill
$LASTEXITCODE
.\.venv\Scripts\python.exe .\pipeline.py verify
```

Default scope:

- **Prices, S&P 500 and VIX:** three years plus **400 calendar days of warm-up**
  so later 200-trading-day averages can be calculated near the start of the three-year display window.
- **P/E:** ten years of completed-month observations. No daily values are invented.
- **Membership:** the roster observed when the job runs. It is NOT applied to past dates.
- **End date:** yesterday in New York, excluding an unfinished current-day bar.

The full load makes approximately 500 separate price requests and may take tens of minutes.
Progress is printed for each dataset. Do not start another copy while it is running.

Optional custom historical start (this includes warm-up; choose it accordingly):

```powershell
.\.venv\Scripts\python.exe .\pipeline.py backfill --start 2022-01-01
```

Run `02_verify_load.sql` in SSMS after the download. Check:

1. Latest run status and any failed/warned datasets.
2. Rows exist for `SP500`, `VIX`, `PE_MONTHLY`, `SPY`, `RSP` and current stocks.
3. Latest dates are plausible; every current stock has a coverage row.
4. Newly listed stocks may have fewer than 200 observations. They will need to be excluded
   from an SMA200 denominator until enough valid history exists.

Exit codes: **0 = ingestion checks passed**, **2 = partial load/warnings**,
**1 = fatal failure**. A partial load retains successful datasets and lists the gaps.
Do not describe it as complete. Rerunning is safe: primary keys prevent duplicate dates,
and replacement of each dataset is transactional. Each rerun creates a new audit/run entry.

## 5. Daily refresh — Step 3

After a historical load, run the same tested program with a different command:

```powershell
Set-Location "$HOME\SP500_Engine"
.\.venv\Scripts\python.exe .\pipeline.py daily
$LASTEXITCODE
.\.venv\Scripts\python.exe .\pipeline.py verify
```

Run around **10:00 AM Pakistan time** after the preceding US trading day. Weekends/holidays
do not require new price rows. An older P/E date is expected because that input is monthly.
If a provider has not published its latest value, the report exposes its actual latest date.

Daily refresh records a fresh membership snapshot and fetches prices through the new end date.
It re-downloads the stored price window instead of just appending one row, because splits
and distributions can revise historical adjusted prices. The saved historical start is
retained. Newly added members receive their available history. Previously captured members
are refreshed too, but are not counted in the latest roster. A delisted symbol that stops
responding is flagged; its previously stored data is retained. No substitute symbol is guessed.

`run_daily.cmd` is included for later use with Task Scheduler. Schedule under the same Windows
account that has SQL access. Automatic scheduling is not enabled by this package.

## 6. Sources and meanings

| Input | Actual source | Stored meaning / intended use |
|---|---|---|
| S&P 500 index close | FRED SP500 public CSV | Price index, excluding dividends; regime and realized volatility. |
| VIX close | Cboe daily CSV | Expected volatility indicator; stress. |
| Monthly index P/E | Multpl monthly table | Price relative to trailing earnings; valuation context. Historical publication dates are not supplied. |
| Current members, names, sectors, CIK | Wikipedia current S&P 500 table | Observed current securities; health universe. Multiple share classes can exceed 500 securities. |
| Stock prices | Yahoo Finance public chart endpoint | Split-adjusted close for later moving averages. |
| SPY and RSP prices | Yahoo Finance public chart endpoint | Both dividend-adjusted closes for a comparable 30-session return difference. |

**Necessary price connector:** FRED/Cboe/Multpl do not supply each member's prices or RSP's
price history. Yahoo is the free price connector included here. SPY is a fund tracking the
ordinary S&P 500; RSP tracks its equal-weight version. Their return difference is a proxy
for large-company leadership, not exact stock-level index contribution. Fund fees and
tracking differences also affect that comparison. No official weights are loaded.

Source URLs are saved per fetch in `FetchAudit` and `report.json`:

- https://fred.stlouisfed.org/series/SP500
- https://www.cboe.com/tradable-products/vix/vix-historical-data/
- https://www.multpl.com/s-p-500-pe-ratio/table/by-month
- https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
- https://finance.yahoo.com/quote/RSP/history/
- https://finance.yahoo.com/quote/SPY/history/

Public download endpoints can change or throttle requests; this package does not guarantee
permanent availability. It uses timeouts, limited retries and visible failures. It never
silently switches providers, fills missing prices, interpolates crises or backdates membership.
Free access also does not grant unrestricted redistribution rights; keep raw downloads local.

## 7. If something fails

| Message | Action |
|---|---|
| SQL connection failed | Match `sql_server` to SSMS and use the same Windows account. Confirm the SQL script ran. |
| ODBC driver missing | Install Microsoft's x64 Driver 18, then rerun `dbcheck`. |
| HTTP 429 | Provider rate limit. Wait and rerun later; successful SQL data remains. Increase `request_pause_seconds` if needed. |
| HTTP 401/403 or changed table | Source access changed or was blocked. Do not buy a subscription; share the named source error so the connector can be repaired. |
| `partial` | Read the latest `report.json` or FetchAudit query; identify the missing/stale series. |

Optional source-only sample, requiring no SQL connection:

```powershell
.\.venv\Scripts\python.exe .\pipeline.py sample
```

It fetches the roster, three index/valuation series, three example stocks, SPY and RSP.
It is a diagnostic, not a mandatory repeat of Step 1. Do not confuse a passing sample with
complete stock coverage or a successful SQL load.
