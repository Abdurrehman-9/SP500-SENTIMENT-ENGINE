/* 01_create_tables_loanbook.sql
   Target database: LoanBook01.
   Idempotent and non-destructive.
   Defines the core market data architecture:
     1. dbo.Constituents (S&P 500 roster)
     2. dbo.SeriesObservation (Macro benchmark time-series: SP500, VIX, P/E)
     3. dbo.DailyPrice (Daily adjusted closing prices for 503 stocks and ETFs)
     4. dbo.v_LatestConstituents (Active roster view)
*/
USE LoanBook01;
GO

-- 1. S&P 500 Active Membership
IF OBJECT_ID(N'dbo.Constituents', N'U') IS NULL
CREATE TABLE dbo.Constituents (
    Symbol varchar(24) NOT NULL PRIMARY KEY,
    CompanyName nvarchar(256) NOT NULL,
    Sector nvarchar(128) NULL
);
GO

-- 2. Macro & Benchmark Time-Series Observations
IF OBJECT_ID(N'dbo.SeriesObservation', N'U') IS NULL
CREATE TABLE dbo.SeriesObservation (
    SeriesCode varchar(24) NOT NULL,
    ObservationDate date NOT NULL,
    Value decimal(20,8) NOT NULL CHECK (Value > 0),
    CONSTRAINT PK_SeriesObservation PRIMARY KEY (SeriesCode, ObservationDate)
);
GO

-- 3. Stock & ETF Daily Prices
IF OBJECT_ID(N'dbo.DailyPrice', N'U') IS NULL
CREATE TABLE dbo.DailyPrice (
    Symbol varchar(24) NOT NULL,
    PriceDate date NOT NULL,
    CloseSplitAdjusted decimal(20,8) NOT NULL CHECK (CloseSplitAdjusted > 0),
    CloseTotalReturnAdjusted decimal(20,8) NULL CHECK (CloseTotalReturnAdjusted > 0),
    CONSTRAINT PK_DailyPrice PRIMARY KEY (Symbol, PriceDate)
);
GO

-- 4. Canonical Roster View for downstream consumers
CREATE OR ALTER VIEW dbo.v_LatestConstituents AS
SELECT Symbol, CompanyName, Sector 
FROM dbo.Constituents;
GO

PRINT 'Core S&P 500 tables and view created successfully in LoanBook01.';
