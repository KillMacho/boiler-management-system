using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using BoilerManagement.Web.Services.DTOs;

namespace BoilerManagement.Web.Services;

public enum WsConnectionState { Disconnected, Connecting, Connected, Reconnecting }

public class WebSocketService(
    TokenStorageService tokenStorage,
    ILogger<WebSocketService> logger) : IAsyncDisposable
{
    private ClientWebSocket? _ws;
    private CancellationTokenSource? _cts;
    private Task? _receiveTask;
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

    private async Task RunWithReconnectAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested)
        {
            SetState(WsConnectionState.Connecting);
            try
            {
                var token = await tokenStorage.GetAccessTokenAsync();
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
                logger.LogInformation("WS connected to {Uri}", uri);

                await ReceiveLoopAsync(_ws, ct);
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;
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
