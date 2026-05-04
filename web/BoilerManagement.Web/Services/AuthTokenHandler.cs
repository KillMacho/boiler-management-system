using System.Net;
using System.Net.Http.Json;
using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

/// <summary>
/// DelegatingHandler that:
/// 1. Injects Authorization: Bearer header on every request.
/// 2. On 401, attempts one silent token refresh, then retries.
/// 3. If refresh fails, clears tokens (caller sees 401 and redirects to /login).
/// </summary>
public class AuthTokenHandler(TokenStorageService tokenStorage) : DelegatingHandler
{
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var token = await tokenStorage.GetAccessTokenAsync();
        if (!string.IsNullOrEmpty(token))
            request.Headers.Authorization = new("Bearer", token);

        var response = await base.SendAsync(request, cancellationToken);

        if (response.StatusCode == HttpStatusCode.Unauthorized)
        {
            // Try to refresh
            var refreshed = await TryRefreshAsync(cancellationToken);
            if (refreshed is not null)
            {
                // Clone request and retry with new token
                var retry = await CloneRequestAsync(request);
                retry.Headers.Authorization = new("Bearer", refreshed);
                response = await base.SendAsync(retry, cancellationToken);
            }
        }

        return response;
    }

    private async Task<string?> TryRefreshAsync(CancellationToken ct)
    {
        var refreshToken = await tokenStorage.GetRefreshTokenAsync();
        if (string.IsNullOrEmpty(refreshToken)) return null;

        try
        {
            // Build a raw message to avoid recursion through this handler
            var req = new HttpRequestMessage(HttpMethod.Post, "/api/auth/refresh");
            req.Content = JsonContent.Create(new RefreshRequest(refreshToken));
            var resp = await base.SendAsync(req, ct);
            if (!resp.IsSuccessStatusCode) { await tokenStorage.ClearTokensAsync(); return null; }

            var body = await resp.Content.ReadFromJsonAsync<RefreshResponse>(ct);
            if (body is null) { await tokenStorage.ClearTokensAsync(); return null; }

            await tokenStorage.SetTokensAsync(body.AccessToken, body.RefreshToken);
            return body.AccessToken;
        }
        catch
        {
            await tokenStorage.ClearTokensAsync();
            return null;
        }
    }

    private static async Task<HttpRequestMessage> CloneRequestAsync(HttpRequestMessage original)
    {
        var clone = new HttpRequestMessage(original.Method, original.RequestUri);
        foreach (var header in original.Headers)
            clone.Headers.TryAddWithoutValidation(header.Key, header.Value);

        if (original.Content is not null)
        {
            var bytes = await original.Content.ReadAsByteArrayAsync();
            clone.Content = new ByteArrayContent(bytes);
            foreach (var h in original.Content.Headers)
                clone.Content.Headers.TryAddWithoutValidation(h.Key, h.Value);
        }

        return clone;
    }
}
