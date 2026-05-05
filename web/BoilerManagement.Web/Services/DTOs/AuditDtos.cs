using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record AuditLogDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("user_id")]     int? UserId,
    [property: JsonPropertyName("action")]      string Action,
    [property: JsonPropertyName("entity_type")] string EntityType,
    [property: JsonPropertyName("entity_id")]   string? EntityId,
    [property: JsonPropertyName("details")]     string? Details,
    [property: JsonPropertyName("timestamp")]   DateTime Timestamp);
