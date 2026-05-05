using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class EquipmentService(ApiClient api, ILogger<EquipmentService> logger)
{
    public async Task<List<EquipmentDto>> GetAllAsync(int? boilerId = null, int limit = 200)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (boilerId.HasValue) q.Add($"boiler_id={boilerId}");
            return await api.GetAsync<List<EquipmentDto>>("/api/v1/equipment/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load equipment");
            return [];
        }
    }

    public async Task<List<BoilerDto>> GetBoilersAsync(int limit = 100)
    {
        try
        {
            return await api.GetAsync<List<BoilerDto>>($"/api/v1/boilers/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load boilers");
            return [];
        }
    }

    public async Task<List<EquipmentCategoryDto>> GetCategoriesAsync()
    {
        try
        {
            return await api.GetAsync<List<EquipmentCategoryDto>>("/api/v1/lookups/equipment-categories") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load equipment categories");
            return [];
        }
    }
}
