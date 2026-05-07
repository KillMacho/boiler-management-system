using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using BoilerManagement.Mobile.Models;
using BoilerManagement.Mobile.Services;

namespace BoilerManagement.Mobile.ViewModels;

public partial class ProfileViewModel(AuthService authService, ApiClient api) : BaseViewModel
{
    [ObservableProperty]
    private UserDto? _user;

    [ObservableProperty]
    private string _userRoles = "";

    [ObservableProperty]
    private string _serverUrl = ApiClient.BaseUrl;

    [RelayCommand]
    public async Task LoadAsync()
    {
        IsBusy = true;
        try
        {
            User = await api.GetAsync<UserDto>("/api/auth/me");
            if (User is not null)
            {
                Title = User.Username;
                UserRoles = User.Roles.Count > 0 ? string.Join(", ", User.Roles) : "—";
            }
        }
        catch
        {
            // keep old data
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand]
    private async Task LogoutAsync()
    {
        var confirm = await Shell.Current.DisplayAlertAsync(
            "Выход", "Выйти из аккаунта?", "Выйти", "Отмена");
        if (!confirm) return;

        authService.Logout();
        await Shell.Current.GoToAsync("//login");
    }
}
