using BoilerManagement.Mobile.Pages;

namespace BoilerManagement.Mobile;

public partial class AppShell : Shell
{
    public AppShell()
    {
        InitializeComponent();

        Routing.RegisterRoute("workorderdetail", typeof(WorkOrderDetailPage));
    }
}
