using BoilerManagement.Web.Authentication;
using BoilerManagement.Web.Components;
using BoilerManagement.Web.Services;
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

// ── Authentication & Authorization ───────────────────────────────────────────
// Blazor Server authorization is handled by AuthenticationStateProvider + AuthorizeRouteView.
// We register a no-op auth scheme so middleware doesn't throw on challenge.
builder.Services.AddAuthentication("BlazorServer")
    .AddScheme<Microsoft.AspNetCore.Authentication.AuthenticationSchemeOptions,
               NoOpAuthHandler>("BlazorServer", _ => { });
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

// ── Application services ──────────────────────────────────────────────────────
builder.Services.AddScoped<AuthService>();

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

app.UseStaticFiles();
app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
