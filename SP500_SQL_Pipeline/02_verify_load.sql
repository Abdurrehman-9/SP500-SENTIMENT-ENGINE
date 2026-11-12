USE SP500_Engine;
GO
/* 1. Latest run: success = downloads/load checks passed, not an investment endorsement. */
SELECT TOP (10) * FROM dbo.PipelineRun ORDER BY StartedUtc DESC;

/* 2. Failures and warnings on the latest run: an empty result is desirable. */
DECLARE @RunId uniqueidentifier =
    (SELECT TOP (1) RunId FROM dbo.PipelineRun ORDER BY StartedUtc DESC, RunId DESC);
SELECT Dataset, Status, [RowCount], FirstDate, LastDate, Note
FROM dbo.FetchAudit WHERE RunId = @RunId AND Status <> 'ok'
ORDER BY Dataset;

/* 3. Historical coverage. P/E deliberately has fewer rows because it is monthly. */
SELECT SeriesCode, Frequency, COUNT(*) AS [Rows],
       MIN(ObservationDate) AS FirstDate, MAX(ObservationDate) AS LastDate
FROM dbo.SeriesObservation GROUP BY SeriesCode, Frequency;
SELECT InstrumentType, COUNT(DISTINCT Symbol) AS Symbols, COUNT(*) AS [Rows],
       MIN(PriceDate) AS FirstDate, MAX(PriceDate) AS LastDate
FROM dbo.DailyPrice GROUP BY InstrumentType;

/* 4. Current membership and price coverage at the latest available FRED index date.
   Multiple share classes mean there can be more than 500 securities.
   Rows before this snapshot date are price history, not historical membership. */
DECLARE @AsOf date = (SELECT MAX(ObservationDate) FROM dbo.SeriesObservation WHERE SeriesCode='SP500');
SELECT @AsOf AS BenchmarkDate;
SELECT c.Symbol,c.CompanyName,c.SnapshotDate,
       COUNT(p.PriceDate) AS AvailablePricesThroughBenchmark,
       MAX(p.PriceDate) AS LastPriceThroughBenchmark,
       CASE WHEN COUNT(p.PriceDate)>=200 AND MAX(p.PriceDate)=@AsOf
            THEN 'Enough rows; check gaps before SMA200' ELSE 'Insufficient or stale' END AS Coverage
FROM dbo.v_LatestConstituents c
LEFT JOIN dbo.DailyPrice p ON p.Symbol=c.Symbol AND p.PriceDate<=@AsOf
GROUP BY c.Symbol,c.CompanyName,c.SnapshotDate
ORDER BY AvailablePricesThroughBenchmark, c.Symbol;

/* 5. Raw numbers to inspect manually. SPY and RSP must both use adjusted close
   for their eventual return comparison; do not mix SPY total return with FRED price return. */
SELECT TOP (6) * FROM dbo.SeriesObservation WHERE SeriesCode='SP500' ORDER BY ObservationDate DESC;
SELECT TOP (6) * FROM dbo.SeriesObservation WHERE SeriesCode='VIX' ORDER BY ObservationDate DESC;
SELECT TOP (6) * FROM dbo.SeriesObservation WHERE SeriesCode='PE_MONTHLY' ORDER BY ObservationDate DESC;
SELECT TOP (10) * FROM dbo.DailyPrice WHERE Symbol IN ('SPY','RSP') ORDER BY PriceDate DESC, Symbol;

/* Primary keys prevent duplicate symbol/date or series/date records on repeated loads. */
