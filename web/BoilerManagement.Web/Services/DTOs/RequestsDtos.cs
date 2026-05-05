using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record RequestDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("number")]      string Number,
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("type_id")]     int TypeId,
    [property: JsonPropertyName("priority_id")] int PriorityId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("source")]      string Source,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("created_at")]  DateTime CreatedAt,
    [property: JsonPropertyName("created_by")]  int? CreatedBy,
    [property: JsonPropertyName("closed_at")]   DateTime? ClosedAt);

public record CreateRequestDto(
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("source")]      string Source,
    [property: JsonPropertyName("type_id")]     int? TypeId,
    [property: JsonPropertyName("priority_id")] int? PriorityId);

public record RequestCreatedResponseDto(
    [property: JsonPropertyName("request")]    RequestDto Request,
    [property: JsonPropertyName("work_order")] WorkOrderBriefDto? WorkOrder,
    [property: JsonPropertyName("warning")]    string? Warning);

public record WorkOrderBriefDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("request_id")]  int RequestId,
    [property: JsonPropertyName("brigade_id")]  int BrigadeId,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("assigned_at")] DateTime AssignedAt);

public record RequestTypeLookupDto(
    [property: JsonPropertyName("id")]   int Id,
    [property: JsonPropertyName("name")] string Name);

public record RequestPriorityLookupDto(
    [property: JsonPropertyName("id")]                    int Id,
    [property: JsonPropertyName("name")]                  string Name,
    [property: JsonPropertyName("response_time_minutes")] int ResponseTimeMinutes);

public record BoilerLookupDto(
    [property: JsonPropertyName("id")]   int Id,
    [property: JsonPropertyName("name")] string Name);

public record StatusChangeDto(
    [property: JsonPropertyName("status")] string Status);
