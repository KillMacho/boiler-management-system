using Microsoft.AspNetCore.Components.Server.ProtectedBrowserStorage;

namespace BoilerManagement.Web.Services;

/// <summary>
/// Stores JWT tokens in ProtectedSessionStorage (server-side encrypted, per-session).
/// Refresh token additionally persists in ProtectedLocalStorage for cross-tab sharing.
/// Falls back to in-memory when browser storage is unavailable (SSR pre-render).
/// </summary>
public class TokenStorageService(
    ProtectedSessionStorage sessionStorage,
    ProtectedLocalStorage localStorage)
{
    private const string AccessTokenKey = "bms_access_token";
    private const string RefreshTokenKey = "bms_refresh_token";

    // In-memory fallback for SSR pre-render phase
    private string? _memAccessToken;
    private string? _memRefreshToken;

    public async Task<string?> GetAccessTokenAsync()
    {
        try
        {
            var result = await sessionStorage.GetAsync<string>(AccessTokenKey);
            return result.Success ? result.Value : _memAccessToken;
        }
        catch
        {
            return _memAccessToken;
        }
    }

    public async Task<string?> GetRefreshTokenAsync()
    {
        try
        {
            var result = await localStorage.GetAsync<string>(RefreshTokenKey);
            return result.Success ? result.Value : _memRefreshToken;
        }
        catch
        {
            return _memRefreshToken;
        }
    }

    public async Task SetTokensAsync(string accessToken, string refreshToken)
    {
        _memAccessToken = accessToken;
        _memRefreshToken = refreshToken;
        try
        {
            await sessionStorage.SetAsync(AccessTokenKey, accessToken);
            await localStorage.SetAsync(RefreshTokenKey, refreshToken);
        }
        catch { /* storage unavailable during SSR */ }
    }

    public async Task ClearTokensAsync()
    {
        _memAccessToken = null;
        _memRefreshToken = null;
        try
        {
            await sessionStorage.DeleteAsync(AccessTokenKey);
            await localStorage.DeleteAsync(RefreshTokenKey);
        }
        catch { }
    }
}
