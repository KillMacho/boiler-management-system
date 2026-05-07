using BoilerManagement.Mobile.ViewModels;

namespace BoilerManagement.Mobile.Pages;

public partial class WorkOrdersListPage : ContentPage
{
    private readonly WorkOrdersListViewModel _vm;

    public WorkOrdersListPage(WorkOrdersListViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        BindingContext = vm;
    }

    protected override async void OnAppearing()
    {
        base.OnAppearing();
        _vm.StartPolling();
        await _vm.LoadAsync();
    }

    protected override void OnDisappearing()
    {
        base.OnDisappearing();
        _vm.StopPolling();
    }
}
