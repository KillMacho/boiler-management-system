using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record WorkOrderDto(
    [property: JsonPropertyName("id")]           int Id,
    [property: JsonPropertyName("request_id")]   int RequestId,
    [property: JsonPropertyName("brigade_id")]   int BrigadeId,
    [property: JsonPropertyName("status")]       string Status,
    [property: JsonPropertyName("assigned_at")]  DateTime AssignedAt,
    [property: JsonPropertyName("started_at")]   DateTime? StartedAt,
    [property: JsonPropertyName("completed_at")] DateTime? CompletedAt);

public record ChecklistItemDto(
    [property: JsonPropertyName("id")]             int Id,
    [property: JsonPropertyName("work_order_id")]  int WorkOrderId,
    [property: JsonPropertyName("description")]    string Description,
    [property: JsonPropertyName("is_completed")]   bool IsCompleted,
    [property: JsonPropertyName("sort_order")]     int SortOrder,
    [property: JsonPropertyName("completed_at")]   DateTime? CompletedAt);

public record PhotoDto(
    [property: JsonPropertyName("id")]            int Id,
    [property: JsonPropertyName("work_order_id")] int WorkOrderId,
    [property: JsonPropertyName("file_path")]     string FilePath,
    [property: JsonPropertyName("uploaded_at")]   DateTime UploadedAt);

public record CompleteWorkOrderDto(
    [property: JsonPropertyName("notes")]        string? Notes,
    [property: JsonPropertyName("total_amount")] decimal TotalAmount);
