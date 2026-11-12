# S&P 500 Sentiment & Market Surveillance Engine

An end-to-end, SQL Server–backed quantitative market intelligence pipeline and executive Streamlit dashboard that monitors the structural health of the S&P 500 across trend regime, constituent breadth, cap-weight concentration, and volatility/valuation risk.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Key Features](#key-features)
4. [Dynamic State-Aware Dashboard Logic](#dynamic-state-aware-dashboard-logic)
5. [Automated Daily Updates (GitHub Actions)](#automated-daily-updates-github-actions)
6. [Prerequisites](#prerequisites)
7. [Local Setup Instructions](#local-setup-instructions)
8. [Verification & Testing](#verification--testing)
9. [Project Structure](#project-structure)

---

## Project Overview

Standard capitalization-weighted index levels often conceal underlying market fragility. A rising S&P 500 headline number can mask narrowing stock participation, mega-cap leadership concentration, or elevated implied volatility.

The **S&P 500 Sentiment Engine** separates ingestion, deterministic SQL/Python feature engineering, and executive visualization into three decoupled layers:

- **Ingestion (`pipeline.py`):** Captures public market series and full constituent OHLCV histories with full run auditing (`dbo.PipelineRun`, `dbo.FetchAudit`).
- **Feature Engineering (`features.py`):** Computes 200-session moving averages, constituent breadth percentages, 30-day `SPY` vs. `RSP` leadership gaps, 20-day realized volatility, and 60-month trailing P/E comparisons in SQL Server (`dbo.StockDailyFeatures`, `dbo.DailyMarketMetrics`).
- **Executive Dashboard (`app.py`):** Renders a clean, state-aware Streamlit UI with dynamic KPI status cards, an auto-generated executive briefing, interactive Plotly diagnostics, a raw data explorer, and stakeholder methodology documentation.

---

## Architecture & Data Flow

```text
+-------------------------------------------------------------------------+
| 1. PUBLIC DATA SOURCES                                                  |
|  - FRED (SP500 Index) + Yahoo Finance (^GSPC holiday/lag fallback)      |
|  - Cboe (Daily VIX History CSV)                                         |
|  - Multpl (Completed Monthly Trailing P/E)                              |
|  - Wikipedia (Current S&P 500 Constituent Roster)                       |
|  - Yahoo Finance (500+ Stock Split-Adj Closes + SPY / RSP Total Return) |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| 2. INGESTION & AUDIT LAYER (pipeline.py)                                |
|  - Transactional SQL replacement per symbol/series                      |
|  - Raw payload archival & SHA-256 checksums in data/raw/<run-id>/       |
|  - SQL Server Tables: PipelineRun, FetchAudit, ConstituentSnapshot,     |
|                       SeriesObservation, DailyPrice                     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| 3. FEATURE ENGINEERING LAYER (features.py)                              |
|  - Index 200-SMA & 20-day trend slope classification                    |
|  - Constituent 200-SMA & coverage-gated Market Health breadth           |
|  - 30-session SPY vs. RSP concentration proxy                           |
|  - VIX vs. 20d realized volatility & 5-year P/E valuation spread        |
|  - SQL Server Tables: StockDailyFeatures, DailyMarketMetrics            |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
| 4. EXECUTIVE UI & CI/CD AUTOMATION                                      |
|  - Streamlit Dashboard (app.py): State-aware KPI cards, Executive       |
|    Briefing, Regime/Health/Concentration/Stress tabs, Data Explorer     |
|  - GitHub Actions (.github/workflows/daily_update.yml): Mon-Fri         |
|    22:00 UTC scheduled refresh + versioned snapshot commits             |
+-------------------------------------------------------------------------+
```

---

## Key Features

- **State-Aware Executive Briefing & Tab Narratives:** Dynamic `if/elif/else` evaluation helpers (`evaluate_regime_state`, `evaluate_health_state`, `evaluate_concentration_state`, `evaluate_stress_valuation_state`, and `build_executive_summary`) automatically rewrite executive takeaways as market conditions shift between `Bull`, `Bear`, `Neutral`, and warmup `Pending` states.
- **Live-Bound KPI Status Indicators:** All five main dashboard KPI cards dynamically bind numerical values, color cues, and status badges (`BULL`/`BEAR`/`NEUTRAL`, `STRONG`/`MIXED`/`WEAK`, `MEGA-CAP LED`/`BROAD MARKET LED`/`BALANCED`, `LOW VOLATILITY`–`HIGH STRESS`, and `PREMIUM`/`DISCOUNTED`/`NEAR AVERAGE`) directly to `dbo.DailyMarketMetrics`.
- **Null-Safe Warmup & Holiday Handling:** Early history warmup windows (`< 220` index sessions or `< 200` constituent sessions) degrade gracefully to `Pending` without exposing `NaN` strings, while Federal-holiday FRED lags (e.g., Veterans Day) automatically supplement missing S&P 500 closes from Yahoo Finance `^GSPC` without overwriting official FRED history.
- **Automated CI/CD Market Refresh:** Post-US market close GitHub Actions automation runs ingestion, feature generation, database verification, and curated snapshot exports on a cron schedule.
- **Data Integrity & Auditability:** Every run logs dataset timestamps, row counts, and SHA-256 digests in SQL Server; Breadth classifications below `95%` constituent coverage are automatically marked `Suppressed`.

---

## Dynamic State-Aware Dashboard Logic

For any selected trading date, [app.py](src/app.py) evaluates the backend row from `dbo.DailyMarketMetrics` across four conditional state machines:

| Pillar | Evaluated Backend Inputs | Dynamic UI Output & States |
|---|---|---|
| **Market Regime** | `Regime`, `IndexClose`, `IndexSMA200`, `IndexSMA200_20d_ago` | `BULL`, `BEAR`, `NEUTRAL` (price reclaim vs. pullback), or `PENDING`; dynamically computes point spread and 20-day slope direction. |
| **Market Health** | `HealthBand`, `BreadthHealthPct`, `BreadthAboveCount`, `BreadthEligibleCount`, `BreadthCoveragePct` | `STRONG` (`> 60%`), `MIXED` (`40%–60%`), `WEAK` (`< 40%`), `SUPPRESSED` (`< 95%` coverage), or `PENDING`; detects bullish index / weak breadth divergences. |
| **Concentration** | `LeadershipGap_PctPoints`, `SPY_30d_Return`, `RSP_30d_Return` | `MEGA-CAP LED` (`> +1.5 pp`), `BROAD MARKET LED` (`< -1.5 pp`), `BALANCED` (`-1.5` to `+1.5 pp`), or `PENDING`. |
| **Stress & Valuation** | `VIX_Close`, `RealizedVol_20d_Annualized`, `Current_PE`, `Historical_PE_60m_Mean`, `PE_vs_Historical_Mean_Pct` | Volatility badge (`LOW VOLATILITY`, `NORMAL`, `ELEVATED`, `HIGH STRESS`) with implied-vs-realized spread note + valuation badge (`PREMIUM` `> +5%`, `DISCOUNTED` `< -5%`, `NEAR AVERAGE`). |

---

## Automated Daily Updates (GitHub Actions)

Daily orchestration is defined in [.github/workflows/daily_update.yml](.github/workflows/daily_update.yml):

1. **Schedule:** Triggers automatically Monday–Friday at **22:00 UTC** (`cron: '0 22 * * 1-5'`, after US equity market close) and supports manual triggers via `workflow_dispatch` (`daily` or `verify` mode).
2. **Runtime & Security:** Runs on `windows-latest` (`pwsh` + Microsoft `ODBC Driver 18 for SQL Server` + Python `3.11`). Database connection settings are injected ephemerally from GitHub Repository Secrets (`SQL_SERVER`, `SQL_DATABASE`, plus optional `SQL_USERNAME`, `SQL_PASSWORD`, and `FRED_API_KEY`) and restored/cleaned via an `if: always()` cleanup step.
3. **Pipeline & Verification:** Executes `pipeline.py daily`, `features.py`, and `pipeline.py verify`.
4. **Snapshot Versioning:** Exports `dbo.DailyMarketMetrics` to `data/snapshots/daily_market_metrics.csv` and commits changes cleanly with `[skip ci]`.

---

## Prerequisites

- **OS:** Windows 10/11 or Windows Server (uses `curl.exe` and Microsoft ODBC Driver)
- **Python:** 64-bit **Python 3.11+**
- **Database:** **Microsoft SQL Server** (Express, Standard, or Enterprise)
- **ODBC Driver:** **Microsoft ODBC Driver 18 for SQL Server (x64)**
- **Python Packages:** `pyodbc>=5.2,<6`, `tzdata>=2025.1`, `pandas`, `plotly`, `streamlit`

---

## Local Setup Instructions

### 1. Clone and Create Virtual Environment
```powershell
git clone https://github.com/<your-username>/sp500-sentiment-engine.git
cd sp500-sentiment-engine

py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pandas plotly streamlit
```

### 2. Provision SQL Server Schema
1. Open **SQL Server Management Studio (SSMS)** and connect using Windows Authentication.
2. Execute the schema scripts in order:
   - `sql/01_create_tables_loanbook.sql` (or `sql/01_create_database.sql` for a standalone `SP500_Engine` database)
   - `sql/03_create_features_schema.sql`

### 3. Configure Database Target
Update `config.json` with your SQL Server instance and database name:
```json
{
  "sql_server": ".\\SQLEXPRESS",
  "sql_database": "LoanBook01",
  "odbc_driver": "ODBC Driver 18 for SQL Server",
  "trust_server_certificate": true
}
```

### 4. Verify Connectivity, Backfill, Compute Features & Launch UI
```powershell
# 1. Verify database connection
.\.venv\Scripts\python.exe .\src\pipeline.py dbcheck

# 2. Initial historical backfill (3 years + 400-day warmup)
.\.venv\Scripts\python.exe .\src\pipeline.py backfill

# 3. Calculate derived breadth, regime, concentration, and stress features
.\.venv\Scripts\python.exe .\src\features.py

# 4. Launch the Executive Streamlit Dashboard
.\.venv\Scripts\streamlit.exe run .\src\app.py --server.port 8501
```

For subsequent daily updates, run:
```powershell
.\run_daily.cmd
```

---

## Verification & Testing

Run the offline integrity and transaction rollback test suite:
```powershell
.\.venv\Scripts\python.exe -m unittest -v tests/test_pipeline.py
```

Verify SQL Server series and stock price coverage:
```powershell
.\.venv\Scripts\python.exe .\src\pipeline.py verify
```

---

## Project Structure

```text
sp500-sentiment-engine/
├── .github/
│   └── workflows/
│       └── daily_update.yml             # Scheduled Mon-Fri 22:00 UTC CI/CD pipeline
├── assets/
│   └── image_874844.png                 # Dashboard UI previews & architecture visuals
├── data/
│   ├── raw/                             # Local raw downloads & run report.json (gitignored)
│   └── snapshots/
│       └── daily_market_metrics.csv     # Versioned daily summary snapshot
├── logs/                                # Runtime pipeline.log & features.log (gitignored)
├── sql/
│   ├── 01_create_database.sql           # Standalone SP500_Engine DB & core tables
│   ├── 01_create_tables_loanbook.sql    # Ingestion tables inside existing LoanBook01 DB
│   ├── 02_verify_load.sql               # SSMS ingestion validation queries
│   └── 03_create_features_schema.sql    # StockDailyFeatures & DailyMarketMetrics schema
├── src/
│   ├── app.py                           # State-aware Streamlit Executive Dashboard
│   ├── pipeline.py                      # Public-source scraper, ^GSPC fallback & SQL loader
│   └── features.py                      # Regime, breadth, concentration & risk calculations
├── tests/
│   └── test_pipeline.py                 # Offline parser & transaction rollback unit tests
├── .gitignore
├── config.json                          # SQL Server & download runtime configuration
├── README.md                            # Project & stakeholder documentation
├── requirements.txt                     # Core pipeline Python dependencies
├── run_daily.cmd                        # Windows Task Scheduler daily runner
└── VALIDATION.md                        # Verification checklist & audit notes
```

