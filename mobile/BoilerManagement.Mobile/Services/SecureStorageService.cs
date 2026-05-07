namespace BoilerManagement.Mobile.Services;

public class SecureStorageService
{
    private const string AccessTokenKey  = "access_token";
    private const string RefreshTokenKey = "refresh_token";

    public async Task<string?> GetAccessTokenAsync()  => await SecureStorage.GetAsync(AccessTokenKey);
    public async Task<string?> GetRefreshTokenAsync() => await SecureStorage.GetAsync(RefreshTokenKey);

    public async Task SetTokensAsync(string accessToken, string refreshToken)
    {
        await SecureStorage.SetAsync(AccessTokenKey, accessToken);
        await SecureStorage.SetAsync(RefreshTokenKey, refreshToken);
    }

    public void ClearTokens()
    {
        SecureStorage.Remove(AccessTokenKey);
        SecureStorage.Remove(RefreshTokenKey);
    }
}
