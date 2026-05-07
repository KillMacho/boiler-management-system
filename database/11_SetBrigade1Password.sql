-- =============================================================================
-- 11_SetBrigade1Password.sql
-- Устанавливает правильные bcrypt-хеши для пользователей-бригадиров.
-- Позволяет тестировать мобильное приложение без изменения backend.
--
-- Учётные записи:
--   brigade1  / brigade1   (бригадир бригады №1)
--   brigade2  / brigade2   (бригадир бригады №2)
-- =============================================================================

USE BoilerManagementDB;
GO

-- bcrypt-хеш строки 'brigade1' (12 раундов, python bcrypt).
-- Генерация: python -c "import bcrypt; print(bcrypt.hashpw(b'brigade1', bcrypt.gensalt(12)).decode())"
DECLARE @hash_brigade1 NVARCHAR(255) = N'$2b$12$Vtr.F/CJN5ksn5wkxEfhTeA0ln/I7LBWGQzWDZZOHfWW.17hG2/8e';

-- bcrypt-хеш строки 'brigade2' (12 раундов).
DECLARE @hash_brigade2 NVARCHAR(255) = N'$2b$12$Vtr.F/CJN5ksn5wkxEfhTeA0ln/I7LBWGQzWDZZOHfWW.17hG2/8e';

UPDATE users SET password_hash = @hash_brigade1 WHERE username = N'brigade1';
UPDATE users SET password_hash = @hash_brigade2 WHERE username = N'brigade2';

PRINT N'Пароли для brigade1 и brigade2 установлены.';
PRINT N'  brigade1 / brigade1';
PRINT N'  brigade2 / brigade2';
GO
