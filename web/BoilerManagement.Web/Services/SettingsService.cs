using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class SettingsService(ApiClient api, ILogger<SettingsService> logger)
{
    public async Task<List<ThresholdDto>> GetThresholdsAsync()
    {
        try
        {
            return await api.GetAsync<List<ThresholdDto>>("/api/v1/monitoring/thresholds") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load thresholds");
            return [];
        }
    }

    public async Task<ThresholdDto?> CreateThresholdAsync(ThresholdCreateDto dto)
    {
        try
        {
            return await api.PostAsync<ThresholdCreateDto, ThresholdDto>(
                "/api/v1/monitoring/thresholds", dto);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to create threshold");
            return null;
        }
    }

    public async Task<ThresholdDto?> UpdateThresholdAsync(int id, ThresholdCreateDto dto)
    {
        try
        {
            return await api.PutAsync<ThresholdCreateDto, ThresholdDto>(
                $"/api/v1/monitoring/thresholds/{id}", dto);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to update threshold {Id}", id);
            return null;
        }
    }

    public async Task<bool> DeleteThresholdAsync(int id)
    {
        try
        {
            await api.DeleteAsync($"/api/v1/monitoring/thresholds/{id}");
            return true;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to delete threshold {Id}", id);
            return false;
        }
    }

    public async Task<List<MaintenanceRegulationDto>> GetRegulationsAsync()
    {
        try
        {
            return await api.GetAsync<List<MaintenanceRegulationDto>>("/api/v1/regulations/?limit=200") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load regulations");
            return [];
        }
    }

    public async Task<List<MaintenanceTypeDto>> GetMaintenanceTypesAsync()
    {
        try
        {
            return await api.GetAsync<List<MaintenanceTypeDto>>("/api/v1/maintenance-types/?limit=200") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load maintenance types");
            return [];
        }
    }

    public async Task<UserInfo?> GetCurrentUserAsync()
    {
        try
        {
            return await api.GetAsync<UserInfo>("/api/auth/me");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load current user");
            return null;
        }
    }

    public async Task<string> CheckBackendHealthAsync()
    {
        try
        {
            var result = await api.GetAsync<UserInfo>("/api/auth/me");
            return result is not null ? "ok" : "error";
        }
        catch
        {
            return "unavailable";
        }
    }

    public async Task<string> CheckOnecHealthAsync()
    {
        try
        {
            var result = await api.GetAsync<Dictionary<string, object>>("/api/v1/integration/onec/health");
            return result?.GetValueOrDefault("статус")?.ToString() ?? "unknown";
        }
        catch
        {
            return "unavailable";
        }
    }
}
