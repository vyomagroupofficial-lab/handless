@echo off
cd /d "%~dp0"
title Vyoma Handless - Desktop Studio
echo ============================================================
echo   Vyoma Handless - Desktop AI Copilot
echo   Groq Whisper Large v3 ^| AI Sidebar ^| pywinauto UIA
echo ============================================================
echo.

set "PY_EXE=.venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    echo [WARNING] Virtual environment not found at .venv. Attempting system Python...
    set "PY_EXE=python"
)

echo Starting application...
"%PY_EXE%" -m handless.app %*
if %errorlevel% neq 0 (
    echo.
    echo Application exited with code %errorlevel%. Press any key to close.
    pause >nul
)
