/* Target existing database LoanBook01 where PKUBL\abdur.rehman3 is db_owner.
   Safe to run again. Existing tables (LoanmartData, clean_loan_book) are NEVER touched.
*/
USE LoanBook01;
GO

IF OBJECT_ID(N'dbo.PipelineRun', N'U') IS NULL
CREATE TABLE dbo.PipelineRun (
    RunId uniqueidentifier NOT NULL PRIMARY KEY,
    StartedUtc datetime2(0) NOT NULL,
    FinishedUtc datetime2(0) NULL,
    Mode varchar(16) NOT NULL,
    RequestedStart date NOT NULL,
    RequestedEnd date NOT NULL,
    Status varchar(16) NOT NULL,
    Summary nvarchar(2000) NULL
);
GO

IF OBJECT_ID(N'dbo.FetchAudit', N'U') IS NULL
CREATE TABLE dbo.FetchAudit (
    RunId uniqueidentifier NOT NULL REFERENCES dbo.PipelineRun(RunId),
    Dataset nvarchar(80) NOT NULL,
    SourceUrl nvarchar(2048) NOT NULL,
    RetrievedUtc datetime2(0) NOT NULL,
    Status varchar(16) NOT NULL,
    [RowCount] int NOT NULL,
    FirstDate date NULL,
    LastDate date NULL,
    RawFile nvarchar(1024) NULL,
    Sha256 char(64) NULL,
    Note nvarchar(2000) NULL,
    CONSTRAINT PK_FetchAudit PRIMARY KEY (RunId, Dataset)
);
GO

/* Every run records the roster actually observed THEN. This is not past membership. */
IF OBJECT_ID(N'dbo.ConstituentSnapshot', N'U') IS NULL
CREATE TABLE dbo.ConstituentSnapshot (
    RunId uniqueidentifier NOT NULL REFERENCES dbo.PipelineRun(RunId),
    SnapshotDate date NOT NULL,
    Symbol varchar(24) NOT NULL,
    ProviderSymbol varchar(24) NOT NULL,
    CompanyName nvarchar(256) NOT NULL,
    Sector nvarchar(128) NULL,
    Cik varchar(10) NULL,
    SourceUrl nvarchar(2048) NOT NULL,
    CONSTRAINT PK_ConstituentSnapshot PRIMARY KEY (RunId, Symbol)
);
GO

IF OBJECT_ID(N'dbo.SeriesObservation', N'U') IS NULL
CREATE TABLE dbo.SeriesObservation (
    SeriesCode varchar(24) NOT NULL,
    ObservationDate date NOT NULL,
    Value decimal(20,8) NOT NULL CHECK (Value > 0),
    Frequency varchar(8) NOT NULL CHECK (Frequency IN ('daily','monthly')),
    Source varchar(32) NOT NULL,
    LastLoadRunId uniqueidentifier NOT NULL REFERENCES dbo.PipelineRun(RunId),
    CONSTRAINT PK_SeriesObservation PRIMARY KEY (SeriesCode, ObservationDate)
);
GO

IF OBJECT_ID(N'dbo.DailyPrice', N'U') IS NULL
CREATE TABLE dbo.DailyPrice (
    Symbol varchar(24) NOT NULL,
    PriceDate date NOT NULL,
    /* Yahoo close is split-adjusted. AdjClose additionally adjusts for distributions. */
    CloseSplitAdjusted decimal(20,8) NOT NULL CHECK (CloseSplitAdjusted > 0),
    CloseTotalReturnAdjusted decimal(20,8) NULL CHECK (CloseTotalReturnAdjusted > 0),
    Volume bigint NULL CHECK (Volume >= 0),
    InstrumentType varchar(8) NOT NULL CHECK (InstrumentType IN ('stock','etf')),
    Source varchar(32) NOT NULL,
    LastLoadRunId uniqueidentifier NOT NULL REFERENCES dbo.PipelineRun(RunId),
    CONSTRAINT PK_DailyPrice PRIMARY KEY (Symbol, PriceDate)
);
GO

CREATE OR ALTER VIEW dbo.v_LatestConstituents AS
SELECT c.* FROM dbo.ConstituentSnapshot AS c
WHERE c.RunId = (
    SELECT TOP (1) r.RunId FROM dbo.PipelineRun AS r
    WHERE EXISTS (SELECT 1 FROM dbo.ConstituentSnapshot s WHERE s.RunId = r.RunId)
    ORDER BY r.StartedUtc DESC, r.RunId DESC
);
GO

PRINT 'S&P 500 Engine tables and view created successfully in LoanBook01.';
