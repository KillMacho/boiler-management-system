-- =============================================================================
-- 04_CreateIndexes.sql
-- Индексы для часто запрашиваемых полей.
-- Цель: покрыть основные сценарии чтения (дашборд, поиск заявок, история телеметрии).
-- =============================================================================

USE BoilerManagementDB;
GO

-- Телеметрия: главный сценарий — "последние N минут для котельной X".
-- Сортировка по timestamp DESC позволяет использовать индекс для TOP N.
CREATE INDEX IX_telemetry_boiler_timestamp
    ON telemetry (boiler_id, [timestamp] DESC)
    INCLUDE (temperature_heat, pressure, co_level, gas_flow, water_level,
             temperature_return, furnace_draft, status);
GO

-- Телеметрия: полнотекстовый дашборд "все котельные в тревоге".
CREATE INDEX IX_telemetry_status_timestamp
    ON telemetry (status, [timestamp] DESC)
    WHERE status IN (N'warning', N'critical');
GO

-- Оборудование по котельной.
CREATE INDEX IX_equipment_boiler ON equipment (boiler_id);
CREATE INDEX IX_equipment_category ON equipment (category_id);
GO

-- Заявки: фильтрация по статусу/котельной/дате.
CREATE INDEX IX_requests_status ON requests (status, created_at DESC);
CREATE INDEX IX_requests_boiler ON requests (boiler_id, created_at DESC);
CREATE INDEX IX_requests_type ON requests (type_id);
CREATE INDEX IX_requests_priority ON requests (priority_id);
GO

-- Наряды: фильтрация по заявке/бригаде/статусу.
CREATE INDEX IX_work_orders_request ON work_orders (request_id);
CREATE INDEX IX_work_orders_brigade ON work_orders (brigade_id, status);
CREATE INDEX IX_work_orders_status ON work_orders (status, assigned_at DESC);
GO

-- Чек-листы и фото — часто джойнятся по work_order_id.
CREATE INDEX IX_checklist_wo ON work_order_checklist_items (work_order_id);
CREATE INDEX IX_wo_photos_wo ON work_order_photos (work_order_id);
GO

-- Склад.
CREATE INDEX IX_stock_material ON material_stock (material_id);
CREATE INDEX IX_stock_warehouse ON material_stock (warehouse_id);
CREATE INDEX IX_movements_material_date ON material_movements (material_id, created_at DESC);
CREATE INDEX IX_movements_wo ON material_movements (work_order_id) WHERE work_order_id IS NOT NULL;
GO

-- Планирование ТО.
CREATE INDEX IX_regulations_equipment ON maintenance_regulations (equipment_id);
CREATE INDEX IX_regulations_due ON maintenance_regulations (next_due_date);
CREATE INDEX IX_plan_items_schedule ON maintenance_plan_items (schedule_id);
CREATE INDEX IX_plan_items_date ON maintenance_plan_items (planned_date, status);
CREATE INDEX IX_plan_items_brigade ON maintenance_plan_items (assigned_brigade_id)
    WHERE assigned_brigade_id IS NOT NULL;
GO

-- Персонал и бригады.
CREATE INDEX IX_employees_department ON employees (department_id);
CREATE INDEX IX_employees_position ON employees (position_id);
CREATE INDEX IX_employees_status ON employees (status);
CREATE INDEX IX_brigade_members_emp ON brigade_members (employee_id);
CREATE INDEX IX_timesheets_emp_date ON timesheets (employee_id, [date] DESC);
GO

-- Аудит: частый поиск "что делал пользователь X за период".
CREATE INDEX IX_audit_user_ts ON audit_log (user_id, [timestamp] DESC)
    WHERE user_id IS NOT NULL;
CREATE INDEX IX_audit_entity ON audit_log (entity_type, entity_id);
GO

-- ML-прогнозы по котельной.
CREATE INDEX IX_ml_boiler_ts ON ml_predictions (boiler_id, [timestamp] DESC);
CREATE INDEX IX_ml_alerts ON ml_predictions ([timestamp] DESC)
    WHERE triggered_alert = 1;
GO

-- Пороги по котельной.
CREATE INDEX IX_thresholds_boiler_param ON thresholds (boiler_id, parameter_name);
GO

PRINT N'Индексы созданы.';
GO
