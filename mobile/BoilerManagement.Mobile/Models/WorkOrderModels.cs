using System.Text.Json.Serialization;

namespace BoilerManagement.Mobile.Models;

public record WorkOrderDto(
    [property: JsonPropertyName("id")]           int Id,
    [property: JsonPropertyName("request_id")]   int RequestId,
    [property: JsonPropertyName("brigade_id")]   int BrigadeId,
    [property: JsonPropertyName("status")]       string Status,
    [property: JsonPropertyName("assigned_at")]  DateTime AssignedAt,
    [property: JsonPropertyName("started_at")]   DateTime? StartedAt,
    [property: JsonPropertyName("completed_at")] DateTime? CompletedAt);

public record ChecklistItemDto(
    [property: JsonPropertyName("id")]            int Id,
    [property: JsonPropertyName("work_order_id")] int WorkOrderId,
    [property: JsonPropertyName("description")]   string Description,
    [property: JsonPropertyName("is_completed")]  bool IsCompleted,
    [property: JsonPropertyName("sort_order")]    int SortOrder,
    [property: JsonPropertyName("completed_at")]  DateTime? CompletedAt);

public record PhotoDto(
    [property: JsonPropertyName("id")]            int Id,
    [property: JsonPropertyName("work_order_id")] int WorkOrderId,
    [property: JsonPropertyName("file_path")]     string FilePath,
    [property: JsonPropertyName("uploaded_at")]   DateTime UploadedAt);

public record RequestDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("number")]      string Number,
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("type_id")]     int TypeId,
    [property: JsonPropertyName("priority_id")] int PriorityId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("source")]      string Source,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("created_at")]  DateTime CreatedAt);

public record CompleteRequest(
    [property: JsonPropertyName("notes")]        string? Notes,
    [property: JsonPropertyName("total_amount")] double TotalAmount = 0.0);

public record ChecklistToggleRequest(
    [property: JsonPropertyName("is_completed")] bool IsCompleted);

// View model for work order list display
public class WorkOrderDisplayItem
{
    public WorkOrderDto WorkOrder { get; init; } = null!;
    public RequestDto? Request { get; set; }

    public string StatusDisplay => WorkOrder.Status switch
    {
        "assigned"    => "Назначен",
        "in_progress" => "В работе",
        "completed"   => "Завершён",
        "cancelled"   => "Отменён",
        _             => WorkOrder.Status
    };

    public Color StatusColor => WorkOrder.Status switch
    {
        "assigned"    => Colors.Orange,
        "in_progress" => Colors.Blue,
        "completed"   => Colors.Green,
        "cancelled"   => Colors.Gray,
        _             => Colors.Gray
    };

    public string Description => Request?.Description ?? "—";
    public string Number => $"№ {WorkOrder.Id}";
    public bool IsActive => WorkOrder.Status is "assigned" or "in_progress";
}

// Mutable checklist item for UI binding
public class ChecklistItemViewModel : CommunityToolkit.Mvvm.ComponentModel.ObservableObject
{
    private bool _isCompleted;

    public int Id { get; init; }
    public int WorkOrderId { get; init; }
    public string Description { get; init; } = "";
    public int SortOrder { get; init; }

    public bool IsCompleted
    {
        get => _isCompleted;
        set => SetProperty(ref _isCompleted, value);
    }

    public static ChecklistItemViewModel FromDto(ChecklistItemDto dto) => new()
    {
        Id = dto.Id,
        WorkOrderId = dto.WorkOrderId,
        Description = dto.Description,
        SortOrder = dto.SortOrder,
        IsCompleted = dto.IsCompleted,
    };
}
