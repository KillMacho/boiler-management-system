using System.Net.Http.Json;
using System.Net.Http.Headers;
using System.Text.Json;
using BoilerManagement.Mobile.Models;

namespace BoilerManagement.Mobile.Services;

public class ApiClient
{
    public const string BaseUrl = "http://192.168.1.2:8000";

    private readonly HttpClient _http;
    private readonly SecureStorageService _storage;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public ApiClient(SecureStorageService storage)
    {
        _storage = storage;
        _http = new HttpClient { BaseAddress = new Uri(BaseUrl), Timeout = TimeSpan.FromSeconds(30) };
    }

    private async Task AttachTokenAsync()
    {
        var token = await _storage.GetAccessTokenAsync();
        _http.DefaultRequestHeaders.Authorization = !string.IsNullOrEmpty(token)
            ? new AuthenticationHeaderValue("Bearer", token)
            : null;
    }

    private async Task<bool> TryRefreshAsync()
    {
        var refreshToken = await _storage.GetRefreshTokenAsync();
        if (string.IsNullOrEmpty(refreshToken)) return false;
        try
        {
            var resp = await _http.PostAsJsonAsync("/api/auth/refresh", new RefreshRequest(refreshToken));
            if (!resp.IsSuccessStatusCode) { _storage.ClearTokens(); return false; }
            var body = await resp.Content.ReadFromJsonAsync<AccessTokenOnlyResponse>(JsonOptions);
            if (body is null) { _storage.ClearTokens(); return false; }
            var existing = await _storage.GetRefreshTokenAsync() ?? "";
            await _storage.SetTokensAsync(body.AccessToken, existing);
            return true;
        }
        catch
        {
            _storage.ClearTokens();
            return false;
        }
    }

    public async Task<T?> GetAsync<T>(string path)
    {
        await AttachTokenAsync();
        var resp = await _http.GetAsync(path);
        if (resp.StatusCode == System.Net.HttpStatusCode.Unauthorized && await TryRefreshAsync())
        {
            await AttachTokenAsync();
            resp = await _http.GetAsync(path);
        }
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<T>(JsonOptions);
    }

    public async Task<TResponse?> PostAsync<TRequest, TResponse>(string path, TRequest body)
    {
        await AttachTokenAsync();
        var resp = await _http.PostAsJsonAsync(path, body);
        if (resp.StatusCode == System.Net.HttpStatusCode.Unauthorized && await TryRefreshAsync())
        {
            await AttachTokenAsync();
            resp = await _http.PostAsJsonAsync(path, body);
        }
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<TResponse>(JsonOptions);
    }

    public async Task<TResponse?> PostNoBodyAsync<TResponse>(string path)
    {
        await AttachTokenAsync();
        var resp = await _http.PostAsync(path, null);
        if (resp.StatusCode == System.Net.HttpStatusCode.Unauthorized && await TryRefreshAsync())
        {
            await AttachTokenAsync();
            resp = await _http.PostAsync(path, null);
        }
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<TResponse>(JsonOptions);
    }

    public async Task<TResponse?> PostMultipartAsync<TResponse>(string path, MultipartFormDataContent form)
    {
        await AttachTokenAsync();
        var resp = await _http.PostAsync(path, form);
        if (resp.StatusCode == System.Net.HttpStatusCode.Unauthorized && await TryRefreshAsync())
        {
            await AttachTokenAsync();
            resp = await _http.PostAsync(path, form);
        }
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<TResponse>(JsonOptions);
    }

    // Raw login — no auth header
    public async Task<TokenResponse?> LoginAsync(string username, string password)
    {
        var form = new FormUrlEncodedContent(new[]
        {
            new KeyValuePair<string, string>("username", username),
            new KeyValuePair<string, string>("password", password),
        });
        var resp = await _http.PostAsync("/api/auth/login", form);
        if (!resp.IsSuccessStatusCode) return null;
        return await resp.Content.ReadFromJsonAsync<TokenResponse>(JsonOptions);
    }
}
