# S&P 500 Market Monitoring Pipeline

Core ingestion, feature engineering, and verification scripts for the **S&P 500 Sentiment & Quantitative Surveillance Engine**.

Target Database: **`LoanBook01`** (Microsoft SQL Server)

---

## 1. Key Pipeline Files

| File | Purpose | Execution Command |
|---|---|---|
| `01_create_tables_loanbook.sql` | Provisions core tables (`Constituents`, `SeriesObservation`, `DailyPrice`) in SSMS. | Execute in SSMS |
| `03_create_features_schema.sql` | Provisions derived tables (`StockDailyFeatures`, `DailyMarketMetrics`) in SSMS. | Execute in SSMS |
| `02_verify_load.sql` | Full 5-table verification script and data integrity health check. | Execute in SSMS |
| `pipeline.py` | In-memory data streaming ingestion from public sources (FRED, Cboe, Multpl, Yahoo). | `python pipeline.py daily` |
| `features.py` | Vectorized mathematical indicator calculation (Regime, Breadth, Concentration, Stress). | `python features.py` |
| `app.py` | Streamlit Executive Surveillance Dashboard. | `streamlit run app.py` |
| `config.json` | SQL Server instance target and HTTP connection settings. | Config file |
| `run_daily.cmd` | Windows one-click batch runner that executes ingestion, features, and verification. | Double-click or run in cmd |

---

## 2. Relational Schema Summary (37 Clean Columns)

1. **`dbo.Constituents` (3 columns):** `Symbol`, `CompanyName`, `Sector`
2. **`dbo.SeriesObservation` (3 columns):** `SeriesCode`, `ObservationDate`, `Value`
3. **`dbo.DailyPrice` (4 columns):** `Symbol`, `PriceDate`, `CloseSplitAdjusted`, `CloseTotalReturnAdjusted`
4. **`dbo.StockDailyFeatures` (6 columns):** `Symbol`, `PriceDate`, `CloseSplitAdjusted`, `SMA200`, `AboveSMA200`, `IsEligibleBreadth`
5. **`dbo.DailyMarketMetrics` (21 columns):** Core surveillance deliverables across Regime, Breadth Health %, Concentration Leadership Gap, and Volatility Stress.

---

## 3. Quick Run Commands

```powershell
# 1. Test database connectivity
.\.venv\Scripts\python.exe pipeline.py dbcheck

# 2. Fetch latest market data
.\.venv\Scripts\python.exe pipeline.py daily

# 3. Compute quantitative indicators
.\.venv\Scripts\python.exe features.py

# 4. Verify SQL Server row counts and table integrity
.\.venv\Scripts\python.exe pipeline.py verify

# 5. Launch dashboard
.\.venv\Scripts\streamlit.exe run app.py --server.port 8501
```
