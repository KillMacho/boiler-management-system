using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using BoilerManagement.Mobile.Models;
using BoilerManagement.Mobile.Services;

namespace BoilerManagement.Mobile.ViewModels;

public partial class WorkOrdersListViewModel(WorkOrderService workOrderService) : BaseViewModel
{
    public ObservableCollection<WorkOrderDisplayItem> WorkOrders { get; } = [];

    [ObservableProperty]
    private bool _showOnlyActive = true;

    [ObservableProperty]
    private bool _isRefreshing = false;

    [ObservableProperty]
    private string _emptyMessage = "Нет активных нарядов";

    private List<WorkOrderDisplayItem> _allItems = [];
    private Timer? _pollTimer;

    public void StartPolling()
    {
        _pollTimer ??= new Timer(_ => MainThread.BeginInvokeOnMainThread(async () =>
        {
            await LoadOrdersAsync(silent: true);
        }), null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
    }

    public void StopPolling() => _pollTimer?.Change(Timeout.Infinite, Timeout.Infinite);

    [RelayCommand]
    public async Task LoadAsync()
    {
        IsBusy = true;
        await LoadOrdersAsync();
        IsBusy = false;
    }

    [RelayCommand]
    private async Task RefreshAsync()
    {
        IsRefreshing = true;
        await LoadOrdersAsync();
        IsRefreshing = false;
    }

    private async Task LoadOrdersAsync(bool silent = false)
    {
        try
        {
            var orders = await workOrderService.GetMyWorkOrdersAsync();
            var items = new List<WorkOrderDisplayItem>();

            foreach (var wo in orders)
            {
                var request = await workOrderService.GetRequestAsync(wo.RequestId);
                items.Add(new WorkOrderDisplayItem { WorkOrder = wo, Request = request });
            }

            var prevCount = _allItems.Count;
            _allItems = items;
            ApplyFilter();

            if (!silent && items.Count > prevCount)
            {
                // New work order appeared — could trigger local notification
                HapticFeedback.Default.Perform(HapticFeedbackType.LongPress);
            }
        }
        catch
        {
            // Network error - keep old data
        }
    }

    partial void OnShowOnlyActiveChanged(bool value) => ApplyFilter();

    private void ApplyFilter()
    {
        WorkOrders.Clear();
        var filtered = ShowOnlyActive
            ? _allItems.Where(x => x.IsActive)
            : _allItems;

        foreach (var item in filtered.OrderByDescending(x => x.WorkOrder.AssignedAt))
            WorkOrders.Add(item);

        EmptyMessage = ShowOnlyActive ? "Нет активных нарядов" : "Нет нарядов";
    }

    [RelayCommand]
    private async Task OpenDetailAsync(WorkOrderDisplayItem item)
    {
        await Shell.Current.GoToAsync($"workorderdetail?id={item.WorkOrder.Id}");
    }
}
