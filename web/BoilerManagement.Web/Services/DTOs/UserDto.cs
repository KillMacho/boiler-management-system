using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record UserInfo(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("username")]    string Username,
    [property: JsonPropertyName("roles")]       List<string> Roles,
    [property: JsonPropertyName("is_active")]   bool IsActive,
    [property: JsonPropertyName("employee_id")] int? EmployeeId = null);
