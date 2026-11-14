# S&P 500 Sentiment & Quantitative Market Surveillance Engine

An end-to-end quantitative market intelligence pipeline and executive surveillance dashboard that monitors the structural health of the U.S. equity market across **Trend Regime**, **Constituent Breadth**, **Cap-Weight Concentration**, and **Volatility/Valuation Stress**.

Powered by **Microsoft SQL Server**, **Python 3.11+**, and **Streamlit**.

---

## Table of Contents

1. [Executive Summary & Purpose](#executive-summary--purpose)
2. [The Four Analytical Pillars](#the-four-analytical-pillars)
3. [Lean Relational Data Architecture](#lean-relational-data-architecture)
4. [Master Data Dictionary](#master-data-dictionary)
5. [Decoupled 3-Tier Pipeline](#decoupled-3-tier-pipeline)
6. [Dynamic State-Aware Dashboard](#dynamic-state-aware-dashboard)
7. [Local Setup & Execution Guide](#local-setup--execution-guide)
8. [Automated Daily Execution (GitHub Actions)](#automated-daily-execution-github-actions)
9. [Project Directory Structure](#project-directory-structure)

---

## Executive Summary & Purpose

Standard capitalization-weighted index levels often mask underlying systemic fragility. A rising S&P 500 headline price can conceal deteriorating stock participation, extreme mega-cap leadership concentration, or unhedged valuation multiples.

The **S&P 500 Sentiment Engine** replaces superficial sentiment heuristics with a **mathematically grounded, explainable surveillance system** that tracks 1,000+ trading sessions across all 503 constituent equities and core macro benchmarks.

### The Four Core Deliverables

| Deliverable | Key Question Answered | Primary Mathematical Indicator | Benchmark / Bands |
|---|---|---|---|
| **1. Market Regime** | Is the market fundamentally expanding or contracting? | S&P 500 Close vs. 200-Day SMA ($\text{SMA}_{200}$) & 20-Day Slope | **Bull** (Price > Trend & Slope $\ge 0$), **Bear** (Price < Trend & Slope $\le 0$), **Neutral** |
| **2. Market Health** | Is the rally broad-based or hollow? | Breadth Health % ($\% \text{ of stocks } > \text{SMA}_{200}$) | **Strong** (>70%), **Healthy** (50%–70%), **Cautious** (30%–50%), **Fragile** (<30%) |
| **3. Market Concentration** | Are mega-caps driving returns at the expense of average stocks? | 30-Day Leadership Gap ($\text{SPY}_{\text{30d}} - \text{RSP}_{\text{30d}}$) | **Mega-Cap Led** (> +1.5 pp), **Balanced** (-1.5 to +1.5 pp), **Broad Market Led** (< -1.5 pp) |
| **4. Market Stress** | Are options markets pricing elevated fear or stretched valuations? | Cboe VIX, 20-Day Realized Volatility, and 60-Month Trailing P/E Multiple | **Calm** (VIX < 20), **Elevated** (20–30), **Panic** (> 30); P/E Premium vs. 5-Yr Mean |

---

## The Four Analytical Pillars

### 1. Market Regime Classification
We evaluate the closing index level relative to its 200-session Simple Moving Average ($\text{SMA}_{200}$) and calculate the 20-trading-day trend velocity ($\Delta \text{SMA}_{200}$):

$$\text{SMA}_{200}(t) = \frac{1}{200} \sum_{i=0}^{199} \text{Close}(t-i)$$

$$\Delta \text{SMA}_{200}(t) = \text{SMA}_{200}(t) - \text{SMA}_{200}(t-20)$$

- **Bull:** $\text{Close}(t) > \text{SMA}_{200}(t) \quad \text{AND} \quad \Delta \text{SMA}_{200}(t) \ge 0$
- **Bear:** $\text{Close}(t) < \text{SMA}_{200}(t) \quad \text{AND} \quad \Delta \text{SMA}_{200}(t) \le 0$
- **Neutral:** Conflicting price position and trend slope (e.g., pullback in a rising trend, or oversold bounce below a declining trend).

### 2. Constituent Breadth & Market Health
To verify participation, we calculate individual 200-day trend lines for all 503 underlying index constituents. A security is **eligible** only if it possesses $\ge 200$ trading sessions of price history (eliminating IPO warmup bias). 

A minimum **95% constituent coverage gate** is enforced before certifying market breadth:

$$\text{BreadthHealthPct}(t) = \frac{\sum_{k=1}^{N_{\text{eligible}}} \mathbb{I}\left(\text{StockClose}_{k}(t) > \text{StockSMA200}_{k}(t)\right)}{N_{\text{eligible}}(t)} \times 100$$

### 3. Capitalization-Weighted Concentration Proxy
We compare the 30-trading-day total return of the market-cap-weighted fund (**SPY**) against the equal-weighted fund (**RSP**). Both series utilize dividend- and split-adjusted closing prices:

$$\text{Return}_{30\text{d}}(t) = \frac{\text{AdjClose}(t) - \text{AdjClose}(t-30)}{\text{AdjClose}(t-30)}$$

$$\text{LeadershipGap}(t) = \left(\text{Return}_{\text{SPY}, 30\text{d}}(t) - \text{Return}_{\text{RSP}, 30\text{d}}(t)\right) \times 100$$

A persistently positive gap indicates market vulnerability: the headline index is advancing solely because the largest tech conglomerates are rising, while the average company is lagging.

### 4. Volatility Stress & Valuation Baseline
- **Expected Volatility:** Cboe Volatility Index (**VIX**), reflecting the market's 30-day forward implied volatility.
- **Realized Volatility:** 20-session annualized sample standard deviation of daily log returns:

$$\sigma_{\text{realized}}(t) = \sqrt{\frac{252}{19} \sum_{i=0}^{19} \left(r_{t-i} - \bar{r}\right)^2} \times 100 \quad \text{where} \quad r_t = \ln\left(\frac{\text{Close}_t}{\text{Close}_{t-1}}\right)$$

- **Valuation Spread:** Monthly Shiller P/E multiple compared against its 60-month historical arithmetic mean:

$$\text{PE\_PremiumPct}(t) = \frac{\text{Current\_PE}(t) - \overline{\text{PE}}_{60\text{m}}(t)}{\overline{\text{PE}}_{60\text{m}}(t)} \times 100$$

---

## Lean Relational Data Architecture

To ensure auditability, zero technical bloat, and presentation-ready defense, the database has been streamlined into **5 clean tables containing exactly 37 columns**:

```
                                  PUBLIC DATA PROVIDERS
                  FRED (SP500) • Cboe (VIX) • Multpl (PE) • Yahoo (SPY, RSP, 503 Stocks)
                                            │
                                            ▼
                  ┌───────────────────────────────────────────────────┐
                  │          In-Memory Streaming Ingestion            │
                  │                   (pipeline.py)                   │
                  └─────────────────────────┬─────────────────────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               ▼                            ▼                            ▼
┌─────────────────────────────┐┌─────────────────────────────┐┌─────────────────────────────┐
│      dbo.Constituents       ││   dbo.SeriesObservation     ││       dbo.DailyPrice        │
├─────────────────────────────┤├─────────────────────────────┤├─────────────────────────────┤
│ • Symbol (PK)               ││ • SeriesCode (PK)           ││ • Symbol (PK)               │
│ • CompanyName               ││ • ObservationDate (PK)      ││ • PriceDate (PK)            │
│ • Sector                    ││ • Value                     ││ • CloseSplitAdjusted        │
│                             ││                             ││ • CloseTotalReturnAdjusted  │
│ (Active S&P 500 Roster)     ││ (Macro Benchmark Series)    ││ (Stock & ETF Adjusted Bars) │
└──────────────┬──────────────┘└──────────────┬──────────────┘└──────────────┬──────────────┘
               │                              │                              │
               └───────────────────────┐      │      ┌───────────────────────┘
                                       │      │      │
                                       ▼      ▼      ▼
                  ┌───────────────────────────────────────────────────┐
                  │             Python Feature Engineering            │
                  │                   (features.py)                   │
                  └─────────────────────────┬─────────────────────────┘
                                            │
                       ┌────────────────────┴────────────────────┐
                       ▼                                         ▼
┌───────────────────────────────────────────────┐┌───────────────────────────────────────────────┐
│            dbo.StockDailyFeatures             ││            dbo.DailyMarketMetrics            │
├───────────────────────────────────────────────┤├───────────────────────────────────────────────┤
│ • Symbol (PK)                                 ││ • TradingDate (PK)                            │
│ • PriceDate (PK)                              ││ • IndexClose, IndexSMA200, IndexSMA200_20d_ago│
│ • CloseSplitAdjusted                          ││ • Regime (Bull, Neutral, Bear)                │
│ • SMA200 (1-Year Average Trend Line)          ││ • BreadthAboveCount, BreadthEligibleCount     │
│ • AboveSMA200 (1 = Healthy, 0 = Below)        ││ • BreadthCoveragePct, BreadthHealthPct        │
│ • IsEligibleBreadth (1 = Has 200 Days History)││ • HealthBand (Strong, Healthy, Cautious, etc.)│
│                                               ││ • SPY_30d_Return, RSP_30d_Return              │
│ (Individual Stock 200-SMA Calculations)       ││ • LeadershipGap_PctPoints                     │
│                                               ││ • VIX_Close, VIX_Date                         │
│                                               ││ • RealizedVol_20d_Annualized                  │
│                                               ││ • Current_PE, Historical_PE_60m_Mean          │
│                                               ││ • PE_vs_Historical_Mean_Pct                   │
│                                               ││ (Primary Executive Surveillance Deliverables) │
└───────────────────────────────────────────────┘└───────────────────────────────────────────────┘
```

### Table Summary

| Table | Rows | Columns | Purpose |
|---|:---:|:---:|---|
| **`dbo.Constituents`** | 503 | **3** | Active S&P 500 corporate membership, legal names, and GICS sectors. |
| **`dbo.SeriesObservation`** | 2,206 | **3** | Macro benchmark time-series (S&P 500 index level, VIX, monthly P/E). |
| **`dbo.DailyPrice`** | 514,055 | **4** | Historical split- and dividend-adjusted closing prices for 505 assets. |
| **`dbo.StockDailyFeatures`** | 511,997 | **6** | Individual stock 200-session trend lines, uptrend flags, and eligibility checks. |
| **`dbo.DailyMarketMetrics`** | 1,029 | **21** | Primary surveillance metrics spanning the 4 analytical pillars. |
| **TOTAL** | **1,029,790** | **37** | **100% focused on quantitative analytics—zero IT plumbing bloat.** |

---

## Master Data Dictionary

A complete, non-technical Data Dictionary is maintained directly in the repository:

- **Formatted Excel Workbook:** **[SP500_Data_Dictionary_Plain_English.xlsx](SP500_Data_Dictionary_Plain_English.xlsx)**  
  Includes dark navy executive headers, frozen top panes, auto-filters, zebra row striping, and plain English definitions for every column.
- **Universal CSV Version:** **[SP500_Data_Dictionary_Stakeholder_Complete.csv](SP500_Data_Dictionary_Stakeholder_Complete.csv)**  
  Saved in UTF-8 BOM encoding for seamless integration into business intelligence tools.

---

## Decoupled 3-Tier Pipeline

1. **Ingestion Layer (`pipeline.py`):**
   - Connects to public APIs (FRED, Cboe, Multpl, Wikipedia, Yahoo Finance).
   - In-memory data streaming avoids writing intermediate files to disk.
   - Includes automatic Federal Reserve holiday fallback to Yahoo Finance `^GSPC` (preserving official FRED historical records).
   - Idempotent and transactional: runs can be safely repeated without generating duplicates.
2. **Feature Engineering Layer (`features.py`):**
   - Efficient in-memory vectorized calculations across 500,000+ price bars.
   - Computes rolling moving averages, constituent breadths, leadership gaps, and volatility spreads.
   - Transactionally updates `dbo.StockDailyFeatures` and `dbo.DailyMarketMetrics`.
3. **Visualization Layer (`app.py`):**
   - Built on Streamlit and Plotly.
   - Fully decoupled from ingestion; queries pre-computed SQL features for sub-second rendering.

---

## Dynamic State-Aware Dashboard

For any selected trading session, [app.py](SP500_SQL_Pipeline/app.py) evaluates backend metrics through state-aware conditional engines to generate context-specific executive commentary:

- **Executive Summary Bar:** High-impact status cards with live-bound color badges (`BULL`, `HEALTHY`, `BALANCED`, `CALM`, `PREMIUM`).
- **Tab 1 — Market Regime:** Interactive S&P 500 price chart overlaid with the 200-day moving average and 20-day trend velocity indicator.
- **Tab 2 — Market Health:** Historical breadth percentage chart color-banded into Strong (>70%), Healthy (50%–70%), Cautious (30%–50%), and Fragile (<30%) zones.
- **Tab 3 — Concentration:** SPY vs. RSP 30-day cumulative return divergence chart exposing mega-cap vs. broad-market leadership.
- **Tab 4 — Stress & Valuation:** Dual-axis visualization comparing implied volatility (VIX), realized volatility (20d), and historical 5-year P/E multiples.
- **Tab 5 — Stock Breadth Explorer:** Interactive search table covering all 503 individual companies with sector filters, prices, and 200-day trend statuses.
- **Tab 6 — Architecture & Methodology:** Self-documenting architectural diagrams and mathematical formulations for stakeholder review.

---

## Local Setup & Execution Guide

### Prerequisites
- **Operating System:** Windows 10/11 or Windows Server
- **Python:** 64-bit Python 3.11 or newer
- **Database:** Microsoft SQL Server (Local, Express, or Enterprise)
- **ODBC Driver:** Microsoft ODBC Driver 17 or 18 for SQL Server (x64)

### 1. Provision SQL Server Schema
Open **SQL Server Management Studio (SSMS)**, connect to your server, and execute:
1. `SP500_SQL_Pipeline/01_create_tables_loanbook.sql` (Creates `Constituents`, `SeriesObservation`, `DailyPrice`)
2. `SP500_SQL_Pipeline/03_create_features_schema.sql` (Creates `StockDailyFeatures`, `DailyMarketMetrics`)

### 2. Configure Database Connection
Edit `SP500_SQL_Pipeline/config.json`:
```json
{
  "sql_server": "localhost\\SQLEXPRESS",
  "sql_database": "LoanBook01",
  "odbc_driver": "ODBC Driver 18 for SQL Server",
  "trust_server_certificate": true,
  "history_years": 3,
  "warmup_calendar_days": 400,
  "pe_history_years": 8
}
```

### 3. Run Pipeline & Launch Dashboard
Open PowerShell:
```powershell
# Navigate to the pipeline directory
cd d:\S&P500\SP500_SQL_Pipeline

# 1. Verify database connection
.\.venv\Scripts\python.exe pipeline.py dbcheck

# 2. Daily data ingestion (or backfill for initial setup)
.\.venv\Scripts\python.exe pipeline.py daily

# 3. Calculate derived indicators & features
.\.venv\Scripts\python.exe features.py

# 4. Verify data integrity & row counts
.\.venv\Scripts\python.exe pipeline.py verify

# 5. Launch the Streamlit Dashboard
.\.venv\Scripts\streamlit.exe run app.py --server.port 8501
```

For automated one-click execution on Windows, run:
```powershell
.\run_daily.cmd
```

---

## Automated Daily Execution (GitHub Actions)

Orchestrated via [.github/workflows/daily_update.yml](.github/workflows/daily_update.yml):
1. **Trigger:** Runs automatically Monday–Friday at **22:00 UTC** (after US equity close) and supports manual on-demand triggers.
2. **Environment:** Executes on `windows-latest` with Python 3.11 and Microsoft ODBC Driver 18.
3. **Execution:** Ingests market data, recalculates features, audits data integrity, and commits versioned metric snapshots.

---

## Project Directory Structure

```text
SP500-SENTIMENT-ENGINE/
├── .github/
│   └── workflows/
│       └── daily_update.yml                     # Scheduled Mon-Fri 22:00 UTC CI/CD pipeline
├── .gitignore                                   # Clean ignore rules (excludes venv, raw dumps, logs)
├── README.md                                    # Master project documentation & presentation guide
├── SP500_Data_Dictionary_Plain_English.xlsx     # Executive Excel Data Dictionary (37 clean columns)
├── SP500_Data_Dictionary_Stakeholder_Complete.csv # Universal CSV Data Dictionary (37 clean columns)
│
└── SP500_SQL_Pipeline/
    ├── 01_create_tables_loanbook.sql            # Core SQL schema (Constituents, Series, Prices)
    ├── 02_verify_load.sql                       # 5-table verification script & data health audit
    ├── 03_create_features_schema.sql            # Analytical feature tables (Features, Metrics)
    ├── app.py                                   # Streamlit Executive Surveillance Application
    ├── config.json                              # Database target & ingestion configuration
    ├── features.py                              # Mathematical feature engineering engine
    ├── pipeline.py                              # In-memory market data ingestion worker
    ├── requirements.txt                         # Python package dependencies
    └── run_daily.cmd                            # Windows one-click automated runner
```

---

## License & Attribution

Designed and engineered for explainable quantitative market surveillance. Data provided by public institutional sources: St. Louis Federal Reserve (**FRED**), Chicago Board Options Exchange (**Cboe**), **Multpl**, and **Yahoo Finance**.
