using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record MaintenanceTypeDto(
    [property: JsonPropertyName("id")]               int Id,
    [property: JsonPropertyName("name")]             string Name,
    [property: JsonPropertyName("periodicity_days")] int PeriodicityDays);

public record MaintenanceRegulationDto(
    [property: JsonPropertyName("id")]                  int Id,
    [property: JsonPropertyName("equipment_id")]        int EquipmentId,
    [property: JsonPropertyName("maintenance_type_id")] int MaintenanceTypeId,
    [property: JsonPropertyName("next_due_date")]       DateOnly NextDueDate,
    [property: JsonPropertyName("last_performed_at")]   DateTime? LastPerformedAt);

public record MaintenanceScheduleDto(
    [property: JsonPropertyName("id")]           int Id,
    [property: JsonPropertyName("period_start")] DateOnly PeriodStart,
    [property: JsonPropertyName("period_end")]   DateOnly PeriodEnd,
    [property: JsonPropertyName("status")]       string Status,
    [property: JsonPropertyName("created_at")]   DateTime CreatedAt);

public record MaintenancePlanItemDto(
    [property: JsonPropertyName("id")]                   int Id,
    [property: JsonPropertyName("schedule_id")]          int ScheduleId,
    [property: JsonPropertyName("equipment_id")]         int EquipmentId,
    [property: JsonPropertyName("maintenance_type_id")]  int MaintenanceTypeId,
    [property: JsonPropertyName("planned_date")]         DateOnly PlannedDate,
    [property: JsonPropertyName("assigned_brigade_id")]  int? AssignedBrigadeId,
    [property: JsonPropertyName("status")]               string Status);
