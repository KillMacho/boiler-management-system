-- =============================================================================
-- 06_CreateAdminUser.sql
-- Создание / обновление пользователя admin со всеми 9 ролями.
-- Идемпотентен: можно запускать многократно.
--
-- Учётная запись:
--   username: admin
--   password: admin123  (bcrypt-хеш генерируется backend'ом и подставляется ниже)
-- =============================================================================

USE BoilerManagementDB;
GO

SET NOCOUNT ON;
BEGIN TRANSACTION;
BEGIN TRY

-- bcrypt-хеш строки 'admin123', сгенерирован через passlib (12 раундов).
-- Если меняете пароль — пересгенерируйте хеш в venv:
--   python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('NEW_PASSWORD'))"
DECLARE @bcrypt_hash NVARCHAR(255) = N'$2b$12$2EFSIKCH81ObVH9U8/GoBe2mv.v4h7mHWyXew5Q.seWXi8lREzNhm';
DECLARE @admin_id INT;

-- Если admin уже есть (создан в 05_InsertTestData.sql) — обновим хеш.
-- Если нет — создадим.
IF EXISTS (SELECT 1 FROM users WHERE username = N'admin')
BEGIN
    UPDATE users
       SET password_hash = @bcrypt_hash,
           is_active     = 1
     WHERE username = N'admin';

    SELECT @admin_id = id FROM users WHERE username = N'admin';
END
ELSE
BEGIN
    INSERT INTO users (username, password_hash, is_active)
    VALUES (N'admin', @bcrypt_hash, 1);

    SET @admin_id = SCOPE_IDENTITY();
END

-- Все 9 ролей: вычистим старые связи, выставим полный набор.
DELETE FROM user_roles WHERE user_id = @admin_id;

INSERT INTO user_roles (user_id, role_id)
SELECT @admin_id, id FROM roles;

PRINT N'Пользователь admin создан/обновлён. Все 9 ролей назначены.';
PRINT N'Логин: admin / Пароль: admin123';

END TRY
BEGIN CATCH
    ROLLBACK TRANSACTION;
    THROW;
END CATCH;

COMMIT TRANSACTION;
GO
