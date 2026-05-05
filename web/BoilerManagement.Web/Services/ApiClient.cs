using System.Net.Http.Json;

namespace BoilerManagement.Web.Services;

/// <summary>
/// Scoped HTTP client for the backend API.
/// Injects Authorization: Bearer header on every request using the scoped
/// TokenStorageService — this guarantees we always read the token from the
/// correct Blazor circuit scope, avoiding the root-scope issue with typed clients.
/// </summary>
public class ApiClient(
    HttpClient http,
    TokenStorageService tokenStorage,
    ILogger<ApiClient> logger)
{
    public HttpClient Http => http;

    private async Task AttachTokenAsync()
    {
        var token = await tokenStorage.GetAccessTokenAsync();
        if (!string.IsNullOrEmpty(token))
            http.DefaultRequestHeaders.Authorization = new("Bearer", token);
        else
            http.DefaultRequestHeaders.Authorization = null;
    }

    public async Task<T?> GetAsync<T>(string path, CancellationToken ct = default)
    {
        try
        {
            await AttachTokenAsync();
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
            await AttachTokenAsync();
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
        await AttachTokenAsync();
        return await http.PostAsJsonAsync(path, body, ct);
    }
}
