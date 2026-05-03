-- Day 7: regulatory_reports table for tracking generated and submitted XML reports.
-- Stores generation metadata, EDO submission results, and document flow status.

USE BoilerManagementDB;
GO

IF OBJECT_ID('regulatory_reports', 'U') IS NULL
BEGIN
    CREATE TABLE regulatory_reports (
        id              INT             NOT NULL IDENTITY(1,1) PRIMARY KEY,
        report_type     NVARCHAR(20)    NOT NULL,       -- '6-NDFL', 'RSV', '4-FSS', 'SZV-STAZH'
        period          NVARCHAR(20)    NOT NULL,       -- '2026-Q1', '2026', '2026-04'
        inn             NVARCHAR(12)    NOT NULL,       -- Organization INN
        generated_at    DATETIME        NOT NULL DEFAULT SYSUTCDATETIME(),
        file_path       NVARCHAR(1000)  NOT NULL,
        file_size       INT             NOT NULL DEFAULT 0,
        submission_id   NVARCHAR(50)    NULL,           -- SUB-YYYY-MM-DD-NNNNN from EDO
        receipt_number  NVARCHAR(100)   NULL,           -- КВТ-... from EDO
        edo_status      NVARCHAR(50)    NULL            -- accepted/processing/confirmed/rejected
            CONSTRAINT CK_rr_edo_status CHECK (
                edo_status IS NULL OR edo_status IN (
                    N'accepted', N'processing',
                    N'delivered_to_authority', N'confirmed', N'rejected'
                )
            ),
        last_status_check DATETIME      NULL,

        CONSTRAINT CK_rr_report_type CHECK (
            report_type IN (N'6-NDFL', N'RSV', N'4-FSS', N'SZV-STAZH')
        )
    );
END
GO

-- Index for common queries by period and report type
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('regulatory_reports')
      AND name = 'IX_rr_period_type'
)
    CREATE INDEX IX_rr_period_type ON regulatory_reports (period, report_type);
GO

PRINT 'Migration 09: regulatory_reports table created successfully.';
