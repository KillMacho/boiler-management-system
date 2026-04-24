-- =============================================================================
-- 00_DropDatabase.sql
-- Удаление базы данных BoilerManagementDB (для чистой пересборки).
-- Закрывает все активные соединения, чтобы DROP не завис.
-- =============================================================================

USE master;
GO

IF DB_ID(N'BoilerManagementDB') IS NOT NULL
BEGIN
    PRINT N'База BoilerManagementDB существует — переводим в SINGLE_USER и удаляем.';
    ALTER DATABASE BoilerManagementDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE BoilerManagementDB;
    PRINT N'База BoilerManagementDB удалена.';
END
ELSE
BEGIN
    PRINT N'База BoilerManagementDB не найдена — пропускаем DROP.';
END
GO

-- Удаление SQL-логинов приложения (если существовали от предыдущей установки).
-- Сначала удаляем ассоциированные сессии, потом сам логин.
DECLARE @sql NVARCHAR(MAX) = N'';

SELECT @sql = @sql +
    N'KILL ' + CAST(session_id AS NVARCHAR(10)) + N';' + CHAR(10)
FROM sys.dm_exec_sessions
WHERE login_name IN (N'app_backend', N'app_web', N'app_mobile');

IF LEN(@sql) > 0
BEGIN
    PRINT N'Закрываем активные сессии прикладных логинов.';
    EXEC sp_executesql @sql;
END

IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_backend')
    DROP LOGIN app_backend;
IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_web')
    DROP LOGIN app_web;
IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_mobile')
    DROP LOGIN app_mobile;

PRINT N'Очистка завершена.';
GO
