using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class WorkOrdersService(ApiClient api, ILogger<WorkOrdersService> logger)
{
    public async Task<List<WorkOrderDto>> GetAllAsync(string? status = null, int? brigadeId = null, int limit = 100)
    {
        try
        {
            var q = new List<string>();
            if (!string.IsNullOrEmpty(status)) q.Add($"status={Uri.EscapeDataString(status)}");
            if (brigadeId.HasValue)            q.Add($"brigade_id={brigadeId}");
            q.Add($"limit={limit}");
            var url = "/api/v1/work-orders/?" + string.Join("&", q);
            return await api.GetAsync<List<WorkOrderDto>>(url) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load work orders");
            return [];
        }
    }

    public async Task<WorkOrderDto?> GetByIdAsync(int id)
    {
        try
        {
            return await api.GetAsync<WorkOrderDto>($"/api/v1/work-orders/{id}");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load work order {Id}", id);
            return null;
        }
    }

    public async Task<WorkOrderDto?> StartAsync(int id)
    {
        try
        {
            return await api.PostAsync<object, WorkOrderDto>($"/api/v1/work-orders/{id}/start", new { });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to start work order {Id}", id);
            return null;
        }
    }

    public async Task<WorkOrderDto?> CompleteAsync(int id, string? notes = null, decimal totalAmount = 0)
    {
        try
        {
            return await api.PostAsync<CompleteWorkOrderDto, WorkOrderDto>(
                $"/api/v1/work-orders/{id}/complete",
                new CompleteWorkOrderDto(notes, totalAmount));
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to complete work order {Id}", id);
            return null;
        }
    }
}
