using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record BoilerDto(
    [property: JsonPropertyName("id")]                 int Id,
    [property: JsonPropertyName("name")]               string Name,
    [property: JsonPropertyName("address")]            string Address,
    [property: JsonPropertyName("status")]             string Status,
    [property: JsonPropertyName("commissioning_date")] DateOnly CommissioningDate);

public record EquipmentDto(
    [property: JsonPropertyName("id")]                int Id,
    [property: JsonPropertyName("boiler_id")]         int BoilerId,
    [property: JsonPropertyName("category_id")]       int CategoryId,
    [property: JsonPropertyName("serial_number")]     string SerialNumber,
    [property: JsonPropertyName("model")]             string Model,
    [property: JsonPropertyName("manufacturer")]      string? Manufacturer,
    [property: JsonPropertyName("installation_date")] DateOnly InstallationDate,
    [property: JsonPropertyName("warranty_until")]    DateOnly? WarrantyUntil,
    [property: JsonPropertyName("status")]            string Status);

public record EquipmentPassportDto(
    [property: JsonPropertyName("id")]           int Id,
    [property: JsonPropertyName("equipment_id")] int EquipmentId,
    [property: JsonPropertyName("passport_data")] string PassportData,
    [property: JsonPropertyName("created_at")]   DateTime CreatedAt);

public record EquipmentCategoryDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("name")]        string Name,
    [property: JsonPropertyName("description")] string? Description);
