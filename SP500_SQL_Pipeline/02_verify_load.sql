/* 02_verify_load.sql
   Target database: LoanBook01.
   Inspects the clean relational tables across the entire S&P 500 Sentiment Engine.
*/
USE LoanBook01;
GO

PRINT '==================================================';
PRINT '  S&P 500 SENTIMENT ENGINE: DATA INTEGRITY AUDIT  ';
PRINT '==================================================';

-- 1. S&P 500 Roster
PRINT CHAR(10) + '1. ACTIVE S&P 500 CONSTITUENTS (dbo.Constituents)';
SELECT COUNT(*) AS [Total Constituents], COUNT(DISTINCT Sector) AS [GICS Sectors]
FROM dbo.Constituents;

SELECT TOP (5) Symbol, CompanyName, Sector 
FROM dbo.Constituents 
ORDER BY Symbol;

-- 2. Macro Benchmark Time-Series
PRINT CHAR(10) + '2. BENCHMARK TIME-SERIES (dbo.SeriesObservation)';
SELECT SeriesCode, COUNT(*) AS [Observations],
       MIN(ObservationDate) AS FirstObservation,
       MAX(ObservationDate) AS LatestObservation
FROM dbo.SeriesObservation 
GROUP BY SeriesCode;

-- 3. Stock and ETF Daily Prices
PRINT CHAR(10) + '3. DAILY PRICE HISTORY (dbo.DailyPrice)';
SELECT COUNT(DISTINCT Symbol) AS [Distinct Symbols],
       COUNT(*) AS [Total Price Rows],
       MIN(PriceDate) AS EarliestPriceDate,
       MAX(PriceDate) AS LatestPriceDate
FROM dbo.DailyPrice;

-- 4. Derived Features & Indicators
PRINT CHAR(10) + '4. DERIVED STOCK FEATURES (dbo.StockDailyFeatures)';
SELECT COUNT(DISTINCT Symbol) AS [Stocks Processed],
       COUNT(*) AS [Feature Rows],
       SUM(CAST(AboveSMA200 AS int)) AS [Stocks Above SMA200 (All-Time Sessions)]
FROM dbo.StockDailyFeatures;

-- 5. Daily Market Metrics (Primary KPIs)
PRINT CHAR(10) + '5. PRIMARY MARKET SURVEILLANCE METRICS (dbo.DailyMarketMetrics)';
SELECT COUNT(*) AS [Surveillance Trading Days],
       MIN(TradingDate) AS EarliestDate,
       MAX(TradingDate) AS LatestDate
FROM dbo.DailyMarketMetrics;

SELECT TOP (5) 
    TradingDate, IndexClose, Regime, 
    BreadthHealthPct, HealthBand, 
    LeadershipGap_PctPoints, 
    VIX_Close, Current_PE, PE_vs_Historical_Mean_Pct
FROM dbo.DailyMarketMetrics
ORDER BY TradingDate DESC;
GO
