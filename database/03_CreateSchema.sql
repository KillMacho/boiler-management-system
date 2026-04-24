-- =============================================================================
-- 03_CreateSchema.sql
-- Создание всех таблиц БД BoilerManagementDB.
--
-- Группы:
--   1. Справочники (категории, типы, приоритеты, роли, квалификации)
--   2. Объекты учёта (котельные, оборудование, паспорта)
--   3. Персонал (подразделения, должности, сотрудники, бригады)
--   4. Пользователи и аудит
--   5. Контрагенты
--   6. Телеметрия и пороги
--   7. Заявки и наряды
--   8. Планирование ТО
--   9. Склад и закупки
--  10. ML-подсистема
--  11. GRANT-ы для app_web и app_mobile
--
-- Таблицы создаются в порядке зависимостей (родители до детей).
-- =============================================================================

USE BoilerManagementDB;
GO

-- =============================================================================
-- 1. СПРАВОЧНИКИ
-- =============================================================================

CREATE TABLE equipment_categories (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(100) NOT NULL UNIQUE,
    description     NVARCHAR(500) NULL
);
GO

CREATE TABLE request_types (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(100) NOT NULL UNIQUE
);
GO

CREATE TABLE request_priorities (
    id                      INT IDENTITY(1,1) PRIMARY KEY,
    name                    NVARCHAR(50) NOT NULL UNIQUE,
    response_time_minutes   INT NOT NULL CHECK (response_time_minutes > 0)
);
GO

CREATE TABLE maintenance_types (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    name                NVARCHAR(100) NOT NULL UNIQUE,
    periodicity_days    INT NOT NULL CHECK (periodicity_days > 0)
);
GO

CREATE TABLE material_categories (
    id      INT IDENTITY(1,1) PRIMARY KEY,
    name    NVARCHAR(100) NOT NULL UNIQUE
);
GO

CREATE TABLE warehouses (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(150) NOT NULL,
    address     NVARCHAR(500) NULL
);
GO

CREATE TABLE departments (
    id      INT IDENTITY(1,1) PRIMARY KEY,
    name    NVARCHAR(150) NOT NULL UNIQUE
);
GO

CREATE TABLE positions (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(150) NOT NULL UNIQUE,
    base_salary     DECIMAL(12,2) NOT NULL CHECK (base_salary >= 0)
);
GO

CREATE TABLE qualifications (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    name        NVARCHAR(150) NOT NULL UNIQUE,
    description NVARCHAR(500) NULL
);
GO

CREATE TABLE roles (
    id      INT IDENTITY(1,1) PRIMARY KEY,
    name    NVARCHAR(50) NOT NULL UNIQUE
);
GO

-- =============================================================================
-- 2. ОБЪЕКТЫ УЧЁТА
-- =============================================================================

CREATE TABLE boilers (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    name                NVARCHAR(200) NOT NULL,
    address             NVARCHAR(500) NOT NULL,
    latitude            DECIMAL(9,6) NOT NULL,
    longitude           DECIMAL(9,6) NOT NULL,
    commissioning_date  DATE NOT NULL,
    status              NVARCHAR(30) NOT NULL
        CONSTRAINT CK_boilers_status CHECK (status IN (N'active', N'maintenance', N'inactive', N'decommissioned'))
);
GO

CREATE TABLE equipment (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    boiler_id           INT NOT NULL REFERENCES boilers(id),
    category_id         INT NOT NULL REFERENCES equipment_categories(id),
    serial_number       NVARCHAR(100) NOT NULL,
    model               NVARCHAR(200) NOT NULL,
    manufacturer        NVARCHAR(200) NULL,
    installation_date   DATE NOT NULL,
    warranty_until      DATE NULL,
    status              NVARCHAR(30) NOT NULL
        CONSTRAINT CK_equipment_status CHECK (status IN (N'active', N'repair', N'decommissioned')),
    CONSTRAINT UQ_equipment_serial UNIQUE (serial_number)
);
GO

CREATE TABLE equipment_passports (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    equipment_id    INT NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    -- JSON в NVARCHAR(MAX); SQL Server 2016+ умеет JSON_VALUE/JSON_QUERY.
    passport_data   NVARCHAR(MAX) NOT NULL
        CONSTRAINT CK_passport_json CHECK (ISJSON(passport_data) = 1),
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_passport_created DEFAULT SYSUTCDATETIME()
);
GO

