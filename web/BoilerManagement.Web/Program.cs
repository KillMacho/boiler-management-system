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
// Named clients — handler is resolved from the circuit scope via IServiceProvider
builder.Services.AddHttpClient("api", client =>
{
    client.BaseAddress = new Uri(apiBaseUrl);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// Bare client for auth endpoints (no token handler — used during login/refresh)
builder.Services.AddHttpClient("bare", client =>
{
    client.BaseAddress = new Uri(apiBaseUrl);
    client.DefaultRequestHeaders.Add("Accept", "application/json");
});

// ApiClient is Scoped — it holds a long-lived HttpClient and injects the Bearer
// token itself on every request using the scoped TokenStorageService.
builder.Services.AddScoped<ApiClient>(sp =>
{
    var factory = sp.GetRequiredService<IHttpClientFactory>();
    var http = factory.CreateClient("api");
    var tokenStorage = sp.GetRequiredService<TokenStorageService>();
    var logger = sp.GetRequiredService<ILogger<ApiClient>>();
    return new ApiClient(http, tokenStorage, logger);
});

// ── Application services ──────────────────────────────────────────────────────
builder.Services.AddScoped<AuthService>();
builder.Services.AddScoped<MonitoringService>();
builder.Services.AddScoped<WebSocketService>();
builder.Services.AddScoped<RequestsService>();
builder.Services.AddScoped<WorkOrdersService>();
builder.Services.AddScoped<WarehouseService>();
builder.Services.AddScoped<EquipmentService>();
builder.Services.AddScoped<MaintenanceService>();
builder.Services.AddScoped<PersonnelService>();
builder.Services.AddScoped<AuditService>();

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
