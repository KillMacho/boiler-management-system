using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class RequestsService(ApiClient api, ILogger<RequestsService> logger)
{
    public async Task<List<RequestDto>> GetAllAsync(
        string? status = null, int? typeId = null, int? priorityId = null,
        int? boilerId = null, int limit = 100)
    {
        try
        {
            var q = new List<string>();
            if (!string.IsNullOrEmpty(status))   q.Add($"status={Uri.EscapeDataString(status)}");
            if (typeId.HasValue)                 q.Add($"type_id={typeId}");
            if (priorityId.HasValue)             q.Add($"priority_id={priorityId}");
            if (boilerId.HasValue)               q.Add($"boiler_id={boilerId}");
            q.Add($"limit={limit}");
            var url = "/api/v1/requests/?" + string.Join("&", q);
            return await api.GetAsync<List<RequestDto>>(url) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load requests");
            return [];
        }
    }

    public async Task<RequestDto?> GetByIdAsync(int id)
    {
        try
        {
            return await api.GetAsync<RequestDto>($"/api/v1/requests/{id}");
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load request {Id}", id);
            return null;
        }
    }

    public async Task<RequestCreatedResponseDto?> CreateAsync(CreateRequestDto dto)
    {
        try
        {
            return await api.PostAsync<CreateRequestDto, RequestCreatedResponseDto>("/api/v1/requests/", dto);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to create request");
            return null;
        }
    }

    public async Task<RequestDto?> ChangeStatusAsync(int id, string newStatus)
    {
        try
        {
            return await api.PutAsync<StatusChangeDto, RequestDto>(
                $"/api/v1/requests/{id}/status",
                new StatusChangeDto(newStatus));
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to change status of request {Id}", id);
            return null;
        }
    }

    public async Task<List<RequestTypeLookupDto>> GetTypesAsync()
    {
        try
        {
            return await api.GetAsync<List<RequestTypeLookupDto>>("/api/v1/lookups/request-types") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load request types");
            return [];
        }
    }

    public async Task<List<RequestPriorityLookupDto>> GetPrioritiesAsync()
    {
        try
        {
            return await api.GetAsync<List<RequestPriorityLookupDto>>("/api/v1/lookups/request-priorities") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load request priorities");
            return [];
        }
    }

    public async Task<List<BoilerLookupDto>> GetBoilersAsync()
    {
        try
        {
            return await api.GetAsync<List<BoilerLookupDto>>("/api/v1/boilers/?limit=200") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load boilers");
            return [];
        }
    }
}
