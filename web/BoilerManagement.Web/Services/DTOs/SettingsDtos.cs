using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record ThresholdDto(
    [property: JsonPropertyName("id")]             int Id,
    [property: JsonPropertyName("boiler_id")]      int? BoilerId,
    [property: JsonPropertyName("parameter_name")] string ParameterName,
    [property: JsonPropertyName("min_warning")]    decimal? MinWarning,
    [property: JsonPropertyName("max_warning")]    decimal? MaxWarning,
    [property: JsonPropertyName("min_critical")]   decimal? MinCritical,
    [property: JsonPropertyName("max_critical")]   decimal? MaxCritical);

public record ThresholdCreateDto(
    [property: JsonPropertyName("boiler_id")]      int? BoilerId,
    [property: JsonPropertyName("parameter_name")] string ParameterName,
    [property: JsonPropertyName("min_warning")]    decimal? MinWarning,
    [property: JsonPropertyName("max_warning")]    decimal? MaxWarning,
    [property: JsonPropertyName("min_critical")]   decimal? MinCritical,
    [property: JsonPropertyName("max_critical")]   decimal? MaxCritical);
