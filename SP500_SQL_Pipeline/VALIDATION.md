# Delivery validation — 11 November 2026

**Tested:** live public downloads and parsing, plus 14 offline integrity tests.
**Not tested here:** connection to your Microsoft SQL Server, execution of the T-SQL setup,
or downloading every current member's prices. Those checks run on your Windows machine.

| Sample dataset | Result |
|---|---|
| Current constituent table | 503 distinct security tickers |
| FRED S&P 500 | 1,028 observations, latest 10 November 2026 |
| Cboe VIX | 1,057 observations, latest 10 November 2026 |
| Multpl P/E | 119 monthly observations, latest 1 October 2026 |
| AAPL, MSFT, BRK.B | Each returned 1,028 prices through 10 November 2026 |
| SPY, RSP | Each returned 1,028 prices through 10 November 2026, including adjusted closes |

Dates are filtered, not filled. The source calendars can differ; later calculations must
join matching trading dates. Sample stocks and ETFs contained every FRED benchmark date
after their first available price in this sample. The current partial month of P/E is excluded.

The final parsers were also replayed against the saved responses after implementation changes.
`sample_validation.json` retains source URLs, retrieval timestamps, response hashes and row counts.
It is evidence of a sample download, not proof of a complete SQL load. Original response files
from this development sample are not distributed in this package; your runs save their own copies.

Offline tests cover missing values, rejected HTML/error responses, duplicate dates, exclusion
of future observations, monthly/live P/E separation, preservation of share classes, ticker
mapping, price-adjustment types and invalid numbers. Two transaction tests verify rerun
deduplication and rollback using an in-memory SQL harness. That harness is only a test aid;
the delivered application stores data exclusively in Microsoft SQL Server. It does not
replace a real SQL Server integration test.

## Local acceptance

1. SSMS creates the database and five tables successfully.
2. `pipeline.py dbcheck` connects successfully.
3. `pipeline.py backfill` runs; inspect any warnings/failures in `FetchAudit`.
4. Run `02_verify_load.sql`. Confirm individual current-member price coverage, including
   missing sessions and stocks with insufficient 200-session history.
5. Run `pipeline.py daily`. Previously loaded dates remain unique, and latest available
   observations load successfully. Run/audit counts increase intentionally.

This is a working ingestion package, not a claim of perfect historical coverage or
permanent uptime from free websites.
