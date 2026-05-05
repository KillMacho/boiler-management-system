using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class AuditService(ApiClient api, ILogger<AuditService> logger)
{
    public async Task<List<AuditLogDto>> GetLogsAsync(
        int? userId = null, string? entityType = null, string? action = null, int limit = 100)
    {
        try
        {
            var q = new List<string> { $"limit={limit}" };
            if (userId.HasValue)                   q.Add($"user_id={userId}");
            if (!string.IsNullOrEmpty(entityType)) q.Add($"entity_type={Uri.EscapeDataString(entityType)}");
            if (!string.IsNullOrEmpty(action))     q.Add($"action={Uri.EscapeDataString(action)}");
            return await api.GetAsync<List<AuditLogDto>>("/api/v1/audit/?" + string.Join("&", q)) ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load audit logs");
            return [];
        }
    }
}
