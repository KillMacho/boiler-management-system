using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public class AccountingService(ApiClient api, ILogger<AccountingService> logger)
{
    public async Task<OnecSendPeriodResponse?> SendPeriodAsync(string period)
    {
        try
        {
            return await api.PostAsync<OnecSendPeriodRequest, OnecSendPeriodResponse>(
                "/api/v1/integration/onec/send-period",
                new OnecSendPeriodRequest(period));
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to send period {Period} to 1C", period);
            return null;
        }
    }

    public async Task<GenerateReportResponse?> GenerateReportAsync(string reportType, string period)
    {
        try
        {
            return await api.PostAsync<GenerateReportRequest, GenerateReportResponse>(
                "/api/v1/reporting/generate",
                new GenerateReportRequest(reportType, period));
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to generate {Type} report for {Period}", reportType, period);
            return null;
        }
    }

    public async Task<SubmitReportResponse?> SubmitReportAsync(string reportType, string period)
    {
        try
        {
            return await api.PostAsync<SubmitReportRequest, SubmitReportResponse>(
                "/api/v1/reporting/submit",
                new SubmitReportRequest(reportType, period));
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to submit {Type} report for {Period}", reportType, period);
            return null;
        }
    }

    public async Task<List<ReportDetailDto>> GetReportsAsync()
    {
        try
        {
            return await api.GetAsync<List<ReportDetailDto>>("/api/v1/reporting/list") ?? [];
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Failed to load reports list");
            return [];
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
