using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Options;

namespace BoilerManagement.Web.Authentication;

/// <summary>
/// No-op authentication handler registered as the default scheme so ASP.NET Core
/// middleware doesn't throw when it needs to challenge. Actual authentication is
/// handled by JwtAuthenticationStateProvider in the Blazor circuit.
/// </summary>
public class NoOpAuthHandler(
    IOptionsMonitor<AuthenticationSchemeOptions> options,
    ILoggerFactory logger,
    UrlEncoder encoder)
    : AuthenticationHandler<AuthenticationSchemeOptions>(options, logger, encoder)
{
    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
        => Task.FromResult(AuthenticateResult.NoResult());

    protected override Task HandleChallengeAsync(AuthenticationProperties properties)
        => Task.CompletedTask;

    protected override Task HandleForbiddenAsync(AuthenticationProperties properties)
        => Task.CompletedTask;
}
