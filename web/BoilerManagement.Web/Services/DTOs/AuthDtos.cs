namespace BoilerManagement.Web.Services.DTOs;

public record LoginRequest(string Username, string Password);

public record LoginResponse(
    string AccessToken,
    string RefreshToken,
    string TokenType,
    UserInfo User);

public record RefreshRequest(string RefreshToken);

public record RefreshResponse(
    string AccessToken,
    string RefreshToken,
    string TokenType);
