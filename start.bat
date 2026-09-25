@echo off
echo.
echo ============================================================
echo   VietDub Auto - Khoi dong he thong
echo ============================================================
echo.

REM Kiem tra FFmpeg
where ffmpeg >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] FFmpeg chua duoc cai dat!
    echo     Chay lenh sau de cai dat:
    echo     winget install ffmpeg
    echo     Hoac tai tai: https://ffmpeg.org/download.html
    pause
    exit /b 1
)

REM Kiem tra .env
if not exist "backend\.env" (
    echo [!] Chua co file .env
    copy .env.example backend\.env
    echo [+] Da tao backend\.env tu .env.example
    echo [!] Hay mo backend\.env va dien API keys truoc khi chay!
    notepad backend\.env
    pause
)

echo [+] Khoi dong FastAPI backend...
cd backend
start "VietDub Backend" cmd /k "python api/server.py"
cd ..

timeout /t 2 /nobreak >nul

echo [+] Mo Web UI...
start "" "frontend\index.html"

echo.
echo ============================================================
echo  Backend dang chay tai: http://localhost:8000
echo  Web UI: frontend/index.html
echo ============================================================
echo.
echo Nhan phim bat ky de dong cua so nay...
pause >nul
