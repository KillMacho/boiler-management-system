-- Day 4: extend status CHECK constraints to support new lifecycle statuses.
-- New request statuses: needs_manual_assignment, waiting_materials, work_completed, act_generated
-- New work_order statuses: waiting_materials

USE BoilerManagementDB;
GO

-- ── requests.status ──────────────────────────────────────────────────────────
ALTER TABLE requests DROP CONSTRAINT CK_requests_status;
GO

ALTER TABLE requests ADD CONSTRAINT CK_requests_status CHECK (
    status IN (
        N'new',
        N'needs_manual_assignment',
        N'assigned',
        N'waiting_materials',
        N'in_progress',
        N'work_completed',
        N'act_generated',
        N'completed',
        N'closed',
        N'cancelled'
    )
);
GO

-- ── work_orders.status ───────────────────────────────────────────────────────
ALTER TABLE work_orders DROP CONSTRAINT CK_wo_status;
GO

ALTER TABLE work_orders ADD CONSTRAINT CK_wo_status CHECK (
    status IN (
        N'assigned',
        N'waiting_materials',
        N'in_progress',
        N'completed',
        N'cancelled'
    )
);
GO

PRINT 'Migration 08: status constraints extended successfully.';
