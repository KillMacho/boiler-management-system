# start-all.ps1
$root = $PSScriptRoot

Write-Host "Starting all services..." -ForegroundColor Green

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

# Simulator
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\simulator'; .\.venv\Scripts\Activate.ps1; python -m app.main"

# Mock 1C
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\mock-services\onec-mock'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8080"

# Mock EDO
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\mock-services\edo-mock'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8081"

# Blazor (раскомментируй после Дня 8)
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$root\web\BoilerManagement.Web'; dotnet run --urls http://localhost:5000"

Write-Host "All services started in separate windows" -ForegroundColor Green