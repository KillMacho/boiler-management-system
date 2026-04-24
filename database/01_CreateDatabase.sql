-- =============================================================================
-- 01_CreateDatabase.sql
-- Создание базы данных BoilerManagementDB с collation для русского языка.
-- Cyrillic_General_CI_AS: регистр игнорируется, диакритика учитывается —
-- стандарт для русскоязычных приложений SQL Server.
-- =============================================================================

USE master;
GO

IF DB_ID(N'BoilerManagementDB') IS NOT NULL
BEGIN
    RAISERROR(N'База BoilerManagementDB уже существует — выполните 00_DropDatabase.sql.', 16, 1);
    RETURN;
END
GO

CREATE DATABASE BoilerManagementDB
COLLATE Cyrillic_General_CI_AS;
GO

-- Модель восстановления SIMPLE для учебного проекта (меньше размер лога).
ALTER DATABASE BoilerManagementDB SET RECOVERY SIMPLE;
-- Автоматическое обновление статистики и авто-закрытие — как в проде.
ALTER DATABASE BoilerManagementDB SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE BoilerManagementDB SET AUTO_CLOSE OFF;
-- READ_COMMITTED_SNAPSHOT снижает блокировки при чтении (для FastAPI-запросов).
ALTER DATABASE BoilerManagementDB SET READ_COMMITTED_SNAPSHOT ON;
GO

PRINT N'База BoilerManagementDB создана с collation Cyrillic_General_CI_AS.';
GO
