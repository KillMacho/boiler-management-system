-- Remove boilers with id > 15 and all their dependent data
BEGIN TRANSACTION;

-- Find request IDs for boilers > 15
CREATE TABLE #req_ids (id INT);
INSERT INTO #req_ids SELECT id FROM requests WHERE boiler_id > 15;

-- Find work_order IDs for those requests
CREATE TABLE #wo_ids (id INT);
INSERT INTO #wo_ids SELECT id FROM work_orders WHERE request_id IN (SELECT id FROM #req_ids);

-- Delete leaf tables first
DELETE FROM work_order_photos          WHERE work_order_id IN (SELECT id FROM #wo_ids);
DELETE FROM work_order_checklist_items WHERE work_order_id IN (SELECT id FROM #wo_ids);
DELETE FROM acts                       WHERE work_order_id IN (SELECT id FROM #wo_ids);
DELETE FROM work_orders                WHERE id            IN (SELECT id FROM #wo_ids);
DELETE FROM requests                   WHERE id            IN (SELECT id FROM #req_ids);

DROP TABLE #req_ids;
DROP TABLE #wo_ids;

DELETE FROM telemetry      WHERE boiler_id > 15;
DELETE FROM ml_predictions WHERE boiler_id > 15;

-- equipment_passports
CREATE TABLE #eq_ids (id INT);
INSERT INTO #eq_ids SELECT id FROM equipment WHERE boiler_id > 15;
DELETE FROM equipment_passports WHERE equipment_id IN (SELECT id FROM #eq_ids);
DELETE FROM equipment           WHERE id           IN (SELECT id FROM #eq_ids);
DROP TABLE #eq_ids;

DELETE FROM thresholds WHERE boiler_id > 15;
DELETE FROM boilers    WHERE id > 15;

COMMIT;

SELECT COUNT(*) AS remaining_boilers FROM boilers;
