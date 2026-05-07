using CommunityToolkit.Maui;
using Microsoft.Extensions.Logging;
using BoilerManagement.Mobile.Services;
using BoilerManagement.Mobile.ViewModels;
using BoilerManagement.Mobile.Pages;

namespace BoilerManagement.Mobile;

public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .UseMauiCommunityToolkit()
            .ConfigureFonts(fonts => { });

        // Services
        builder.Services.AddSingleton<SecureStorageService>();
        builder.Services.AddSingleton<ApiClient>();
        builder.Services.AddSingleton<AuthService>();
        builder.Services.AddSingleton<WorkOrderService>();

        // ViewModels
        builder.Services.AddTransient<LoginViewModel>();
        builder.Services.AddTransient<WorkOrdersListViewModel>();
        builder.Services.AddTransient<WorkOrderDetailViewModel>();
        builder.Services.AddTransient<ProfileViewModel>();

        // Pages
        builder.Services.AddTransient<LoginPage>();
        builder.Services.AddTransient<WorkOrdersListPage>();
        builder.Services.AddTransient<WorkOrderDetailPage>();
        builder.Services.AddTransient<ProfilePage>();

#if DEBUG
        builder.Logging.AddDebug();
#endif

        return builder.Build();
    }
}
