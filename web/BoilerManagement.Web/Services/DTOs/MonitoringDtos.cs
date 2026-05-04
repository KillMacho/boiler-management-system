using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record BoilerStatusDto(
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("name")]        string Name,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("parameters")]  Dictionary<string, string?> Parameters,
    [property: JsonPropertyName("breaches")]    List<BreachDto> Breaches,
    [property: JsonPropertyName("last_update")] DateTime? LastUpdate);

public record BreachDto(
    [property: JsonPropertyName("parameter")] string Parameter,
    [property: JsonPropertyName("kind")]      string Kind,
    [property: JsonPropertyName("value")]     string Value,
    [property: JsonPropertyName("bound")]     string? Bound = null);

public record ActiveAlarmDto(
    [property: JsonPropertyName("request_id")]  int RequestId,
    [property: JsonPropertyName("number")]      string Number,
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("created_at")]  DateTime CreatedAt);

public record TelemetryHistoryDto(
    [property: JsonPropertyName("id")]                int Id,
    [property: JsonPropertyName("boiler_id")]         int BoilerId,
    [property: JsonPropertyName("timestamp")]         DateTime Timestamp,
    [property: JsonPropertyName("status")]            string Status,
    [property: JsonPropertyName("temperature_heat")]  decimal? TemperatureHeat,
    [property: JsonPropertyName("pressure")]          decimal? Pressure,
    [property: JsonPropertyName("co_level")]          decimal? CoLevel,
    [property: JsonPropertyName("gas_flow")]          decimal? GasFlow,
    [property: JsonPropertyName("water_level")]       decimal? WaterLevel,
    [property: JsonPropertyName("temperature_return")] decimal? TemperatureReturn,
    [property: JsonPropertyName("furnace_draft")]     decimal? FurnaceDraft);

// WebSocket messages
public record WsMessage(
    [property: JsonPropertyName("type")] string Type);

public record WsFullStatus(
    [property: JsonPropertyName("type")]      string Type,
    [property: JsonPropertyName("timestamp")] double Timestamp,
    [property: JsonPropertyName("boilers")]   List<WsBoilerSnapshot> Boilers);

public record WsBoilerSnapshot(
    [property: JsonPropertyName("boiler_id")]   int BoilerId,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("parameters")]  Dictionary<string, string?> Parameters,
    [property: JsonPropertyName("breaches")]    List<BreachDto> Breaches,
    [property: JsonPropertyName("updated_at")]  double UpdatedAt);

public record WsTelemetryUpdate(
    [property: JsonPropertyName("type")]             string Type,
    [property: JsonPropertyName("boiler_id")]        int BoilerId,
    [property: JsonPropertyName("timestamp")]        string Timestamp,
    [property: JsonPropertyName("status")]           string Status,
    [property: JsonPropertyName("parameters")]       Dictionary<string, string?> Parameters,
    [property: JsonPropertyName("breaches")]         List<BreachDto> Breaches,
    [property: JsonPropertyName("auto_request_id")]  int? AutoRequestId);
