using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record EmployeeDto(
    [property: JsonPropertyName("id")]              int Id,
    [property: JsonPropertyName("first_name")]      string FirstName,
    [property: JsonPropertyName("last_name")]       string LastName,
    [property: JsonPropertyName("middle_name")]     string? MiddleName,
    [property: JsonPropertyName("employee_number")] string EmployeeNumber,
    [property: JsonPropertyName("department_id")]   int DepartmentId,
    [property: JsonPropertyName("position_id")]     int PositionId,
    [property: JsonPropertyName("hire_date")]       DateOnly HireDate,
    [property: JsonPropertyName("status")]          string Status)
{
    public string FullName => string.Join(" ", LastName, FirstName, MiddleName).Trim();
}

public record BrigadeDto(
    [property: JsonPropertyName("id")]                   int Id,
    [property: JsonPropertyName("name")]                 string Name,
    [property: JsonPropertyName("leader_employee_id")]   int? LeaderEmployeeId,
    [property: JsonPropertyName("status")]               string Status);

public record DepartmentDto(
    [property: JsonPropertyName("id")]   int Id,
    [property: JsonPropertyName("name")] string Name);

public record PositionDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("name")]        string Name,
    [property: JsonPropertyName("base_salary")] decimal BaseSalary);
