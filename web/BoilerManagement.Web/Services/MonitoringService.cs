using System.Net.Http.Json;
using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class MonitoringService(ApiClient api, ILogger<MonitoringService> logger)
{
    public async Task<List<BoilerStatusDto>> GetStatusAsync()
    {
        try
        {
            return await api.GetAsync<List<BoilerStatusDto>>("/api/v1/monitoring/status")
                   ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load monitoring status");
            return [];
        }
    }

    public async Task<List<ActiveAlarmDto>> GetActiveAlarmsAsync()
    {
        try
        {
            return await api.GetAsync<List<ActiveAlarmDto>>("/api/v1/monitoring/alarms/active")
                   ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load active alarms");
            return [];
        }
    }

    public async Task<List<TelemetryHistoryDto>> GetHistoryAsync(int boilerId, int hours = 24, int limit = 500)
    {
        try
        {
            var from = DateTime.UtcNow.AddHours(-hours).ToString("o");
            return await api.GetAsync<List<TelemetryHistoryDto>>(
                $"/api/v1/telemetry/{boilerId}/history?from={Uri.EscapeDataString(from)}&limit={limit}")
                   ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load telemetry history for boiler {Id}", boilerId);
            return [];
        }
    }
}
