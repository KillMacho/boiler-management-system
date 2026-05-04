using System.Security.Claims;
using BoilerManagement.Web.Services;
using Microsoft.AspNetCore.Components.Authorization;

namespace BoilerManagement.Web.Authentication;

public class JwtAuthenticationStateProvider(
    TokenStorageService tokenStorage,
    ILogger<JwtAuthenticationStateProvider> logger) : AuthenticationStateProvider
{
    private static readonly AuthenticationState Anonymous =
        new(new ClaimsPrincipal(new ClaimsIdentity()));

    public override async Task<AuthenticationState> GetAuthenticationStateAsync()
    {
        var token = await tokenStorage.GetAccessTokenAsync();
        var principal = JwtTokenHandler.ParseToken(token);

        if (principal is null)
        {
            logger.LogDebug("No valid token — returning anonymous state");
            return Anonymous;
        }

        logger.LogDebug("Valid token for user {User}", principal.Identity?.Name);
        return new AuthenticationState(principal);
    }

    public void NotifyUserAuthentication(string accessToken)
    {
        var principal = JwtTokenHandler.ParseToken(accessToken);
        var state = principal is not null
            ? new AuthenticationState(principal)
            : Anonymous;
        NotifyAuthenticationStateChanged(Task.FromResult(state));
    }

    public void NotifyUserLogout()
    {
        NotifyAuthenticationStateChanged(Task.FromResult(Anonymous));
    }
}
