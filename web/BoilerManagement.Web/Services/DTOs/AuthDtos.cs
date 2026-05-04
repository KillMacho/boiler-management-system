using System.Text.Json.Serialization;

namespace BoilerManagement.Web.Services.DTOs;

public record LoginRequest(string Username, string Password);

public record LoginResponse(
    [property: JsonPropertyName("access_token")]  string AccessToken,
    [property: JsonPropertyName("refresh_token")] string RefreshToken,
    [property: JsonPropertyName("token_type")]    string TokenType,
    [property: JsonPropertyName("user")]          UserInfo User);

public record RefreshRequest(
    [property: JsonPropertyName("refresh_token")] string RefreshToken);

public record RefreshResponse(
    [property: JsonPropertyName("access_token")]  string AccessToken,
    [property: JsonPropertyName("refresh_token")] string RefreshToken,
    [property: JsonPropertyName("token_type")]    string TokenType);
