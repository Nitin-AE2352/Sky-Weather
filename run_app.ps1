$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPython = Join-Path $projectRoot "venv\Scripts\python.exe"
$backendMain = Join-Path $projectRoot "Backend\main.py"
$frontendRoot = Join-Path $projectRoot "React-Weather-App"

if (-not (Test-Path $backendPython)) {
    throw "Python virtual environment was not found at $backendPython"
}

if (-not (Test-Path $backendMain)) {
    throw "Backend entry point was not found at $backendMain"
}

if (-not (Test-Path (Join-Path $frontendRoot "package.json"))) {
    throw "React frontend was not found at $frontendRoot"
}

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "& '$backendPython' '$backendMain'"
) -WorkingDirectory $projectRoot

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command",
    "Set-Location '$frontendRoot'; npm run dev -- --host 127.0.0.1 --force"
) -WorkingDirectory $frontendRoot

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"

Write-Host "SkyCast frontend: http://127.0.0.1:5173"
Write-Host "SkyCast backend:  http://127.0.0.1:8000"
Write-Host "API docs:         http://127.0.0.1:8000/docs"
