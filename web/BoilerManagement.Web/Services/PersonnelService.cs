using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class PersonnelService(ApiClient api, ILogger<PersonnelService> logger)
{
    public async Task<List<EmployeeDto>> GetEmployeesAsync(int? departmentId = null, string? status = null, int limit = 200)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (departmentId.HasValue)             q.Add($"department_id={departmentId}");
            if (!string.IsNullOrEmpty(status))     q.Add($"status={Uri.EscapeDataString(status)}");
            return await api.GetAsync<List<EmployeeDto>>("/api/v1/employees/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load employees");
            return [];
        }
    }

    public async Task<List<BrigadeDto>> GetBrigadesAsync(int limit = 100)
    {
        try
        {
            return await api.GetAsync<List<BrigadeDto>>($"/api/v1/brigades/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load brigades");
            return [];
        }
    }

    public async Task<List<DepartmentDto>> GetDepartmentsAsync()
    {
        try
        {
            return await api.GetAsync<List<DepartmentDto>>("/api/v1/departments/?limit=100") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load departments");
            return [];
        }
    }

    public async Task<List<PositionDto>> GetPositionsAsync()
    {
        try
        {
            return await api.GetAsync<List<PositionDto>>("/api/v1/positions/?limit=100") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load positions");
            return [];
        }
    }
}
