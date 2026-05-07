using BoilerManagement.Mobile.Services;

namespace BoilerManagement.Mobile;

public partial class App : Application
{
    private readonly AuthService _authService;

    public App(AuthService authService)
    {
        InitializeComponent();
        _authService = authService;
    }

    protected override Window CreateWindow(IActivationState? activationState)
    {
        return new Window(new AppShell());
    }

    protected override async void OnStart()
    {
        base.OnStart();
        await TryAutoLoginAsync();
    }

    private async Task TryAutoLoginAsync()
    {
        var restored = await _authService.TryRestoreSessionAsync();
        if (restored)
        {
            await Shell.Current.GoToAsync("//main/workorders");
        }
    }
}
