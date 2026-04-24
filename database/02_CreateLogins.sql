-- =============================================================================
-- 02_CreateLogins.sql
-- Создание SQL-логинов для трёх приложений:
--   * app_backend  — полные права (FastAPI, owner-уровень)
--   * app_web      — read-only на справочники + запись в audit_log (Blazor)
--   * app_mobile   — доступ только к нарядам, чек-листам, фото и актам (MAUI)
--
-- ВАЖНО: пароли заданы для учебного стенда. В проде менять через SSMS/Azure KV.
-- =============================================================================

USE master;
GO

-- ---- app_backend -----------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_backend')
    CREATE LOGIN app_backend
        WITH PASSWORD = N'Backend_P@ssw0rd_2026',
             DEFAULT_DATABASE = BoilerManagementDB,
             CHECK_EXPIRATION = OFF,
             CHECK_POLICY = OFF;
GO

-- ---- app_web ---------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_web')
    CREATE LOGIN app_web
        WITH PASSWORD = N'Web_P@ssw0rd_2026',
             DEFAULT_DATABASE = BoilerManagementDB,
             CHECK_EXPIRATION = OFF,
             CHECK_POLICY = OFF;
GO

-- ---- app_mobile ------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = N'app_mobile')
    CREATE LOGIN app_mobile
        WITH PASSWORD = N'Mobile_P@ssw0rd_2026',
             DEFAULT_DATABASE = BoilerManagementDB,
             CHECK_EXPIRATION = OFF,
             CHECK_POLICY = OFF;
GO

USE BoilerManagementDB;
GO

-- ---- Пользователи внутри БД ------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'app_backend')
    CREATE USER app_backend FOR LOGIN app_backend;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'app_web')
    CREATE USER app_web FOR LOGIN app_web;
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = N'app_mobile')
    CREATE USER app_mobile FOR LOGIN app_mobile;
GO

-- ---- Права app_backend: db_owner ------------------------------------------
-- FastAPI управляет схемой через миграции, ему нужен полный доступ.
ALTER ROLE db_owner ADD MEMBER app_backend;
GO

-- ---- Права app_web: read-all + write в audit_log --------------------------
-- Blazor Server показывает справочники и логирует действия пользователей.
ALTER ROLE db_datareader ADD MEMBER app_web;
-- Прямую запись audit_log разрешаем через отдельный GRANT после создания таблиц
-- (GRANT выполняется в конце 03_CreateSchema.sql, потому что таблицы ещё не созданы).
GO

-- ---- Права app_mobile: только наряды, чек-листы, фото, акты, заявки -------
-- Выполняется в конце 03_CreateSchema.sql после создания таблиц.
GO

PRINT N'Логины app_backend, app_web, app_mobile созданы.';
PRINT N'Конкретные GRANT на таблицы выполняются в 03_CreateSchema.sql.';
GO
