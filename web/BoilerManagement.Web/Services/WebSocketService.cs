using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public enum WsConnectionState { Disconnected, Connecting, Connected, Reconnecting }

public class WebSocketService(
    TokenStorageService tokenStorage,
    IHttpClientFactory httpClientFactory,
    ILogger<WebSocketService> logger) : IAsyncDisposable
{
    private ClientWebSocket? _ws;
    private CancellationTokenSource? _cts;
    private readonly Uri _baseUri = new("ws://localhost:8000");

    public WsConnectionState State { get; private set; } = WsConnectionState.Disconnected;

    public event Action<WsTelemetryUpdate>? OnTelemetryUpdate;
    public event Action<WsFullStatus>? OnFullStatus;
    public event Action<WsConnectionState>? OnStateChanged;

    public async Task ConnectAsync()
    {
        if (State == WsConnectionState.Connected || State == WsConnectionState.Connecting)
            return;

        _cts = new CancellationTokenSource();
        _ = RunWithReconnectAsync(_cts.Token);
        await Task.CompletedTask;
    }

    // Returns a fresh access token, refreshing if needed. Returns null if no token available.
    private async Task<string?> GetFreshTokenAsync()
    {
        var token = await tokenStorage.GetAccessTokenAsync();
        if (!string.IsNullOrEmpty(token)) return token;

        // No access token — try refresh
        return await TryRefreshAsync();
    }

    private async Task<string?> TryRefreshAsync()
    {
        var refreshToken = await tokenStorage.GetRefreshTokenAsync();
        if (string.IsNullOrEmpty(refreshToken)) return null;
        try
        {
            var bare = httpClientFactory.CreateClient("bare");
            var resp = await bare.PostAsJsonAsync("/api/auth/refresh", new RefreshRequest(refreshToken));
            if (!resp.IsSuccessStatusCode) { await tokenStorage.ClearTokensAsync(); return null; }
            var body = await resp.Content.ReadFromJsonAsync<RefreshResponse>();
            if (body is null) { await tokenStorage.ClearTokensAsync(); return null; }
            await tokenStorage.SetTokensAsync(body.AccessToken, body.RefreshToken);
            logger.LogInformation("WS: token refreshed successfully");
            return body.AccessToken;
        }
        catch
        {
            await tokenStorage.ClearTokensAsync();
            return null;
        }
    }

    private async Task RunWithReconnectAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            SetState(WsConnectionState.Connecting);
            try
            {
                var token = await GetFreshTokenAsync();
                if (string.IsNullOrEmpty(token))
                {
                    logger.LogWarning("WS: no access token, waiting 5s");
                    await Task.Delay(5000, ct);
                    continue;
                }

                _ws?.Dispose();
                _ws = new ClientWebSocket();
                var uri = new Uri(_baseUri, $"/ws/monitoring?token={Uri.EscapeDataString(token)}");
                await _ws.ConnectAsync(uri, ct);

                SetState(WsConnectionState.Connected);
                logger.LogInformation("WS connected");

                await ReceiveLoopAsync(_ws, ct);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;
            }
            catch (WebSocketException ex) when (ex.Message.Contains("403") || ex.Message.Contains("401"))
            {
                // Token rejected — try refreshing before next attempt
                logger.LogWarning("WS: auth rejected, refreshing token and retrying in 5s");
                await TryRefreshAsync();
            }
            catch (Exception ex)
            {
                logger.LogWarning(ex, "WS connection lost, reconnecting in 5s");
            }

            if (!ct.IsCancellationRequested)
            {
                SetState(WsConnectionState.Reconnecting);
                try { await Task.Delay(5000, ct); } catch (OperationCanceledException) { break; }
            }
        }

        SetState(WsConnectionState.Disconnected);
    }

    private async Task ReceiveLoopAsync(ClientWebSocket ws, CancellationToken ct)
    {
        var buffer = new byte[64 * 1024];
        var sb = new StringBuilder();

        while (ws.State == WebSocketState.Open && !ct.IsCancellationRequested)
        {
            sb.Clear();
            WebSocketReceiveResult result;
            do
            {
                result = await ws.ReceiveAsync(buffer, ct);
                if (result.MessageType == WebSocketMessageType.Close) return;
                sb.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
            } while (!result.EndOfMessage);

            var text = sb.ToString();
            if (text == "pong") continue;

            try { ProcessMessage(text); }
            catch (Exception ex) { logger.LogWarning(ex, "WS: failed to parse message"); }
        }
    }

    private void ProcessMessage(string json)
    {
        using var doc = JsonDocument.Parse(json);
        var type = doc.RootElement.GetProperty("type").GetString();

        switch (type)
        {
            case "full_status":
                var full = JsonSerializer.Deserialize<WsFullStatus>(json);
                if (full is not null) OnFullStatus?.Invoke(full);
                break;
            case "telemetry_update":
                var update = JsonSerializer.Deserialize<WsTelemetryUpdate>(json);
                if (update is not null) OnTelemetryUpdate?.Invoke(update);
                break;
            case "heartbeat":
                break;
        }
    }

    public async Task DisconnectAsync()
    {
        _cts?.Cancel();
        if (_ws?.State == WebSocketState.Open)
        {
            try { await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye", CancellationToken.None); }
            catch { /* ignore */ }
        }
        SetState(WsConnectionState.Disconnected);
    }

    private void SetState(WsConnectionState state)
    {
        State = state;
        OnStateChanged?.Invoke(state);
    }

    public async ValueTask DisposeAsync()
    {
        await DisconnectAsync();
        _ws?.Dispose();
        _cts?.Dispose();
    }
}
