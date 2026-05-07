using System.Net;
using System.Net.Http.Json;
using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

/// <summary>
/// Scoped HTTP client for the backend API.
/// Injects Authorization: Bearer header on every request using the scoped
/// TokenStorageService. On 401, attempts one silent token refresh, then retries.
/// </summary>
public class ApiClient(
    HttpClient http,
    IHttpClientFactory httpClientFactory,
    TokenStorageService tokenStorage,
    ILogger<ApiClient> logger)
{
    public HttpClient Http => http;

    private async Task AttachTokenAsync()
    {
        var token = await tokenStorage.GetAccessTokenAsync();
        http.DefaultRequestHeaders.Authorization = !string.IsNullOrEmpty(token)
            ? new("Bearer", token)
            : null;
    }

    private async Task<bool> TryRefreshAsync()
    {
        var refreshToken = await tokenStorage.GetRefreshTokenAsync();
        if (string.IsNullOrEmpty(refreshToken)) return false;
        try
        {
            var bare = httpClientFactory.CreateClient("bare");
            var resp = await bare.PostAsJsonAsync("/api/auth/refresh", new RefreshRequest(refreshToken));
            if (!resp.IsSuccessStatusCode) { await tokenStorage.ClearTokensAsync(); return false; }
            var body = await resp.Content.ReadFromJsonAsync<RefreshResponse>();
            if (body is null) { await tokenStorage.ClearTokensAsync(); return false; }
            await tokenStorage.SetTokensAsync(body.AccessToken, body.RefreshToken);
            return true;
        }
        catch
        {
            await tokenStorage.ClearTokensAsync();
            return false;
        }
    }

    public async Task<T?> GetAsync<T>(string path, CancellationToken ct = default)
    {
        try
        {
            await AttachTokenAsync();
            var resp = await http.GetAsync(path, ct);
            if (resp.StatusCode == HttpStatusCode.Unauthorized && await TryRefreshAsync())
            {
                await AttachTokenAsync();
                resp = await http.GetAsync(path, ct);
            }
            resp.EnsureSuccessStatusCode();
            return await resp.Content.ReadFromJsonAsync<T>(cancellationToken: ct);
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
            if (resp.StatusCode == HttpStatusCode.Unauthorized && await TryRefreshAsync())
            {
                await AttachTokenAsync();
                resp = await http.PostAsJsonAsync(path, body, ct);
            }
            resp.EnsureSuccessStatusCode();
            return await resp.Content.ReadFromJsonAsync<TResponse>(cancellationToken: ct);
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

    public async Task<TResponse?> PutAsync<TRequest, TResponse>(
        string path, TRequest body, CancellationToken ct = default)
    {
        try
        {
            await AttachTokenAsync();
            var resp = await http.PutAsJsonAsync(path, body, ct);
            if (resp.StatusCode == HttpStatusCode.Unauthorized && await TryRefreshAsync())
            {
                await AttachTokenAsync();
                resp = await http.PutAsJsonAsync(path, body, ct);
            }
            resp.EnsureSuccessStatusCode();
            return await resp.Content.ReadFromJsonAsync<TResponse>(cancellationToken: ct);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "PUT {Path} failed", path);
            throw;
        }
    }

    public async Task DeleteAsync(string path, CancellationToken ct = default)
    {
        try
        {
            await AttachTokenAsync();
            var resp = await http.DeleteAsync(path, ct);
            if (resp.StatusCode == HttpStatusCode.Unauthorized && await TryRefreshAsync())
            {
                await AttachTokenAsync();
                resp = await http.DeleteAsync(path, ct);
            }
            resp.EnsureSuccessStatusCode();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "DELETE {Path} failed", path);
            throw;
        }
    }
}
