using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record MaterialDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("category_id")] int CategoryId,
    [property: JsonPropertyName("name")]        string Name,
    [property: JsonPropertyName("unit")]        string Unit,
    [property: JsonPropertyName("barcode")]     string? Barcode,
    [property: JsonPropertyName("min_stock")]   decimal MinStock,
    [property: JsonPropertyName("price")]       decimal Price);

public record WarehouseDto(
    [property: JsonPropertyName("id")]      int Id,
    [property: JsonPropertyName("name")]    string Name,
    [property: JsonPropertyName("address")] string? Address);

public record MaterialStockDto(
    [property: JsonPropertyName("id")]                int Id,
    [property: JsonPropertyName("material_id")]       int MaterialId,
    [property: JsonPropertyName("warehouse_id")]      int WarehouseId,
    [property: JsonPropertyName("quantity")]          decimal Quantity,
    [property: JsonPropertyName("reserved_quantity")] decimal ReservedQuantity);

public record MaterialMovementDto(
    [property: JsonPropertyName("id")]             int Id,
    [property: JsonPropertyName("material_id")]    int MaterialId,
    [property: JsonPropertyName("warehouse_id")]   int WarehouseId,
    [property: JsonPropertyName("movement_type")]  string MovementType,
    [property: JsonPropertyName("quantity")]       decimal Quantity,
    [property: JsonPropertyName("work_order_id")]  int? WorkOrderId,
    [property: JsonPropertyName("created_at")]     DateTime CreatedAt);

public record PurchaseRequestDto(
    [property: JsonPropertyName("id")]          int Id,
    [property: JsonPropertyName("material_id")] int MaterialId,
    [property: JsonPropertyName("quantity")]    decimal Quantity,
    [property: JsonPropertyName("status")]      string Status,
    [property: JsonPropertyName("created_at")]  DateTime CreatedAt);

public record MaterialCategoryDto(
    [property: JsonPropertyName("id")]   int Id,
    [property: JsonPropertyName("name")] string Name);
