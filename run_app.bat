@echo off
setlocal

cd /d "%~dp0"

echo Starting SkyCast backend on http://127.0.0.1:8000 ...
start "SkyCast Backend" powershell -NoExit -ExecutionPolicy Bypass -Command "& '.\venv\Scripts\python.exe' '.\Backend\main.py'"

echo Starting SkyCast frontend on http://127.0.0.1:5173 ...
start "SkyCast Frontend" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location '.\React-Weather-App'; npm run dev -- --host 127.0.0.1"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"

echo.
echo SkyCast is running.
echo Frontend: http://127.0.0.1:5173
echo Backend:  http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo.
pause
