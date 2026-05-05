param([string]$proxy_ip = "192.168.1.4")

$full_proxy = "http://${proxy_ip}:3128"

# Системные переменные
[Environment]::SetEnvironmentVariable("HTTPS_PROXY", $full_proxy, "User")
[Environment]::SetEnvironmentVariable("HTTP_PROXY", $full_proxy, "User")

# Текущая сессия PowerShell
$env:HTTPS_PROXY = $full_proxy
$env:HTTP_PROXY = $full_proxy

# Обновить settings.json в VS Code
$settings_path = "$env:APPDATA\Code\User\settings.json"
if (Test-Path $settings_path) {
    $content = Get-Content $settings_path -Raw | ConvertFrom-Json
    $content | Add-Member -NotePropertyName "http.proxy" -NotePropertyValue $full_proxy -Force
    $content | ConvertTo-Json -Depth 10 | Set-Content $settings_path
    Write-Host "VS Code settings updated"
}

Write-Host "Proxy set to: $full_proxy"
Write-Host "Перезапусти PowerShell и VS Code"