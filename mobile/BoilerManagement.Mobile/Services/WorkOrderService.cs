using BoilerManagement.Mobile.Models;

namespace BoilerManagement.Mobile.Services;

public class WorkOrderService(ApiClient api)
{
    public async Task<List<WorkOrderDto>> GetMyWorkOrdersAsync()
    {
        try
        {
            return await api.GetAsync<List<WorkOrderDto>>("/api/v1/work-orders/my") ?? [];
        }
        catch
        {
            return [];
        }
    }

    public async Task<WorkOrderDto?> GetWorkOrderAsync(int id)
    {
        try { return await api.GetAsync<WorkOrderDto>($"/api/v1/work-orders/{id}"); }
        catch { return null; }
    }

    public async Task<RequestDto?> GetRequestAsync(int requestId)
    {
        try { return await api.GetAsync<RequestDto>($"/api/v1/requests/{requestId}"); }
        catch { return null; }
    }

    public async Task<List<ChecklistItemDto>> GetChecklistAsync(int workOrderId)
    {
        try
        {
            return await api.GetAsync<List<ChecklistItemDto>>($"/api/v1/work-orders/{workOrderId}/checklist") ?? [];
        }
        catch { return []; }
    }

    public async Task<List<PhotoDto>> GetPhotosAsync(int workOrderId)
    {
        try
        {
            return await api.GetAsync<List<PhotoDto>>($"/api/v1/work-orders/{workOrderId}/photos") ?? [];
        }
        catch { return []; }
    }

    public async Task<WorkOrderDto?> StartAsync(int workOrderId)
    {
        try { return await api.PostNoBodyAsync<WorkOrderDto>($"/api/v1/work-orders/{workOrderId}/start"); }
        catch { return null; }
    }

    public async Task<WorkOrderDto?> CompleteAsync(int workOrderId, string? notes = null)
    {
        try
        {
            return await api.PostAsync<CompleteRequest, WorkOrderDto>(
                $"/api/v1/work-orders/{workOrderId}/complete",
                new CompleteRequest(notes, 0.0));
        }
        catch { return null; }
    }

    public async Task<ChecklistItemDto?> ToggleChecklistItemAsync(int workOrderId, int itemId, bool isCompleted)
    {
        try
        {
            return await api.PostAsync<ChecklistToggleRequest, ChecklistItemDto>(
                $"/api/v1/work-orders/{workOrderId}/checklist/{itemId}",
                new ChecklistToggleRequest(isCompleted));
        }
        catch { return null; }
    }

    public async Task<PhotoDto?> UploadPhotoAsync(int workOrderId, Stream photoStream, string fileName)
    {
        try
        {
            var content = new MultipartFormDataContent();
            var streamContent = new StreamContent(photoStream);
            streamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");
            content.Add(streamContent, "file", fileName);
            return await api.PostMultipartAsync<PhotoDto>($"/api/v1/work-orders/{workOrderId}/photos", content);
        }
        catch { return null; }
    }
}
