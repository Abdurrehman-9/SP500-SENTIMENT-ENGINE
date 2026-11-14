/* 03_create_features_schema.sql
   Target database: LoanBook01.
   Idempotent and non-destructive.
   Defines the derived analytical and machine-learning feature tables:
     1. dbo.DailyMarketMetrics (Executive regime, breadth, concentration, and stress metrics)
     2. dbo.StockDailyFeatures (Individual stock 200-day moving averages and breadth filters)
*/
USE LoanBook01;
GO

IF OBJECT_ID(N'dbo.DailyMarketMetrics', N'U') IS NULL
CREATE TABLE dbo.DailyMarketMetrics (
    TradingDate date NOT NULL PRIMARY KEY,
    
    -- Pillar 1: Market Regime
    IndexClose decimal(20,8) NULL,
    IndexSMA200 decimal(20,8) NULL,
    IndexSMA200_20d_ago decimal(20,8) NULL,
    Regime varchar(16) NOT NULL, -- 'Bull', 'Bear', 'Neutral', 'Unavailable'
    
    -- Pillar 2: Market Health / Breadth
    BreadthAboveCount int NULL,
    BreadthEligibleCount int NULL,
    BreadthRosterCount int NULL,
    BreadthExcludedCount int NULL,
    BreadthCoveragePct decimal(10,4) NULL,
    BreadthHealthPct decimal(10,4) NULL,
    HealthBand varchar(16) NULL, -- 'Strong', 'Healthy', 'Cautious', 'Fragile'
    
    -- Pillar 3: Concentration Proxy (SPY vs RSP 30 trading sessions)
    SPY_30d_Return decimal(10,6) NULL,
    RSP_30d_Return decimal(10,6) NULL,
    LeadershipGap_PctPoints decimal(10,4) NULL,
    
    -- Pillar 4: Stress and Valuation
    VIX_Close decimal(10,4) NULL,
    VIX_Date date NULL,
    RealizedVol_20d_Annualized decimal(10,4) NULL,
    Current_PE decimal(10,4) NULL,
    Historical_PE_60m_Mean decimal(10,4) NULL,
    PE_vs_Historical_Mean_Pct decimal(10,4) NULL
);
GO

IF OBJECT_ID(N'dbo.StockDailyFeatures', N'U') IS NULL
CREATE TABLE dbo.StockDailyFeatures (
    Symbol varchar(24) NOT NULL,
    PriceDate date NOT NULL,
    CloseSplitAdjusted decimal(20,8) NOT NULL,
    SMA200 decimal(20,8) NULL,
    AboveSMA200 bit NULL,
    IsEligibleBreadth bit NOT NULL DEFAULT 0,
    CONSTRAINT PK_StockDailyFeatures PRIMARY KEY (Symbol, PriceDate)
);
GO

PRINT 'DailyMarketMetrics and StockDailyFeatures tables created successfully in LoanBook01.';
