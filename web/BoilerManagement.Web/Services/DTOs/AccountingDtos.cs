using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record OnecSendPeriodRequest(
    [property: JsonPropertyName("period")] string Period);

public record OnecSendPeriodResponse(
    [property: JsonPropertyName("period")]               string Period,
    [property: JsonPropertyName("acts_sent")]            int ActsSent,
    [property: JsonPropertyName("materials_sent")]       int MaterialsSent,
    [property: JsonPropertyName("transactions_sent")]    int TransactionsSent,
    [property: JsonPropertyName("timesheet_rows_sent")]  int TimesheetRowsSent,
    [property: JsonPropertyName("errors")]               List<string> Errors,
    [property: JsonPropertyName("success")]              bool Success);

public record GenerateReportRequest(
    [property: JsonPropertyName("report_type")] string ReportType,
    [property: JsonPropertyName("period")]      string Period);

public record GenerateReportResponse(
    [property: JsonPropertyName("id")]           int Id,
    [property: JsonPropertyName("report_type")] string ReportType,
    [property: JsonPropertyName("period")]       string Period,
    [property: JsonPropertyName("filepath")]     string Filepath,
    [property: JsonPropertyName("size_bytes")]   int SizeBytes,
    [property: JsonPropertyName("generated_at")] string GeneratedAt);

public record SubmitReportRequest(
    [property: JsonPropertyName("report_type")] string ReportType,
    [property: JsonPropertyName("period")]      string Period,
    [property: JsonPropertyName("inn")]         string Inn = "7700000001");

public record SubmitReportResponse(
    [property: JsonPropertyName("id")]              int Id,
    [property: JsonPropertyName("report_type")]     string ReportType,
    [property: JsonPropertyName("period")]          string Period,
    [property: JsonPropertyName("submission_id")]   string SubmissionId,
    [property: JsonPropertyName("receipt_number")] string ReceiptNumber,
    [property: JsonPropertyName("edo_status")]      string EdoStatus,
    [property: JsonPropertyName("message")]         string Message);

public record ReportDetailDto(
    [property: JsonPropertyName("id")]                int Id,
    [property: JsonPropertyName("report_type")]       string ReportType,
    [property: JsonPropertyName("period")]            string Period,
    [property: JsonPropertyName("inn")]               string Inn,
    [property: JsonPropertyName("generated_at")]      string GeneratedAt,
    [property: JsonPropertyName("file_path")]         string FilePath,
    [property: JsonPropertyName("file_size")]         int FileSize,
    [property: JsonPropertyName("submission_id")]     string? SubmissionId,
    [property: JsonPropertyName("receipt_number")]    string? ReceiptNumber,
    [property: JsonPropertyName("edo_status")]        string? EdoStatus,
    [property: JsonPropertyName("last_status_check")] string? LastStatusCheck);
