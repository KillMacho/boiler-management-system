using BoilerManagement.Mobile.Models;

namespace BoilerManagement.Mobile.Services;

public class AuthService(ApiClient api, SecureStorageService storage)
{
    public UserDto? CurrentUser { get; private set; }

    public async Task<bool> LoginAsync(string username, string password)
    {
        try
        {
            var resp = await api.LoginAsync(username, password);
            if (resp is null) return false;
            await storage.SetTokensAsync(resp.AccessToken, resp.RefreshToken);
            CurrentUser = resp.User;
            return true;
        }
        catch
        {
            return false;
        }
    }

    public async Task<bool> TryRestoreSessionAsync()
    {
        var refresh = await storage.GetRefreshTokenAsync();
        if (string.IsNullOrEmpty(refresh)) return false;
        try
        {
            var me = await api.GetAsync<UserDto>("/api/auth/me");
            if (me is null) { storage.ClearTokens(); return false; }
            CurrentUser = me;
            return true;
        }
        catch
        {
            storage.ClearTokens();
            return false;
        }
    }

    public void Logout()
    {
        storage.ClearTokens();
        CurrentUser = null;
    }
}
