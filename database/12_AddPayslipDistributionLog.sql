-- Day 16: payslip distribution audit log
USE BoilerManagementDB;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.tables WHERE name = 'payslip_distribution_log'
)
BEGIN
    CREATE TABLE payslip_distribution_log (
        id              INT           NOT NULL IDENTITY(1,1) PRIMARY KEY,
        employee_id     INT           NOT NULL REFERENCES employees(id),
        period_code     NVARCHAR(7)   NOT NULL,   -- YYYY-MM
        email           NVARCHAR(255) NOT NULL,
        status          NVARCHAR(20)  NOT NULL     -- 'sent' | 'failed'
            CONSTRAINT CHK_psl_status CHECK (status IN (N'sent', N'failed')),
        error_message   NVARCHAR(500) NULL,
        sent_at         DATETIME      NOT NULL DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_psl_employee_period
        ON payslip_distribution_log (employee_id, period_code);

    CREATE INDEX IX_psl_sent_at
        ON payslip_distribution_log (sent_at DESC);

    PRINT 'Created table payslip_distribution_log';
END
ELSE
    PRINT 'Table payslip_distribution_log already exists — skipped';
GO
