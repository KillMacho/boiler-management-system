using BoilerManagement.Web.Authentication;
using BoilerManagement.Web.Components;
using BoilerManagement.Web.Services;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.AspNetCore.Components.Server.ProtectedBrowserStorage;
using MudBlazor.Services;

var builder = WebApplication.CreateBuilder(args);

// ── Configuration ─────────────────────────────────────────────────────────────
var apiBaseUrl = builder.Configuration["ApiBaseUrl"]
    ?? throw new InvalidOperationException("ApiBaseUrl is not configured");

// ── Razor + Blazor Server ─────────────────────────────────────────────────────
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

// ── Authentication & Authorization ────────────────────────────────────────────
// ASP.NET Core middleware needs a registered IAuthenticationService to handle
// the HTTP-level authorization challenge on the initial SSR request.
// The actual JWT auth lives inside the Blazor SignalR circuit via
// JwtAuthenticationStateProvider — the cookie scheme here only handles the
// HTTP challenge redirect so we get /login instead of 500.
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(options =>
    {
        options.LoginPath = "/login";
        options.AccessDeniedPath = "/access-denied";
    });
builder.Services.AddAuthorization();
builder.Services.AddCascadingAuthenticationState();

builder.Services.AddScoped<AuthenticationStateProvider, JwtAuthenticationStateProvider>();
builder.Services.AddScoped<JwtAuthenticationStateProvider>(sp =>
    (JwtAuthenticationStateProvider)sp.GetRequiredService<AuthenticationStateProvider>());

// ── Browser Storage ───────────────────────────────────────────────────────────
builder.Services.AddScoped<ProtectedSessionStorage>();
builder.Services.AddScoped<ProtectedLocalStorage>();
builder.Services.AddScoped<TokenStorageService>();

// ── HttpClient with auth handler ──────────────────────────────────────────────
builder.Services.AddScoped<AuthTokenHandler>();

builder.Services.AddHttpClient<ApiClient>(client =>
{
    client.BaseAddress = new Uri(apiBaseUrl);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
})
.AddHttpMessageHandler<AuthTokenHandler>();

// Bare client for auth endpoints (no token handler — used during login/refresh)
builder.Services.AddHttpClient("bare", client =>
{
    client.BaseAddress = new Uri(apiBaseUrl);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// ── Application services ──────────────────────────────────────────────────────
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<MonitoringService>();
builder.Services.AddScoped<WebSocketService>();

// ── MudBlazor ─────────────────────────────────────────────────────────────────
builder.Services.AddMudServices(config =>
{
    config.SnackbarConfiguration.PositionClass = MudBlazor.Defaults.Classes.Position.BottomRight;
    config.SnackbarConfiguration.PreventDuplicates = false;
    config.SnackbarConfiguration.VisibleStateDuration = 4000;
});

// ── Logging ───────────────────────────────────────────────────────────────────
builder.Logging.AddConsole();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
}

app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
