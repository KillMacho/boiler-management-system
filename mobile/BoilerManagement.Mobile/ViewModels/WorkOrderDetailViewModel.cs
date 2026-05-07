using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using BoilerManagement.Mobile.Models;
using BoilerManagement.Mobile.Services;

namespace BoilerManagement.Mobile.ViewModels;

[QueryProperty(nameof(WorkOrderId), "id")]
public partial class WorkOrderDetailViewModel(WorkOrderService workOrderService) : BaseViewModel
{
    [ObservableProperty]
    private int _workOrderId;

    [ObservableProperty]
    private WorkOrderDto? _workOrder;

    [ObservableProperty]
    private RequestDto? _request;

    [ObservableProperty]
    private bool _canStart;

    [ObservableProperty]
    private bool _canComplete;

    [ObservableProperty]
    private string _checklistProgress = "0 / 0";

    [ObservableProperty]
    private bool _isUploadingPhoto = false;

    public ObservableCollection<ChecklistItemViewModel> ChecklistItems { get; } = [];
    public ObservableCollection<PhotoDto> Photos { get; } = [];

    partial void OnWorkOrderIdChanged(int value)
    {
        MainThread.BeginInvokeOnMainThread(async () => await LoadAsync());
    }

    [RelayCommand]
    public async Task LoadAsync()
    {
        if (WorkOrderId == 0) return;
        IsBusy = true;

        try
        {
            WorkOrder = await workOrderService.GetWorkOrderAsync(WorkOrderId);
            if (WorkOrder is null) return;

            Request = await workOrderService.GetRequestAsync(WorkOrder.RequestId);
            Title = $"Наряд #{WorkOrder.Id}";

            CanStart    = WorkOrder.Status == "assigned";
            CanComplete = WorkOrder.Status == "in_progress";

            // Load checklist
            ChecklistItems.Clear();
            var items = await workOrderService.GetChecklistAsync(WorkOrderId);
            foreach (var item in items.OrderBy(x => x.SortOrder))
                ChecklistItems.Add(ChecklistItemViewModel.FromDto(item));

            UpdateChecklistProgress();

            // Load photos
            Photos.Clear();
            var photos = await workOrderService.GetPhotosAsync(WorkOrderId);
            foreach (var p in photos) Photos.Add(p);
        }
        finally
        {
            IsBusy = false;
        }
    }

    [RelayCommand]
    private async Task StartWorkAsync()
    {
        var confirm = await Shell.Current.DisplayAlertAsync(
            "Начать работу", $"Начать выполнение наряда #{WorkOrderId}?", "Начать", "Отмена");
        if (!confirm) return;

        IsBusy = true;
        var updated = await workOrderService.StartAsync(WorkOrderId);
        if (updated is not null)
        {
            WorkOrder = updated;
            CanStart    = false;
            CanComplete = true;
        }
        else
        {
            await Shell.Current.DisplayAlertAsync("Ошибка", "Не удалось начать наряд", "OK");
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task CompleteWorkAsync()
    {
        var incomplete = ChecklistItems.Count(x => !x.IsCompleted);
        if (incomplete > 0)
        {
            var proceed = await Shell.Current.DisplayAlertAsync(
                "Незавершённые пункты",
                $"Есть {incomplete} незавершённых пунктов чек-листа. Завершить наряд?",
                "Завершить", "Отмена");
            if (!proceed) return;
        }
        else
        {
            var confirm = await Shell.Current.DisplayAlertAsync(
                "Завершить наряд", "Все работы выполнены?", "Завершить", "Отмена");
            if (!confirm) return;
        }

        IsBusy = true;
        var updated = await workOrderService.CompleteAsync(WorkOrderId);
        if (updated is not null)
        {
            WorkOrder = updated;
            CanStart    = false;
            CanComplete = false;
            await Shell.Current.DisplayAlertAsync("Готово", "Наряд завершён", "OK");
            await Shell.Current.GoToAsync("..");
        }
        else
        {
            await Shell.Current.DisplayAlertAsync("Ошибка", "Не удалось завершить наряд", "OK");
        }
        IsBusy = false;
    }

    [RelayCommand]
    private async Task ToggleChecklistItemAsync(ChecklistItemViewModel item)
    {
        var newValue = !item.IsCompleted;
        var result = await workOrderService.ToggleChecklistItemAsync(WorkOrderId, item.Id, newValue);
        if (result is not null)
        {
            item.IsCompleted = result.IsCompleted;
            UpdateChecklistProgress();
        }
    }

    [RelayCommand]
    private async Task TakePhotoAsync()
    {
        try
        {
            if (!MediaPicker.Default.IsCaptureSupported)
            {
                await Shell.Current.DisplayAlertAsync("Ошибка", "Камера недоступна", "OK");
                return;
            }

            var photo = await MediaPicker.Default.CapturePhotoAsync();
            if (photo is null) return;

            IsUploadingPhoto = true;
            await using var stream = await photo.OpenReadAsync();
            var result = await workOrderService.UploadPhotoAsync(WorkOrderId, stream, photo.FileName);
            if (result is not null)
            {
                Photos.Insert(0, result);
            }
            else
            {
                await Shell.Current.DisplayAlertAsync("Ошибка", "Не удалось загрузить фото", "OK");
            }
        }
        catch (Exception ex)
        {
            await Shell.Current.DisplayAlertAsync("Ошибка", ex.Message, "OK");
        }
        finally
        {
            IsUploadingPhoto = false;
        }
    }

    private void UpdateChecklistProgress()
    {
        var done  = ChecklistItems.Count(x => x.IsCompleted);
        var total = ChecklistItems.Count;
        ChecklistProgress = $"{done} / {total}";
    }
}
