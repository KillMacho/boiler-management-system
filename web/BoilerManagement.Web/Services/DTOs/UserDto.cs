namespace BoilerManagement.Web.Services.DTOs;

public record UserInfo(
    int Id,
    string Username,
    string FullName,
    string Email,
    List<string> Roles);
