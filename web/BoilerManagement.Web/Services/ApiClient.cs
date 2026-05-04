using System.Net.Http.Json;

namespace BoilerManagement.Web.Services;

/// <summary>
/// Typed HTTP client for the backend API.
/// Authorization header is injected automatically by AuthTokenHandler.
/// </summary>
public class ApiClient(HttpClient http, ILogger<ApiClient> logger)
{
    public HttpClient Http => http;

    public async Task<T?> GetAsync<T>(string path, CancellationToken ct = default)
    {
        try
        {
            return await http.GetFromJsonAsync<T>(path, ct);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "GET {Path} failed", path);
            throw;
        }
    }

    public async Task<TResponse?> PostAsync<TRequest, TResponse>(
        string path, TRequest body, CancellationToken ct = default)
    {
        try
        {
            var resp = await http.PostAsJsonAsync(path, body, ct);
            resp.EnsureSuccessStatusCode();
            return await resp.Content.ReadFromJsonAsync<TResponse>(ct);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "POST {Path} failed", path);
            throw;
        }
    }

    public async Task<HttpResponseMessage> PostRawAsync<TRequest>(
        string path, TRequest body, CancellationToken ct = default)
    {
        return await http.PostAsJsonAsync(path, body, ct);
    }
}
