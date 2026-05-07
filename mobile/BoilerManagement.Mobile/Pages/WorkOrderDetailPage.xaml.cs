using BoilerManagement.Mobile.ViewModels;

namespace BoilerManagement.Mobile.Pages;

public partial class WorkOrderDetailPage : ContentPage
{
    private readonly WorkOrderDetailViewModel _vm;

    public WorkOrderDetailPage(WorkOrderDetailViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        BindingContext = vm;
    }
}