-- =============================================================================
-- 3. ПЕРСОНАЛ
-- =============================================================================

CREATE TABLE employees (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    first_name          NVARCHAR(100) NOT NULL,
    last_name           NVARCHAR(100) NOT NULL,
    middle_name         NVARCHAR(100) NULL,
    employee_number     NVARCHAR(20) NOT NULL UNIQUE,
    department_id       INT NOT NULL REFERENCES departments(id),
    position_id         INT NOT NULL REFERENCES positions(id),
    hire_date           DATE NOT NULL,
    status              NVARCHAR(30) NOT NULL
        CONSTRAINT CK_employees_status CHECK (status IN (N'active', N'vacation', N'sick', N'terminated'))
);
GO

CREATE TABLE employee_contacts (
    -- Один контактный email на сотрудника — делаем employee_id PK (1:1).
    employee_id                     INT NOT NULL PRIMARY KEY
        REFERENCES employees(id) ON DELETE CASCADE,
    email                           NVARCHAR(255) NOT NULL,
    email_verified                  BIT NOT NULL CONSTRAINT DF_contacts_verified DEFAULT 0,
    email_notifications_enabled     BIT NOT NULL CONSTRAINT DF_contacts_notif DEFAULT 1,
    last_updated                    DATETIME2 NOT NULL CONSTRAINT DF_contacts_updated DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE employee_qualifications (
    employee_id         INT NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    qualification_id    INT NOT NULL REFERENCES qualifications(id),
    -- grade (разряд) — для рабочих специальностей 2-6, для ИТР может быть NULL.
    grade               TINYINT NULL CHECK (grade BETWEEN 1 AND 10),
    assigned_date       DATE NOT NULL CONSTRAINT DF_empqual_date DEFAULT CAST(SYSUTCDATETIME() AS DATE),
    PRIMARY KEY (employee_id, qualification_id)
);
GO

CREATE TABLE brigades (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    name                NVARCHAR(150) NOT NULL UNIQUE,
    leader_employee_id  INT NULL REFERENCES employees(id),
    status              NVARCHAR(30) NOT NULL
        CONSTRAINT CK_brigades_status CHECK (status IN (N'active', N'inactive'))
);
GO

CREATE TABLE brigade_members (
    brigade_id      INT NOT NULL REFERENCES brigades(id) ON DELETE CASCADE,
    employee_id     INT NOT NULL REFERENCES employees(id),
    joined_date     DATE NOT NULL CONSTRAINT DF_brigmem_date DEFAULT CAST(SYSUTCDATETIME() AS DATE),
    PRIMARY KEY (brigade_id, employee_id)
);
GO

CREATE TABLE work_type_qualifications (
    request_type_id     INT NOT NULL REFERENCES request_types(id) ON DELETE CASCADE,
    qualification_id    INT NOT NULL REFERENCES qualifications(id),
    PRIMARY KEY (request_type_id, qualification_id)
);
GO

CREATE TABLE timesheets (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    employee_id     INT NOT NULL REFERENCES employees(id),
    [date]          DATE NOT NULL,
    hours_worked    DECIMAL(5,2) NOT NULL CHECK (hours_worked >= 0 AND hours_worked <= 24),
    hours_type      NVARCHAR(20) NOT NULL
        CONSTRAINT CK_timesheets_type CHECK (hours_type IN (N'regular', N'overtime', N'vacation', N'sick')),
    CONSTRAINT UQ_timesheets_emp_date_type UNIQUE (employee_id, [date], hours_type)
);
GO

-- =============================================================================
-- 4. ПОЛЬЗОВАТЕЛИ И АУДИТ
-- =============================================================================

CREATE TABLE users (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    username        NVARCHAR(100) NOT NULL UNIQUE,
    password_hash   NVARCHAR(255) NOT NULL,
    -- NULL для сервисных аккаунтов (бот, интеграции).
    employee_id     INT NULL REFERENCES employees(id),
    is_active       BIT NOT NULL CONSTRAINT DF_users_active DEFAULT 1,
    last_login      DATETIME2 NULL,
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_users_created DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE user_roles (
    user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     INT NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
GO

CREATE TABLE audit_log (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    user_id         INT NULL REFERENCES users(id),
    action          NVARCHAR(100) NOT NULL,
    entity_type     NVARCHAR(100) NOT NULL,
    entity_id       NVARCHAR(100) NULL,
    [timestamp]     DATETIME2 NOT NULL CONSTRAINT DF_audit_ts DEFAULT SYSUTCDATETIME(),
    details         NVARCHAR(MAX) NULL
        CONSTRAINT CK_audit_details_json CHECK (details IS NULL OR ISJSON(details) = 1)
);
GO

-- =============================================================================
-- 5. КОНТРАГЕНТЫ
-- =============================================================================

CREATE TABLE customers (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    name            NVARCHAR(300) NOT NULL,
    inn             NVARCHAR(12) NOT NULL UNIQUE,
    contact_phone   NVARCHAR(30) NULL,
    contact_email   NVARCHAR(255) NULL
);
GO

-- =============================================================================
-- 6. ТЕЛЕМЕТРИЯ И ПОРОГИ
-- =============================================================================
-- Примечание: SQL Server Express не поддерживает partitioning (Enterprise-only).
-- Для учебного проекта используем обычную таблицу + составной индекс
-- (boiler_id, timestamp) в 04_CreateIndexes.sql. При переходе на Standard/Enterprise
-- достаточно будет создать partition function / scheme по timestamp.

CREATE TABLE telemetry (
    id                      BIGINT IDENTITY(1,1) PRIMARY KEY,
    boiler_id               INT NOT NULL REFERENCES boilers(id),
    [timestamp]             DATETIME2 NOT NULL,
    temperature_heat        DECIMAL(6,2) NULL,  -- температура прямой воды, °C
    pressure                DECIMAL(6,3) NULL,  -- давление, МПа
    co_level                DECIMAL(8,3) NULL,  -- концентрация CO, ppm
    gas_flow                DECIMAL(10,3) NULL, -- расход газа, м³/ч
    water_level             DECIMAL(6,2) NULL,  -- уровень воды, мм
    temperature_return      DECIMAL(6,2) NULL,  -- температура обратки, °C
    furnace_draft           DECIMAL(8,3) NULL,  -- разрежение в топке, Па
    status                  NVARCHAR(20) NOT NULL
        CONSTRAINT CK_telemetry_status CHECK (status IN (N'normal', N'warning', N'critical'))
);
GO

CREATE TABLE thresholds (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    -- NULL = общие пороги для всех котельных.
    boiler_id       INT NULL REFERENCES boilers(id),
    parameter_name  NVARCHAR(50) NOT NULL,
    min_warning     DECIMAL(10,3) NULL,
    max_warning     DECIMAL(10,3) NULL,
    min_critical    DECIMAL(10,3) NULL,
    max_critical    DECIMAL(10,3) NULL
);
GO

-- =============================================================================
-- 7. ЗАЯВКИ И НАРЯДЫ
-- =============================================================================

CREATE TABLE requests (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    number          NVARCHAR(30) NOT NULL UNIQUE,
    boiler_id       INT NOT NULL REFERENCES boilers(id),
    type_id         INT NOT NULL REFERENCES request_types(id),
    priority_id     INT NOT NULL REFERENCES request_priorities(id),
    description     NVARCHAR(2000) NULL,
    source          NVARCHAR(20) NOT NULL
        CONSTRAINT CK_requests_source CHECK (source IN
            (N'phone', N'email', N'web', N'mobile', N'monitoring', N'ml_prediction')),
    status          NVARCHAR(30) NOT NULL
        CONSTRAINT CK_requests_status CHECK (status IN
            (N'new', N'assigned', N'in_progress', N'completed', N'closed', N'cancelled')),
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_requests_created DEFAULT SYSUTCDATETIME(),
    created_by      INT NULL REFERENCES users(id),
    closed_at       DATETIME2 NULL
);
GO

CREATE TABLE work_orders (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    request_id      INT NOT NULL REFERENCES requests(id),
    brigade_id      INT NOT NULL REFERENCES brigades(id),
    assigned_at     DATETIME2 NOT NULL CONSTRAINT DF_wo_assigned DEFAULT SYSUTCDATETIME(),
    started_at      DATETIME2 NULL,
    completed_at    DATETIME2 NULL,
    status          NVARCHAR(30) NOT NULL
        CONSTRAINT CK_wo_status CHECK (status IN
            (N'assigned', N'in_progress', N'completed', N'cancelled'))
);
GO

CREATE TABLE work_order_checklist_items (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    work_order_id   INT NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    description     NVARCHAR(1000) NOT NULL,
    is_completed    BIT NOT NULL CONSTRAINT DF_checklist_completed DEFAULT 0,
    completed_at    DATETIME2 NULL,
    sort_order      INT NOT NULL CONSTRAINT DF_checklist_sort DEFAULT 0
);
GO

CREATE TABLE work_order_photos (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    work_order_id   INT NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    file_path       NVARCHAR(1000) NOT NULL,
    uploaded_at     DATETIME2 NOT NULL CONSTRAINT DF_photos_uploaded DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE acts (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    work_order_id   INT NOT NULL REFERENCES work_orders(id),
    number          NVARCHAR(30) NOT NULL UNIQUE,
    total_amount    DECIMAL(14,2) NOT NULL CHECK (total_amount >= 0),
    generated_at    DATETIME2 NOT NULL CONSTRAINT DF_acts_generated DEFAULT SYSUTCDATETIME(),
    pdf_path        NVARCHAR(1000) NULL,
    CONSTRAINT UQ_acts_wo UNIQUE (work_order_id)  -- один акт на наряд
);
GO

-- =============================================================================
-- 8. ПЛАНИРОВАНИЕ ТО
-- =============================================================================

CREATE TABLE maintenance_regulations (
    id                      INT IDENTITY(1,1) PRIMARY KEY,
    equipment_id            INT NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    maintenance_type_id     INT NOT NULL REFERENCES maintenance_types(id),
    next_due_date           DATE NOT NULL,
    last_performed_at       DATETIME2 NULL,
    CONSTRAINT UQ_regulations_eq_type UNIQUE (equipment_id, maintenance_type_id)
);
GO

CREATE TABLE maintenance_schedules (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_ms_created DEFAULT SYSUTCDATETIME(),
    status          NVARCHAR(30) NOT NULL
        CONSTRAINT CK_ms_status CHECK (status IN (N'draft', N'approved', N'active', N'closed')),
    CONSTRAINT CK_ms_period CHECK (period_end >= period_start)
);
GO

CREATE TABLE maintenance_plan_items (
    id                      INT IDENTITY(1,1) PRIMARY KEY,
    schedule_id             INT NOT NULL REFERENCES maintenance_schedules(id) ON DELETE CASCADE,
    equipment_id            INT NOT NULL REFERENCES equipment(id),
    maintenance_type_id     INT NOT NULL REFERENCES maintenance_types(id),
    planned_date            DATE NOT NULL,
    assigned_brigade_id     INT NULL REFERENCES brigades(id),
    status                  NVARCHAR(30) NOT NULL
        CONSTRAINT CK_mpi_status CHECK (status IN
            (N'planned', N'in_progress', N'completed', N'cancelled', N'postponed'))
);
GO

-- =============================================================================
-- 9. СКЛАД И ЗАКУПКИ
-- =============================================================================

CREATE TABLE materials (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    category_id     INT NOT NULL REFERENCES material_categories(id),
    name            NVARCHAR(300) NOT NULL,
    unit            NVARCHAR(20) NOT NULL,
    barcode         NVARCHAR(50) NULL UNIQUE,
    min_stock       DECIMAL(14,3) NOT NULL CONSTRAINT DF_materials_min DEFAULT 0 CHECK (min_stock >= 0),
    price           DECIMAL(14,2) NOT NULL CHECK (price >= 0)
);
GO

CREATE TABLE material_stock (
    id                  INT IDENTITY(1,1) PRIMARY KEY,
    material_id         INT NOT NULL REFERENCES materials(id),
    warehouse_id        INT NOT NULL REFERENCES warehouses(id),
    quantity            DECIMAL(14,3) NOT NULL CONSTRAINT DF_stock_qty DEFAULT 0 CHECK (quantity >= 0),
    reserved_quantity   DECIMAL(14,3) NOT NULL CONSTRAINT DF_stock_res DEFAULT 0 CHECK (reserved_quantity >= 0),
    CONSTRAINT UQ_stock_mat_wh UNIQUE (material_id, warehouse_id),
    CONSTRAINT CK_stock_reserved_le_qty CHECK (reserved_quantity <= quantity)
);
GO

CREATE TABLE material_movements (
    id              BIGINT IDENTITY(1,1) PRIMARY KEY,
    material_id     INT NOT NULL REFERENCES materials(id),
    warehouse_id    INT NOT NULL REFERENCES warehouses(id),
    movement_type   NVARCHAR(20) NOT NULL
        CONSTRAINT CK_mvmt_type CHECK (movement_type IN
            (N'income', N'outcome', N'reserve', N'unreserve', N'transfer')),
    quantity        DECIMAL(14,3) NOT NULL CHECK (quantity > 0),
    work_order_id   INT NULL REFERENCES work_orders(id),
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_mvmt_created DEFAULT SYSUTCDATETIME()
);
GO

CREATE TABLE purchase_requests (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    material_id     INT NOT NULL REFERENCES materials(id),
    quantity        DECIMAL(14,3) NOT NULL CHECK (quantity > 0),
    status          NVARCHAR(30) NOT NULL
        CONSTRAINT CK_pr_status CHECK (status IN
            (N'draft', N'submitted', N'approved', N'ordered', N'received', N'cancelled')),
    created_at      DATETIME2 NOT NULL CONSTRAINT DF_pr_created DEFAULT SYSUTCDATETIME()
);
GO

-- =============================================================================
-- 10. ML-ПОДСИСТЕМА
-- =============================================================================

CREATE TABLE ml_predictions (
    id                          BIGINT IDENTITY(1,1) PRIMARY KEY,
    boiler_id                   INT NOT NULL REFERENCES boilers(id),
    [timestamp]                 DATETIME2 NOT NULL CONSTRAINT DF_ml_ts DEFAULT SYSUTCDATETIME(),
    probability                 DECIMAL(5,4) NOT NULL CHECK (probability BETWEEN 0 AND 1),
    predicted_failure_type      NVARCHAR(100) NULL,
    horizon_minutes             INT NOT NULL CHECK (horizon_minutes > 0),
    triggered_alert             BIT NOT NULL CONSTRAINT DF_ml_alert DEFAULT 0,
    -- actual_outcome заполняется постфактум: подтвердился прогноз или нет.
    actual_outcome              NVARCHAR(30) NULL
        CONSTRAINT CK_ml_outcome CHECK (actual_outcome IS NULL OR actual_outcome IN
            (N'confirmed', N'false_positive', N'pending'))
);
GO

-- =============================================================================
-- 11. GRANT-Ы ДЛЯ ПРИКЛАДНЫХ ЛОГИНОВ
-- =============================================================================
-- app_web: уже в db_datareader — дополнительно разрешаем вставку в audit_log.
GRANT INSERT ON dbo.audit_log TO app_web;
GO

-- app_mobile: SELECT на справочники и объекты, write только в узком наборе.
-- Чтение — нужно для отображения на планшете/телефоне.
GRANT SELECT ON dbo.boilers TO app_mobile;
GRANT SELECT ON dbo.equipment TO app_mobile;
GRANT SELECT ON dbo.equipment_categories TO app_mobile;
GRANT SELECT ON dbo.request_types TO app_mobile;
GRANT SELECT ON dbo.request_priorities TO app_mobile;
GRANT SELECT ON dbo.requests TO app_mobile;
GRANT SELECT ON dbo.brigades TO app_mobile;
GRANT SELECT ON dbo.brigade_members TO app_mobile;
GRANT SELECT ON dbo.employees TO app_mobile;

-- Мобильный бригадир работает с нарядами и чек-листами в поле.
GRANT SELECT, UPDATE ON dbo.work_orders TO app_mobile;
GRANT SELECT, INSERT, UPDATE ON dbo.work_order_checklist_items TO app_mobile;
GRANT SELECT, INSERT ON dbo.work_order_photos TO app_mobile;
GRANT SELECT, INSERT ON dbo.acts TO app_mobile;
GO

PRINT N'Схема создана: 39 таблиц, GRANT-ы применены.';
GO
