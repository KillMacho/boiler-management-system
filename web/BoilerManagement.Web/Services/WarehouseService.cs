using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class WarehouseService(ApiClient api, ILogger<WarehouseService> logger)
{
    public async Task<List<MaterialStockDto>> GetStockAsync(int? warehouseId = null, int limit = 200)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (warehouseId.HasValue) q.Add($"warehouse_id={warehouseId}");
            return await api.GetAsync<List<MaterialStockDto>>("/api/v1/stock/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load stock");
            return [];
        }
    }

    public async Task<List<MaterialMovementDto>> GetMovementsAsync(int limit = 100)
    {
        try
        {
            return await api.GetAsync<List<MaterialMovementDto>>($"/api/v1/movements/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load movements");
            return [];
        }
    }

    public async Task<List<PurchaseRequestDto>> GetPurchaseRequestsAsync(string? status = null, int limit = 100)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (!string.IsNullOrEmpty(status)) q.Add($"status={Uri.EscapeDataString(status)}");
            return await api.GetAsync<List<PurchaseRequestDto>>("/api/v1/purchase-requests/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load purchase requests");
            return [];
        }
    }

    public async Task<List<MaterialDto>> GetMaterialsAsync(int limit = 200)
    {
        try
        {
            return await api.GetAsync<List<MaterialDto>>($"/api/v1/materials/?limit={limit}") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load materials");
            return [];
        }
    }

    public async Task<List<WarehouseDto>> GetWarehousesAsync()
    {
        try
        {
            return await api.GetAsync<List<WarehouseDto>>("/api/v1/warehouses/?limit=100") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load warehouses");
            return [];
        }
    }
}
