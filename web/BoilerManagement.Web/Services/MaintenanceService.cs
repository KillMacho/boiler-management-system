using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class MaintenanceService(ApiClient api, ILogger<MaintenanceService> logger)
{
    public async Task<List<MaintenanceRegulationDto>> GetRegulationsAsync(int limit = 200)
    {
        try
        {
            return await api.GetAsync<List<MaintenanceRegulationDto>>($"/api/v1/regulations/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load regulations");
            return [];
        }
    }

    public async Task<List<MaintenanceScheduleDto>> GetSchedulesAsync(int limit = 50)
    {
        try
        {
            return await api.GetAsync<List<MaintenanceScheduleDto>>($"/api/v1/schedules/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load schedules");
            return [];
        }
    }

    public async Task<List<MaintenancePlanItemDto>> GetPlanItemsAsync(int? scheduleId = null, int limit = 200)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (scheduleId.HasValue) q.Add($"schedule_id={scheduleId}");
            return await api.GetAsync<List<MaintenancePlanItemDto>>("/api/v1/plan-items/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load plan items");
            return [];
        }
    }

    public async Task<List<MaintenanceRegulationDto>> GetUpcomingAsync(int daysAhead = 7)
    {
        try
        {
            return await api.GetAsync<List<MaintenanceRegulationDto>>($"/api/v1/maintenance/upcoming?days_ahead={daysAhead}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load upcoming maintenance");
            return [];
        }
    }
}
