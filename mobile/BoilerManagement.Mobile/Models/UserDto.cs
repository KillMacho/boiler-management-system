using System.Text.Json.Serialization;

namespace BoilerManagement.Mobile.Models;

public record UserDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("username")]    string Username,
    [property: JsonPropertyName("employee_id")] int? EmployeeId,
    [property: JsonPropertyName("is_active")]   bool IsActive,
    [property: JsonPropertyName("last_login")]  DateTime? LastLogin,
    [property: JsonPropertyName("roles")]       List<string> Roles);
