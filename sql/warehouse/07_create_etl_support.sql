USE Olist_DW;
GO
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;
GO

IF OBJECT_ID('dbo.ETLRun','U') IS NULL
CREATE TABLE dbo.ETLRun (
    RunId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    StartedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
    FinishedAt datetime2(0) NULL,
    Status varchar(12) NOT NULL CHECK (Status IN ('RUNNING','SUCCEEDED','FAILED')),
    ErrorMessage nvarchar(4000) NULL
);
IF OBJECT_ID('dbo.ETLStepLog','U') IS NULL
CREATE TABLE dbo.ETLStepLog (
    StepId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    RunId bigint NOT NULL REFERENCES dbo.ETLRun(RunId),
    StepName sysname NOT NULL,
    StartedAt datetime2(0) NOT NULL,
    FinishedAt datetime2(0) NOT NULL,
    Status varchar(12) NOT NULL CHECK (Status IN ('SUCCEEDED','FAILED')),
    TargetRows bigint NULL,
    ErrorMessage nvarchar(4000) NULL
);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ETLStepLog')
               AND name='IX_ETLStepLog_RunId')
CREATE INDEX IX_ETLStepLog_RunId ON dbo.ETLStepLog(RunId,StepId);
IF OBJECT_ID('dbo.ETLReconciliation','U') IS NULL
CREATE TABLE dbo.ETLReconciliation (
    ReconciliationId bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,
    RunId bigint NULL REFERENCES dbo.ETLRun(RunId),
    MetricName sysname NOT NULL,
    SourceValue decimal(20,2) NOT NULL,
    TargetValue decimal(20,2) NOT NULL,
    Difference AS (TargetValue-SourceValue) PERSISTED,
    CheckedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME()
);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.ETLReconciliation')
               AND name='IX_ETLReconciliation_RunId')
CREATE INDEX IX_ETLReconciliation_RunId ON dbo.ETLReconciliation(RunId,ReconciliationId);
GO
