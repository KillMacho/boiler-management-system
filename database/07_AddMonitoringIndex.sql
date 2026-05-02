-- UTF-8 BOM required for sqlcmd Cyrillic support.
-- Day 3: Uniqueness constraints for monitoring deduplication and telemetry idempotency.

USE BoilerManagementDB;
GO

-- Unique filtered index: at most one open Авария request per boiler.
-- Prevents race condition where two simultaneous critical telemetry events
-- would each try to create a new emergency request for the same boiler.
DECLARE @avaria_id INT;
SELECT @avaria_id = id FROM request_types WHERE name = N'Авария';

IF @avaria_id IS NOT NULL
BEGIN
    DECLARE @sql NVARCHAR(MAX);
    SET @sql = N'
        IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N''UX_requests_open_avariya'' AND object_id = OBJECT_ID(N''requests''))
        BEGIN
            EXEC(N''CREATE UNIQUE INDEX UX_requests_open_avariya
                  ON requests(boiler_id)
                  WHERE type_id = ' + CAST(@avaria_id AS NVARCHAR) + N'
                    AND status IN (N''''new'''', N''''assigned'''', N''''in_progress'''')'');
        END';
    EXEC sp_executesql @sql;
    PRINT 'UX_requests_open_avariya created for type_id=' + CAST(@avaria_id AS NVARCHAR);
END
ELSE
    PRINT 'WARNING: request_type Авария not found — UX_requests_open_avariya not created';
GO

-- Telemetry idempotency: duplicate (boiler_id, timestamp) = same reading, ignore.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'UX_telemetry_boiler_timestamp' AND object_id = OBJECT_ID(N'telemetry'))
BEGIN
    CREATE UNIQUE INDEX UX_telemetry_boiler_timestamp
        ON telemetry(boiler_id, [timestamp]);
    PRINT 'UX_telemetry_boiler_timestamp created';
END
ELSE
    PRINT 'UX_telemetry_boiler_timestamp already exists';
GO
