using System.Net.Http.Json;
using BoilerManagement.Web.Authentication;
using BoilerManagement.Web.Services.DTOs;
using Microsoft.AspNetCore.Components;
using MudBlazor;

namespace BoilerManagement.Web.Services;

public class AuthService(
    ApiClient api,
    TokenStorageService tokenStorage,
    JwtAuthenticationStateProvider authStateProvider,
    NavigationManager navigation,
    ISnackbar snackbar,
    ILogger<AuthService> logger)
{
    private UserInfo? _currentUser;

    public UserInfo? CurrentUser => _currentUser;

    public async Task<bool> LoginAsync(string username, string password)
    {
        try
        {
            // Backend expects OAuth2 form-data
            var formData = new FormUrlEncodedContent([
                new("username", username),
                new("password", password),
            ]);

            var resp = await api.Http.PostAsync("/api/auth/login", formData);
            if (!resp.IsSuccessStatusCode)
            {
                var err = await resp.Content.ReadAsStringAsync();
                logger.LogWarning("Login failed for {User}: {Status} {Err}", username, resp.StatusCode, err);
                snackbar.Add("Неверный логин или пароль", Severity.Error);
                return false;
            }

            var body = await resp.Content.ReadFromJsonAsync<LoginResponse>();
            if (body is null)
            {
                snackbar.Add("Ошибка сервера: пустой ответ", Severity.Error);
                return false;
            }

            await tokenStorage.SetTokensAsync(body.AccessToken, body.RefreshToken);
            _currentUser = body.User;
            authStateProvider.NotifyUserAuthentication(body.AccessToken);

            logger.LogInformation("User {User} logged in", username);
            snackbar.Add($"Добро пожаловать, {body.User.FullName}!", Severity.Success);
            return true;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Login exception for {User}", username);
            snackbar.Add("Ошибка соединения с сервером", Severity.Error);
            return false;
        }
    }

    public async Task LogoutAsync()
    {
        try
        {
            await api.Http.PostAsync("/api/auth/logout", null);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Logout API call failed — clearing tokens anyway");
        }

        await tokenStorage.ClearTokensAsync();
        _currentUser = null;
        authStateProvider.NotifyUserLogout();
        logger.LogInformation("User logged out");
        navigation.NavigateTo("/login", forceLoad: false);
    }

    public async Task<UserInfo?> GetCurrentUserAsync()
    {
        if (_currentUser is not null) return _currentUser;
        try
        {
            _currentUser = await api.GetAsync<UserInfo>("/api/auth/me");
            return _currentUser;
        }
        catch
        {
            return null;
        }
    }

    public void ClearCachedUser() => _currentUser = null;
}
